from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple
import httpx
import time
from ..exceptions import AuthError

class AuthHandler(ABC):
    """
    Base class for all authentication strategies.
    Allows modifying headers, params, or the request body.
    """
    @abstractmethod
    async def apply(
        self, 
        incoming_headers: Dict[str, str],
        upstream_headers: Dict[str, str], 
        upstream_params: Dict[str, Any], 
        upstream_json: Dict[str, Any],
        **kwargs
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

    async def apply(self, incoming_headers, upstream_headers, upstream_params, upstream_json, **kwargs):
        if self.location == "header":
            upstream_headers[self.name] = self.key
        elif self.location == "param":
            upstream_params[self.name] = self.key
        elif self.location == "body":
            upstream_json[self.name] = self.key
        return upstream_headers, upstream_params, upstream_json

class PassthroughHandler(AuthHandler):
    """
    Forwards an auth-related header from the incoming request to the upstream.
    Supports Bearer token normalization.
    """
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
    """
    Implements OAuth2 Client Credentials flow with automatic token caching and refresh.
    Allows for a custom token_extractor to handle diverse response formats.
    """
    def __init__(
        self, 
        token_url: str, 
        client_id: str, 
        client_secret: str, 
        scope: Optional[str] = None,
        token_extractor: Optional[Callable[[Dict[str, Any]], Tuple[str, int]]] = None
    ):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.token_extractor = token_extractor
        self._token: Optional[str] = None
        self._expires_at: float = 0

    async def apply(self, incoming_headers, upstream_headers, upstream_params, upstream_json, **kwargs):
        token = await self._get_valid_token()
        upstream_headers["Authorization"] = f"Bearer {token}"
        return upstream_headers, upstream_params, upstream_json

    async def _get_valid_token(self) -> str:
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
            
            # Use custom extractor if provided, otherwise fallback to standard keys
            if self.token_extractor:
                try:
                    self._token, expires_in = self.token_extractor(res_json)
                    self._expires_at = time.time() + expires_in
                except Exception as e:
                    raise AuthError(f"Token extraction failed: {str(e)}")
            else:
                self._token = res_json.get("access_token")
                expires_in = res_json.get("expires_in", 3600)
                self._expires_at = time.time() + expires_in

            if not self._token:
                raise AuthError("No access_token found in response")
                
            return self._token
