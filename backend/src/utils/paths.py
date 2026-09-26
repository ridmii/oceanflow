"""
paths.py
========
Canonical path constants and helpers for the backend project.

All paths are resolved relative to this file's location (backend/src/utils/),
so the project can be run from any working directory.

Usage
-----
    from src.utils.paths import DATA_DIR, CONFIG_DIR, ensure_run_dirs

    run_dir = ensure_run_dirs("run_20240101_001")
"""

from __future__ import annotations

from pathlib import Path

# ── Root directories ──────────────────────────────────────────────────────────
#  backend/src/utils/paths.py  →  parent x3 = backend/
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.resolve()

DATA_DIR:    Path = PROJECT_ROOT / "data"
CONFIG_DIR:  Path = PROJECT_ROOT / "config"
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
SRC_DIR:     Path = PROJECT_ROOT / "src"

# ── Ensure data/ exists on import ────────────────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Per-run helpers ───────────────────────────────────────────────────────────
def runs_dir(run_id: str) -> Path:
    """Return the root directory for a simulation run (not yet created)."""
    return DATA_DIR / "runs" / run_id


def frames_dir(run_id: str) -> Path:
    """Return the frames output directory for a run (not yet created)."""
    return runs_dir(run_id) / "frames"


def density_dir(run_id: str) -> Path:
    """Return the density output directory for a run (not yet created)."""
    return runs_dir(run_id) / "density"


def ensure_run_dirs(run_id: str) -> Path:
    """
    Create all output directories for a simulation run and return the run root.

    Creates
    -------
    data/runs/{run_id}/
    data/runs/{run_id}/frames/
    data/runs/{run_id}/density/

    Parameters
    ----------
    run_id:
        Unique identifier for this run, e.g. ``"run_20240101_001"``.

    Returns
    -------
    Path
        The run root directory (``data/runs/{run_id}/``).
    """
    root = runs_dir(run_id)
    for d in (root, frames_dir(run_id), density_dir(run_id)):
        d.mkdir(parents=True, exist_ok=True)
    return root


# ── Test data helpers ─────────────────────────────────────────────────────────
TEST_DATA_DIR: Path = DATA_DIR / "test"

def ensure_test_dir() -> Path:
    """Create data/test/ if needed and return it."""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_DATA_DIR
