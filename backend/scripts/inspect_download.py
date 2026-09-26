#!/usr/bin/env python3
"""
inspect_download.py
===================
Open a downloaded NetCDF file, print a structural summary, check data
validity, and save a quiver plot of surface currents.

Usage
-----
    python scripts/inspect_download.py path/to/test_currents.nc

    # Example:
    python scripts/inspect_download.py data/test/test_currents.nc

Output
------
    - Printed summary to stdout
    - backend/data/test/inspect_plot.png  (quiver plot of surface currents)
    - Final verdict: LOOKS VALID or a list of problems found
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent.parent.resolve()
_PLOT_DIR    = _BACKEND_DIR / "data" / "test"

EXPECTED_UNITS = {"m s-1", "m/s", "meter per second", "m s**-1"}
EXPECTED_VARS  = {"uo", "vo"}


# ──────────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "netcdf_path",
        type=Path,
        nargs="?",
        default=_BACKEND_DIR / "data" / "test" / "test_currents.nc",
        help="Path to the NetCDF file to inspect (default: data/test/test_currents.nc)",
    )
    return p.parse_args()


def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


def main() -> None:
    args = parse_args()
    nc_path = args.netcdf_path.resolve()

    print("=" * 60)
    print("  Copernicus Marine — NetCDF Inspector")
    print("=" * 60)
    print(f"  File: {nc_path}")

    # ── File existence check ──────────────────────────────────────
    if not nc_path.exists():
        print(f"\n[ERROR] File not found: {nc_path}")
        print("        Run: python scripts/download_test_subset.py")
        sys.exit(1)

    size_mb = nc_path.stat().st_size / 1_048_576
    print(f"  Size: {size_mb:.2f} MB")

    # ── Import ────────────────────────────────────────────────────
    try:
        import xarray as xr
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")          # headless — no display required
        import matplotlib.pyplot as plt
    except ImportError as exc:
        print(f"\n[ERROR] Missing dependency: {exc}")
        print("        Run: pip install xarray netCDF4 matplotlib numpy")
        sys.exit(1)

    # ── Open dataset ──────────────────────────────────────────────
    try:
        ds = xr.open_dataset(nc_path, engine="netcdf4")
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] Could not open file with xarray: {exc}")
        sys.exit(1)

    problems: list[str] = []

    # ── 1. Dimensions ─────────────────────────────────────────────
    _section("Dimensions")
    for dim, size in ds.dims.items():
        print(f"  {dim:20s}: {size}")

    # ── 2. Variables ──────────────────────────────────────────────
    _section("Variables")
    for var_name, var in ds.data_vars.items():
        units = var.attrs.get("units", "—")
        print(f"  {var_name:20s}: shape={list(var.shape)}  units={units!r}")

    # ── 3. Coordinate ranges ──────────────────────────────────────
    _section("Coordinate ranges")
    for coord_name in ("longitude", "lon", "latitude", "lat", "time", "depth"):
        if coord_name in ds.coords:
            coord = ds.coords[coord_name]
            if coord.dtype.kind in ("f", "i", "u"):
                print(f"  {coord_name:20s}: {float(coord.min().values):.4f} → {float(coord.max().values):.4f}")
            else:
                vals = coord.values
                print(f"  {coord_name:20s}: {vals[0]} → {vals[-1]}  ({len(vals)} steps)")

    # ── 4. uo / vo statistics ─────────────────────────────────────
    _section("Variable statistics (uo, vo)")
    missing_vars = EXPECTED_VARS - set(ds.data_vars)
    if missing_vars:
        msg = f"Missing variables: {', '.join(sorted(missing_vars))}"
        problems.append(msg)
        print(f"  [PROBLEM] {msg}")
    else:
        for vname in ("uo", "vo"):
            da = ds[vname]
            arr = da.values.astype(float)
            n_nan  = int(np.isnan(arr).sum())
            n_tot  = arr.size
            nan_pct = 100 * n_nan / n_tot if n_tot > 0 else 0
            v_min  = float(np.nanmin(arr)) if n_nan < n_tot else float("nan")
            v_max  = float(np.nanmax(arr)) if n_nan < n_tot else float("nan")
            v_mean = float(np.nanmean(arr)) if n_nan < n_tot else float("nan")
            units  = da.attrs.get("units", "unknown")

            print(
                f"  {vname:6s}: min={v_min:+.4f}  max={v_max:+.4f}  "
                f"mean={v_mean:+.4f}  NaN={n_nan}/{n_tot} ({nan_pct:.1f}%)  "
                f"units={units!r}"
            )

            # Checks
            if n_nan == n_tot:
                problems.append(f"{vname}: all values are NaN")
            elif nan_pct > 80:
                problems.append(f"{vname}: >{nan_pct:.0f}% NaN — possible land mask issue")

            if n_nan < n_tot and v_min == 0 and v_max == 0:
                problems.append(f"{vname}: all non-NaN values are exactly zero")

            if units.lower().strip() not in EXPECTED_UNITS:
                problems.append(f"{vname}: unexpected units {units!r} (expected m/s)")

    # ── 5. Quiver plot ────────────────────────────────────────────
    _section("Generating quiver plot")
    plot_path = _PLOT_DIR / "inspect_plot.png"
    _PLOT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        _make_quiver_plot(ds, plot_path)
        print(f"  Saved → {plot_path}")
    except Exception as exc:  # noqa: BLE001
        msg = f"Plot generation failed: {exc}"
        print(f"  [WARN] {msg}")
        problems.append(msg)

    # ── 6. Verdict ────────────────────────────────────────────────
    _section("Verdict")
    if not problems:
        print("  ✅  LOOKS VALID")
        print()
        print("  [NEXT] The dataset appears healthy. You can now:")
        print("         1. Update config/simulation.yaml with these coordinates.")
        print("         2. Begin integrating Parcels/PlasticParcels for the simulation.")
    else:
        print("  ❌  PROBLEMS FOUND:")
        for i, p in enumerate(problems, 1):
            print(f"    {i}. {p}")
        print()
        print("  Suggested actions:")
        print("    - Verify the dataset ID in backend/.env.")
        print("    - Check that uo and vo are available in your dataset via:")
        print("      python scripts/discover_datasets.py")
        print("    - Try a different time period or a smaller spatial subset.")

    print()
    ds.close()


def _make_quiver_plot(ds, plot_path: Path) -> None:
    """Plot a coarse quiver of surface uo/vo on a lat/lon grid."""
    import numpy as np
    import matplotlib.pyplot as plt

    # Locate coordinate names (different products use different spellings)
    lon_name = next((c for c in ("longitude", "lon") if c in ds.coords), None)
    lat_name = next((c for c in ("latitude",  "lat") if c in ds.coords), None)

    if lon_name is None or lat_name is None:
        raise ValueError("Cannot locate lon/lat coordinates in dataset.")

    if "uo" not in ds.data_vars or "vo" not in ds.data_vars:
        raise ValueError("uo and/or vo not present in dataset.")

    # Select first time step, shallowest depth
    def _sel_surface(da):
        """Reduce to 2-D (lat, lon) by choosing the first time and depth."""
        for dim in ("time",):
            if dim in da.dims:
                da = da.isel({dim: 0})
        for dim in ("depth", "depthu", "depthv"):
            if dim in da.dims:
                da = da.isel({dim: 0})
        return da

    uo_2d = _sel_surface(ds["uo"])
    vo_2d = _sel_surface(ds["vo"])

    lon = ds.coords[lon_name].values
    lat = ds.coords[lat_name].values

    # Subsample to keep quiver readable (≤ 40 × 40 arrows)
    step_lon = max(1, len(lon) // 40)
    step_lat = max(1, len(lat) // 40)

    lon_sub = lon[::step_lon]
    lat_sub = lat[::step_lat]
    uo_sub  = uo_2d.values[::step_lat, ::step_lon]
    vo_sub  = vo_2d.values[::step_lat, ::step_lon]

    LON, LAT = np.meshgrid(lon_sub, lat_sub)

    fig, ax = plt.subplots(figsize=(10, 6))
    speed = np.hypot(uo_sub, vo_sub)
    q = ax.quiver(
        LON, LAT, uo_sub, vo_sub, speed,
        cmap="viridis", scale=5, scale_units="inches",
        width=0.003, alpha=0.85,
    )
    fig.colorbar(q, ax=ax, label="Speed (m/s)")

    ax.set_title("Surface Current (uo, vo) — first time step", fontsize=13)
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_facecolor("#0a0a1a")
    fig.patch.set_facecolor("#10101e")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

    plt.tight_layout()
    plt.savefig(plot_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
