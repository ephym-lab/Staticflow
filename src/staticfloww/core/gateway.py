from typing import Any, Optional
from .routing import Router, RouteDefinition
from .proxy import ProxyHandler
from .engine import FlowEngine
from ..schemas.base import StaticPayload
from ..exceptions import StaticflowwError, RouteNotFoundError

class Gateway:
    def __init__(self, base_url: str, auditor: Optional[Any] = None):
        self.router = Router()
        self.proxy = ProxyHandler(base_url=base_url)
        self.engine = FlowEngine(proxy=self.proxy)
        self.auditor = auditor

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
        """
        request_type = payload.details.type
        route = self.router.get_route(request_type)
        
        if not route:
            raise RouteNotFoundError(request_type)

        context = {
            "request_type": request_type,
            "session_id": payload.SessionID,
            "imei": payload.IMEI
        }

        # Auditing: Log Request
        if self.auditor:
            await self.auditor.log_request(payload.model_dump(), context)
        
        try:
            response_data = await self.engine.process(payload, route, incoming_headers=headers, **kwargs)
            
            # Auditing: Log Response
            if self.auditor:
                # We dump the data if it's a Pydantic model
                log_data = response_data.model_dump() if hasattr(response_data, "model_dump") else response_data
                await self.auditor.log_response(log_data, context)
                
            return response_data
            
        except Exception as e:
            # TODO: Log error to auditor
            raise e

    async def shutdown(self):
        await self.proxy.close()
