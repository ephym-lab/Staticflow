import pytest
from staticfloww import Gateway, StaticPayload
from unittest.mock import AsyncMock
import httpx

@pytest.mark.asyncio
async def test_parallel_fanout():
    app = Gateway(base_url="http://mock")
    
    app.add_route(
        type="MULTI_ACTION",
        fan_out=[
            {"type": "sub1", "path": "/1", "mock_data": {"a": 1}},
            {"type": "sub2", "path": "/2", "mock_data": {"b": 2}}
        ]
    )
    
    payload = StaticPayload(details={"type": "MULTI_ACTION", "action": "MULTI_ACTION"})
    result = await app.route_request(payload)
    
    assert result["a"] == 1
    assert result["b"] == 2

@pytest.mark.asyncio
async def test_fanout_custom_merge():
    def merger(results, **kwargs):
        return {"count": len(results)}
        
    app = Gateway(base_url="http://mock")
    app.add_route(
        type="COUNT_ACTION",
        fan_out=[
            {"type": "s1", "path": "/1", "mock_data": {}},
            {"type": "s2", "path": "/2", "mock_data": {}}
        ],
        merge_hook=merger
    )
    
    payload = StaticPayload(details={"type": "COUNT_ACTION", "action": "COUNT_ACTION"})
    result = await app.route_request(payload)
    assert result["count"] == 2
