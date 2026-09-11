from app.regime import RegimeTracker, classify_instant


def test_classify_instant_basic():
    assert classify_instant(0, 0, 0) == "SHUTDOWN"
    assert classify_instant(2500, 90, 800) in ("CLIMB", "TAKEOFF")
    assert classify_instant(2500, 120, -600) == "DESCENT"
    assert classify_instant(1900, 92, 0) == "LOITER"


def test_hysteresis_requires_persistence():
    tr = RegimeTracker(hold_n=4)
    # settle into LOITER
    for _ in range(6):
        tr.update(1900, 92, 0)
    assert tr.current == "LOITER"
    # a single climb sample must NOT flip the regime
    tr.update(2600, 95, 700)
    assert tr.current == "LOITER"
    # sustained climb eventually does
    for _ in range(5):
        tr.update(2600, 95, 700)
    assert tr.current in ("CLIMB", "TAKEOFF")


def test_shutdown_switches_immediately():
    tr = RegimeTracker(hold_n=6)
    for _ in range(6):
        tr.update(1900, 92, 0)
    tr.update(0, 0, 0)
    assert tr.current == "SHUTDOWN"
