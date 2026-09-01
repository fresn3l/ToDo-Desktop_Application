"""
Home weather widget — Open-Meteo forecast, cached locally.

Place and units stay on this computer. The browser never talks to the
weather host; Python fetches over HTTPS and hands the UI a small payload.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import eel

from paths import data_directory

GEOCODE_HOST = "geocoding-api.open-meteo.com"
FORECAST_HOST = "api.open-meteo.com"
CACHE_MINUTES = 20
MAX_BODY = 400_000
MAX_QUERY = 80
USER_AGENT = "Kosistenz/1.0 (local weather widget)"

WMO_LABELS = {
    0: "Clear",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}


def _settings_path():
    return data_directory() / "weather_settings.json"


def _cache_path():
    return data_directory() / "weather_cache.json"


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _write_json(path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp, path)


def _read_json(path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def default_settings() -> Dict[str, Any]:
    return {
        "place": "",
        "admin": "",
        "country": "",
        "latitude": None,
        "longitude": None,
        "timezone": "",
        "units": "fahrenheit",
    }


def coerce_units(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text in ("c", "celsius", "metric"):
        return "celsius"
    return "fahrenheit"


def weather_label(code: Any) -> str:
    try:
        key = int(code)
    except (TypeError, ValueError):
        return "Unknown"
    return WMO_LABELS.get(key, "Unknown")


def sanitize_settings(raw: Any) -> Dict[str, Any]:
    base = default_settings()
    if not isinstance(raw, dict):
        return base
    base["place"] = str(raw.get("place") or "").strip()[:MAX_QUERY]
    base["admin"] = str(raw.get("admin") or "").strip()[:MAX_QUERY]
    base["country"] = str(raw.get("country") or "").strip()[:MAX_QUERY]
    base["timezone"] = str(raw.get("timezone") or "").strip()[:80]
    base["units"] = coerce_units(raw.get("units"))
    try:
        lat = float(raw.get("latitude"))
        lon = float(raw.get("longitude"))
    except (TypeError, ValueError):
        return {**base, "latitude": None, "longitude": None}
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return {**base, "latitude": None, "longitude": None}
    base["latitude"] = round(lat, 4)
    base["longitude"] = round(lon, 4)
    return base


def load_settings() -> Dict[str, Any]:
    return sanitize_settings(_read_json(_settings_path()))


def save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    packed = sanitize_settings(settings)
    _write_json(_settings_path(), packed)
    return packed


def has_place(settings: Optional[Dict[str, Any]] = None) -> bool:
    packed = settings if settings is not None else load_settings()
    return packed.get("latitude") is not None and packed.get("longitude") is not None


def place_label(settings: Dict[str, Any]) -> str:
    name = settings.get("place") or "Unknown place"
    admin = settings.get("admin") or ""
    country = settings.get("country") or ""
    bits = [name]
    if admin and admin != name:
        bits.append(admin)
    if country and country not in bits:
        bits.append(country)
    return ", ".join(bits)


def _allowed_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {GEOCODE_HOST, FORECAST_HOST}


def fetch_json(url: str) -> Dict[str, Any]:
    if not _allowed_host(url):
        raise ValueError("Unexpected weather host")
    req = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    with urlopen(req, timeout=12) as resp:
        data = resp.read(MAX_BODY + 1)
    if len(data) > MAX_BODY:
        raise ValueError("Weather response is too large")
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Weather response was not an object")
    return parsed


def search_places(query: str) -> List[Dict[str, Any]]:
    q = str(query or "").strip()[:MAX_QUERY]
    if len(q) < 2:
        return []
    url = "https://{host}/v1/search?{qs}".format(
        host=GEOCODE_HOST,
        qs=urlencode({"name": q, "count": 6, "language": "en", "format": "json"}),
    )
    payload = fetch_json(url)
    rows = payload.get("results")
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            lat = float(row.get("latitude"))
            lon = float(row.get("longitude"))
        except (TypeError, ValueError):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        out.append(
            {
                "place": name[:MAX_QUERY],
                "admin": str(row.get("admin1") or "").strip()[:MAX_QUERY],
                "country": str(row.get("country") or "").strip()[:MAX_QUERY],
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "timezone": str(row.get("timezone") or "").strip()[:80],
                "label": place_label(
                    {
                        "place": name,
                        "admin": row.get("admin1") or "",
                        "country": row.get("country") or "",
                    }
                ),
            }
        )
    return out


def _hourly_pairs(raw: Dict[str, Any], key: str) -> List[Tuple[str, Any]]:
    hours = raw.get("time")
    values = raw.get(key)
    if not isinstance(hours, list) or not isinstance(values, list):
        return []
    pairs = []
    for stamp, value in zip(hours, values):
        if not isinstance(stamp, str):
            continue
        pairs.append((stamp, value))
    return pairs


def _parse_local(stamp: str) -> Optional[datetime]:
    text = str(stamp or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def next_rain(hourly: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """First hour in the next 12 with a meaningful chance of rain."""
    for row in hourly[:12]:
        try:
            chance = int(row.get("precip_chance") or 0)
        except (TypeError, ValueError):
            chance = 0
        if chance >= 40:
            return {
                "at": row.get("hour") or "",
                "chance": chance,
                "label": row.get("label") or "",
            }
    return None


def _hour_label(stamp: str) -> str:
    parsed = _parse_local(stamp)
    if parsed is None:
        return stamp
    hour = parsed.strftime("%I").lstrip("0") or "12"
    ampm = parsed.strftime("%p").lower()
    return f"{hour}{ampm}"


def _day_label(stamp: str, today: datetime) -> str:
    parsed = _parse_local(stamp)
    if parsed is None:
        return stamp
    if parsed.date() == today.date():
        return "Today"
    if parsed.date() == (today + timedelta(days=1)).date():
        return "Tomorrow"
    return parsed.strftime("%a")


def normalize_forecast(
    payload: Dict[str, Any],
    settings: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or _now()
    current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
    hourly_raw = payload.get("hourly") if isinstance(payload.get("hourly"), dict) else {}
    daily_raw = payload.get("daily") if isinstance(payload.get("daily"), dict) else {}

    temps = dict(_hourly_pairs(hourly_raw, "temperature_2m"))
    chances = dict(_hourly_pairs(hourly_raw, "precipitation_probability"))
    codes = dict(_hourly_pairs(hourly_raw, "weather_code"))

    hourly: List[Dict[str, Any]] = []
    for stamp, chance in chances.items():
        parsed = _parse_local(stamp)
        if parsed is None or parsed < now - timedelta(minutes=30):
            continue
        try:
            chance_n = int(chance) if chance is not None else 0
        except (TypeError, ValueError):
            chance_n = 0
        temp = temps.get(stamp)
        try:
            temp_n = round(float(temp)) if temp is not None else None
        except (TypeError, ValueError):
            temp_n = None
        hourly.append(
            {
                "at": stamp,
                "hour": _hour_label(stamp),
                "temp": temp_n,
                "precip_chance": max(0, min(100, chance_n)),
                "code": codes.get(stamp),
                "label": weather_label(codes.get(stamp)),
            }
        )
        if len(hourly) >= 12:
            break

    daily: List[Dict[str, Any]] = []
    days = daily_raw.get("time") if isinstance(daily_raw.get("time"), list) else []
    highs = daily_raw.get("temperature_2m_max") if isinstance(daily_raw.get("temperature_2m_max"), list) else []
    lows = daily_raw.get("temperature_2m_min") if isinstance(daily_raw.get("temperature_2m_min"), list) else []
    day_chance = daily_raw.get("precipitation_probability_max") if isinstance(daily_raw.get("precipitation_probability_max"), list) else []
    day_code = daily_raw.get("weather_code") if isinstance(daily_raw.get("weather_code"), list) else []
    for i, stamp in enumerate(days[:7]):
        if not isinstance(stamp, str):
            continue
        try:
            high = round(float(highs[i])) if i < len(highs) and highs[i] is not None else None
        except (TypeError, ValueError, IndexError):
            high = None
        try:
            low = round(float(lows[i])) if i < len(lows) and lows[i] is not None else None
        except (TypeError, ValueError, IndexError):
            low = None
        try:
            chance_n = int(day_chance[i]) if i < len(day_chance) and day_chance[i] is not None else 0
        except (TypeError, ValueError):
            chance_n = 0
        code = day_code[i] if i < len(day_code) else None
        daily.append(
            {
                "at": stamp,
                "day": _day_label(stamp, now),
                "high": high,
                "low": low,
                "precip_chance": max(0, min(100, chance_n)),
                "label": weather_label(code),
            }
        )

    try:
        temp_now = round(float(current.get("temperature_2m")))
    except (TypeError, ValueError):
        temp_now = hourly[0]["temp"] if hourly else None
    try:
        feels = round(float(current.get("apparent_temperature")))
    except (TypeError, ValueError):
        feels = temp_now
    try:
        humidity = int(current.get("relative_humidity_2m"))
    except (TypeError, ValueError):
        humidity = None
    try:
        wind = round(float(current.get("wind_speed_10m")))
    except (TypeError, ValueError):
        wind = None

    code = current.get("weather_code")
    if code is None and hourly:
        code = hourly[0].get("code")
    precip_now = hourly[0]["precip_chance"] if hourly else 0

    rain = next_rain(hourly)
    return {
        "ok": True,
        "fetched_at": now.isoformat(),
        "units": settings["units"],
        "unit_symbol": "°F" if settings["units"] == "fahrenheit" else "°C",
        "wind_unit": "mph" if settings["units"] == "fahrenheit" else "km/h",
        "place": place_label(settings),
        "timezone": settings.get("timezone") or "",
        "current": {
            "temp": temp_now,
            "feels": feels,
            "humidity": humidity,
            "wind": wind,
            "code": code,
            "label": weather_label(code),
            "precip_chance": precip_now,
        },
        "hourly": hourly,
        "daily": daily,
        "next_rain": rain,
    }


def _forecast_url(settings: Dict[str, Any]) -> str:
    units = settings["units"]
    qs = urlencode(
        {
            "latitude": settings["latitude"],
            "longitude": settings["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code,relative_humidity_2m,wind_speed_10m,precipitation",
            "hourly": "temperature_2m,precipitation_probability,weather_code,precipitation",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "forecast_days": 7,
            "timezone": settings.get("timezone") or "auto",
            "temperature_unit": units,
            "wind_speed_unit": "mph" if units == "fahrenheit" else "kmh",
            "precipitation_unit": "inch" if units == "fahrenheit" else "mm",
        }
    )
    return f"https://{FORECAST_HOST}/v1/forecast?{qs}"


def _cache_fresh(cache: Dict[str, Any], settings: Dict[str, Any], now: datetime) -> bool:
    if not cache:
        return False
    if cache.get("units") != settings["units"]:
        return False
    if cache.get("latitude") != settings["latitude"] or cache.get("longitude") != settings["longitude"]:
        return False
    stamp = str(cache.get("fetched_at") or "")
    parsed = _parse_local(stamp)
    if parsed is None:
        return False
    return now - parsed <= timedelta(minutes=CACHE_MINUTES)


def load_forecast(force: bool = False) -> Dict[str, Any]:
    settings = load_settings()
    if not has_place(settings):
        return {"ok": False, "need_place": True, "settings": settings}
    now = _now()
    cache = _read_json(_cache_path())
    if not force and _cache_fresh(cache, settings, now) and isinstance(cache.get("forecast"), dict):
        forecast = cache["forecast"]
        forecast["cached"] = True
        forecast["settings"] = settings
        return forecast
    try:
        payload = fetch_json(_forecast_url(settings))
        forecast = normalize_forecast(payload, settings, now=now)
    except Exception as exc:
        stale = cache.get("forecast") if isinstance(cache.get("forecast"), dict) else None
        if stale:
            stale = dict(stale)
            stale["ok"] = True
            stale["cached"] = True
            stale["stale"] = True
            stale["error"] = str(exc)
            stale["settings"] = settings
            return stale
        return {
            "ok": False,
            "need_place": False,
            "error": str(exc),
            "settings": settings,
        }
    _write_json(
        _cache_path(),
        {
            "fetched_at": now.isoformat(),
            "latitude": settings["latitude"],
            "longitude": settings["longitude"],
            "units": settings["units"],
            "forecast": forecast,
        },
    )
    forecast["cached"] = False
    forecast["settings"] = settings
    return forecast


@eel.expose
def get_weather_settings() -> Dict[str, Any]:
    packed = load_settings()
    packed["label"] = place_label(packed) if has_place(packed) else ""
    packed["has_place"] = has_place(packed)
    return packed


@eel.expose
def search_weather_places(query: str) -> List[Dict[str, Any]]:
    return search_places(query)


@eel.expose
def set_weather_place(place: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings()
    packed = sanitize_settings({**current, **(place if isinstance(place, dict) else {})})
    if not has_place(packed):
        raise ValueError("Pick a place with a map location")
    save_settings(packed)
    return load_forecast(force=True)


@eel.expose
def set_weather_units(units: str) -> Dict[str, Any]:
    current = load_settings()
    current["units"] = coerce_units(units)
    save_settings(current)
    if not has_place(current):
        packed = get_weather_settings()
        return {"ok": False, "need_place": True, "settings": packed}
    return load_forecast(force=True)


@eel.expose
def get_weather_forecast(force: bool = False) -> Dict[str, Any]:
    return load_forecast(force=bool(force))
