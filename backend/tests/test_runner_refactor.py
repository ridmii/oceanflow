"""
tests/test_runner_refactor.py
==============================
Integration test for the refactored run_simulation pure function.
Runs a tiny simulation (10 particles, 1 day, 4 steps) into a tmp dir.
Does NOT touch backend/data/.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.simulation.runner import SimulationParams, run_simulation


TINY_PARAMS = SimulationParams(
    region={"west": -160, "east": -120, "south": 20, "north": 50},
    time={
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-02T00:00:00Z",  # 1 day = 4 steps of 6 h
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


@pytest.fixture(scope="module")
def sim_output(tmp_path_factory):
    """Run tiny simulation once; share output across all tests in this module."""
    tmp = tmp_path_factory.mktemp("runner")
    data_dir = str(tmp)
    calls = []

    def progress_cb(frame, total, percent):
        calls.append((frame, total, percent))

    run_simulation("test-run", TINY_PARAMS, progress_cb, data_dir=data_dir)

    return {
        "run_dir": tmp / "runs" / "test-run",
        "calls": calls,
        "particle_count": 10,
    }


def test_meta_json_exists(sim_output):
    assert (sim_output["run_dir"] / "meta.json").exists()


def test_meta_json_schema(sim_output):
    with open(sim_output["run_dir"] / "meta.json") as f:
        meta = json.load(f)
    assert meta["schemaVersion"] == 1
    assert meta["frameCount"] == 5        # 4 steps + frame 0
    assert meta["particleCount"] == 10
    assert "generatedAt" in meta
    assert "startDate" in meta
    assert "bounds" in meta
    assert "heatmapGrid" in meta
    assert "sources" in meta


def test_frames_exist(sim_output):
    frames_dir = sim_output["run_dir"] / "frames"
    assert frames_dir.is_dir()
    for i in range(5):  # 0–4
        assert (frames_dir / f"{i}.bin").exists(), f"Missing frame {i}.bin"


def test_frame_byte_size(sim_output):
    """Each frame must be exactly particleCount * 19 bytes."""
    frames_dir = sim_output["run_dir"] / "frames"
    expected = sim_output["particle_count"] * 19
    for i in range(5):
        actual = (frames_dir / f"{i}.bin").stat().st_size
        assert actual == expected, f"Frame {i}.bin: {actual} != {expected}"


def test_frame_binary_layout(sim_output):
    """Parse frame 1 and check all fields unpack without error."""
    frames_dir = sim_output["run_dir"] / "frames"
    data = (frames_dir / "1.bin").read_bytes()
    n = sim_output["particle_count"]
    assert len(data) == n * 19

    offset = 0
    for _ in range(n):
        lon  = struct.unpack_from("<f", data, offset)[0]; offset += 4
        lat  = struct.unpack_from("<f", data, offset)[0]; offset += 4
        spd  = struct.unpack_from("<f", data, offset)[0]; offset += 4
        age  = struct.unpack_from("<f", data, offset)[0]; offset += 4
        sidx = struct.unpack_from("<h", data, offset)[0]; offset += 2
        alv  = struct.unpack_from("<B", data, offset)[0]; offset += 1
        # Basic sanity
        assert -180 <= lon <= 180 or lon == 0.0
        assert -90  <= lat <= 90  or lat == 0.0
        assert spd >= 0
        assert age >= 0
        assert alv in (0, 1)


def test_progress_cb_called(sim_output):
    """progress_cb must be called at least at frame 0 and at the last step."""
    calls = sim_output["calls"]
    assert len(calls) >= 1
    # First call is frame 0
    assert calls[0][0] == 0
    # Last call total matches num_steps
    last_frame, last_total, last_pct = calls[-1]
    assert last_frame == last_total  # called at completion
    assert last_pct == 100.0


def test_done_marker_not_written_by_runner(sim_output):
    """The runner must NOT write the DONE marker — that's the caller's job."""
    assert not (sim_output["run_dir"] / "DONE").exists()
