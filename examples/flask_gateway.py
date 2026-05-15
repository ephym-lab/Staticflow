import asyncio
from flask import Flask, request, jsonify
from staticfloww import Gateway, StaticPayload, MemoryAuditor

# --- StaticFlow with Flask ---
app = Flask(__name__)

# Initialize an Auditor
auditor = MemoryAuditor()

# Pass the auditor here -> it will handle all logging automatically
gateway = Gateway(
    base_url="https://api.open-meteo.com",
    auditor=auditor
)

# Register a route (standard StaticFlow logic)
gateway.add_route(
    action="GET_WEATHER",
    path="/v1/forecast",
    method="GET"
)

@app.post("/gateway")
def handle_gateway():
    """
    Standard Flask POST endpoint for the God Schema.
    """
    raw_data = request.get_json()
    payload = StaticPayload(**raw_data)
    
    try:
        result = asyncio.run(gateway.route_request(payload))
        return jsonify(result)
    
    except Exception as e:
        status_code = getattr(e, "status_code", 500)
        return jsonify({
            "error": str(e),
            "status": "failed"
        }), status_code

@app.get("/logs")
def view_logs():
    """
    Local endpoint to view the audit history.
    """
    limit = request.args.get('limit', 10, type=int)
    logs = asyncio.run(auditor.get_logs(limit=limit))
    return jsonify(logs)

if __name__ == "__main__":
    print("🚀 Flask Gateway starting on http://localhost:5000")
    app.run(port=5000, debug=True)
