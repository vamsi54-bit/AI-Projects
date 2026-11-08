import requests

# district -> (latitude, longitude), district level only (matches the privacy design)
DISTRICTS = {
    "Not specified": None,
    "Alluri Sitharama Raju": (18.08, 82.67),
    "Anakapalli": (17.69, 83.00),
    "Anantapur": (14.68, 77.60),
    "Annamayya": (14.05, 78.75),
    "Bapatla": (15.90, 80.47),
    "Chittoor": (13.22, 79.10),
    "East Godavari": (17.00, 81.80),
    "Eluru": (16.71, 81.10),
    "Guntur": (16.30, 80.44),
    "Kadapa": (14.47, 78.82),
    "Kakinada": (16.99, 82.25),
    "Konaseema": (16.58, 82.01),
    "Krishna": (16.19, 81.14),
    "Kurnool": (15.83, 78.04),
    "Nandyal": (15.48, 78.48),
    "Nellore": (14.44, 79.99),
    "NTR": (16.51, 80.65),
    "Palnadu": (16.24, 80.05),
    "Parvathipuram Manyam": (18.78, 83.43),
    "Prakasam": (15.50, 80.05),
    "Sri Sathya Sai": (14.17, 77.81),
    "Srikakulam": (18.30, 83.90),
    "Tirupati": (13.63, 79.42),
    "Visakhapatnam": (17.69, 83.22),
    "Vizianagaram": (18.11, 83.40),
    "West Godavari": (16.54, 81.52),
}

_cache = {}


def get_weather(district: str):
    """Returns (display_text, note_for_llm). Both empty if unavailable."""
    coords = DISTRICTS.get(district)
    if not coords:
        return "", ""
    if district in _cache:
        return _cache[district]
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords[0],
                "longitude": coords[1],
                "current": "temperature_2m,relative_humidity_2m",
                "daily": "precipitation_sum,precipitation_probability_max",
                "forecast_days": 3,
                "timezone": "Asia/Kolkata",
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        temp = d["current"]["temperature_2m"]
        hum = d["current"]["relative_humidity_2m"]
        rain_mm = sum(x or 0 for x in d["daily"]["precipitation_sum"])
        rain_prob = max(x or 0 for x in d["daily"]["precipitation_probability_max"])

        if hum >= 80 and (rain_prob >= 50 or rain_mm >= 5):
            risk = "HIGH"
        elif hum >= 70 or rain_prob >= 40:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        text = (f"{district}: {temp:.0f}°C, humidity {hum:.0f}%, "
                f"rain next 3 days {rain_mm:.0f} mm (chance up to {rain_prob:.0f}%). "
                f"Fungal disease risk: {risk}.")
        note = (f"Weather in {district} district: {temp:.0f}C, humidity {hum:.0f}%, "
                f"{rain_mm:.0f} mm rain expected in the next 3 days, fungal risk {risk}.")
        _cache[district] = (text, note)
        return text, note
    except Exception as e:
        print("Weather error:", repr(e))
        return "", ""