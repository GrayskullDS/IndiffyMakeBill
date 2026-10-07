"""Offline tests: FRED and the Claude API are both stubbed."""

import json
from types import SimpleNamespace as NS

import pytest

from macro_agent import agent, tools


@pytest.fixture(autouse=True)
def fake_fred(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test")

    def fake_get(path, **params):
        if path == "series/search":
            return {"seriess": [{"id": "CPIAUCSL", "title": "CPI", "frequency_short": "M",
                                 "units_short": "Index", "last_updated": "2026-09-10 07:44:02"}]}
        months = [f"2025-{m:02d}-01" for m in range(1, 13)] + [f"2026-{m:02d}-01" for m in range(1, 10)]
        return {"observations": [{"date": d, "value": str(2.0 + i / 10)} for i, d in enumerate(months)]
                + [{"date": "2026-10-01", "value": "."}]}

    monkeypatch.setattr(tools, "_get", fake_get)


def test_snapshot_computes_six_month_change():
    rows = json.loads(tools.regime_snapshot())
    assert len(rows) == len(tools.SNAPSHOT)
    cpi = rows[0]
    assert cpi["latest_date"] == "2026-09-01"  # "." missing value skipped
    assert cpi["six_months_ago"] == 3.4 and cpi["change_6m"] == 0.6


def test_series_and_search():
    s = json.loads(tools.fred_series("CPIAUCSL", units="pc1"))
    assert s["latest"] == ["2026-09-01", 4.0] and s["count"] == 21
    assert json.loads(tools.fred_search("cpi"))[0]["id"] == "CPIAUCSL"


@pytest.mark.parametrize("args,ok", [
    ({"series_id": "GDP"}, True),
    ({}, False),
    ({"series_id": 5}, False),
    ({"series_id": "GDP", "units": "bogus"}, False),
    ({"series_id": "GDP", "extra": 1}, False),
])
def test_validate(args, ok):
    assert (tools.validate("fred_series", args) is None) == ok


class FakeStream:
    def __init__(self, response):
        self.response = response
        self.text_stream = [b.text for b in response.content if b.type == "text"]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.response


def test_turn_runs_tools_then_finishes():
    responses = iter([
        NS(stop_reason="tool_use", content=[
            NS(type="text", text="Checking."),
            NS(type="tool_use", id="t1", name="regime_snapshot", input={}),
            NS(type="tool_use", id="t2", name="fred_series", input={"units": "pc1"}),  # invalid
        ]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="Goldilocks.")]),
    ])
    calls = []

    def stream(**kw):
        calls.append(kw)
        return FakeStream(next(responses))

    client = NS(beta=NS(messages=NS(stream=stream)))
    messages = [{"role": "user", "content": "regime?"}]
    agent.turn(client, messages)

    assert calls[0]["fallbacks"] == "default" and calls[0]["model"] == "claude-opus-5-5"
    results = messages[2]["content"]
    assert results[0]["tool_use_id"] == "t1" and "is_error" not in results[0]
    assert results[1]["is_error"] and "series_id" in results[1]["content"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
