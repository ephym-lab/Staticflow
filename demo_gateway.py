from __future__ import annotations
import asyncio
from typing import Optional, Union, Any
from pydantic import BaseModel, Field, ConfigDict
from src.staticfloww import Gateway, StaticPayload, Section, APIKeyHandler

# 1. Define our custom sections
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

# 2. Define our God Schema
class LapfundPayload(StaticPayload):
    UserDetails: Any = None

# 3. Define some business logic hooks
async def enrich_user_data(data: Any) -> UpstreamCreateUser:
    # Manual validation if it's a dict
    if isinstance(data, dict):
        data = UserDetails.model_validate(data)
    
    print(f"--- [Hook: before_request] Enriching {data.first_name} ---")
    return UpstreamCreateUser(
        name=f"{data.first_name} {data.last_name}",
        contact_email=data.email
    )

async def format_response(data: dict) -> FrontendUserRes:
    print(f"--- [Hook: after_response] Formatting response for ID {data.get('id')} ---")
    return FrontendUserRes(
        id=data.get("id", 0),
        full_name=data.get("name", "Unknown")
    )

async def main():
    # Initialize Gateway (using a dummy URL for now)
    app = Gateway(base_url="https://api.mock-service.com")

    # Register a route with plucking, validation, and hooks
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

    app.add_route(
        type="GET_SECURE_DATA",
        path="/api/secure",
        method="GET",
        auth=APIKeyHandler(key="secret_token_123"),
        mock_data={"data": "This is protected info"}
    )

    # 4. Simulate the incoming God Schema Payload
    raw_payload = {
        "details": {
            "type": "CREATE_MEMBER",
            "country": "KENYA"
        },
        "UserDetails": {
            "first_name": "Antigravity",
            "last_name": "AI",
            "email": "antigravity@google.com"
        },
        "SessionID": "sess_123",
        "IMEI": "dev_456"
    }

    payload = LapfundPayload(**raw_payload)

    print("\n Generating TypeScript Types for LapfundPayload...")
    from src.staticfloww import generate_typescript
    ts_code = generate_typescript(LapfundPayload)
    print("--- Generated TypeScript ---")
    print(ts_code)
    print("----------------------------")

    print("\n Processing request through StaticFlow Gateway...")
    
    # Since we don't have a real server, let's mock the proxy response for this demo
    # In a real scenario, Gateway would actually hit the URL.
    from unittest.mock import AsyncMock
    import httpx
    
    mock_response = httpx.Response(
        200, 
        json={"id": 1001, "name": "Antigravity AI"},
        request=httpx.Request("POST", "https://api.mock-service.com/api/members/register")
    )
    app.proxy.request = AsyncMock(return_value=mock_response)

    try:
        result = await app.route_request(payload)
        print("\nFinal Response to Frontend:")
        print(result.model_dump_json(indent=2))

        # --- Test Auth/Mock Mode ---
        print("\n🧪 Testing Auth Mode (GET_SECURE_DATA)...")
        secure_payload = LapfundPayload(details={"type": "GET_SECURE_DATA"})
        secure_result = await app.route_request(secure_payload)
        print("Secure Response:", secure_result)

    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(main())
