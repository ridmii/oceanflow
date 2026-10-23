import shutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from typing import List
from src.api.schemas import RunSummary, FluxResponse
from src.storage.runs import list_runs, get_meta, get_run_dir, compute_flux

router = APIRouter()

@router.get("/runs", response_model=List[RunSummary])
def get_runs():
    return list_runs()

@router.get("/runs/{run_id}/meta")
def get_run_meta(run_id: str):
    try:
        run_dir = get_run_dir(run_id)
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Run not found."})
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_RUN_ID", "message": str(e)})
        
    meta = get_meta(run_id)
    if meta is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "meta.json not found for run."})
    
    return JSONResponse(
        content=meta,
        headers={"Cache-Control": "public, max-age=60"}
    )

@router.get("/runs/{run_id}/flux", response_model=FluxResponse)
def get_run_flux(run_id: str, lon: float, lat: float, radius_km: float = 100.0):
    if not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAM", "message": "lon must be between -180 and 180"})
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAM", "message": "lat must be between -90 and 90"})
    if not (10 <= radius_km <= 1000):
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAM", "message": "radius_km must be between 10 and 1000"})
        
    try:
        run_dir = get_run_dir(run_id)
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Run not found."})
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_RUN_ID", "message": str(e)})
        
    try:
        data = compute_flux(run_id, lon, lat, radius_km)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL", "message": str(e)})


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str):
    try:
        run_dir = get_run_dir(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_RUN_ID", "message": str(e)})

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Run not found."})

    is_running = not (run_dir / "DONE").exists() and not (run_dir / "FAILED").exists()
    if is_running:
        raise HTTPException(
            status_code=409,
            detail={"code": "RUN_IN_PROGRESS", "message": "Cannot delete a run that is currently running."}
        )

    try:
        shutil.rmtree(run_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL", "message": f"Failed to delete run directory: {e}"})

    return None
