"""API-layer tests for the GridWise FastAPI service.

Covers:
- /health happy path
- invalid JSON body -> 400
- 23 hours -> 400
- 0 operator notes -> 400
- 4 operator notes -> 400
- duplicate hour index -> 400
- valid public sample -> 200 with the required top-level keys and a 24-entry
  hourly_plan whose `note_index` (via the directives list) is preserved by the
  interpretation order.

The tests use FastAPI's TestClient, so no live server is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = json.loads((ROOT / "data" / "public_samples.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _valid_sample() -> dict:
    """Return the input payload for SAMPLE-01 from the public sample pack."""
    case = next(c for c in SAMPLES["cases"] if c["id"] == "SAMPLE-01")
    return case["input"]


def _make_hours() -> list[dict]:
    """Build a minimal valid 24-hour list with the required fields."""
    return [
        {
            "hour": h,
            "demand_kwh": 100.0,
            "solar_kwh": 10.0,
            "tariff_bdt_per_kwh": 8.0,
        }
        for h in range(24)
    ]


def _battery() -> dict:
    return {
        "capacity_kwh": 200.0,
        "initial_energy_kwh": 100.0,
        "minimum_energy_kwh": 20.0,
        "max_charge_kwh_per_hour": 50.0,
        "max_discharge_kwh_per_hour": 50.0,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Malformed body
# ---------------------------------------------------------------------------

def test_invalid_json_returns_400(client: TestClient) -> None:
    response = client.post(
        "/optimize-energy",
        content="this is not json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body == {"error": "invalid request"}


def test_missing_required_field_returns_400(client: TestClient) -> None:
    # scenario_id is missing entirely
    response = client.post(
        "/optimize-energy",
        json={"operator_notes": ["x"], "hours": _make_hours(), "battery": _battery()},
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


# ---------------------------------------------------------------------------
# Hours length / content
# ---------------------------------------------------------------------------

def test_twenty_three_hours_returns_400(client: TestClient) -> None:
    payload = {
        "scenario_id": "BAD-23",
        "operator_notes": ["keep running"],
        "hours": _make_hours()[:23],
        "battery": _battery(),
    }
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_duplicate_hour_returns_400(client: TestClient) -> None:
    hours = _make_hours()
    hours[5] = {**hours[5], "hour": 0}  # duplicate hour 0
    payload = {
        "scenario_id": "DUP-HOUR",
        "operator_notes": ["keep running"],
        "hours": hours,
        "battery": _battery(),
    }
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


# ---------------------------------------------------------------------------
# Operator notes count
# ---------------------------------------------------------------------------

def test_zero_notes_returns_400(client: TestClient) -> None:
    payload = {
        "scenario_id": "ZERO",
        "operator_notes": [],
        "hours": _make_hours(),
        "battery": _battery(),
    }
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_four_notes_returns_400(client: TestClient) -> None:
    payload = {
        "scenario_id": "FOUR",
        "operator_notes": ["note one", "note two", "note three", "note four"],
        "hours": _make_hours(),
        "battery": _battery(),
    }
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_blank_note_returns_400(client: TestClient) -> None:
    payload = {
        "scenario_id": "BLANK",
        "operator_notes": ["keep running", "   "],
        "hours": _make_hours(),
        "battery": _battery(),
    }
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


# ---------------------------------------------------------------------------
# Valid sample
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL_KEYS = {
    "scenario_id",
    "directive_interpretation",
    "hourly_plan",
    "total_grid_kwh",
    "total_cost_bdt",
    "peak_grid_kwh",
    "plan_summary",
}

REQUIRED_DIRECTIVE_KEYS = {
    "note_index",
    "applies",
    "directive_type",
    "structured_adjustment",
    "explanation",
}

REQUIRED_HOURLY_KEYS = {
    "hour",
    "grid_kwh",
    "solar_used_kwh",
    "battery_action",
    "battery_kwh",
    "battery_energy_after_kwh",
}


def test_valid_sample_returns_200_with_required_shape(client: TestClient) -> None:
    payload = _valid_sample()
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 200, response.text

    body = response.json()
    # top-level keys
    assert set(body) >= REQUIRED_TOP_LEVEL_KEYS, set(body)
    assert body["scenario_id"] == "SAMPLE-01"

    # directive_interpretation: length matches input notes, in note_index order
    interpretation = body["directive_interpretation"]
    assert isinstance(interpretation, list)
    assert len(interpretation) == len(payload["operator_notes"])
    for i, entry in enumerate(interpretation):
        assert set(entry) >= REQUIRED_DIRECTIVE_KEYS, entry
        assert entry["note_index"] == i, interpretation

    # hourly_plan: 24 entries, sorted by hour
    plan = body["hourly_plan"]
    assert isinstance(plan, list)
    assert len(plan) == 24
    hours = [row["hour"] for row in plan]
    assert hours == sorted(hours) == list(range(24))
    for row in plan:
        assert set(row) >= REQUIRED_HOURLY_KEYS, row

    # totals are numeric
    assert isinstance(body["total_grid_kwh"], (int, float))
    assert isinstance(body["total_cost_bdt"], (int, float))
    assert isinstance(body["peak_grid_kwh"], (int, float))
    assert body["peak_grid_kwh"] >= 0

    # plan_summary is a non-empty string
    assert isinstance(body["plan_summary"], str)
    assert body["plan_summary"].strip()


def test_valid_sample_three_notes_preserves_index_order(client: TestClient) -> None:
    """Pick a sample that has 3 operator notes and verify note_index 0/1/2."""
    three_note_cases = [c for c in SAMPLES["cases"] if len(c["input"]["operator_notes"]) == 3]
    assert three_note_cases, "expected at least one 3-note public sample"

    case = three_note_cases[0]
    response = client.post("/optimize-energy", json=case["input"])
    assert response.status_code == 200, response.text

    interpretation = response.json()["directive_interpretation"]
    assert len(interpretation) == 3
    assert [entry["note_index"] for entry in interpretation] == [0, 1, 2]


def test_valid_sample_battery_invariant(client: TestClient) -> None:
    """battery_energy_after_kwh must always be inside [minimum, capacity]."""
    payload = _valid_sample()
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 200, response.text

    bmin = payload["battery"]["minimum_energy_kwh"]
    cap = payload["battery"]["capacity_kwh"]
    for row in response.json()["hourly_plan"]:
        assert bmin <= row["battery_energy_after_kwh"] <= cap + 1e-6, row
