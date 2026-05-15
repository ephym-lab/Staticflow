import httpx
from typing import Any, Dict, Optional
from ..exceptions import (
    UpstreamTimeoutError, 
    UpstreamConnectionError, 
    UpstreamResponseError
)

class ProxyHandler:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True
        )

    async def request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        try:
            # Only send JSON if there's actual data and it's not a GET request
            # (or if specifically required)
            send_json = json_data if method.upper() != "GET" else None
            
            response = await self._client.request(
                method=method,
                url=path,
                json=send_json,
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
        await self._client.aclose()
