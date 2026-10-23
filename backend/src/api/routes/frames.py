from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from src.storage.runs import get_frame_path, get_density_path, get_meta

router = APIRouter()

@router.get("/runs/{run_id}/frames/{frame_index}")
@router.head("/runs/{run_id}/frames/{frame_index}")
def get_frame(run_id: str, frame_index: int):
    # This might throw 400 if out of range, from get_frame_path
    frame_path = get_frame_path(run_id, frame_index)
    if frame_path is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Frame not found."})

    meta = get_meta(run_id)
    particle_count = meta.get("particleCount", 0)

    return FileResponse(
        path=frame_path,
        media_type="application/octet-stream",
        headers={
            "X-Frame-Index": str(frame_index),
            "X-Particle-Count": str(particle_count),
            "Cache-Control": "public, max-age=31536000, immutable"
        }
    )

@router.get("/runs/{run_id}/density/{frame_index}")
@router.head("/runs/{run_id}/density/{frame_index}")
def get_density(run_id: str, frame_index: int):
    density_path = get_density_path(run_id, frame_index)
    if density_path is None:
        raise HTTPException(status_code=404, detail={"code": "DENSITY_NOT_FOUND", "message": "Density frame not found."})
        
    meta = get_meta(run_id)
    cols = meta.get("heatmapGrid", {}).get("cols", 0)
    rows = meta.get("heatmapGrid", {}).get("rows", 0)

    return FileResponse(
        path=density_path,
        media_type="application/octet-stream",
        headers={
            "X-Frame-Index": str(frame_index),
            "X-Grid-Cols": str(cols),
            "X-Grid-Rows": str(rows),
            "Cache-Control": "public, max-age=31536000, immutable"
        }
    )
