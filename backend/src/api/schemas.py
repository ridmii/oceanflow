"""
src/api/schemas.py
==================
Pydantic request/response models.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


# ── Existing (M2) ──────────────────────────────────────────────────────────────
class RunSummary(BaseModel):
    runId: str
    createdAt: str
    status: str
    particleCount: Optional[int] = None
    frameCount: Optional[int] = None


class FluxQuery(BaseModel):
    lon: float
    lat: float
    radiusKm: float

class FluxSource(BaseModel):
    sourceId: str
    name: str
    passes: int
    particles: int

class FluxTimeSeries(BaseModel):
    frameIndex: int
    cumulativePasses: int

class FluxResponse(BaseModel):
    runId: str
    query: FluxQuery
    totalPasses: int
    uniqueParticles: int
    particleCount: int
    fraction: float
    estimatedTons: float
    bySource: list[FluxSource]
    timeSeries: list[FluxTimeSeries]



# ── M3 request models ──────────────────────────────────────────────────────────
class RegionParams(BaseModel):
    west: float
    east: float
    south: float
    north: float

    @model_validator(mode="after")
    def check_region(self) -> "RegionParams":
        if not (-180 <= self.west <= 180):
            raise ValueError("west must be in [-180, 180]")
        if not (-180 <= self.east <= 180):
            raise ValueError("east must be in [-180, 180]")
        if not (-90 <= self.south <= 90):
            raise ValueError("south must be in [-90, 90]")
        if not (-90 <= self.north <= 90):
            raise ValueError("north must be in [-90, 90]")
        if self.west >= self.east:
            raise ValueError("west must be less than east")
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        return self


class TimeParams(BaseModel):
    start: str
    end: str
    timeStepHours: int

    @model_validator(mode="after")
    def check_time(self) -> "TimeParams":
        import datetime

        if not (1 <= self.timeStepHours <= 24):
            raise ValueError("timeStepHours must be in [1, 24]")

        try:
            start = datetime.datetime.fromisoformat(self.start.rstrip("Z"))
            end = datetime.datetime.fromisoformat(self.end.rstrip("Z"))
        except ValueError as exc:
            raise ValueError(f"start/end must be valid ISO 8601: {exc}") from exc

        if start >= end:
            raise ValueError("start must be before end")

        if (end - start).days > 365:
            raise ValueError("time range must not exceed 365 days")

        return self


class ParticleParams(BaseModel):
    count: int
    maxAgeDays: int
    windagePercent: float
    diffusionM2PerS: float
    beachingEnabled: bool

    @model_validator(mode="after")
    def check_particles(self) -> "ParticleParams":
        if not (100 <= self.count <= 200_000):
            raise ValueError("count must be in [100, 200000]")
        if not (1 <= self.maxAgeDays <= 3650):
            raise ValueError("maxAgeDays must be in [1, 3650]")
        if not (0 <= self.windagePercent <= 5):
            raise ValueError("windagePercent must be in [0, 5]")
        if not (0 <= self.diffusionM2PerS <= 1000):
            raise ValueError("diffusionM2PerS must be in [0, 1000]")
        return self


class SimulateRequest(BaseModel):
    region: RegionParams
    time: TimeParams
    particles: ParticleParams


# ── M3 response models ─────────────────────────────────────────────────────────
class SimulateResponse(BaseModel):
    runId: str
    status: str  # "pending"


class StatusResponse(BaseModel):
    runId: str
    status: str   # pending | running | complete | failed
    progress: float  # 0.0 – 1.0
    message: str
    error: Optional[str] = None
