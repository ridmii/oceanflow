"""
scripts/07_cleanup_old_runs.py
==============================
Usage: python scripts/07_cleanup_old_runs.py --older-than-days 30 [--dry-run]
"""

import argparse
import shutil
import time
from pathlib import Path

import sys
import os

# Ensure src can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.settings import settings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--older-than-days", type=int, required=True, help="Delete runs older than this many days")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted")
    args = parser.parse_args()
    
    cutoff_time = time.time() - (args.older_than_days * 86400)
    runs_dir = Path(settings.data_dir) / "runs"
    
    if not runs_dir.exists():
        print("No runs directory found.")
        return
        
    deleted_count = 0
    freed_bytes = 0
    
    def get_dir_size(d: Path) -> int:
        return sum(f.stat().st_size for f in d.rglob('*') if f.is_file())
        
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
            
        done_marker = run_dir / "DONE"
        failed_marker = run_dir / "FAILED"
        
        is_done = done_marker.exists()
        is_failed = failed_marker.exists()
        
        if not is_done and not is_failed:
            continue
            
        marker_path = done_marker if is_done else failed_marker
        mtime = marker_path.stat().st_mtime
        
        if mtime < cutoff_time:
            size = get_dir_size(run_dir)
            if args.dry_run:
                print(f"[DRY RUN] Would delete {run_dir.name} ({size / 1024 / 1024:.2f} MB)")
            else:
                shutil.rmtree(run_dir)
                print(f"Deleted {run_dir.name} ({size / 1024 / 1024:.2f} MB)")
            deleted_count += 1
            freed_bytes += size
            
    print("\nSummary:")
    if args.dry_run:
        print(f"Would delete {deleted_count} runs, freeing {freed_bytes / 1024 / 1024:.2f} MB")
    else:
        print(f"Deleted {deleted_count} runs, freed {freed_bytes / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
