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

class Router:
    def __init__(self):
        self._routes: Dict[str, RouteDefinition] = {}

    def add_route(self, **kwargs):
        route = RouteDefinition(**kwargs)
        self._routes[route.type] = route

    def get_route(self, request_type: str) -> Optional[RouteDefinition]:
        return self._routes.get(request_type)
