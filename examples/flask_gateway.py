import asyncio
from flask import Flask, request, jsonify
from staticfloww import Gateway, StaticPayload

# --- StaticFlow with Flask ---
# This shows that StaticFlow is framework-agnostic and 
# can be used even in synchronous environments like Flask.

app = Flask(__name__)
gateway = Gateway(base_url="https://api.open-meteo.com")

# Register a route (standard StaticFlow logic)
gateway.add_route(
    action="GET_WEATHER",
    path="/v1/forecast",
    method="GET"
)

@app.route('/gateway', methods=['POST'])
def handle_gateway():
    """
    Standard Flask POST endpoint.
    """
    # 1. Get raw dictionary from Flask request
    raw_data = request.get_json()
    
    # 2. Wrap it in the God Schema payload
    payload = StaticPayload(**raw_data)
    
    # 3. Execute the async gateway logic using asyncio.run
    try:
        # Note: In a production Flask app (like with Gunicorn), 
        # using asyncio.run is fine for individual I/O bound calls.
        result = asyncio.run(gateway.route_request(payload))
        return jsonify(result)
    
    except Exception as e:
        # Propagate the correct status code (e.g., 400, 404, 502)
        status_code = getattr(e, "status_code", 500)
        return jsonify({
            "error": str(e),
            "status": "failed"
        }), status_code

if __name__ == "__main__":
    print("🚀 Flask Gateway starting on http://localhost:5000")
    app.run(port=5000, debug=True)
