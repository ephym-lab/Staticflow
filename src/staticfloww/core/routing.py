from typing import Any, Callable, Dict, Optional, Type, List, Union
from pydantic import BaseModel
from dataclasses import dataclass

@dataclass
class RouteDefinition:
    type: str
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
    type: str
    routes: List[RouteDefinition]
    merge_hook: Optional[Callable[[List[Any]], Any]] = None

class Router:
    def __init__(self):
        self._routes: Dict[str, Union[RouteDefinition, FanOutRouteDefinition]] = {}

    def add_route(self, **kwargs):
        if "fan_out" in kwargs:
            fan_out_routes = kwargs.pop("fan_out")
            route = FanOutRouteDefinition(
                type=kwargs["type"],
                routes=[RouteDefinition(**r) if isinstance(r, dict) else r for r in fan_out_routes],
                merge_hook=kwargs.get("merge_hook")
            )
        else:
            route = RouteDefinition(**kwargs)
        self._routes[route.type] = route

    def get_route(self, request_type: str) -> Optional[Union[RouteDefinition, FanOutRouteDefinition]]:
        return self._routes.get(request_type)
