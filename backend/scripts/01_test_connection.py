#!/usr/bin/env python3
"""
01_test_connection.py
=====================
Tests Copernicus connection and verifies the configured dataset ID.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def main():
    backend_dir = Path(__file__).resolve().parent.parent
    load_dotenv(backend_dir / ".env")

    dataset_id = os.getenv("COPERNICUS_DATASET_ID")
    if not dataset_id or dataset_id == "fill_after_discovery":
        print("[ERROR] COPERNICUS_DATASET_ID is not set in .env")
        sys.exit(1)

    import copernicusmarine as cm

    print(f"Querying catalogue for dataset ID: {dataset_id}")
    
    try:
        # describe(dataset_id=...) returns CopernicusMarineCatalogue
        catalogue_obj = cm.describe(dataset_id=dataset_id)
        # Convert to dictionary for easy traversal
        catalogue = catalogue_obj.dict() if hasattr(catalogue_obj, "dict") else catalogue_obj
    except Exception as e:
        print(f"[ERROR] Failed to fetch catalogue: {e}")
        sys.exit(1)

    # Search for the dataset in the catalogue
    target_dataset = None
    for product in catalogue.get("products", []):
        for ds in product.get("datasets", []):
            if ds.get("dataset_id") == dataset_id:
                target_dataset = ds
                break
        if target_dataset:
            break
            
    if not target_dataset:
        print(f"[ERROR] Dataset {dataset_id} not found in the catalogue.")
        sys.exit(1)

    print("\nDataset found!")
    
    desc = target_dataset.get("dataset_name", target_dataset.get("dataset_id", "No description"))
    print(f"Description: {desc}")
    
    # Versions -> Parts -> Services -> Variables
    variables = []
    start_time = "unknown"
    end_time = "present"
    
    for version in target_dataset.get("versions", []):
        for part in version.get("parts", []):
            for svc in part.get("services", []):
                for layer in svc.get("variables", []):
                    vname = layer.get("short_name") or layer.get("standard_name")
                    if vname and vname not in variables:
                        variables.append(vname)
            
            # The time coverage is often in the parts or services in the newer models
            for meta in part.get("metadata", []):
                pass # Just simplified, time might be somewhere here.

    print(f"Variables available: {', '.join(variables)}")
    
    if "uo" in variables and "vo" in variables:
        print("\n[OK] Required variables 'uo' and 'vo' are present.")
    else:
        print("\n[ERROR] Missing 'uo' or 'vo' in this dataset.")
        sys.exit(1)

if __name__ == "__main__":
    main()
