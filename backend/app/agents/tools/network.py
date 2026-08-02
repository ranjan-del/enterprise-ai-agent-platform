"""Network-backed tools: ``weather`` and ``github``.

These are the only tools that reach outside the process, so they are handled
differently from the rest:

* They are **disabled by default** (``ALLOW_NETWORK_TOOLS=false``). With the
  flag off they raise a clear ToolError instead of inventing data, which keeps
  the platform honest: an offline install never sees fabricated weather.
* Both endpoints are keyless public APIs (open-meteo.com, api.github.com), so
  enabling them still requires no account and no secret.
* The HTTP call and the response parsing are separate functions. The parsers
  (``parse_forecast``, ``parse_repo``) are pure and are what the tests cover,
  so tool behaviour is verified without any network access.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.agents.tools.base import Tool, ToolContext, ToolError
from app.core.config import settings

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_GITHUB_REPO_URL = "https://api.github.com/repos"

# Open-Meteo returns a WMO weather code; map the common ones to English.
_WMO_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}


def _require_network_enabled(tool: str) -> None:
    if not settings.ALLOW_NETWORK_TOOLS:
        raise ToolError(
            f"the '{tool}' tool needs internet access, which is disabled. "
            "Set ALLOW_NETWORK_TOOLS=true to enable it."
        )


def _get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET a URL and decode JSON, translating every failure into a ToolError."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=settings.NETWORK_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ToolError(f"upstream returned HTTP {exc.code}") from exc
    except Exception as exc:  # network down, DNS failure, bad JSON, timeout
        raise ToolError(f"network request failed: {exc}") from exc


# --- weather ---------------------------------------------------------------


def parse_forecast(location: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Turn an Open-Meteo forecast payload into the tool's result shape."""
    current = payload.get("current") or {}
    if "temperature_2m" not in current:
        raise ToolError("forecast response did not contain current conditions")
    code = int(current.get("weather_code", -1))
    return {
        "location": location,
        "temperature_c": current.get("temperature_2m"),
        "wind_kph": current.get("wind_speed_10m"),
        "conditions": _WMO_CODES.get(code, "unknown"),
        "observed_at": current.get("time"),
    }


def _weather(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _require_network_enabled("weather")
    location = str(params.get("location", "")).strip()
    if not location:
        raise ToolError("weather requires a 'location'")

    geo = _get_json(_GEOCODE_URL, {"name": location, "count": 1, "format": "json"})
    results = (geo or {}).get("results") or []
    if not results:
        raise ToolError(f"could not find a place called '{location}'")
    place = results[0]

    forecast = _get_json(
        _FORECAST_URL,
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,weather_code,wind_speed_10m",
        },
    )
    return parse_forecast(place.get("name", location), forecast)


# --- github ----------------------------------------------------------------


def parse_repo(payload: dict[str, Any]) -> dict[str, Any]:
    """Turn a GitHub repository payload into the tool's result shape."""
    if "full_name" not in payload:
        raise ToolError("repository response was not in the expected shape")
    return {
        "repo": payload["full_name"],
        "description": payload.get("description") or "",
        "stars": payload.get("stargazers_count", 0),
        "forks": payload.get("forks_count", 0),
        "open_issues": payload.get("open_issues_count", 0),
        "language": payload.get("language") or "unknown",
        "url": payload.get("html_url", ""),
    }


def _github(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _require_network_enabled("github")
    repo = str(params.get("repo", "")).strip().strip("/")
    if repo.count("/") != 1 or not all(part for part in repo.split("/")):
        raise ToolError("github requires a 'repo' in the form 'owner/name'")
    owner, name = repo.split("/")
    payload = _get_json(
        f"{_GITHUB_REPO_URL}/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}"
    )
    return parse_repo(payload)


weather_tool = Tool(
    name="weather",
    description="Current conditions for a place, via the keyless Open-Meteo API "
    "(requires ALLOW_NETWORK_TOOLS=true).",
    parameters={"location": "Place name, e.g. 'Bengaluru'"},
    run=_weather,
    examples=['{"location": "Bengaluru"}'],
    requires_network=True,
)

github_tool = Tool(
    name="github",
    description="Public repository facts (stars, forks, issues, language) from "
    "the GitHub REST API (requires ALLOW_NETWORK_TOOLS=true).",
    parameters={"repo": "Repository in 'owner/name' form"},
    run=_github,
    examples=['{"repo": "fastapi/fastapi"}'],
    requires_network=True,
)
