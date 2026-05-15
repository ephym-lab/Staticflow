import pytest
from unittest.mock import AsyncMock, patch
from staticfloww.core.proxy import ProxyHandler
from staticfloww.core.routing import RouteDefinition

@pytest.mark.asyncio
async def test_proxy_explicit_form_format():
    """
    Test that ProxyHandler respects the explicit request_format='form' parameter.
    """
    proxy = ProxyHandler(base_url="https://api.example.com")
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    
    payload = {"grant_type": "client_credentials"}
    
    with patch("httpx.AsyncClient.request", return_value=mock_response) as mock_request:
        await proxy.request(
            method="POST",
            path="/token",
            json_data=payload,
            request_format="form"
        )
        
        args, kwargs = mock_request.call_args
        # Should be in 'data' (form), NOT 'json'
        assert kwargs["data"] == payload
        assert kwargs["json"] is None
        # Should have automatically added the header
        assert kwargs["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

@pytest.mark.asyncio
async def test_proxy_default_json_format():
    """
    Test that ProxyHandler defaults to 'json' if no format is specified.
    """
    proxy = ProxyHandler(base_url="https://api.example.com")
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    
    payload = {"data": "test"}
    
    with patch("httpx.AsyncClient.request", return_value=mock_response) as mock_request:
        await proxy.request(
            method="POST",
            path="/api",
            json_data=payload
        )
        
        args, kwargs = mock_request.call_args
        assert kwargs["json"] == payload
        assert kwargs["data"] is None
