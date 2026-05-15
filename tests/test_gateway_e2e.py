import pytest
import asyncio
from typing import Optional, Union, Any
from pydantic import BaseModel
from staticfloww import Gateway, StaticPayload, Section, APIKeyHandler
from unittest.mock import AsyncMock
import httpx

class UserDetails(Section):
    first_name: str
    last_name: str
    email: str

class UpstreamCreateUser(BaseModel):
    name: str
    contact_email: str

class FrontendUserRes(BaseModel):
    id: int
    full_name: str
    status: str = "Success"

class LapfundPayload(StaticPayload):
    UserDetails: Any = None

async def enrich_user_data(data: Any, **kwargs) -> UpstreamCreateUser:
    if isinstance(data, dict):
        data = UserDetails.model_validate(data)
    return UpstreamCreateUser(
        name=f"{data.first_name} {data.last_name}",
        contact_email=data.email
    )

async def format_response(data: dict, **kwargs) -> FrontendUserRes:
    return FrontendUserRes(
        id=data.get("id", 0),
        full_name=data.get("name", "Unknown")
    )

@pytest.mark.asyncio
async def test_gateway_full_flow():
    app = Gateway(base_url="https://api.mock-service.com")

    app.add_route(
        type="CREATE_MEMBER",
        path="/api/members/register",
        method="POST",
        extract="UserDetails",
        before_request=enrich_user_data,
        after_response=format_response,
        request_model=UpstreamCreateUser,
        response_model=FrontendUserRes
    )

    raw_payload = {
        "details": {
            "type": "CREATE_MEMBER",
            "country": "KENYA"
        },
        "UserDetails": {
            "first_name": "Antigravity",
            "last_name": "AI",
            "email": "antigravity@google.com"
        }
    }

    payload = LapfundPayload(**raw_payload)
    
    # Mock proxy
    mock_response = httpx.Response(
        200, 
        json={"id": 1001, "name": "Antigravity AI"},
        request=httpx.Request("POST", "https://api.mock-service.com/api/members/register")
    )
    app.proxy.request = AsyncMock(return_value=mock_response)

    result = await app.route_request(payload)
    
    assert result.id == 1001
    assert result.full_name == "Antigravity AI"
    assert result.status == "Success"

@pytest.mark.asyncio
async def test_mock_mode_route():
    app = Gateway(base_url="http://mock")
    app.add_route(
        type="MOCK_ACTION",
        path="/mock",
        mock_data={"status": "mocked"}
    )
    
    payload = StaticPayload(details={"type": "MOCK_ACTION", "action": "MOCK_ACTION"})
    result = await app.route_request(payload)
    assert result["status"] == "mocked"
