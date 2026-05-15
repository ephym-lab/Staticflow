import traceback
from typing import Any, Optional, Dict
from .routing import Router, RouteDefinition
from .proxy import ProxyHandler
from .engine import FlowEngine
from ..schemas.base import StaticPayload
from ..exceptions import StaticflowwError, RouteNotFoundError
from .auth import APIKeyHandler, PassthroughHandler, OAuth2Handler

class Gateway:
    """
    Main Gateway class that coordinates the entire request lifecycle.
    Supports action-based routing and unified transaction auditing.
    """
    def __init__(self, base_url: str, auditor: Optional[Any] = None):
        self.base_url = base_url.rstrip("/")
        self.router = Router()
        self.proxy = ProxyHandler(base_url=self.base_url)
        self.engine = FlowEngine(proxy=self.proxy)
        self.auditor = auditor
        print(f"📡 [StaticFlow] Gateway Active -> {self.base_url}")

    def api_key_auth(self, **kwargs) -> APIKeyHandler:
        """Factory for APIKeyHandler"""
        return APIKeyHandler(**kwargs)

    def passthrough_auth(self, **kwargs) -> PassthroughHandler:
        """Factory for PassthroughHandler"""
        return PassthroughHandler(**kwargs)

    def oauth2_auth(self, token_path: str, **kwargs) -> OAuth2Handler:
        """
        Factory for OAuth2Handler that automatically prepends the gateway's base_url
        to the token_path.
        """
        full_url = f"{self.base_url}/{token_path.lstrip('/')}"
        return OAuth2Handler(token_url=full_url, **kwargs)

    def add_route(self, **kwargs):
        """
        Registers a new route to the gateway.
        """
        self.router.add_route(**kwargs)

    async def route_request(
        self, 
        payload: StaticPayload, 
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        """
        Main entry point to process a God Schema payload.
        Orchestrates the flow and logs the entire transaction at the end.
        """
        request_type = payload.details.action
        route = self.router.get_route(request_type)
        
        if not route:
            raise RouteNotFoundError(request_type)

        context = {
            "request_type": request_type,
            "session_id": payload.SessionID,
            "imei": payload.IMEI,
            "country": payload.Country
        }

        request_data = payload.model_dump()
        response_data = None
        error_summary = None

        try:
            # Execute the core engine flow
            response_data = await self.engine.process(payload, route, incoming_headers=headers, **kwargs)
            return response_data
            
        except Exception as e:
            # Capture full traceback for the auditor
            error_summary = {
                "message": str(e),
                "type": e.__class__.__name__,
                "traceback": traceback.format_exc()
            }
            raise e
            
        finally:
            # 🛡 Unified Transaction Auditing
            if self.auditor:
                clean_res = response_data.model_dump() if hasattr(response_data, "model_dump") else response_data
                
                await self.auditor.log_transaction(
                    request=request_data,
                    response=clean_res,
                    error=error_summary, # Now contains the full traceback!
                    context=context
                )

    async def shutdown(self):
        """
        Closes the underlying HTTP client.
        """
        await self.proxy.close()
