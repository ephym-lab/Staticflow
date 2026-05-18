from typing import Any, Dict, Optional, Union, List
import asyncio
from ..schemas.base import StaticPayload
from ..exceptions import (
    RequestValidationError, 
    ResponseValidationError, 
    HookError
)
from .routing import RouteDefinition, FanOutRouteDefinition
from .proxy import ProxyHandler

class FlowEngine:
    """
    The core engine that orchestrates the request flow:
    Extraction -> Hooks -> Proxy -> Validation
    Supports both single-action and multi-action fan-out routes.
    """
    def __init__(self, proxy: ProxyHandler):
        self.proxy = proxy

    async def process(
        self, 
        payload: StaticPayload, 
        route: Union[RouteDefinition, FanOutRouteDefinition], 
        incoming_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        if isinstance(route, FanOutRouteDefinition):
            return await self._process_fanout(payload, route, incoming_headers, **kwargs)
        return await self._process_single(payload, route, incoming_headers, **kwargs)

    async def _process_fanout(
        self, 
        payload: StaticPayload, 
        fanout_route: FanOutRouteDefinition, 
        incoming_headers: Optional[Dict[str, str]],
        **kwargs
    ) -> Any:
        print(f"--- [Fan-out] Executing {len(fanout_route.routes)} parallel requests for {fanout_route.action} ---")
        
        # Concurrency control: prevent overwhelming upstream services
        concurrency_limit = kwargs.get("max_concurrency", 20)
        sem = asyncio.Semaphore(concurrency_limit)
        
        async def controlled_task(r):
            async with sem:
                return await self._process_single(payload, r, incoming_headers, **kwargs)

        # Use TaskGroup for structured concurrency
        # This ensures that if one task fails, the others are properly cleaned up.
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for r in fanout_route.routes:
                tasks.append(tg.create_task(controlled_task(r)))
        
        results = [t.result() for t in tasks]

        # Merge results
        if fanout_route.merge_hook:
            return await self._maybe_await(fanout_route.merge_hook(results, **kwargs))
        
        # Default merge strategy: Merge dicts
        merged = {}
        for res in results:
            if isinstance(res, dict):
                merged.update(res)
            elif hasattr(res, "model_dump"):
                merged.update(res.model_dump())
        return merged

    async def _process_single(
        self, 
        payload: StaticPayload, 
        route: RouteDefinition, 
        incoming_headers: Optional[Dict[str, str]],
        **kwargs
    ) -> Any:
        # 1. Extraction (Plucking)
        data = payload
        if route.extract:
            data = payload.pluck(route.extract)
            if data is None:
                pass

        # 2. Before Request Hook (Business Logic)
        if route.before_request:
            try:
                data = await self._maybe_await(route.before_request(data, **kwargs))
            except Exception as e:
                raise HookError(f"Error in before_request hook: {str(e)}") from e

        # 3. Request Validation
        if route.request_model:
            try:
                data = route.request_model.model_validate(data)
            except Exception as e:
                raise RequestValidationError(str(e)) from e

        # Prepare request components
        request_json = data.model_dump() if hasattr(data, "model_dump") else data
        upstream_headers = {}
        upstream_params = {}
        
        # Keep a copy of the request dictionary for dynamic path parameter formatting
        path_format_data = request_json if isinstance(request_json, dict) else {}

        # For GET requests, the 'data' is typically query parameters
        if route.method.upper() == "GET" and isinstance(request_json, dict):
            upstream_params.update(request_json)
            request_json = None # No body for GET
        
        if hasattr(route, "auth") and route.auth:
            # Note: request_json might be None here for GET
            effective_base = route.base_url or self.proxy.base_url
            upstream_headers, upstream_params, request_json = await route.auth.apply(
                incoming_headers or {},
                upstream_headers,
                upstream_params,
                request_json or {},
                base_url=effective_base,
                **kwargs
            )

        # 4. Proxy Call (or Mock)
        if route.mock_data is not None:
            print(f"--- [Mock Mode] Returning mock data for {route.action} ---")
            response_data = route.mock_data
        else:
            # Handle Dynamic Path Templates (e.g., /members/{id})
            formatted_path = route.path
            if "{" in formatted_path and "}" in formatted_path:
                try:
                    formatted_path = formatted_path.format(**path_format_data)
                    # Clean up path parameters from query parameters
                    for key in path_format_data:
                        if f"{{{key}}}" in route.path:
                            upstream_params.pop(key, None)
                except Exception:
                    pass # Fallback to original path if formatting fails

            if hasattr(route, "resilience") and route.resilience:
                response = await route.resilience.execute(
                    self.proxy.request,
                    method=route.method,
                    path=formatted_path,
                    json_data=request_json,
                    headers=upstream_headers,
                    params=upstream_params,
                    request_format=route.request_format,
                    base_url=route.base_url
                )
            else:
                response = await self.proxy.request(
                    method=route.method,
                    path=formatted_path,
                    json_data=request_json,
                    headers=upstream_headers,
                    params=upstream_params,
                    request_format=route.request_format,
                    base_url=route.base_url
                )
            
            # Check for HTTP errors
            response.raise_for_status()
            response_data = response.json()

        # 5. After Response Hook
        if route.after_response:
            try:
                response_data = await self._maybe_await(route.after_response(response_data, **kwargs))
            except Exception as e:
                raise HookError(f"Error in after_response hook: {str(e)}") from e

        # 6. Response Validation
        if route.response_model:
            try:
                response_data = route.response_model.model_validate(response_data)
            except Exception as e:
                raise ResponseValidationError(str(e)) from e

        return response_data

    async def _maybe_await(self, result: Any) -> Any:
        import inspect
        if inspect.isawaitable(result):
            return await result
        return result
