"""Flight-phase (regime) detection with hysteresis.

WHY hysteresis: raw thresholding on RPM/airspeed chatters at phase boundaries
(e.g. climb<->cruise), and every downstream residual and anomaly score is
regime-conditioned. A phase that flips every sample would make the healthy
baseline covariance meaningless. We require a candidate phase to persist for
`hold_n` consecutive samples before we switch to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import EngineConfig, DEFAULT_ENGINE

PHASES = (
    "SHUTDOWN", "START", "TAXI", "TAKEOFF", "CLIMB",
    "CRUISE", "LOITER", "DESCENT",
)


def classify_instant(
    rpm: float,
    airspeed_kts: float,
    vertical_speed_fpm: float,
    cfg: EngineConfig = DEFAULT_ENGINE,
) -> str:
    """Instantaneous (no-memory) phase guess from three signals."""
    if rpm < 200:
        return "SHUTDOWN"
    if rpm < cfg.idle_rpm * 0.9 and airspeed_kts < 5:
        return "START"
    if airspeed_kts < 30:
        return "TAXI"

    high_power = rpm > 0.92 * cfg.max_rpm
    if vertical_speed_fpm > 300:
        return "TAKEOFF" if (airspeed_kts < 70 and high_power) else "CLIMB"
    if vertical_speed_fpm < -250:
        return "DESCENT"
    # level flight: distinguish cruise vs loiter by power / speed
    if airspeed_kts < 105 and rpm < 0.82 * cfg.max_rpm:
        return "LOITER"
    return "CRUISE"


@dataclass
class RegimeTracker:
    """Stateful wrapper applying persistence hysteresis to classify_instant."""

    cfg: EngineConfig = DEFAULT_ENGINE
    hold_n: int = 4
    current: str = "SHUTDOWN"
    _candidate: str = field(default="SHUTDOWN", repr=False)
    _count: int = field(default=0, repr=False)

    def update(
        self, rpm: float, airspeed_kts: float, vertical_speed_fpm: float
    ) -> str:
        inst = classify_instant(rpm, airspeed_kts, vertical_speed_fpm, self.cfg)
        if inst == self.current:
            self._candidate = inst
            self._count = 0
            return self.current
        if inst == self._candidate:
            self._count += 1
        else:
            self._candidate = inst
            self._count = 1
        # SHUTDOWN/START switch instantly (safety-relevant, and unambiguous)
        if self._count >= self.hold_n or inst in ("SHUTDOWN", "START"):
            self.current = inst
            self._count = 0
        return self.current
