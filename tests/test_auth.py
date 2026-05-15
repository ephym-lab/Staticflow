import pytest
from staticfloww import APIKeyHandler, PassthroughHandler, AuthError
import httpx

@pytest.mark.asyncio
async def test_apikey_header():
    handler = APIKeyHandler(key="secret123", name="X-Token", location="header")
    h, p, j = await handler.apply({}, {}, {}, {})
    assert h["X-Token"] == "secret123"

@pytest.mark.asyncio
async def test_apikey_body():
    handler = APIKeyHandler(key="secret123", name="token", location="body")
    h, p, j = await handler.apply({}, {}, {}, {})
    assert j["token"] == "secret123"

@pytest.mark.asyncio
async def test_passthrough_normalization():
    # Ensure
    handler = PassthroughHandler(bearer_format="ensure")
    h, p, j = await handler.apply({"Authorization": "abc"}, {}, {}, {})
    assert h["Authorization"] == "Bearer abc"
    
    # Strip
    handler = PassthroughHandler(bearer_format="strip")
    h, p, j = await handler.apply({"Authorization": "Bearer abc"}, {}, {}, {})
    assert h["Authorization"] == "abc"

@pytest.mark.asyncio
async def test_passthrough_missing():
    handler = PassthroughHandler()
    with pytest.raises(AuthError):
        await handler.apply({}, {}, {}, {})
