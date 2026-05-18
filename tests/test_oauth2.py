import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from staticfloww.core.auth import OAuth2Handler

@pytest.mark.asyncio
async def test_oauth2_fetch_token():
    """
    Test that OAuth2Handler fetches a token and caches it.
    """
    handler = OAuth2Handler(
        token_url="https://auth.example.com/token",
        client_id="test_id",
        client_secret="test_secret"
    )

    # Create a mock response that behaves like httpx.Response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "valid_token",
        "expires_in": 3600
    }
    mock_response.text = '{"access_token": "valid_token"}'

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        # First call: Should fetch
        headers, params, body = await handler.apply({}, {}, {}, {})
        
        assert headers["Authorization"] == "Bearer valid_token"
        assert mock_post.call_count == 1
        
        # Second call: Should use cache
        headers, params, body = await handler.apply({}, {}, {}, {})
        assert headers["Authorization"] == "Bearer valid_token"
        assert mock_post.call_count == 1  # Still 1 because of caching

@pytest.mark.asyncio
async def test_oauth2_custom_extractor():
    """
    Test that OAuth2Handler supports custom response formats via token_extractor.
    """
    def custom_extractor(res):
        return res["token"], res["ttl"]

    handler = OAuth2Handler(
        token_url="https://auth.example.com/token",
        client_id="test_id",
        client_secret="test_secret",
        token_extractor=custom_extractor
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "token": "custom_abc",
        "ttl": 600
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        headers, params, body = await handler.apply({}, {}, {}, {})
        assert headers["Authorization"] == "Bearer custom_abc"

@pytest.mark.asyncio
async def test_oauth2_token_refresh():
    """
    Test that token is refreshed when expired.
    """
    handler = OAuth2Handler(
        token_url="https://auth.example.com/token",
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Manually set an expired state
    handler._token = "old_token"
    handler._expires_at = time.time() - 100  # Expired

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_token",
        "expires_in": 3600
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        headers, params, body = await handler.apply({}, {}, {}, {})
        assert headers["Authorization"] == "Bearer new_token"
        assert mock_post.call_count == 1

@pytest.mark.asyncio
async def test_oauth2_token_path_resolution():
    """
    Test that OAuth2Handler resolves token_path using pre-configured or dynamic base_url,
    and supports full URL bypass.
    """
    # 1. Pre-configured base_url
    handler1 = OAuth2Handler(
        token_path="/oauth/token",
        client_id="test_id",
        client_secret="test_secret",
        base_url="https://preconfig.com"
    )
    assert handler1.token_url == "https://preconfig.com/oauth/token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "token_pre",
        "expires_in": 3600
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        headers, params, body = await handler1.apply({}, {}, {}, {})
        assert headers["Authorization"] == "Bearer token_pre"
        # Verify post called on resolved URL
        assert mock_post.call_args[0][0] == "https://preconfig.com/oauth/token"

    # 2. Dynamic base_url via kwargs
    handler2 = OAuth2Handler(
        token_path="/oauth/token",
        client_id="test_id",
        client_secret="test_secret"
    )
    assert handler2.token_url is None

    mock_response_dynamic = MagicMock()
    mock_response_dynamic.status_code = 200
    mock_response_dynamic.json.return_value = {
        "access_token": "token_dynamic",
        "expires_in": 3600
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response_dynamic
        headers, params, body = await handler2.apply({}, {}, {}, {}, base_url="https://dynamic.com")
        assert headers["Authorization"] == "Bearer token_dynamic"
        assert mock_post.call_args[0][0] == "https://dynamic.com/oauth/token"

    # 3. Positional path + dynamic base_url
    handler3 = OAuth2Handler(
        "/oauth/token-pos",
        "test_id",
        "test_secret"
    )
    assert handler3.token_path == "/oauth/token-pos"
    assert handler3.token_url is None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response_dynamic
        headers, params, body = await handler3.apply({}, {}, {}, {}, base_url="https://dynamic-pos.com")
        assert mock_post.call_args[0][0] == "https://dynamic-pos.com/oauth/token-pos"

    # 4. Full URL bypass inside token_path
    handler4 = OAuth2Handler(
        token_path="https://bypass.com/oauth/token",
        client_id="test_id",
        client_secret="test_secret"
    )
    # Since it starts with https://, it should be treated as full url
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        headers, params, body = await handler4.apply({}, {}, {}, {})
        assert mock_post.call_args[0][0] == "https://bypass.com/oauth/token"

