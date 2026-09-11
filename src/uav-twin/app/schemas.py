"""Request models for the API. Deliberately permissive:

Every field the backend might omit is Optional, extra keys are ignored, and the
route handlers tolerate `None` everywhere. A twin failure must never block the
backend's telemetry persistence, so we bias hard toward "accept and degrade".
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class TelemetryBlock(_Loose):
    rpm: Optional[float] = None
    manifold_pressure: Optional[float] = None
    throttle_position_pct: Optional[float] = None
    fuel_flow: Optional[float] = None
    oil_pressure: Optional[float] = None
    oil_temperature: Optional[float] = None
    coolant_temp_c: Optional[float] = None
    intake_air_temp_c: Optional[float] = None
    fuel_rail_pressure_bar: Optional[float] = None
    egt_cylinders: Optional[list[float]] = None
    cht_cylinders: Optional[list[float]] = None
    vibration: Optional[float] = None
    battery_voltage: Optional[float] = None


class AmbientBlock(_Loose):
    pressure_kpa: Optional[float] = None
    temp_c: Optional[float] = None
    altitude_ft: Optional[float] = None
    airspeed_kts: Optional[float] = None
    vertical_speed_fpm: Optional[float] = None


class PairedBlock(_Loose):
    engineId: Optional[int] = None
    egt_cylinders: Optional[list[float]] = None
    cht_cylinders: Optional[list[float]] = None
    coolant_temp_c: Optional[float] = None
    oil_pressure: Optional[float] = None
    fuel_flow: Optional[float] = None
    manifold_pressure: Optional[float] = None


class TwinStepRequest(_Loose):
    engineId: int = 1
    timestamp: Optional[str] = None
    seq: Optional[int] = None
    cylinderCount: Optional[int] = 4
    engineType: Optional[str] = "PISTON_CI_TURBO"
    telemetry: TelemetryBlock = Field(default_factory=TelemetryBlock)
    ambient: AmbientBlock = Field(default_factory=AmbientBlock)
    paired: Optional[PairedBlock] = None


class MissionSegment(_Loose):
    phase: Optional[str] = None
    altitude_ft: Optional[float] = 20000.0
    power_pct: Optional[float] = 55.0
    duration_h: Optional[float] = 1.0


class TwinSimulateRequest(_Loose):
    engineId: int = 1
    missionProfile: list[MissionSegment] = Field(default_factory=list)
    variants: Optional[list[str]] = None
