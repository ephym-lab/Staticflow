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
        params: Optional[Dict[str, Any]] = None,
        request_format: str = "json"
    ) -> httpx.Response:
        try:
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
            
            response = await self._client.request(
                method=method,
                url=path,
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
        await self._client.aclose()
