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
