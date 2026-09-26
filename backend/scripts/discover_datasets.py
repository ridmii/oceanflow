#!/usr/bin/env python3
"""
discover_datasets.py
====================
Query the Copernicus Marine catalogue and display all datasets belonging to
the Global Ocean Physics Analysis and Forecast product, highlighting datasets
that contain surface current variables uo and vo.

Run this script to find the correct COPERNICUS_DATASET_ID to put in your .env.

Usage
-----
    python scripts/discover_datasets.py

    # Optional: filter by a different product ID
    python scripts/discover_datasets.py --product GLOBAL_ANALYSISFORECAST_PHY_001_024

After running
-------------
1. Review the printed dataset list.
2. Cross-check your choice in the MyOcean Pro viewer:
       https://data.marine.copernicus.eu/viewer/expert
3. Set COPERNICUS_DATASET_ID in backend/.env.
4. Run: python scripts/download_test_subset.py
"""

from __future__ import annotations

import os
import sys
import argparse
import textwrap

# ── Load .env ────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

# ── Target product (default) ─────────────────────────────────────────────────
DEFAULT_PRODUCT = "GLOBAL_ANALYSISFORECAST_PHY_001_024"
TARGET_VARS = {"uo", "vo"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--product",
        default=DEFAULT_PRODUCT,
        help=f"Copernicus product ID to inspect (default: {DEFAULT_PRODUCT})",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 70)
    print(f"  Copernicus Marine — Dataset Discovery")
    print(f"  Product: {args.product}")
    print("=" * 70)
    print()

    # ── Import ────────────────────────────────────────────────────────────────
    try:
        import copernicusmarine as cm
    except ImportError:
        print("[ERROR] copernicusmarine not installed. Run: pip install copernicusmarine")
        sys.exit(1)

    # ── Fetch catalogue ───────────────────────────────────────────────────────
    print("[...] Fetching catalogue (may take 10–30 s) …\n")
    try:
        catalogue = cm.describe(include_datasets=True, include_description=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Could not fetch catalogue: {exc}")
        print("        Have you run `copernicusmarine login`?")
        sys.exit(1)

    # ── Find matching product ─────────────────────────────────────────────────
    products = catalogue.get("products", [])
    matching = [p for p in products if p.get("product_id", "") == args.product]

    if not matching:
        print(f"[WARN] Product '{args.product}' not found in catalogue.")
        print("       Available product IDs (first 20):")
        for p in products[:20]:
            print(f"         {p.get('product_id', 'unknown')}")
        sys.exit(1)

    product = matching[0]
    datasets = product.get("datasets", [])

    if not datasets:
        print(f"[WARN] Product '{args.product}' has no datasets listed.")
        sys.exit(1)

    # ── Print datasets ────────────────────────────────────────────────────────
    print(f"Found {len(datasets)} dataset(s) in product '{args.product}':\n")
    print("-" * 70)

    best_dataset_id: str | None = None

    for ds in datasets:
        ds_id   = ds.get("dataset_id", "unknown")
        desc    = ds.get("title", ds.get("description", "—"))
        service = ds.get("services", [{}])[0] if ds.get("services") else {}

        # Variables
        variables: list[str] = []
        for svc in ds.get("services", []):
            for layer in svc.get("variables", []):
                vname = layer.get("short_name") or layer.get("standard_name") or ""
                if vname:
                    variables.append(vname)
        variables = list(dict.fromkeys(variables))  # deduplicate, preserve order
        has_uovo = TARGET_VARS.issubset(set(variables))

        # Time coverage
        time_min = ds.get("start_datetime", "—")
        time_max = ds.get("end_datetime", "present")

        # Spatial resolution
        resolution = ds.get("coordinate_system", {}).get("spatial_resolution", "—")

        flag = "  ✓ HAS uo+vo" if has_uovo else ""

        print(f"  Dataset ID  : {ds_id}{flag}")
        print(f"  Title       : {textwrap.shorten(desc, width=65)}")
        print(f"  Time range  : {time_min} → {time_max}")
        print(f"  Resolution  : {resolution}")
        if variables:
            var_str = ", ".join(variables[:12])
            if len(variables) > 12:
                var_str += f", … (+{len(variables)-12} more)"
            print(f"  Variables   : {var_str}")
        print()

        if has_uovo and best_dataset_id is None:
            best_dataset_id = ds_id

    print("-" * 70)

    # ── Recommendation ────────────────────────────────────────────────────────
    if best_dataset_id:
        print(f"\n[SUGGESTED] First dataset with uo+vo: {best_dataset_id!r}")
        print()
        print("  Suggested subset command (verify dates / region first):")
        print()
        print(textwrap.dedent(f"""\
            copernicusmarine subset \\
              --dataset-id {best_dataset_id} \\
              --variable uo --variable vo \\
              --minimum-longitude -160 --maximum-longitude -120 \\
              --minimum-latitude 20  --maximum-latitude 50 \\
              --minimum-depth 0 --maximum-depth 1 \\
              --start-datetime "2024-01-01T00:00:00" \\
              --end-datetime   "2024-01-02T00:00:00" \\
              --output-filename data/test/test_currents.nc
        """))
    else:
        print("\n[WARN] No dataset with both uo and vo was found.")
        print("       Try a different product ID with --product.")

    print()
    print("[NOTE] Always verify your choice in the MyOcean Pro viewer before downloading:")
    print("       https://data.marine.copernicus.eu/viewer/expert")
    print()
    print("[NEXT] Set COPERNICUS_DATASET_ID in backend/.env, then run:")
    print("       python scripts/download_test_subset.py")
    print()


if __name__ == "__main__":
    main()
