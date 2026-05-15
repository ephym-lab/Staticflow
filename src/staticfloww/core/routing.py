from typing import Any, Callable, Dict, Optional, Type, List, Union
from pydantic import BaseModel
from dataclasses import dataclass

@dataclass
class RouteDefinition:
    action: str
    path: str
    method: str = "POST"
    extract: Optional[str] = None
    before_request: Optional[Callable[[Any], Any]] = None
    after_response: Optional[Callable[[Any], Any]] = None
    request_model: Optional[Type[BaseModel]] = None
    response_model: Optional[Type[BaseModel]] = None
    auth: Optional[Any] = None
    mock_data: Optional[Any] = None
    resilience: Optional[Any] = None

@dataclass
class FanOutRouteDefinition:
    action: str
    routes: List[RouteDefinition]
    merge_hook: Optional[Callable[[List[Any]], Any]] = None

class Router:
    def __init__(self):
        self._routes: Dict[str, Union[RouteDefinition, FanOutRouteDefinition]] = {}

    def add_route(self, **kwargs):
        # Support both 'type' and 'action' for registration
        action_name = kwargs.pop("action", kwargs.pop("type", None))
        if not action_name:
            raise ValueError("Route must have an 'action' or 'type' defined")

        if "fan_out" in kwargs:
            fan_out_routes = kwargs.pop("fan_out")
            processed_subroutes = []
            for r in fan_out_routes:
                if isinstance(r, dict):
                    # Ensure sub-routes also use 'action' internally
                    sub_action = r.pop("action", r.pop("type", None))
                    processed_subroutes.append(RouteDefinition(action=sub_action, **r))
                else:
                    processed_subroutes.append(r)
            
            route = FanOutRouteDefinition(
                action=action_name,
                routes=processed_subroutes,
                merge_hook=kwargs.get("merge_hook")
            )
        else:
            route = RouteDefinition(action=action_name, **kwargs)
        self._routes[route.action] = route

    def get_route(self, action_name: str) -> Optional[Union[RouteDefinition, FanOutRouteDefinition]]:
        return self._routes.get(action_name)
