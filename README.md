# StaticFlow 🚀

**The Unified API Gateway Framework for "God Schema" Architectures.**

`StaticFlow` is a lightweight, high-performance Python framework designed to simplify Backend-for-Frontend (BFF) development. It enables a **"Universal Gateway"** pattern where the frontend communicates via a single, static JSON contract (the "God Schema"), while the gateway handles routing, data extraction, and upstream proxying.

---

## 🌟 The Problem
In modern microservice or multi-API environments, frontend applications suffer from:
-   **Fragmented Requests**: Needing to hit multiple diverse endpoints for a single view.
-   **Breaking Contracts**: Any change in an upstream API requires a frontend update.
-   **Auth Complexity**: Managing different authentication flows for different services.
-   **Observability Gaps**: Difficulty tracking a single user action across multiple downstream calls.

## ✨ The Solution: StaticFlow
`StaticFlow` provides a unified proxy layer that "plucks" exactly what it needs from a static, massive payload (the God Schema) and forwards it to the correct upstream service.

---

## 🛠 Key Features

-   **🎯 The "God Schema" Engine**: Maintain one single Pydantic-based schema that never changes shape.
-   **🧬 Smart Extraction**: Automatically extract and validate data segments (e.g., `MemberDetails`) based on the request `type`.
-   **⚡ High-Performance Proxy**: Built-in connection pooling using `httpx` with optimized timeouts and retries.
-   **🛡 Strict Bi-directional Validation**: Validate and transform data **before** it hits the upstream and **before** it returns to the frontend using Pydantic models.
-   **🔒 Unified Auth**: Seamlessly handle system-to-system auth (Client Credentials) or user-token passthrough.
-   **🔌 Pluggable Auditing**: Choose your audit strategy: **MongoDB**, **In-Memory**, or **Disable** entirely.
-   **📝 Async Logging**: Built-in middleware for tracking latency and status code normalization without blocking the request.
-   **🛡 Resilience**: Built-in circuit breaking and error normalization (e.g., turning 10 different error formats into one standard).
-   **📜 Contract Generation**: Automatically export your Python schema to **TypeScript types** for your frontend team.
-   **🧪 Mocking Mode**: Return mock data for specific routes to unblock frontend development.

---

## 📐 Architecture

```mermaid
graph TD
    A[Frontend App] -- "1. Single POST (Static God Schema)" --> B[StaticFlow Gateway]
    B -- "2. Extract & Validate" --> C{Routing Engine}
    C -- "Internal Action" --> D[Internal Handler (Auth/Logs/DB)]
    C -- "Proxy Action" --> E[Upstream Service A]
    C -- "Proxy Action" --> F[Upstream Service B]
    B -- "3. Standardized Response" --> A
    B -. "4. Async Log" .-> G[(Audit Database)]
```

---

## 🚀 Quick Start (Concept)

### 1. Define your Static Schema
```python
from staticflow import StaticPayload, Section
from typing import Optional

class MyGodSchema(StaticPayload):
    # Meta fields for all requests
    SessionID: str
    IMEI: Optional[str] = ""
    
    # Data Sections for specific requests
    UserDetails: Optional[Section] = None
    PaymentDetails: Optional[Section] = None
```

### 2. Configure the Gateway
```python
from staticflow import Gateway

app = Gateway(base_url="https://api.your-backend.com")

app.add_route(
    type="CREATE_MEMBER",
    path="/api/members/register",
    method="POST",
    extract="UserDetails",
    before_request=enrich_user_data,  # Custom Business Logic
    after_response=format_response,   # Custom Response Formatting
    request_model=UpstreamCreateUser, # Validates before sending
    response_model=FrontendUserRes     # Cleans up before returning
)
```

### 3. Configure Auditing (Optional)
```python
from staticflow import Gateway, MongoAudit, MemoryAudit

# Option A: Production MongoDB Auditing
app = Gateway(base_url="...", auditor=MongoAudit(uri="mongodb://localhost:27017"))

# Option B: Lightweight In-Memory Auditing (for small apps/tests)
app = Gateway(base_url="...", auditor=MemoryAudit())

# Option C: Disable Auditing completely
app = Gateway(base_url="...", auditor=None)
```

### 4. Handle the Flow
```python
@app.post("/gateway/process")
async def process(payload: MyGodSchema):
    # StaticFlow extracts, routes, proxies, and logs automatically
    return await app.route_request(payload)
```

---

## 📦 The "God Schema" Payload Pattern
The frontend always sends the same shape. The gateway ignores empty sections and only processes what is required for the specific `type`.

```json
{
  "FormID": "MEMBER_REG_2026",
  "details": {
    "type": "CREATE-MEMBER",
    "country": "KENYA"
  },
  "MemberDetails": {
    "firstName": "John",
    "lastName": "Doe"
  },
  "PaymentDetails": [],
  "Filters": {},
  "SessionID": "token_abc_123",
  "IMEI": "device_8877",
  "Country": "KENYA"
}
```

---

## 📂 Project Structure
```text
staticflow/
├── core/
│   ├── engine.py      # The Extraction Logic
│   ├── proxy.py       # High-performance Httpx Wrapper
│   └── routing.py     # Mapping & Path Resolution
├── middleware/
│   └── auditing.py    # Async Logging Handlers
├── schemas/
│   └── base.py        # Base StaticPayload models
└── utils/
    └── ts_gen.py      # TypeScript Generator
```

---

## 🔐 Flexible Auth Strategies
StaticFlow can manage diverse authentication requirements for different upstream services, keeping your frontend code clean:

```python
# Service A uses OAuth2 (Client Credentials)
app.add_route(type="GET-MEMBER", auth=OAuth2Handler(settings.oauth_config))

# Service B uses a static API Key
app.add_route(type="UPDATE-PROFILE", auth=APIKeyHandler(key="your_secret_key"))

# Service C uses Passthrough (forwarding the user's Bearer token)
app.add_route(type="GET-LOGS", auth=PassthroughHandler())
```

---

## 🛣 Future Roadmap

-   **🔀 Parallel Fan-out**: Trigger multiple upstream requests in parallel and merge results into a single response.
-   **⏱ Rate Limiting**: Built-in protection to prevent gateway or upstream abuse.
-   **🛡 Data Masking**: Automatically redact sensitive fields (PII) from audit logs.
-   **📊 Health Dashboard**: Real-time status of all upstream services.
-   **🔌 Custom Interceptors**: `before_request` and `after_response` hooks for deep customization.
-   **🤖 AI Scaffolding Agent**: Provide an API doc URL and let AI automatically generate your Pydantic schemas and gateway configurations.

---

## 📄 License
MIT License. Created with ❤️ for clean API architectures.
# Staticflow
