from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple
import httpx
import time
from ..exceptions import AuthError

def _register_with_gateway(handler):
    try:
        from .gateway import Gateway
        if Gateway._last_active_gateway and not Gateway._last_active_gateway.default_auth:
            Gateway._last_active_gateway.default_auth = handler
    except Exception:
        pass


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
        _register_with_gateway(self)

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
        _register_with_gateway(self)

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
    Supports token_path, token_url, and base_url resolution.
    """
    def __init__(
        self, 
        token_url: Optional[str] = None, 
        client_id: Optional[str] = None, 
        client_secret: Optional[str] = None, 
        scope: Optional[str] = None,
        token_extractor: Optional[Callable[[Dict[str, Any]], Tuple[str, int]]] = None,
        token_path: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        if client_id is None:
            raise ValueError("client_id is required for OAuth2Handler")
        if client_secret is None:
            raise ValueError("client_secret is required for OAuth2Handler")

        self.base_url = base_url.rstrip("/") if base_url else None

        # Automatically determine token_url vs token_path
        # If token_url is actually a path (e.g. does not start with http:// or https://),
        # treat it as token_path.
        if token_url and not token_path:
            if token_url.startswith("http://") or token_url.startswith("https://"):
                self.token_url = token_url
                self.token_path = None
            else:
                self.token_path = token_url
                self.token_url = None
        else:
            self.token_url = token_url
            self.token_path = token_path

        # If base_url is present, and we have a path but no URL, pre-resolve the token_url!
        if self.base_url and self.token_path and not self.token_url:
            path = self.token_path
            if path.startswith("http://") or path.startswith("https://"):
                self.token_url = path
            else:
                self.token_url = f"{self.base_url}/{path.lstrip('/')}"

        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.token_extractor = token_extractor
        self._token: Optional[str] = None
        self._expires_at: float = 0
        _register_with_gateway(self)

    async def apply(self, incoming_headers, upstream_headers, upstream_params, upstream_json, **kwargs):
        # Dynamically retrieve base_url if passed, or fallback to configured self.base_url
        base_url = kwargs.get("base_url") or self.base_url
        token = await self._get_valid_token(base_url=base_url)
        upstream_headers["Authorization"] = f"Bearer {token}"
        return upstream_headers, upstream_params, upstream_json

    async def _get_valid_token(self, base_url: Optional[str] = None) -> str:
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        
        # Resolve the full token URL
        token_url = self.token_url
        if not token_url:
            path = self.token_path or "/"
            if path.startswith("http://") or path.startswith("https://"):
                token_url = path
            else:
                if not base_url:
                    raise AuthError(
                        "Cannot resolve token path: base_url not provided. "
                        "Please pass a full token_url or configure a base_url."
                    )
                token_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        else:
            # If token_url is not a full HTTP URL, treat it as a path
            if not (token_url.startswith("http://") or token_url.startswith("https://")):
                if not base_url:
                    raise AuthError(
                        "Cannot resolve token path: base_url not provided. "
                        "Please pass a full token_url or configure a base_url."
                    )
                token_url = f"{base_url.rstrip('/')}/{token_url.lstrip('/')}"

        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            if self.scope:
                data["scope"] = self.scope
            
            response = await client.post(token_url, data=data)
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
