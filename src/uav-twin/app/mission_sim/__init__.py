"""Ground-truth mission generation. INDEPENDENT of app/physics.py by design.

`generate_mission()` picks JSBSim (FGPiston) when the `jsbsim` package is
importable and falls back to the NumPy generator otherwise. Both write the same
row schema so downstream code does not care which produced the data.
"""

from .numpy_mission import generate_mission_numpy
from .degradation import DegradationSpec, apply_degradation

try:  # optional
    import jsbsim  # noqa: F401
    from .jsbsim_runner import generate_mission_jsbsim

    _HAVE_JSBSIM = True
except Exception:  # pragma: no cover - jsbsim not installed
    _HAVE_JSBSIM = False


def generate_mission(*args, prefer_jsbsim: bool = True, **kwargs):
    if prefer_jsbsim and _HAVE_JSBSIM:
        return generate_mission_jsbsim(*args, **kwargs)
    return generate_mission_numpy(*args, **kwargs)


__all__ = [
    "generate_mission",
    "generate_mission_numpy",
    "DegradationSpec",
    "apply_degradation",
    "_HAVE_JSBSIM",
]
