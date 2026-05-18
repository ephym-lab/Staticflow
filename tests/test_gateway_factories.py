import pytest
from unittest.mock import patch, AsyncMock
from staticfloww import Gateway, StaticPayload
from staticfloww.core.auth import APIKeyHandler, PassthroughHandler, OAuth2Handler

def test_gateway_auth_factories():
    """
    Test that the Gateway creates AuthHandlers correctly using factory methods.
    """
    gateway = Gateway(base_url="https://api.example.com")
    
    # 1. Test API Key Factory
    apikey = gateway.api_key_auth(key="123", name="X-Key")
    assert isinstance(apikey, APIKeyHandler)
    assert apikey.key == "123"
    
    # 2. Test Passthrough Factory
    pass_auth = gateway.passthrough_auth(bearer_format="strip")
    assert isinstance(pass_auth, PassthroughHandler)
    assert pass_auth.bearer_format == "strip"
    
    # 3. Test OAuth2 Factory (with relative path resolution)
    oauth = gateway.oauth2_auth(
        token_path="/v2/token",
        client_id="id",
        client_secret="secret"
    )
    assert isinstance(oauth, OAuth2Handler)
    # Verify the URL was joined correctly
    assert oauth.token_url == "https://api.example.com/v2/token"

def test_gateway_url_resolution_handling():
    """
    Test that URL resolution handles slashes correctly.
    """
    # Gateway with trailing slash
    gateway = Gateway(base_url="https://api.example.com/")
    oauth = gateway.oauth2_auth(token_path="token", client_id="i", client_secret="s")
    assert oauth.token_url == "https://api.example.com/token"
    
    # Path with leading slash
    oauth2 = gateway.oauth2_auth(token_path="/auth/token", client_id="i", client_secret="s")
    assert oauth2.token_url == "https://api.example.com/auth/token"

def test_gateway_default_auth():
    """
    Test that route registrations with auth=True dynamically resolve to the gateway's
    default auth handler, supporting both constructor passing and late-binding registration.
    """
    # 1. Constructor passing
    default_auth_handler = APIKeyHandler(key="const_secret")
    gateway = Gateway(base_url="https://api.example.com", auth=default_auth_handler)
    
    gateway.add_route(
        action="GET_DATA",
        path="/data",
        auth=True
    )
    
    route = gateway.router.get_route("GET_DATA")
    assert route.auth is True # Kept as True until request routing time
    
    # Simulate a request flow triggering route_request (using dynamic resolution)
    import asyncio
    payload = StaticPayload(
        SessionID="sess123",
        IMEI="imei123",
        Country="KE",
        details={"action": "GET_DATA"}
    )
    
    with patch("staticfloww.core.engine.FlowEngine.process", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = {"status": "success"}
        asyncio.run(gateway.route_request(payload))
        
        # Verify route auth was dynamically resolved and set to default_auth!
        assert route.auth == default_auth_handler

    # 2. Late-binding via auto-registration of initialized AuthHandlers
    gateway2 = Gateway(base_url="https://api.example.com")
    gateway2.add_route(
        action="GET_DATA_LATE",
        path="/data",
        auth=True
    )
    
    # Create the handler AFTER creating the gateway and adding the route (auto-registers!)
    late_handler = APIKeyHandler(key="late_secret")
    assert gateway2.default_auth == late_handler
    
    route_late = gateway2.router.get_route("GET_DATA_LATE")
    payload_late = StaticPayload(
        SessionID="sess123",
        IMEI="imei123",
        Country="KE",
        details={"action": "GET_DATA_LATE"}
    )
    
    with patch("staticfloww.core.engine.FlowEngine.process", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = {"status": "success"}
        asyncio.run(gateway2.route_request(payload_late))
        assert route_late.auth == late_handler
