#!/usr/bin/env python3
"""
download_test_subset.py
=======================
Download a small surface-current test subset from Copernicus Marine Service
using ``copernicusmarine.subset()``.

Safety guards
-------------
- Refuses to run if COPERNICUS_DATASET_ID is still the placeholder value.
- Refuses to run if the requested time window exceeds 7 days.
- Downloads surface layer only (depth 0–1 m).
- Downloads only uo (eastward velocity) and vo (northward velocity).

Configuration is read from:
  1. backend/.env   (takes priority)
  2. backend/config/simulation.yaml  (fallback for region/time)

Usage
-----
    python scripts/download_test_subset.py

    # Override region/time on the command line:
    python scripts/download_test_subset.py \\
        --west -160 --east -120 --south 20 --north 50 \\
        --start 2024-01-01 --end 2024-01-02

Output
------
    backend/data/test/test_currents.nc
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent.parent.resolve()

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_BACKEND_DIR / ".env")
except ImportError:
    pass

PLACEHOLDER_ID = "fill_after_discovery"


# ──────────────────────────────────────────────────────────────────────────────
def _env(key: str, fallback: str | None = None) -> str | None:
    return os.getenv(key, fallback)


def _require_env(key: str, hint: str = "") -> str:
    val = os.getenv(key)
    if not val:
        msg = f"[ERROR] Environment variable {key!r} is not set."
        if hint:
            msg += f"\n        {hint}"
        print(msg)
        sys.exit(1)
    return val


def _load_yaml_config() -> dict:
    """Load config/simulation.yaml as a fallback for region/time values."""
    config_path = _BACKEND_DIR / "config" / "simulation.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
        with config_path.open() as f:
            return yaml.safe_load(f) or {}
    except Exception:  # noqa: BLE001
        return {}


def parse_args() -> argparse.Namespace:
    cfg = _load_yaml_config()
    region = cfg.get("region", {})
    time_cfg = cfg.get("time", {})

    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--west",  type=float, default=float(_env("SIMULATION_REGION_WEST",  str(region.get("west",  -160)))))
    p.add_argument("--east",  type=float, default=float(_env("SIMULATION_REGION_EAST",  str(region.get("east",  -120)))))
    p.add_argument("--south", type=float, default=float(_env("SIMULATION_REGION_SOUTH", str(region.get("south",   20)))))
    p.add_argument("--north", type=float, default=float(_env("SIMULATION_REGION_NORTH", str(region.get("north",   50)))))
    p.add_argument("--start", type=str,   default=_env("SIMULATION_START_DATE", str(time_cfg.get("start", "2024-01-01"))))
    p.add_argument("--end",   type=str,   default=_env("SIMULATION_END_DATE",   str(time_cfg.get("end",   "2024-01-02"))))
    p.add_argument("--max-depth", type=float, default=float(_env("SIMULATION_MAX_DEPTH", "1")))
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_BACKEND_DIR / "data" / "test",
        help="Directory to save the downloaded NetCDF file.",
    )
    return p.parse_args()


def _validate_time_range(start: str, end: str) -> tuple[date, date]:
    """Parse and validate the time range. Exits if > 7 days."""
    try:
        d_start = date.fromisoformat(start)
        d_end   = date.fromisoformat(end)
    except ValueError as exc:
        print(f"[ERROR] Invalid date format: {exc}")
        print("        Use ISO format: YYYY-MM-DD")
        sys.exit(1)

    if d_end <= d_start:
        print(f"[ERROR] End date ({d_end}) must be after start date ({d_start}).")
        sys.exit(1)

    delta = d_end - d_start
    if delta > timedelta(days=7):
        print(
            f"[ERROR] Safety guard: time range is {delta.days} days "
            f"({d_start} → {d_end}).\n"
            "        This script is for TEST downloads only (≤ 7 days).\n"
            "        Reduce SIMULATION_START_DATE / SIMULATION_END_DATE in .env."
        )
        sys.exit(1)

    return d_start, d_end


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("  Copernicus Marine — Test Subset Download")
    print("=" * 60)
    print()

    # ── Validate dataset ID ───────────────────────────────────────
    dataset_id = _require_env(
        "COPERNICUS_DATASET_ID",
        hint=(
            "Run `python scripts/discover_datasets.py` to find the correct ID,\n"
            "        then set COPERNICUS_DATASET_ID in backend/.env."
        ),
    )

    if dataset_id.strip().lower() == PLACEHOLDER_ID:
        print(
            "[ERROR] COPERNICUS_DATASET_ID is still the placeholder value.\n"
            "        Run: python scripts/discover_datasets.py\n"
            "        Then set a real dataset ID in backend/.env."
        )
        sys.exit(1)

    # ── Validate time range ───────────────────────────────────────
    d_start, d_end = _validate_time_range(args.start, args.end)

    # ── Summarise what we're about to download ────────────────────
    print(f"  Dataset ID    : {dataset_id}")
    print(f"  Variables     : uo, vo")
    print(f"  Region        : lon [{args.west}, {args.east}], lat [{args.south}, {args.north}]")
    print(f"  Depth         : 0 – {args.max_depth} m (surface only)")
    print(f"  Time          : {d_start} → {d_end}  ({(d_end - d_start).days} day(s))")
    print(f"  Output dir    : {args.output_dir}")
    print()

    # ── Import ────────────────────────────────────────────────────
    try:
        import copernicusmarine as cm
    except ImportError:
        print("[ERROR] copernicusmarine not installed. Run: pip install copernicusmarine")
        sys.exit(1)

    # ── Prepare output directory ──────────────────────────────────
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = args.output_dir / "test_currents.nc"

    # ── Download ──────────────────────────────────────────────────
    print("[...] Starting download …\n")
    try:
        cm.subset(
            dataset_id=dataset_id,
            variables=["uo", "vo"],
            minimum_longitude=args.west,
            maximum_longitude=args.east,
            minimum_latitude=args.south,
            maximum_latitude=args.north,
            minimum_depth=0.0,
            maximum_depth=args.max_depth,
            start_datetime=f"{d_start}T00:00:00",
            end_datetime=f"{d_end}T00:00:00",
            output_filename=str(output_file),
            force_download=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] Download failed: {exc}")
        print(
            "\n  Common causes:\n"
            "    - Token expired → run `copernicusmarine login`\n"
            "    - Dataset ID is wrong → run `python scripts/discover_datasets.py`\n"
            "    - Region / time out of dataset bounds → check the MyOcean viewer\n"
            "      https://data.marine.copernicus.eu/viewer/expert"
        )
        sys.exit(1)

    print()
    if output_file.exists():
        size_mb = output_file.stat().st_size / 1_048_576
        print(f"[OK] Downloaded → {output_file}  ({size_mb:.2f} MB)")
        print()
        print("[NEXT] Inspect the file:")
        print(f"       python scripts/inspect_download.py {output_file}")
    else:
        print("[WARN] Download completed but output file not found.")
        print(f"       Expected: {output_file}")

    print()


if __name__ == "__main__":
    main()
