from fastapi import APIRouter, Depends
from pathlib import Path
from src.api.deps import get_settings
from src.settings import Settings

import parcels

router = APIRouter()

@router.get("/health")
def health_check(settings: Settings = Depends(get_settings)):
    run_count = 0
    runs_dir = Path(settings.data_dir) / "runs"
    if runs_dir.exists():
        run_count = len([d for d in runs_dir.iterdir() if d.is_dir()])

    return {
        "status": "ok",
        "parcelsVersion": parcels.__version__,
        "runCount": run_count
    }
