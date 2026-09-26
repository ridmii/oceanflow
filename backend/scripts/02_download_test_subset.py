#!/usr/bin/env python3
"""
02_download_test_subset.py
==========================
Downloads a small test subset from Copernicus Marine.
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

def main():
    backend_dir = Path(__file__).resolve().parent.parent
    load_dotenv(backend_dir / ".env")

    dataset_id = os.getenv("COPERNICUS_DATASET_ID")
    if not dataset_id or dataset_id == "fill_after_discovery":
        print("[ERROR] COPERNICUS_DATASET_ID is not set in .env")
        sys.exit(1)

    # Read config from .env or use defaults for the MVP
    west = float(os.getenv("SIMULATION_REGION_WEST", "-160"))
    east = float(os.getenv("SIMULATION_REGION_EAST", "-120"))
    south = float(os.getenv("SIMULATION_REGION_SOUTH", "20"))
    north = float(os.getenv("SIMULATION_REGION_NORTH", "50"))
    start_str = os.getenv("SIMULATION_START_DATE", "2024-01-01")
    end_str = os.getenv("SIMULATION_END_DATE", "2024-01-02")

    # Safety checks
    if abs(east - west) > 60 or abs(north - south) > 60:
        print("[ERROR] Region exceeds 60 degrees. Too large for test download.")
        sys.exit(1)

    d_start = date.fromisoformat(start_str)
    d_end = date.fromisoformat(end_str)
    
    if (d_end - d_start) > timedelta(days=3):
        print(f"[ERROR] Time range {(d_end - d_start).days} days exceeds 3 days. Too large for test download.")
        sys.exit(1)

    output_dir = backend_dir / "data" / "test"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "test_currents.nc"

    print(f"Downloading subset for {dataset_id}...")
    print(f"Region: W:{west}, E:{east}, S:{south}, N:{north}")
    print(f"Time: {d_start} to {d_end}")
    
    import copernicusmarine as cm
    
    try:
        # Note: dataset has NO depth dimension. Do not pass depth parameters.
        cm.subset(
            dataset_id=dataset_id,
            variables=["uo", "vo"],
            minimum_longitude=west,
            maximum_longitude=east,
            minimum_latitude=south,
            maximum_latitude=north,
            start_datetime=f"{d_start}T00:00:00",
            end_datetime=f"{d_end}T00:00:00",
            output_filename=str(output_file),
            force_download=True,
            username=os.getenv("COPERNICUS_USERNAME"),
            password=os.getenv("COPERNICUS_PASSWORD"),
        )
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        sys.exit(1)

    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"\n[OK] Download complete: {output_file}")
        print(f"File size: {size_mb:.2f} MB")
    else:
        print("[ERROR] Output file not found after download.")
        sys.exit(1)

if __name__ == "__main__":
    main()
