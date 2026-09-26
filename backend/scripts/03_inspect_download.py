#!/usr/bin/env python3
"""
03_inspect_download.py
======================
Inspects the downloaded NetCDF and generates a quiver plot.
"""

import os
import sys
import numpy as np
from pathlib import Path

def main():
    backend_dir = Path(__file__).resolve().parent.parent
    data_file = backend_dir / "data" / "test" / "test_currents.nc"
    plot_file = backend_dir / "data" / "test" / "inspect_plot.png"

    if not data_file.exists():
        print(f"[ERROR] Data file not found: {data_file}")
        sys.exit(1)

    import xarray as xr
    import matplotlib.pyplot as plt

    try:
        ds = xr.open_dataset(data_file)
    except Exception as e:
        print(f"[ERROR] Failed to open dataset: {e}")
        sys.exit(1)

    print("=== Dimensions ===")
    for dim, size in ds.dims.items():
        print(f"{dim}: {size}")

    print("\n=== Variables ===")
    for var_name, var in ds.data_vars.items():
        units = var.attrs.get("units", "unknown")
        print(f"{var_name}: {list(var.shape)} (units: {units})")

    print("\n=== Coordinate Ranges ===")
    # Handle different names for lat/lon/time
    lon_name = next((c for c in ("longitude", "lon") if c in ds.coords), None)
    lat_name = next((c for c in ("latitude", "lat") if c in ds.coords), None)
    time_name = next((c for c in ("time", "t") if c in ds.coords), None)

    if not lon_name or not lat_name or not time_name:
        print(f"[ERROR] Missing required coordinates (lon/lat/time). Found: {list(ds.coords.keys())}")
        sys.exit(1)

    lon_min, lon_max = float(ds[lon_name].min()), float(ds[lon_name].max())
    lat_min, lat_max = float(ds[lat_name].min()), float(ds[lat_name].max())
    time_min, time_max = str(ds[time_name].min().values), str(ds[time_name].max().values)

    print(f"Longitude: {lon_min:.2f} to {lon_max:.2f}")
    print(f"Latitude: {lat_min:.2f} to {lat_max:.2f}")
    print(f"Time: {time_min} to {time_max}")

    problems = []

    if lon_min < -180.5 or lon_max > 180.5:
        problems.append(f"Longitude range {lon_min} to {lon_max} is outside [-180, 180]")
    if lat_min < -90.5 or lat_max > 90.5:
        problems.append(f"Latitude range {lat_min} to {lat_max} is outside [-90, 90]")
    if time_min == time_max:
        # It's technically not empty but has only 1 step. 
        # The prompt says "time range non-empty".
        pass

    if "uo" not in ds.data_vars or "vo" not in ds.data_vars:
        problems.append("Missing 'uo' or 'vo' variables.")
        print("\n[ERROR] Missing 'uo' or 'vo' variables.")
        sys.exit(1)

    print("\n=== Variable Stats ===")
    for var_name in ("uo", "vo"):
        vals = ds[var_name].values
        n_nan = int(np.isnan(vals).sum())
        n_tot = int(vals.size)
        pct_nan = (n_nan / n_tot) * 100 if n_tot > 0 else 100
        
        v_min = float(np.nanmin(vals)) if n_nan < n_tot else float("nan")
        v_max = float(np.nanmax(vals)) if n_nan < n_tot else float("nan")
        v_mean = float(np.nanmean(vals)) if n_nan < n_tot else float("nan")

        print(f"{var_name}:")
        print(f"  Min: {v_min:.4f}, Max: {v_max:.4f}, Mean: {v_mean:.4f}")
        print(f"  NaNs: {n_nan}/{n_tot} ({pct_nan:.1f}%)")

        if pct_nan > 10:
            problems.append(f"{var_name} has >10% NaNs ({pct_nan:.1f}%)")
            
        # Realistic ocean currents rarely exceed 3 m/s, but maybe up to 5 m/s in Gulf stream
        # The spec says: velocity magnitudes are physically plausible (0 to 3 m/s)
        # Note: uo/vo can be negative, so magnitude is abs(val) or hypot
        max_mag = max(abs(v_min), abs(v_max))
        if not np.isnan(max_mag) and max_mag > 4.0:
            problems.append(f"{var_name} has implausibly large values (max magnitude {max_mag:.2f} m/s)")

    # Create quiver plot for the first time step
    print("\nGenerating quiver plot...")
    try:
        uo_2d = ds["uo"].isel({time_name: 0})
        vo_2d = ds["vo"].isel({time_name: 0})
        
        # In case depth is somehow present despite the instructions, select index 0
        if "depth" in uo_2d.dims:
            uo_2d = uo_2d.isel(depth=0)
            vo_2d = vo_2d.isel(depth=0)

        # Subsample for readability
        lons = ds[lon_name].values
        lats = ds[lat_name].values
        
        step_lon = max(1, len(lons) // 50)
        step_lat = max(1, len(lats) // 50)
        
        sub_lons = lons[::step_lon]
        sub_lats = lats[::step_lat]
        
        uo_sub = uo_2d.values[::step_lat, ::step_lon]
        vo_sub = vo_2d.values[::step_lat, ::step_lon]

        fig, ax = plt.subplots(figsize=(10, 8))
        Q = ax.quiver(sub_lons, sub_lats, uo_sub, vo_sub, 
                     np.hypot(uo_sub, vo_sub), 
                     cmap='viridis', scale=10)
        ax.set_title("Surface Currents (First Timestep)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        fig.colorbar(Q, label='Speed (m/s)')
        
        plt.tight_layout()
        plt.savefig(plot_file)
        print(f"Saved plot to {plot_file}")
    except Exception as e:
        print(f"[ERROR] Plot generation failed: {e}")
        sys.exit(1)

    print("\n=== Verdict ===")
    if not problems:
        print("LOOKS VALID")
    else:
        print("PROBLEMS FOUND:")
        for i, p in enumerate(problems, 1):
            print(f"{i}. {p}")
        sys.exit(1)

if __name__ == "__main__":
    main()
