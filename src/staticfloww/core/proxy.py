import httpx
import asyncio
from typing import Any, Dict, Optional
from ..exceptions import (
    UpstreamTimeoutError, 
    UpstreamConnectionError, 
    UpstreamResponseError
)

class ProxyHandler:
    """
    Handles communication with upstream services using httpx.
    Now supports lazy initialization to be compatible with multiple event loops
    (e.g., when used with asyncio.run in Flask).
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self._loop_id: Optional[int] = None

    def _get_client(self) -> httpx.AsyncClient:
        """
        Ensures the client is initialized and attached to the current active loop.
        If the loop has changed (e.g. new Flask request), it refreshes the client.
        """
        try:
            current_loop = asyncio.get_event_loop()
            current_loop_id = id(current_loop)
        except RuntimeError:
            current_loop_id = None

        # Re-initialize if:
        # 1. No client exists
        # 2. Client is closed
        # 3. We are in a brand new event loop (Flask/asyncio.run case)
        if (self._client is None or 
            self._client.is_closed or 
            self._loop_id != current_loop_id):
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True
            )
            self._loop_id = current_loop_id
            
        return self._client

    async def request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        request_format: str = "json",
        base_url: Optional[str] = None
    ) -> httpx.Response:
        try:
            # Use provided base_url or fallback to default
            effective_base = (base_url or self.base_url).rstrip("/")
            full_url = f"{effective_base}/{path.lstrip('/')}"
            
            # Prepare the body based on explicit request_format
            json_body = None
            form_data = None
            
            if method.upper() != "GET" and json_data:
                if request_format == "form":
                    form_data = json_data
                    # Automatically ensure Content-Type is set if using form
                    if headers is None: headers = {}
                    headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                else:
                    json_body = json_data
            
            # Use lazy-initialized client
            client = self._get_client()
            
            response = await client.request(
                method=method,
                url=full_url,
                json=json_body,
                data=form_data,
                headers=headers,
                params=params
            )
            return response
        except httpx.ConnectError:
            raise UpstreamConnectionError()
        except httpx.TimeoutException:
            raise UpstreamTimeoutError()
        except httpx.HTTPStatusError as exc:
            raise UpstreamResponseError(
                status_code=exc.response.status_code,
                details=exc.response.text
            )
        except httpx.HTTPError as exc:
            raise UpstreamResponseError(status_code=500, details=str(exc))

    async def close(self):
        """
        Closes the underlying HTTP client.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
