"""
src/simulation/runner.py
========================
Pure simulation function — no Celery, no Redis, no FastAPI.

The caller is responsible for writing DONE / FAILED markers.
"""

from __future__ import annotations

import datetime
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd
import xarray as xr

# ── Parcels import ────────────────────────────────────────────────────────────
import parcels
from parcels import (
    AdvectionRK4,
    FieldSet,
    ParticleSet,
    ScipyParticle,
    Variable,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_SOURCES_FILE = _BACKEND_DIR / "config" / "sources.csv"

# DATA_DIR comes from env (Docker: /data, local: backend/data)
_DEFAULT_DATA_DIR = os.environ.get("DATA_DIR", str(_BACKEND_DIR / "data"))

_DATA_FILE = Path(_DEFAULT_DATA_DIR) / "test" / "test_currents.nc"


# ── Particle kernels (module-level so they can be pickled by Parcels) ─────────
def delete_particle(particle, fieldset, time):  # noqa: ARG001
    """Remove out-of-bounds particles."""
    particle.delete()


def sample_speed(particle, fieldset, time):
    """Store instantaneous speed on the particle."""
    (u, v) = fieldset.UV[time, particle.depth, particle.lat, particle.lon]
    particle.speed = math.sqrt(u * u + v * v)


def add_age(particle, fieldset, time):  # noqa: ARG001
    """Accumulate particle age in seconds."""
    particle.age += particle.dt


def custom_brownian(particle, fieldset, time):  # noqa: ARG001
    """
    Deterministic pseudo-random Brownian diffusion.
    Avoids Parcels' C-compiled rng so it works with ScipyParticle.
    """
    noise_x = math.sin(particle.id * 12.9898 + time * 78.233) * 43758.5453
    noise_x = noise_x - math.floor(noise_x)
    noise_y = math.sin(particle.id * 78.233 + time * 12.9898) * 43758.5453
    noise_y = noise_y - math.floor(noise_y)

    r1 = (noise_x - 0.5) * 2.0
    r2 = (noise_y - 0.5) * 2.0

    Kh = 100.0
    dlon = (r1 * math.sqrt(2 * Kh * particle.dt)) / (
        111000.0 * math.cos(particle.lat * math.pi / 180.0)
    )
    dlat = (r2 * math.sqrt(2 * Kh * particle.dt)) / 111000.0

    particle.lon += dlon
    particle.lat += dlat


# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class SimulationParams:
    """All parameters needed to run one simulation.

    Can be constructed from a plain dict via ``SimulationParams(**d)``.
    """

    region: dict   # {west, east, south, north}
    time: dict     # {start, end, timeStepHours}
    particles: dict  # {count, maxAgeDays, windagePercent,
                     #  diffusionM2PerS, beachingEnabled}


# ── Frame writer (same byte layout as scripts/04) ─────────────────────────────
def _write_frame(pset: ParticleSet, filepath: Path, particle_count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Write one binary frame and return (lons, lats, alive) for density computation.

    Per-particle layout (19 bytes, little-endian):
        lon         float32  4 B
        lat         float32  4 B
        speed       float32  4 B
        age         float32  4 B   (seconds → days)
        sourceIndex int16    2 B
        alive       uint8    1 B
    """
    lons = np.zeros(particle_count, dtype=np.float32)
    lats = np.zeros(particle_count, dtype=np.float32)
    speeds = np.zeros(particle_count, dtype=np.float32)
    ages = np.zeros(particle_count, dtype=np.float32)
    source_idxs = np.zeros(particle_count, dtype=np.int16)
    alive = np.zeros(particle_count, dtype=np.uint8)

    for i, p in enumerate(pset):
        if i >= particle_count:
            break
        lons[i] = p.lon
        lats[i] = p.lat
        speeds[i] = p.speed
        ages[i] = p.age / 86400.0  # seconds → days
        source_idxs[i] = p.source_idx
        alive[i] = 1

    with open(filepath, "wb") as f:
        for i in range(particle_count):
            f.write(lons[i].tobytes())
            f.write(lats[i].tobytes())
            f.write(speeds[i].tobytes())
            f.write(ages[i].tobytes())
            f.write(source_idxs[i].tobytes())
            f.write(alive[i].tobytes())

    return lons, lats, alive


# ── Main public function ───────────────────────────────────────────────────────
def run_simulation(
    run_id: str,
    params: SimulationParams,
    progress_cb: Callable[[int, int, float], None],
    data_dir: Optional[str] = None,
) -> None:
    """
    Execute a Lagrangian simulation and write output under
    ``{data_dir}/runs/{run_id}/``.

    Writes:
        meta.json
        frames/{i}.bin   (0 … frameCount-1)

    Does NOT write DONE or FAILED — the caller decides that.
    Raises on error; the caller is responsible for cleanup.

    Args:
        run_id:      Unique identifier for this run.
        params:      SimulationParams instance.
        progress_cb: Called as ``progress_cb(frame_index, total_frames, percent)``
                     every 10 frames (and at frame 0).
        data_dir:    Override for the data root (default: DATA_DIR env var or
                     backend/data when running locally).
    """
    from datetime import timedelta
    from src.simulation.density import compute_density_frame
    from src.settings import settings

    effective_data_dir = data_dir or _DEFAULT_DATA_DIR
    run_dir = Path(effective_data_dir) / "runs" / run_id
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    density_dir = run_dir / "density"
    density_dir.mkdir(parents=True, exist_ok=True)
    
    heatmap_cols = settings.density_default_cols
    heatmap_rows = settings.density_default_rows
    blur_sigma = settings.density_blur_sigma
    bounds = {
        "west": float(params.region.get("west", -160)),
        "east": float(params.region.get("east", -120)),
        "south": float(params.region.get("south", 20)),
        "north": float(params.region.get("north", 50)),
    }

    # ── 1. Build FieldSet ────────────────────────────────────────────────────
    ds = xr.open_dataset(_DATA_FILE)
    lon_name = next((c for c in ("longitude", "lon") if c in ds.coords), "longitude")
    lat_name = next((c for c in ("latitude", "lat") if c in ds.coords), "latitude")
    time_name = next((c for c in ("time", "t") if c in ds.coords), "time")

    variables = {"U": "uo", "V": "vo"}
    dimensions = {"lon": lon_name, "lat": lat_name, "time": time_name}

    fieldset = FieldSet.from_xarray_dataset(
        ds, variables, dimensions, allow_time_extrapolation=True
    )

    # Constant diffusion fields
    Kh = float(params.particles.get("diffusionM2PerS", 50))
    size2D = (ds[lat_name].size, ds[lon_name].size)
    fieldset.add_field(
        parcels.Field(
            "Kh_zonal",
            Kh * np.ones(size2D),
            lon=ds[lon_name].values,
            lat=ds[lat_name].values,
            mesh="spherical",
        )
    )
    fieldset.add_field(
        parcels.Field(
            "Kh_meridional",
            Kh * np.ones(size2D),
            lon=ds[lon_name].values,
            lat=ds[lat_name].values,
            mesh="spherical",
        )
    )

    # ── 2. Read sources and assign particles ─────────────────────────────────
    sources_df = pd.read_csv(_SOURCES_FILE, skiprows=13)
    raw_sources = sources_df.copy()
    sources_df["intensity"] = sources_df["intensity"] / sources_df["intensity"].sum()

    total_particles = int(params.particles.get("count", 500))
    sources_df["num_particles"] = (sources_df["intensity"] * total_particles).astype(int)
    remainder = total_particles - sources_df["num_particles"].sum()
    if remainder > 0:
        sources_df.loc[sources_df["intensity"].idxmax(), "num_particles"] += remainder

    lons: list = []
    lats: list = []
    source_indices: list = []

    for idx, row in sources_df.iterrows():
        n = int(row["num_particles"])
        if n > 0:
            lons.extend(np.random.uniform(-150, -130, n))
            lats.extend(np.random.uniform(30, 40, n))
            source_indices.extend([idx] * n)

    # ── 3. Create ParticleSet ────────────────────────────────────────────────
    class OceanParticle(ScipyParticle):
        speed = Variable("speed", dtype=np.float32, initial=0.0)
        age = Variable("age", dtype=np.float32, initial=0.0)
        source_idx = Variable("source_idx", dtype=np.int32, initial=0)

    pset = ParticleSet.from_list(
        fieldset=fieldset,
        pclass=OceanParticle,
        lon=lons,
        lat=lats,
        source_idx=source_indices,
    )

    # ── 4. Run simulation ────────────────────────────────────────────────────
    kernels = (
        pset.Kernel(AdvectionRK4)
        + pset.Kernel(custom_brownian)
        + pset.Kernel(sample_speed)
        + pset.Kernel(add_age)
    )

    time_step = timedelta(hours=int(params.time.get("timeStepHours", 6)))

    # Compute duration from start / end
    start_str = params.time.get("start", "2024-01-01T00:00:00Z").rstrip("Z")
    end_str = params.time.get("end", "2024-01-02T00:00:00Z").rstrip("Z")
    start_dt = datetime.datetime.fromisoformat(start_str)
    end_dt = datetime.datetime.fromisoformat(end_str)
    duration = end_dt - start_dt
    num_steps = int(duration / time_step)

    def write_density(lons_arr, lats_arr, alive_arr, step_index):
        try:
            H = compute_density_frame(
                lons_arr, lats_arr, alive_arr, bounds,
                cols=heatmap_cols, rows=heatmap_rows, blur_sigma=blur_sigma
            )
            with open(density_dir / f"{step_index}.bin", "wb") as f:
                f.write(H.tobytes())
        except Exception as exc:
            raise RuntimeError(f"Failed to write density for frame {step_index}") from exc

    # Write frame 0 (initial positions)
    l0, lat0, a0 = _write_frame(pset, frames_dir / "0.bin", total_particles)
    write_density(l0, lat0, a0, 0)
    progress_cb(0, num_steps, 0.0)

    for step in range(1, num_steps + 1):
        pset.execute(kernels, runtime=time_step, dt=time_step)
        ln, lt, a = _write_frame(pset, frames_dir / f"{step}.bin", total_particles)
        write_density(ln, lt, a, step)

        if step % 10 == 0 or step == num_steps:
            percent = round(100.0 * step / num_steps, 1)
            progress_cb(step, num_steps, percent)

    # ── 5. Write meta.json ───────────────────────────────────────────────────
    sources_list = [
        {
            "id": str(r["id"]),
            "name": str(r["name"]),
            "lon": float(r["lon"]),
            "lat": float(r["lat"]),
            "intensity": float(r["intensity"]),
            "color": str(r["color"]),
        }
        for _, r in raw_sources.iterrows()
    ]

    region = params.region
    meta = {
        "schemaVersion": 1,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
        "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeStepHours": int(params.time.get("timeStepHours", 6)),
        "frameCount": num_steps + 1,
        "particleCount": total_particles,
        "sources": sources_list,
        "bounds": {
            "west": float(region.get("west", -160)),
            "east": float(region.get("east", -120)),
            "south": float(region.get("south", 20)),
            "north": float(region.get("north", 50)),
        },
        "heatmapGrid": {"cols": 720, "rows": 360},
    }

    with open(run_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    with open(run_dir / "debug.json", "w") as f:
        json.dump({"bytesPerParticle": 19, "parcelsVersion": parcels.__version__}, f, indent=2)
