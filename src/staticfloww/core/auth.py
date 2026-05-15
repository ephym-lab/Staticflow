from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx
from ..exceptions import AuthError

class AuthHandler(ABC):
    """
    Base class for all authentication strategies.
    """
    @abstractmethod
    async def get_headers(self, incoming_headers: Dict[str, str]) -> Dict[str, str]:
        """
        Returns the headers to be added to the upstream request.
        """
        pass

class APIKeyHandler(AuthHandler):
    """
    Adds a static API key to the request headers.
    """
    def __init__(self, key: str, header_name: str = "X-API-Key"):
        self.key = key
        self.header_name = header_name

    async def get_headers(self, incoming_headers: Dict[str, str]) -> Dict[str, str]:
        return {self.header_name: self.key}

class PassthroughHandler(AuthHandler):
    """
    Forwards the Authorization header from the incoming request.
    """
    def __init__(self, header_name: str = "Authorization"):
        self.header_name = header_name

    async def get_headers(self, incoming_headers: Dict[str, str]) -> Dict[str, str]:
        auth_header = incoming_headers.get(self.header_name) or incoming_headers.get(self.header_name.lower())
        if not auth_header:
            raise AuthError(f"Missing required {self.header_name} header for passthrough")
        return {self.header_name: auth_header}

class OAuth2Handler(AuthHandler):
    """
    Implements OAuth2 Client Credentials flow.
    """
    def __init__(self, token_url: str, client_id: str, client_secret: str, scope: Optional[str] = None):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._token: Optional[str] = None
        self._expires_at: float = 0

    async def get_headers(self, incoming_headers: Dict[str, str]) -> Dict[str, str]:
        token = await self._get_valid_token()
        return {"Authorization": f"Bearer {token}"}

    async def _get_valid_token(self) -> str:
        import time
        # Very basic caching logic
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
