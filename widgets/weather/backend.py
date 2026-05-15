import asyncio
import json
import time
import urllib.request
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

_cache: dict = {}
_CACHE_TTL = 1800  # 30 minutes

WMO: dict[int, tuple[str, str, str]] = {
    0:  ("Clear",               "☀️",  "🌙"),
    1:  ("Mainly clear",        "🌤️",  "🌤️"),
    2:  ("Partly cloudy",       "⛅",  "⛅"),
    3:  ("Overcast",            "☁️",  "☁️"),
    45: ("Fog",                 "🌫️", "🌫️"),
    48: ("Icy fog",             "🌫️", "🌫️"),
    51: ("Light drizzle",       "🌦️", "🌦️"),
    53: ("Drizzle",             "🌦️", "🌦️"),
    55: ("Heavy drizzle",       "🌧️", "🌧️"),
    61: ("Light rain",          "🌧️", "🌧️"),
    63: ("Rain",                "🌧️", "🌧️"),
    65: ("Heavy rain",          "🌧️", "🌧️"),
    71: ("Light snow",          "🌨️", "🌨️"),
    73: ("Snow",                "❄️",  "❄️"),
    75: ("Heavy snow",          "❄️",  "❄️"),
    77: ("Snow grains",         "🌨️", "🌨️"),
    80: ("Light showers",       "🌦️", "🌦️"),
    81: ("Showers",             "🌧️", "🌧️"),
    82: ("Heavy showers",       "⛈️",  "⛈️"),
    85: ("Snow showers",        "🌨️", "🌨️"),
    86: ("Heavy snow showers",  "🌨️", "🌨️"),
    95: ("Thunderstorm",        "⛈️",  "⛈️"),
    96: ("Thunderstorm w/ hail","⛈️",  "⛈️"),
    99: ("Thunderstorm",        "⛈️",  "⛈️"),
}

def _interpret(code: int, is_day: bool = True) -> dict:
    desc, day_icon, night_icon = WMO.get(code, ("Unknown", "❓", "❓"))
    return {"desc": desc, "icon": day_icon if is_day else night_icon}

def _wind_dir(deg) -> str:
    if deg is None:
        return "—"
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]

def _fmt_time(iso_dt: str) -> str:
    """'2024-05-14T07:23' → '7:23 AM'"""
    h, m = map(int, iso_dt[11:].split(":"))
    period = "AM" if h < 12 else "PM"
    return f"{h % 12 or 12}:{m:02d} {period}"

def _fetch(lat: float, lon: float, units: str) -> dict:
    temp_unit = "fahrenheit" if units == "imperial" else "celsius"
    wind_unit = "mph"        if units == "imperial" else "kmh"
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,"
        "relative_humidity_2m,weather_code,wind_speed_10m,is_day"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,wind_speed_10m_max,"
        "wind_direction_10m_dominant,uv_index_max,sunrise,sunset"
        "&hourly=temperature_2m,precipitation_probability"
        f"&temperature_unit={temp_unit}"
        f"&wind_speed_unit={wind_unit}"
        "&timezone=auto"
        "&forecast_days=7"
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


@router.get("/data")
async def get_weather(
    lat:   float = Query(...),
    lon:   float = Query(...),
    units: str   = Query("metric"),
):
    key = (round(lat, 3), round(lon, 3), units)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached["_ts"] < _CACHE_TTL:
        return cached["data"]

    loop = asyncio.get_event_loop()
    try:
        raw = await loop.run_in_executor(None, _fetch, lat, lon, units)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    cur    = raw["current"]
    daily  = raw["daily"]
    hourly = raw["hourly"]

    # Group hourly data by date
    hourly_by_date: dict[str, list] = {}
    for i, t in enumerate(hourly["time"]):
        date = t[:10]
        hourly_by_date.setdefault(date, []).append({
            "hour":       int(t[11:13]),
            "temp":       round(hourly["temperature_2m"][i]),
            "precip_prob": hourly["precipitation_probability"][i] or 0,
        })

    data = {
        "current": {
            "temp":     round(cur["temperature_2m"]),
            "feels":    round(cur["apparent_temperature"]),
            "humidity": cur["relative_humidity_2m"],
            "wind":     round(cur["wind_speed_10m"]),
            **_interpret(cur["weather_code"], bool(cur["is_day"])),
        },
        "forecast": [
            {
                "date":        daily["time"][i],
                "high":        round(daily["temperature_2m_max"][i]),
                "low":         round(daily["temperature_2m_min"][i]),
                "precip_prob": daily["precipitation_probability_max"][i] or 0,
                "wind_max":    round(daily["wind_speed_10m_max"][i] or 0),
                "wind_dir":    _wind_dir(daily["wind_direction_10m_dominant"][i]),
                "uv_max":      round(daily["uv_index_max"][i] or 0, 1),
                "sunrise":     _fmt_time(daily["sunrise"][i]),
                "sunset":      _fmt_time(daily["sunset"][i]),
                "hours":       hourly_by_date.get(daily["time"][i], []),
                **_interpret(daily["weather_code"][i]),
            }
            for i in range(min(7, len(daily["time"])))
        ],
        "units": {
            "temp": "°F" if units == "imperial" else "°C",
            "wind": "mph" if units == "imperial" else "km/h",
        },
    }

    _cache[key] = {"data": data, "_ts": now}
    return data
