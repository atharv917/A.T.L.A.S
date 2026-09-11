import numpy as np

from app.anomaly import AnomalyDetector
from app.rul import tier1_arrhenius, tier3_onset, RulEngine
from app.config import DEFAULT_ENGINE


def test_anomaly_stays_quiet_on_noise_then_fires_on_sustained_shift():
    rng = np.random.default_rng(0)
    det = AnomalyDetector(dim=4, warmup=40, cusum_threshold_h=5.0)

    fired_during_healthy = False
    for _ in range(120):
        r = det.update(list(rng.normal(0, 1.0, size=4)))
        fired_during_healthy |= r["fired"]
    assert not fired_during_healthy, "must not fire on pure noise"

    # inject a sustained mean shift on one channel
    fired = False
    for _ in range(60):
        v = rng.normal(0, 1.0, size=4)
        v[2] += 8.0
        r = det.update(list(v))
        fired |= r["fired"]
    assert fired, "must fire once a real shift persists"


def test_anomaly_does_not_fire_on_single_spike():
    rng = np.random.default_rng(1)
    det = AnomalyDetector(dim=4, warmup=30, cusum_threshold_h=6.0)
    for _ in range(80):
        det.update(list(rng.normal(0, 1.0, size=4)))
    spike = [0.0, 0.0, 40.0, 0.0]
    r = det.update(spike)
    assert not r["fired"], "one huge sample alone must not trip the gate"


def test_tier1_returns_distribution_not_scalar():
    out = tier1_arrhenius(760.0, 210.0, 0.1, DEFAULT_ENGINE)
    assert out["p05_hours"] <= out["median_hours"] <= out["p95_hours"]
    assert "assumptions" in out and out["tier"] == 1


def test_tier1_hotter_metal_shortens_life():
    cool = tier1_arrhenius(650.0, 180.0, 0.0, DEFAULT_ENGINE)
    hot = tier1_arrhenius(820.0, 240.0, 0.0, DEFAULT_ENGINE)
    assert hot["median_hours"] < cool["median_hours"]


def test_tier3_makes_no_life_claim_flag():
    out = tier3_onset(2.0, -0.01, 0.8, 0.5)
    assert out["assumptions"]["no_physical_life_claim"] is True
    assert out["median_hours"] > 0


def test_rul_engine_reports_most_conservative_tier():
    eng = RulEngine(cfg=DEFAULT_ENGINE)
    for i in range(30):
        eng.accumulate(760, 210, 3600)
        eng.observe_health(max(0.6, 0.95 - i * 0.01))
    rep = eng.report(760, 210, 0.7, "combustion_cyl3", 0.03)
    med = rep["median_hours"]
    assert all(med <= t["median_hours"] for t in rep["all_tiers"])
    assert rep["p05_hours"] <= rep["median_hours"] <= rep["p95_hours"]
