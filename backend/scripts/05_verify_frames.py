#!/usr/bin/env python3
"""
05_verify_frames.py
===================
Verifies the output frame formats.
"""

import os
import sys
import json
import struct
import numpy as np
from pathlib import Path

def main():
    backend_dir = Path(__file__).resolve().parent.parent
    run_dir = backend_dir / "data" / "runs" / "minimal"
    meta_file = run_dir / "meta.json"
    frame_file = run_dir / "frames" / "0.bin"

    if not meta_file.exists():
        print(f"[ERROR] meta.json not found: {meta_file}")
        sys.exit(1)

    with open(meta_file, "r") as f:
        try:
            meta = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to parse meta.json: {e}")
            sys.exit(1)

    required_fields = ["frameCount", "particleCount", "bytesPerParticle", "durationDays"]
    for field in required_fields:
        if field not in meta:
            print(f"[ERROR] Missing required field in meta.json: {field}")
            sys.exit(1)
            
    print("meta.json OK")

    if not frame_file.exists():
        print(f"[ERROR] frame file not found: {frame_file}")
        sys.exit(1)

    particle_count = meta["particleCount"]
    expected_size = particle_count * 19
    actual_size = frame_file.stat().st_size

    if expected_size != actual_size:
        print(f"[ERROR] frame size mismatch. Expected {expected_size}, got {actual_size}")
        sys.exit(1)
        
    print(f"Frame 0 size OK ({actual_size} bytes)")

    lons = []
    lats = []
    speeds = []
    ages = []
    source_idxs = []
    alives = []

    with open(frame_file, "rb") as f:
        for _ in range(particle_count):
            lons.append(struct.unpack("f", f.read(4))[0])
            lats.append(struct.unpack("f", f.read(4))[0])
            speeds.append(struct.unpack("f", f.read(4))[0])
            ages.append(struct.unpack("f", f.read(4))[0])
            source_idxs.append(struct.unpack("h", f.read(2))[0])
            alives.append(struct.unpack("B", f.read(1))[0])

    lons = np.array(lons)
    lats = np.array(lats)
    speeds = np.array(speeds)
    ages = np.array(ages)
    alives = np.array(alives)

    print("\nStats for Frame 0:")
    print(f"  lon: min={lons.min():.4f}, max={lons.max():.4f}, mean={lons.mean():.4f}")
    print(f"  lat: min={lats.min():.4f}, max={lats.max():.4f}, mean={lats.mean():.4f}")
    print(f"  speed: min={speeds.min():.4f}, max={speeds.max():.4f}, mean={speeds.mean():.4f}")
    print(f"  age: min={ages.min():.4f}, max={ages.max():.4f}, mean={ages.mean():.4f}")
    print(f"  alive: {np.sum(alives==1)} alive, {np.sum(alives==0)} dead")

    print("\nFRAME FORMAT OK")

if __name__ == "__main__":
    main()
