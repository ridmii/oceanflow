#!/usr/bin/env python3
"""
00_verify_env.py
================
Verifies the Python environment, packages, and credentials are set up correctly.

Usage
-----
    python scripts/00_verify_env.py
"""

import os
import sys
from pathlib import Path

def main():
    try:
        from dotenv import load_dotenv
        backend_dir = Path(__file__).resolve().parent.parent
        load_dotenv(backend_dir / ".env")
    except ImportError:
        print("[ERROR] python-dotenv not installed.")
        

    # Check credentials
    username = os.getenv("COPERNICUS_USERNAME")
    password = os.getenv("COPERNICUS_PASSWORD")
    dataset_id = os.getenv("COPERNICUS_DATASET_ID")

    if not username or username == "your_username_here":
        print("[ERROR] COPERNICUS_USERNAME is not set correctly in .env")
        
        
    if not password or password == "your_password_here":
        print("[ERROR] COPERNICUS_PASSWORD is not set correctly in .env")
        

    if not dataset_id or dataset_id == "fill_after_discovery":
        print("[ERROR] COPERNICUS_DATASET_ID is not set correctly in .env")
        

    # Check package imports and versions
    try:
        import copernicusmarine
        print(f"copernicusmarine: {copernicusmarine.__version__}")
    except ImportError:
        print("[ERROR] Failed to import copernicusmarine")
        
        
    try:
        import parcels
        print(f"parcels: {parcels.__version__}")
    except ImportError:
        print("[ERROR] Failed to import parcels")
        
        
    try:
        import plasticparcels
        # plasticparcels may not have __version__ depending on how it's packaged
        try:
            pp_ver = plasticparcels.__version__
        except AttributeError:
            import importlib.metadata
            pp_ver = importlib.metadata.version('plasticparcels')
        print(f"plasticparcels: {pp_ver}")
    except ImportError:
        print("[WARN] Failed to import plasticparcels")
        
        
    try:
        import xarray
        print(f"xarray: {xarray.__version__}")
    except ImportError:
        print("[ERROR] Failed to import xarray")
        
        
    try:
        import numpy
        print(f"numpy: {numpy.__version__}")
    except ImportError:
        print("[ERROR] Failed to import numpy")
        

    print("\nENV OK")

if __name__ == "__main__":
    main()
