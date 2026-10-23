import json
import re
import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException
import numpy as np
from functools import lru_cache
from src.settings import settings
from src.api.schemas import RunSummary

RUN_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

def get_runs_dir() -> Path:
    return Path(settings.data_dir) / "runs"

def validate_run_id(run_id: str) -> str:
    if not RUN_ID_REGEX.match(run_id):
        raise ValueError("Invalid run_id format.")
    return run_id

def get_run_dir(run_id: str) -> Path:
    run_id = validate_run_id(run_id)
    base_dir = get_runs_dir().resolve()
    run_dir = (base_dir / run_id).resolve()
    
    try:
        run_dir.relative_to(base_dir)
    except ValueError:
        raise ValueError("Invalid path traversal detected.")
    
    return run_dir

def read_run_status(run_dir: Path) -> str:
    if (run_dir / "FAILED").exists():
        return "failed"
    if (run_dir / "DONE").exists():
        return "complete"
    # Placeholder for M2. M3 will query Celery/Redis for 'running' or 'pending'.
    return "pending"

def get_meta(run_id: str) -> Optional[dict]:
    run_dir = get_run_dir(run_id)
    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        return None
    with open(meta_path, "r") as f:
        return json.load(f)

def list_runs() -> List[RunSummary]:
    base_dir = get_runs_dir()
    if not base_dir.exists():
        return []

    runs = []
    for d in base_dir.iterdir():
        if d.is_dir():
            run_id = d.name
            try:
                # Basic check to avoid parsing weird directories
                validate_run_id(run_id)
            except ValueError:
                continue

            status = read_run_status(d)
            meta_path = d / "meta.json"
            
            created_at = None
            particle_count = None
            frame_count = None
            
            if meta_path.exists():
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                        created_at = meta.get("generatedAt")
                        particle_count = meta.get("particleCount")
                        frame_count = meta.get("frameCount")
                except Exception:
                    pass
            
            if not created_at:
                mtime = d.stat().st_mtime
                created_at = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).isoformat()
            
            runs.append(RunSummary(
                runId=run_id,
                createdAt=created_at,
                status=status,
                particleCount=particle_count,
                frameCount=frame_count
            ))

    # Sort descending by createdAt
    runs.sort(key=lambda x: x.createdAt, reverse=True)
    return runs

def get_frame_path(run_id: str, index: int) -> Optional[Path]:
    if index < 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAMS", "message": "Frame index must be >= 0."})
        
    meta = get_meta(run_id)
    if meta is None:
        return None
        
    frame_count = meta.get("frameCount", 0)
    if index >= frame_count:
        raise HTTPException(status_code=400, detail={"code": "FRAME_OUT_OF_RANGE", "message": f"Frame index {index} out of range."})
        
    run_dir = get_run_dir(run_id)
    frame_path = run_dir / "frames" / f"{index}.bin"
    if not frame_path.exists():
        return None
    return frame_path

def get_density_path(run_id: str, index: int) -> Optional[Path]:
    if index < 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAMS", "message": "Frame index must be >= 0."})
        
    meta = get_meta(run_id)
    if meta is None:
        return None
        
    frame_count = meta.get("frameCount", 0)
    if index >= frame_count:
        raise HTTPException(status_code=400, detail={"code": "FRAME_OUT_OF_RANGE", "message": f"Frame index {index} out of range."})

    run_dir = get_run_dir(run_id)
    density_path = run_dir / "density" / f"{index}.bin"
    if not density_path.exists():
        return None
    return density_path


FRAME_DTYPE = np.dtype([
    ('lon', '<f4'),
    ('lat', '<f4'),
    ('speed', '<f4'),
    ('age', '<f4'),
    ('sourceIndex', '<i2'),
    ('alive', 'u1')
])

def _haversine_distance(lon1, lat1, lon2, lat2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

@lru_cache(maxsize=128)
def compute_flux(run_id: str, lon: float, lat: float, radius_km: float):
    meta = get_meta(run_id)
    if not meta:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Run metadata not found."})
        
    particle_count = meta.get("particleCount", 0)
    frame_count = meta.get("frameCount", 0)
    sources = meta.get("sources", [])
    
    if not particle_count or not frame_count:
        raise HTTPException(status_code=404, detail={"code": "INVALID_RUN", "message": "Run metadata missing frames or particles."})
        
    run_dir = get_run_dir(run_id)
    
    deg_per_km_lat = 1 / 111.32
    deg_per_km_lon = 1 / (111.32 * max(np.cos(np.radians(lat)), 0.01))
    
    lat_min = lat - radius_km * deg_per_km_lat
    lat_max = lat + radius_km * deg_per_km_lat
    lon_min = lon - radius_km * deg_per_km_lon
    lon_max = lon + radius_km * deg_per_km_lon
    
    seen_particles = set()
    total_passes = 0
    time_series = []
    
    source_passes = {}
    source_particles = {}
    
    last_frame_in_circle = set()
    
    for i in range(frame_count):
        frame_path = run_dir / "frames" / f"{i}.bin"
        if not frame_path.exists():
            time_series.append({
                "frameIndex": i,
                "cumulativePasses": total_passes
            })
            continue
            
        data = np.fromfile(frame_path, dtype=FRAME_DTYPE)
        
        mask = (
            (data['alive'] == 1) &
            (data['lat'] >= lat_min) & (data['lat'] <= lat_max) &
            (data['lon'] >= lon_min) & (data['lon'] <= lon_max)
        )
        
        candidates = np.where(mask)[0]
        
        if len(candidates) > 0:
            c_lons = data['lon'][candidates]
            c_lats = data['lat'][candidates]
            
            dists = _haversine_distance(lon, lat, c_lons, c_lats)
            in_circle_indices = candidates[dists <= radius_km]
            new_in_circle = set(in_circle_indices)
            
            new_passes = new_in_circle - last_frame_in_circle
            total_passes += len(new_passes)
            
            for p in new_passes:
                src_idx = data['sourceIndex'][p]
                source_passes[src_idx] = source_passes.get(src_idx, 0) + 1
                if src_idx not in source_particles:
                    source_particles[src_idx] = set()
                source_particles[src_idx].add(p)
                
            seen_particles.update(new_passes)
            last_frame_in_circle = new_in_circle
        else:
            last_frame_in_circle = set()
            
        time_series.append({
            "frameIndex": i,
            "cumulativePasses": total_passes
        })

    unique_particles = len(seen_particles)
    estimated_tons = unique_particles * (1.8e6 / particle_count)
    fraction = unique_particles / particle_count
    
    by_source = []
    for src_idx, passes in source_passes.items():
        src_info = sources[src_idx] if 0 <= src_idx < len(sources) else {"id": "unknown", "name": "Unknown"}
        by_source.append({
            "sourceId": src_info.get("id", "unknown"),
            "name": src_info.get("name", "Unknown"),
            "passes": passes,
            "particles": len(source_particles.get(src_idx, set()))
        })
    by_source.sort(key=lambda x: x["passes"], reverse=True)
    
    return {
        "runId": run_id,
        "query": {"lon": lon, "lat": lat, "radiusKm": radius_km},
        "totalPasses": total_passes,
        "uniqueParticles": unique_particles,
        "particleCount": particle_count,
        "fraction": fraction,
        "estimatedTons": estimated_tons,
        "bySource": by_source,
        "timeSeries": time_series
    }
