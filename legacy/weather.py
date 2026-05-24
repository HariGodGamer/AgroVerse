import requests

WEATHER_API_KEY = "0d8a42b258ff46f6b3b111338260304"
WEATHER_BASE_URL = "http://api.weatherapi.com/v1/current.json"


def get_weather_by_coords(lat: float, lon: float) -> dict:
    
    try:
        r = requests.get(
            f"{WEATHER_BASE_URL}?key={WEATHER_API_KEY}&q={lat},{lon}",
            timeout=10
        )
        data = r.json()
    except Exception as e:
        return {"error": str(e)}

    if "error" in data:
        return {"error": data["error"]["message"]}

    c = data["current"]
    loc = data["location"]

    temp   = c["temp_c"]
    hum    = c["humidity"]
    wind   = c["wind_kph"]
    rain   = c["precip_mm"]
    uv     = c["uv"]
    vis    = c["vis_km"]

    return {
        "location":    f"{loc['name']}, {loc['region']}, {loc['country']}",
        "condition":   c["condition"]["text"],
        "icon":        c["condition"]["icon"],
        "temperature": temp,
        "humidity":    hum,
        "wind_speed":  wind,
        "rain":        rain,
        "uv_index":    uv,
        "visibility":  vis,
        
        "bars": {
            "temp":       min(100, max(0, round((temp + 10) / 60 * 100))),
            "humidity":   int(hum),
            "wind":       min(100, round(wind)),
            "rain":       min(100, round(rain / 50 * 100)),
            "uv":         min(100, round(uv / 12 * 100)),
            "visibility": min(100, round(vis / 20 * 100)),
        },
    }
