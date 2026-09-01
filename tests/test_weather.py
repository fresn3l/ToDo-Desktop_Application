"""Weather widget: place settings, WMO labels, rain chance, cache."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import weather


class WeatherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_wmo_labels_and_units(self) -> None:
        self.assertEqual(weather.weather_label(61), "Light rain")
        self.assertEqual(weather.weather_label(0), "Clear")
        self.assertEqual(weather.weather_label("nope"), "Unknown")
        self.assertEqual(weather.coerce_units("c"), "celsius")
        self.assertEqual(weather.coerce_units("F"), "fahrenheit")

    def test_sanitize_rejects_bad_coordinates(self) -> None:
        packed = weather.sanitize_settings(
            {"place": "X", "latitude": 200, "longitude": 0, "units": "celsius"}
        )
        self.assertIsNone(packed["latitude"])
        packed = weather.sanitize_settings(
            {"place": "Ann Arbor", "admin": "Michigan", "country": "United States", "latitude": 42.28, "longitude": -83.74}
        )
        self.assertEqual(packed["place"], "Ann Arbor")
        self.assertEqual(packed["latitude"], 42.28)

    def test_next_rain_picks_first_likely_hour(self) -> None:
        hourly = [
            {"hour": "1pm", "precip_chance": 10, "label": "Clear"},
            {"hour": "2pm", "precip_chance": 55, "label": "Rain"},
            {"hour": "3pm", "precip_chance": 80, "label": "Rain"},
        ]
        rain = weather.next_rain(hourly)
        self.assertEqual(rain["at"], "2pm")
        self.assertEqual(rain["chance"], 55)
        self.assertIsNone(weather.next_rain([{"hour": "1pm", "precip_chance": 10}]))

    def test_normalize_builds_hourly_and_daily(self) -> None:
        payload = {
            "current": {
                "temperature_2m": 71.2,
                "apparent_temperature": 69.4,
                "weather_code": 61,
                "relative_humidity_2m": 64,
                "wind_speed_10m": 8.2,
            },
            "hourly": {
                "time": ["2026-09-01T18:00", "2026-09-01T19:00", "2026-09-01T20:00"],
                "temperature_2m": [71, 69, 66],
                "precipitation_probability": [20, 48, 70],
                "weather_code": [2, 61, 63],
            },
            "daily": {
                "time": ["2026-09-01", "2026-09-02"],
                "temperature_2m_max": [74.1, 68.0],
                "temperature_2m_min": [54.6, 51.2],
                "precipitation_probability_max": [70, 20],
                "weather_code": [61, 2],
            },
        }
        settings = weather.sanitize_settings(
            {"place": "Ann Arbor", "latitude": 42.28, "longitude": -83.74, "units": "fahrenheit"}
        )
        now = datetime(2026, 9, 1, 17, 50)
        out = weather.normalize_forecast(payload, settings, now=now)
        self.assertTrue(out["ok"])
        self.assertEqual(out["current"]["temp"], 71)
        self.assertEqual(out["current"]["label"], "Light rain")
        self.assertEqual(out["hourly"][0]["precip_chance"], 20)
        self.assertEqual(out["next_rain"]["chance"], 48)
        self.assertEqual(out["daily"][0]["day"], "Today")
        self.assertEqual(out["daily"][0]["precip_chance"], 70)
        self.assertEqual(out["unit_symbol"], "°F")

    def test_search_and_forecast_go_through_python(self) -> None:
        geocode = {
            "results": [
                {
                    "name": "Ann Arbor",
                    "admin1": "Michigan",
                    "country": "United States",
                    "latitude": 42.2808,
                    "longitude": -83.743,
                    "timezone": "America/Detroit",
                }
            ]
        }
        forecast_payload = {
            "current": {"temperature_2m": 64, "weather_code": 0, "apparent_temperature": 62, "relative_humidity_2m": 40, "wind_speed_10m": 5},
            "hourly": {
                "time": ["2026-09-01T18:00"],
                "temperature_2m": [64],
                "precipitation_probability": [5],
                "weather_code": [0],
            },
            "daily": {
                "time": ["2026-09-01"],
                "temperature_2m_max": [74],
                "temperature_2m_min": [52],
                "precipitation_probability_max": [10],
                "weather_code": [0],
            },
        }

        def fake_fetch(url: str):
            self.assertIn("open-meteo.com", url)
            if "geocoding-api" in url:
                return geocode
            return forecast_payload

        frozen = datetime(2026, 9, 1, 17, 50)
        with mock.patch.object(weather, "fetch_json", side_effect=fake_fetch), mock.patch.object(
            weather, "_now", return_value=frozen
        ):
            places = weather.search_weather_places("Ann Arbor")
            self.assertEqual(places[0]["place"], "Ann Arbor")
            out = weather.set_weather_place(places[0])
            self.assertTrue(out["ok"])
            self.assertEqual(out["current"]["temp"], 64)
            self.assertTrue((self.root / "weather_settings.json").exists())
            self.assertTrue((self.root / "weather_cache.json").exists())
            with mock.patch.object(weather, "fetch_json") as fetch:
                cached = weather.get_weather_forecast()
                fetch.assert_not_called()
            self.assertTrue(cached["cached"])

    def test_missing_place_asks_for_one(self) -> None:
        out = weather.get_weather_forecast()
        self.assertFalse(out["ok"])
        self.assertTrue(out["need_place"])

    def test_host_allowlist(self) -> None:
        with self.assertRaises(ValueError):
            weather.fetch_json("https://example.com/v1/forecast")
