import pytest
from unittest.mock import AsyncMock, patch
from staticfloww.core.proxy import ProxyHandler

@pytest.mark.asyncio
async def test_proxy_base_url_override():
    """
    Test that ProxyHandler respects the base_url override in the request method.
    """
    proxy = ProxyHandler(base_url="https://external-api.com")
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    
    with patch("httpx.AsyncClient.request", return_value=mock_response) as mock_request:
        # 1. Test Default behavior
        await proxy.request(method="GET", path="/data")
        args, kwargs = mock_request.call_args
        assert kwargs["url"] == "https://external-api.com/data"
        
        # 2. Test Override behavior (e.g., hitting localhost for logs)
        await proxy.request(
            method="GET", 
            path="/logs", 
            base_url="http://localhost:5000"
        )
        args, kwargs = mock_request.call_args
        # Should have switched to localhost!
        assert kwargs["url"] == "http://localhost:5000/logs"

def test_proxy_url_joining_robustness():
    """
    Ensure the proxy handles slashes safely regardless of input.
    """
    from staticfloww.core.proxy import ProxyHandler
    proxy = ProxyHandler(base_url="https://api.com/")
    
    # We'll mock the internal _client.request just to check the URL construction
    with patch("httpx.AsyncClient.request") as mock_req:
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Test trailing slash on base + leading slash on path
        loop.run_until_complete(proxy.request("GET", "/test"))
        assert mock_req.call_args[1]["url"] == "https://api.com/test"
