"""
tests/test_density.py
=====================
Unit tests for M5 density generation and backfill.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.simulation.density import compute_density_frame

def test_density_frame_shape_and_dtype():
    lon = np.random.uniform(-100, -90, 100).astype(np.float32)
    lat = np.random.uniform(20, 30, 100).astype(np.float32)
    alive = np.ones(100, dtype=np.uint8)
    bounds = {"west": -180, "east": 180, "south": -90, "north": 90}
    
    H = compute_density_frame(lon, lat, alive, bounds, cols=720, rows=360)
    
    assert H.shape == (360, 720)
    assert H.dtype == np.float32
    assert H.flags.c_contiguous
    assert np.isclose(np.max(H), 1.0)
    assert np.all(H >= 0.0) and np.all(H <= 1.0)

def test_density_ignores_dead_particles():
    lon = np.array([0, 10], dtype=np.float32)
    lat = np.array([0, 10], dtype=np.float32)
    alive = np.array([1, 0], dtype=np.uint8)
    bounds = {"west": -180, "east": 180, "south": -90, "north": 90}
    
    H = compute_density_frame(lon, lat, alive, bounds, cols=10, rows=10, blur_sigma=0.0)
    # The dead particle at (10, 10) shouldn't contribute
    # Only cell containing (0,0) will have 1.0
    assert np.max(H) == 1.0
    assert np.sum(H) == 1.0

def test_density_ignores_out_of_bounds():
    lon = np.array([0, 200], dtype=np.float32)
    lat = np.array([0, 0], dtype=np.float32)
    alive = np.array([1, 1], dtype=np.uint8)
    bounds = {"west": -180, "east": 180, "south": -90, "north": 90}
    
    H = compute_density_frame(lon, lat, alive, bounds, cols=10, rows=10, blur_sigma=0.0)
    assert np.max(H) == 1.0
    assert np.sum(H) == 1.0

def test_density_zero_particles():
    lon = np.array([], dtype=np.float32)
    lat = np.array([], dtype=np.float32)
    alive = np.array([], dtype=np.uint8)
    bounds = {"west": -180, "east": 180, "south": -90, "north": 90}
    
    H = compute_density_frame(lon, lat, alive, bounds, cols=10, rows=10)
    assert H.shape == (10, 10)
    assert np.all(H == 0)
    assert not np.isnan(H).any()

def test_density_pole_and_antimeridian():
    lon = np.array([-180, 180, 0], dtype=np.float32)
    lat = np.array([-90, 90, 0], dtype=np.float32)
    alive = np.array([1, 1, 1], dtype=np.uint8)
    bounds = {"west": -180, "east": 180, "south": -90, "north": 90}
    
    H = compute_density_frame(lon, lat, alive, bounds, cols=10, rows=10)
    assert not np.isnan(H).any()
    
    with pytest.raises(ValueError):
        compute_density_frame(lon, lat, alive, {"west": 180, "east": -180, "south": -90, "north": 90}, cols=10, rows=10)

def test_density_coordinates():
    lon = np.array([-180, 180], dtype=np.float32)
    lat = np.array([90, -90], dtype=np.float32)
    alive = np.array([1, 1], dtype=np.uint8)
    bounds = {"west": -180, "east": 180, "south": -90, "north": 90}
    
    H = compute_density_frame(lon, lat, alive, bounds, cols=10, rows=10, blur_sigma=0.0)
    assert H[0, 0] > 0
    assert H[9, 9] > 0

def test_runner_writes_density(tmp_path_factory):
    from src.simulation.runner import SimulationParams, run_simulation
    tmp = tmp_path_factory.mktemp("runner_density")
    data_dir = str(tmp)

    params = SimulationParams(
        region={"west": -160, "east": -120, "south": 20, "north": 50},
        time={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "timeStepHours": 6,
        },
        particles={
            "count": 10,
            "maxAgeDays": 30,
            "windagePercent": 1.5,
            "diffusionM2PerS": 50,
            "beachingEnabled": False,
        },
    )

    run_simulation("test-density-run", params, lambda *args: None, data_dir=data_dir)

    run_dir = tmp / "runs" / "test-density-run"
    density_dir = run_dir / "density"
    
    assert density_dir.is_dir()
    for i in range(5):  # 4 steps + frame 0
        df_path = density_dir / f"{i}.bin"
        assert df_path.exists()
        assert df_path.stat().st_size == 720 * 360 * 4

def test_backfill_idempotent(tmp_path_factory, monkeypatch):
    import importlib.util
    import sys
    from src.settings import settings
    
    spec = importlib.util.spec_from_file_location("backfill", "scripts/06_backfill_density.py")
    backfill = importlib.util.module_from_spec(spec)
    sys.modules["backfill"] = backfill
    spec.loader.exec_module(backfill)
    
    tmp = tmp_path_factory.mktemp("backfill")
    monkeypatch.setattr(settings, "data_dir", str(tmp))
    
    run_id = "bf-run"
    run_dir = tmp / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "DONE").touch()
    
    import json
    with open(run_dir / "meta.json", "w") as f:
        json.dump({
            "frameCount": 2,
            "particleCount": 10,
            "bounds": {"west": -160, "east": -120, "south": 20, "north": 50},
            "heatmapGrid": {"cols": 720, "rows": 360}
        }, f)
        
    frames_dir = run_dir / "frames"
    frames_dir.mkdir()
    
    dt = np.dtype([
        ("lon", "<f4"),
        ("lat", "<f4"),
        ("speed", "<f4"),
        ("age", "<f4"),
        ("source_idx", "<i2"),
        ("alive", "u1"),
    ])
    
    arr = np.zeros(10, dtype=dt)
    arr["lon"] = -140.0
    arr["lat"] = 30.0
    arr["alive"] = 1
    
    (frames_dir / "0.bin").write_bytes(arr.tobytes())
    (frames_dir / "1.bin").write_bytes(arr.tobytes())
    
    backfill.backfill_run(run_id)
    
    density_dir = run_dir / "density"
    mtime0 = (density_dir / "0.bin").stat().st_mtime
    
    backfill.backfill_run(run_id)
    
    mtime1 = (density_dir / "0.bin").stat().st_mtime
    assert mtime0 == mtime1, "File was overwritten, backfill not idempotent"
