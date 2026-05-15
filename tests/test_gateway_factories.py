import pytest
from staticfloww import Gateway
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
