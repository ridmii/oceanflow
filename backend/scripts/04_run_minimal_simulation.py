#!/usr/bin/env python3
"""
04_run_minimal_simulation.py
============================
Thin CLI wrapper around src.simulation.runner.run_simulation.
Produces the canonical "minimal" run in backend/data/runs/minimal/.

Usage:
    python scripts/04_run_minimal_simulation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import parcels

# Allow running from the backend/ directory without installing the package.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from src.simulation.runner import SimulationParams, run_simulation  # noqa: E402

print(f"Using Parcels version: {parcels.__version__}")

# ── Fixed params for the "minimal" reference run ──────────────────────────────
_PARAMS = SimulationParams(
    region={"west": -160, "east": -120, "south": 20, "north": 50},
    time={
        "start": "2024-01-01T00:00:00Z",
        "end":   "2024-01-31T00:00:00Z",   # 30 days = 120 steps of 6 h
        "timeStepHours": 6,
    },
    particles={
        "count": 500,
        "maxAgeDays": 1095,
        "windagePercent": 1.5,
        "diffusionM2PerS": 50,
        "beachingEnabled": False,
    },
)

_RUN_ID = "minimal"
_RUN_DIR = _BACKEND_DIR / "data" / "runs" / _RUN_ID


def _progress(frame: int, total: int, percent: float) -> None:
    if frame == 0:
        print(f"Starting simulation: {total} steps of 6 hours.")
    elif frame % 10 == 0 or frame == total:
        print(f"Completed step {frame}/{total}")


def main() -> None:
    print(f"Output directory: {_RUN_DIR}")

    run_simulation(
        run_id=_RUN_ID,
        params=_PARAMS,
        progress_cb=_progress,
        data_dir=str(_BACKEND_DIR / "data"),
    )

    # Write DONE marker (caller's responsibility outside the pure function)
    (_RUN_DIR / "DONE").write_text("Completed successfully.")
    print(f"\nSimulation complete! Output written to {_RUN_DIR}")


if __name__ == "__main__":
    main()
