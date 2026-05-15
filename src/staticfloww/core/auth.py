from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import httpx
from ..exceptions import AuthError

class AuthHandler(ABC):
    """
    Base class for all authentication strategies.
    Allows modifying headers, params, or the request body.
    """
    @abstractmethod
    async def apply(
        self, 
        headers: Dict[str, str], 
        params: Dict[str, Any], 
        json_data: Dict[str, Any]
    ) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, Any]]:
        """
        Returns the modified (headers, params, json_data).
        """
        pass

class APIKeyHandler(AuthHandler):
    """
    Adds an API key to the request. 
    Can be placed in headers, query params, or the JSON body.
    """
    def __init__(
        self, 
        key: str, 
        name: str = "X-API-Key", 
        location: str = "header" # "header", "param", or "body"
    ):
        self.key = key
        self.name = name
        self.location = location

    async def apply(self, headers, params, json_data):
        if self.location == "header":
            headers[self.name] = self.key
        elif self.location == "param":
            params[self.name] = self.key
        elif self.location == "body":
            json_data[self.name] = self.key
        return headers, params, json_data

class PassthroughHandler(AuthHandler):
    """
    Forwards an auth-related header from the incoming request.
    """
    def __init__(self, header_name: str = "Authorization"):
        self.header_name = header_name

    async def apply(self, headers, params, json_data):
        # We assume the incoming headers are already passed or available
        # This one is tricky as it needs access to the 'context' of the incoming request.
        # We'll rely on the engine passing the incoming_headers.
        return headers, params, json_data

    async def apply_with_context(self, incoming_headers, headers, params, json_data):
        auth_header = incoming_headers.get(self.header_name) or incoming_headers.get(self.header_name.lower())
        if auth_header:
            headers[self.name] = auth_header # Wait, name? I should use self.header_name
        return headers, params, json_data

# Refined AuthHandler to simplify context passing
class AuthHandler(ABC):
    @abstractmethod
    async def apply(
        self, 
        incoming_headers: Dict[str, str],
        upstream_headers: Dict[str, str], 
        upstream_params: Dict[str, Any], 
        upstream_json: Dict[str, Any],
        **kwargs
    ) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, Any]]:
        pass

class APIKeyHandler(AuthHandler):
    def __init__(self, key: str, name: str = "X-API-Key", location: str = "header"):
        self.key = key
        self.name = name
        self.location = location

    async def apply(self, incoming_headers, upstream_headers, upstream_params, upstream_json, **kwargs):
        if self.location == "header":
            upstream_headers[self.name] = self.key
        elif self.location == "param":
            upstream_params[self.name] = self.key
        elif self.location == "body":
            upstream_json[self.name] = self.key
        return upstream_headers, upstream_params, upstream_json

class PassthroughHandler(AuthHandler):
    def __init__(
        self, 
        header_name: str = "Authorization", 
        upstream_name: Optional[str] = None,
        bearer_format: str = "as_is" # "as_is", "ensure", or "strip"
    ):
        self.header_name = header_name
        self.upstream_name = upstream_name or header_name
        self.bearer_format = bearer_format

    async def apply(self, incoming_headers, upstream_headers, upstream_params, upstream_json, **kwargs):
        val = incoming_headers.get(self.header_name) or incoming_headers.get(self.header_name.lower())
        if not val:
            raise AuthError(f"Missing required {self.header_name} header for passthrough")
        
        # Bearer Normalization
        if self.bearer_format == "strip":
            if val.lower().startswith("bearer "):
                val = val[7:].strip()
        elif self.bearer_format == "ensure":
            if not val.lower().startswith("bearer "):
                val = f"Bearer {val}"
                
        upstream_headers[self.upstream_name] = val
        return upstream_headers, upstream_params, upstream_json

class OAuth2Handler(AuthHandler):
    def __init__(self, token_url: str, client_id: str, client_secret: str, scope: Optional[str] = None):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._token: Optional[str] = None
        self._expires_at: float = 0

    async def apply(self, incoming_headers, upstream_headers, upstream_params, upstream_json, **kwargs):
        token = await self._get_valid_token()
        upstream_headers["Authorization"] = f"Bearer {token}"
        return upstream_headers, upstream_params, upstream_json

    async def _get_valid_token(self) -> str:
        import time
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        
        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            if self.scope:
                data["scope"] = self.scope
            
            response = await client.post(self.token_url, data=data)
            if response.status_code != 200:
                raise AuthError(f"Failed to fetch OAuth2 token: {response.text}")
            
            res_json = response.json()
            self._token = res_json["access_token"]
            self._expires_at = time.time() + res_json.get("expires_in", 3600)
            return self._token
