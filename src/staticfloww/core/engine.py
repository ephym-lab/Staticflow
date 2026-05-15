from typing import Any, Optional
from ..schemas.base import StaticPayload, Section
from .routing import RouteDefinition
from .proxy import ProxyHandler
from ..exceptions import (
    StaticflowwError, 
    ExtractionError, 
    RequestValidationError, 
    ResponseValidationError, 
    HookError
)

class FlowEngine:
    def __init__(self, proxy: ProxyHandler):
        self.proxy = proxy

    async def process(self, payload: StaticPayload, route: RouteDefinition) -> Any:
        # 1. Extraction (Plucking)
        data = payload
        if route.extract:
            data = payload.pluck(route.extract)
            if data is None:
                raise ExtractionError(route.extract)

        # 2. Before Request Hook (Business Logic)
        if route.before_request:
            try:
                data = await self._maybe_await(route.before_request(data))
            except Exception as e:
                raise HookError(f"Error in before_request hook: {str(e)}") from e

        # 3. Request Validation
        if route.request_model and not isinstance(data, route.request_model):
            try:
                data = route.request_model.model_validate(data)
            except Exception as e:
                raise RequestValidationError(str(e)) from e

        # Prepare request data
        request_json = data.model_dump() if hasattr(data, "model_dump") else data

        # 4. Proxy Call (or Mock)
        if route.mock_data is not None:
            print(f"--- [Mock Mode] Returning mock data for {route.type} ---")
            response_data = route.mock_data
        else:
            response = await self.proxy.request(
                method=route.method,
                path=route.path,
                json_data=request_json
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            response_data = response.json()

        # 5. After Response Hook
        if route.after_response:
            try:
                response_data = await self._maybe_await(route.after_response(response_data))
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
