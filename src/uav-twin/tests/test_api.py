"""Contract tests against the FastAPI app via httpx/TestClient."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _frame(eid=1, seq=1, hot=None):
    egt = [615, 618, 620, 616]
    cht = [178, 176, 177, 177]
    if hot is not None:
        egt[hot] += 55
        cht[hot] += 18
    return {
        "engineId": eid, "timestamp": f"2026-09-09T14:{seq % 60:02d}:00",
        "seq": seq, "cylinderCount": 4, "engineType": "PISTON_CI_TURBO",
        "telemetry": {
            "rpm": 2450, "manifold_pressure": 89.2, "throttle_position_pct": 58,
            "fuel_flow": 32.5, "oil_pressure": 412, "oil_temperature": 92,
            "coolant_temp_c": 88, "intake_air_temp_c": 45,
            "fuel_rail_pressure_bar": 1650,
            "egt_cylinders": egt, "cht_cylinders": cht,
            "vibration": 2.1, "battery_voltage": 24.5,
        },
        "ambient": {"pressure_kpa": 46.5, "temp_c": -18.2,
                    "altitude_ft": 22000, "airspeed_kts": 95},
        "paired": {
            "engineId": 2, "egt_cylinders": [610, 605, 612, 608],
            "cht_cylinders": [174, 173, 175, 172],
            "coolant_temp_c": 86, "oil_pressure": 408,
            "fuel_flow": 31.9, "manifold_pressure": 88.7,
        },
    }


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200 and r.text == "ok"


def test_step_shape_matches_contract():
    client.post("/twin/reset")
    r = client.post("/twin/step", json=_frame())
    assert r.status_code == 200
    b = r.json()
    for key in ("regime", "expected", "residual", "parameters", "parameterSigma",
                "engineDelta", "cylinderSpread", "anomalyScore", "confidence",
                "health", "rul", "diagnosis", "dataSource"):
        assert key in b, f"missing {key}"
    assert b["dataSource"] == "SIMULATED"
    assert set(b["parameters"]) == {
        "volumetric_efficiency", "cooling_factor",
        "boost_capability", "oil_system_health",
    }
    assert "overall" in b["health"] and "limited_by" in b["health"]
    assert b["rul"]["p05_hours"] <= b["rul"]["median_hours"] <= b["rul"]["p95_hours"]
    hyps = b["diagnosis"]["hypotheses"]
    assert len(hyps) >= 2  # lowest-probability alternative always present


def test_step_degrades_gracefully_on_missing_fields():
    client.post("/twin/reset")
    r = client.post("/twin/step", json={"engineId": 7, "telemetry": {}, "ambient": {}})
    assert r.status_code == 200
    assert r.json()["dataSource"] == "SIMULATED"


def test_step_without_paired_still_works():
    client.post("/twin/reset")
    f = _frame()
    f.pop("paired")
    r = client.post("/twin/step", json=f)
    assert r.status_code == 200
    assert r.json()["engineDelta"] == {}


def test_cyl3_outlier_shows_in_spread_and_diagnosis():
    client.post("/twin/reset")
    b = None
    for i in range(40):
        b = client.post("/twin/step", json=_frame(seq=i, hot=2)).json()
    assert b["cylinderSpread"]["hottest_cylinder"] == 3
    top = b["diagnosis"]["hypotheses"][0]["fault"]
    assert "cyl3" in top


def test_simulate_shape():
    client.post("/twin/reset")
    for i in range(10):
        client.post("/twin/step", json=_frame(seq=i))
    r = client.post("/twin/simulate", json={
        "engineId": 1,
        "missionProfile": [
            {"phase": "loiter", "altitude_ft": 22000, "power_pct": 58, "duration_h": 12},
            {"phase": "descent", "altitude_ft": 5000, "power_pct": 30, "duration_h": 0.5},
        ],
        "variants": ["as_planned", "derated_85pct"],
    })
    assert r.status_code == 200
    b = r.json()
    assert b["dataSource"] == "SIMULATED"
    assert len(b["results"]) == 2
    for res in b["results"]:
        assert 0.0 <= res["pComplete"] <= 1.0
        assert "damageConsumed" in res
