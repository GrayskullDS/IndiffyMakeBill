"""Client-side tools: thin wrappers over the FRED API (https://fred.stlouisfed.org)."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

import requests

FRED = "https://api.stlouisfed.org/fred"

# The dashboard behind regime_snapshot: (series_id, FRED units transform, label).
# "pc1" = percent change from a year ago; "lin" = level.
SNAPSHOT = [
    ("CPIAUCSL", "pc1", "CPI inflation, % y/y"),
    ("PCEPILFE", "pc1", "Core PCE inflation, % y/y"),
    ("UNRATE", "lin", "Unemployment rate, %"),
    ("PAYEMS", "pc1", "Nonfarm payrolls, % y/y"),
    ("INDPRO", "pc1", "Industrial production, % y/y"),
    ("FEDFUNDS", "lin", "Effective fed funds rate, %"),
    ("DGS10", "lin", "10y Treasury yield, %"),
    ("T10Y2Y", "lin", "10y-2y curve, pp"),
    ("BAMLH0A0HYM2", "lin", "High-yield OAS, pp"),
    ("SAHMREALTIME", "lin", "Sahm rule indicator, pp"),
]


def _get(path: str, **params) -> dict:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY is not set (free key: https://fred.stlouisfed.org/docs/api/api_key.html)")
    r = requests.get(f"{FRED}/{path}", params={**params, "api_key": key, "file_type": "json"}, timeout=20)
    r.raise_for_status()
    return r.json()


def _observations(series_id: str, units: str, start: str) -> list[tuple[str, float]]:
    data = _get("series/observations", series_id=series_id, units=units, observation_start=start)
    return [(o["date"], float(o["value"])) for o in data["observations"] if o["value"] != "."]


def fred_search(query: str, limit: int = 8) -> str:
    data = _get("series/search", search_text=query, limit=limit, order_by="popularity")
    rows = [
        {"id": s["id"], "title": s["title"], "frequency": s["frequency_short"],
         "units": s["units_short"], "last_updated": s["last_updated"][:10]}
        for s in data["seriess"]
    ]
    return json.dumps(rows)


def fred_series(series_id: str, units: str = "lin", start: str | None = None, max_points: int = 60) -> str:
    start = start or (date.today() - timedelta(days=5 * 365)).isoformat()
    obs = _observations(series_id, units, start)
    if not obs:
        return json.dumps({"series_id": series_id, "error": "no observations in range"})
    values = [v for _, v in obs]
    step = max(1, len(obs) // max_points)  # thin long daily series so they fit in context
    return json.dumps({
        "series_id": series_id, "units": units, "count": len(obs),
        "latest": obs[-1], "min": min(values), "max": max(values),
        "observations": obs[::-1][::step][::-1],
    })


def regime_snapshot() -> str:
    start = (date.today() - timedelta(days=3 * 365)).isoformat()
    out = []
    for sid, units, label in SNAPSHOT:
        try:
            obs = _observations(sid, units, start)
            latest = obs[-1]
            # Compare against roughly six months earlier, whatever the series frequency.
            cutoff = (date.fromisoformat(latest[0]) - timedelta(days=182)).isoformat()
            earlier = next((o for o in reversed(obs) if o[0] <= cutoff), obs[0])
            out.append({"series_id": sid, "label": label, "latest_date": latest[0],
                        "latest": round(latest[1], 2), "six_months_ago": round(earlier[1], 2),
                        "change_6m": round(latest[1] - earlier[1], 2)})
        except Exception as e:  # one dead series shouldn't sink the dashboard
            out.append({"series_id": sid, "label": label, "error": str(e)})
    return json.dumps(out)


# Tool definitions sent to Claude. eager_input_streaming is on because the agent streams.
TOOLS = [
    {
        "name": "regime_snapshot",
        "description": "Fetch a fixed dashboard of US growth, inflation, labor, rates and credit indicators "
                       "from FRED, each with its latest value and 6-month change. Start here for any "
                       "question about the current macro regime.",
        "eager_input_streaming": True,
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "fred_series",
        "description": "Fetch observations for one FRED series. Use units='pc1' for year-over-year % change, "
                       "'pch' for period-over-period % change, 'chg' for absolute change, 'lin' for levels.",
        "eager_input_streaming": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "series_id": {"type": "string", "description": "FRED series ID, e.g. CPIAUCSL"},
                "units": {"type": "string", "enum": ["lin", "chg", "ch1", "pch", "pc1", "pca", "log"]},
                "start": {"type": "string", "description": "Start date YYYY-MM-DD (default: 5 years ago)"},
            },
            "required": ["series_id"],
        },
    },
    {
        "name": "fred_search",
        "description": "Search FRED for series IDs by keyword when you don't know the exact ID.",
        "eager_input_streaming": True,
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

HANDLERS = {"regime_snapshot": regime_snapshot, "fred_series": fred_series, "fred_search": fred_search}

_PY_TYPES = {"string": str, "integer": int, "number": (int, float), "object": dict}


def validate(name: str, args: object) -> str | None:
    """Return an error message if args don't match the tool's schema, else None.

    With eager input streaming the API no longer validates tool input, so we do it here.
    """
    tool = next((t for t in TOOLS if t["name"] == name), None)
    if tool is None:
        return f"unknown tool {name!r}"
    if not isinstance(args, dict):
        return "input must be a JSON object"
    schema = tool["input_schema"]
    props = schema["properties"]
    for key in schema["required"]:
        if key not in args:
            return f"missing required field {key!r}"
    for key, value in args.items():
        if key not in props:
            return f"unexpected field {key!r}"
        if not isinstance(value, _PY_TYPES[props[key]["type"]]):
            return f"field {key!r} must be {props[key]['type']}"
        if "enum" in props[key] and value not in props[key]["enum"]:
            return f"field {key!r} must be one of {props[key]['enum']}"
    return None
