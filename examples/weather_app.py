import uvicorn
from fastapi import FastAPI, Request, Response
from typing import Optional, Any
from pydantic import BaseModel
from staticfloww import Gateway, StaticPayload, Section

# 1. Define our specific God Schema Sections
class LocationSection(Section):
    city: str

class WeatherPayload(StaticPayload):
    Location: Optional[LocationSection] = None

# 2. Define how our frontend wants the data (Validation Model)
class CleanWeatherRes(BaseModel):
    city: str
    temperature: float
    windspeed: float
    condition_code: int

# 3. Business Logic Hook: Translate City -> Coordinates
async def geocode_city(data: LocationSection, **kwargs):
    print(f"--- [Hook] Geocoding city: {data.city} ---")
    city_map = {
        "Nairobi": {"latitude": -1.2863, "longitude": 36.8172},
        "London": {"latitude": 51.5074, "longitude": -0.1278},
        "New York": {"latitude": 40.7128, "longitude": -74.0060},
        "Tokyo": {"latitude": 35.6895, "longitude": 139.6917}
    }
    coords = city_map.get(data.city, city_map["Nairobi"])
    return {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "current_weather": "true"
    }

# 4. Response Hook: Clean up Open-Meteo's nested JSON
async def format_weather(raw: dict, **kwargs) -> dict:
    print(f"--- [Hook] Formatting response for {kwargs.get('city_name')} ---")
    current = raw["current_weather"]
    return {
        "city": kwargs.get("city_name", "Unknown"),
        "temperature": current["temperature"],
        "windspeed": current["windspeed"],
        "condition_code": current["weathercode"]
    }

# --- Gateway Setup ---
app = FastAPI(title="StaticFlow Weather Gateway")
gateway = Gateway(base_url="https://api.open-meteo.com")

gateway.add_route(
    action="GET_WEATHER",
    path="/v1/forecast",
    method="GET",
    extract="Location",
    before_request=geocode_city,
    after_response=format_weather,
    response_model=CleanWeatherRes
)

@app.post("/gateway")
async def handle_gateway(payload: WeatherPayload, response: Response):
    """
    Single entry point for all frontend actions.
    """
    city = payload.Location.city if payload.Location else "Nairobi"
    
    try:
        result = await gateway.route_request(
            payload, 
            city_name=city
        )
        return result
    except Exception as e:
        # Extract status code if available (all StaticFlow errors have one)
        status_code = getattr(e, "status_code", 500)
        response.status_code = status_code
        return {"error": str(e), "status": "failed"}

if __name__ == "__main__":
    print("🚀 StaticFlow Weather Gateway starting on http://localhost:8000")
    print("📍 Try POSTing to /gateway with: {'details': {'type': 'GET_WEATHER'}, 'Location': {'city': 'London'}}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
