"""
scripts/06_backfill_density.py
==============================
Usage: python scripts/06_backfill_density.py <run_id> [--force]

Backfill density frames for an existing run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from src.settings import settings
from src.simulation.density import compute_density_frame


def backfill_run(run_id: str, force: bool = False) -> None:
    run_dir = Path(settings.data_dir) / "runs" / run_id

    if not run_dir.exists():
        print(f"Error: Run directory does not exist: {run_dir}")
        sys.exit(1)

    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        print("Error: meta.json not found.")
        sys.exit(1)

    if not (run_dir / "DONE").exists():
        print("Error: DONE marker not found. Refusing to backfill an incomplete run.")
        sys.exit(1)

    frames_dir = run_dir / "frames"
    if not frames_dir.exists():
        print("Error: frames/ directory not found.")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    frame_count = meta.get("frameCount", 0)
    if frame_count == 0:
        print("Error: frameCount is 0 in meta.json")
        sys.exit(1)

    bounds = meta.get("bounds")
    heatmap_grid = meta.get("heatmapGrid")
    if not bounds or not heatmap_grid:
        print("Error: meta.json missing bounds or heatmapGrid")
        sys.exit(1)

    cols = heatmap_grid["cols"]
    rows = heatmap_grid["rows"]

    density_dir = run_dir / "density"
    density_dir.mkdir(parents=True, exist_ok=True)

    if not force:
        existing_count = len(list(density_dir.glob("*.bin")))
        if existing_count == frame_count:
            print("already backfilled")
            return

    particle_count = meta.get("particleCount", 0)
    blur_sigma = settings.density_blur_sigma

    dt = np.dtype([
        ("lon", "<f4"),
        ("lat", "<f4"),
        ("speed", "<f4"),
        ("age", "<f4"),
        ("source_idx", "<i2"),
        ("alive", "u1"),
    ])

    for i in range(frame_count):
        frame_path = frames_dir / f"{i}.bin"
        if not frame_path.exists():
            print(f"Warning: frame {i}.bin not found, skipping.")
            continue

        data = frame_path.read_bytes()
        expected_size = particle_count * 19
        if len(data) != expected_size:
            print(f"Warning: frame {i}.bin size mismatch. Expected {expected_size}, got {len(data)}")
            continue

        arr = np.frombuffer(data, dtype=dt)
        lon = arr["lon"]
        lat = arr["lat"]
        alive = arr["alive"]

        H = compute_density_frame(lon, lat, alive, bounds, cols, rows, blur_sigma)

        density_path = density_dir / f"{i}.bin"
        density_path.write_bytes(H.tobytes())

        if (i + 1) % 10 == 0:
            print(f"Computed density for {i + 1}/{frame_count} frames...")

    print(f"backfilled {frame_count} frames")


def main():
    parser = argparse.ArgumentParser(description="Backfill density frames for a run")
    parser.add_argument("run_id", help="The ID of the run to backfill")
    parser.add_argument("--force", action="store_true", help="Overwrite existing density files")
    args = parser.parse_args()

    backfill_run(args.run_id, args.force)


if __name__ == "__main__":
    main()
