"""
src/api/routes/simulate.py
==========================
POST /api/simulate        — submit a new run (202 Accepted)
GET  /api/simulate/{id}/status — poll status / progress
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

import time
from collections import defaultdict
import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.deps import get_redis, get_settings
from src.api.schemas import SimulateRequest, SimulateResponse, StatusResponse
from src.settings import Settings
from src.storage.runs import get_run_dir

logger = logging.getLogger(__name__)

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────────────

def _count_inflight(data_dir: str) -> int:
    """Count run directories that have neither DONE nor FAILED."""
    runs_root = Path(data_dir) / "runs"
    if not runs_root.exists():
        return 0
    count = 0
    for d in runs_root.iterdir():
        if d.is_dir() and not (d / "DONE").exists() and not (d / "FAILED").exists():
            count += 1
    return count

_RATE_LIMIT_STORE = defaultdict(list)

def _check_rate_limit(request: Request, limit: int) -> bool:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    _RATE_LIMIT_STORE[client_ip] = [t for t in _RATE_LIMIT_STORE[client_ip] if now - t < 60]
    if len(_RATE_LIMIT_STORE[client_ip]) >= limit:
        return False
    _RATE_LIMIT_STORE[client_ip].append(now)
    return True


def _resolve_status(
    run_id: str,
    run_dir: Path,
    redis_client: redis_lib.Redis,
) -> StatusResponse:
    """
    Status resolution order (first match wins):
      1. DONE file        → complete
      2. FAILED file      → failed
      3. Celery PROGRESS  → running  (read meta.percent)
      4. Celery PENDING   → pending
      5. Celery FAILED    → failed
      6. default          → pending
    """
    # Import lazily to avoid Celery overhead at module load time
    from celery.result import AsyncResult
    from src.worker.celery_app import celery_app

    if (run_dir / "DONE").exists():
        return StatusResponse(
            runId=run_id,
            status="complete",
            progress=1.0,
            message="Simulation complete.",
        )

    if (run_dir / "FAILED").exists():
        tb = (run_dir / "FAILED").read_text()
        # Return only the last line to avoid leaking full traceback to clients
        short = tb.strip().splitlines()[-1] if tb.strip() else "Unknown error."
        return StatusResponse(
            runId=run_id,
            status="failed",
            progress=0.0,
            message="Simulation failed.",
            error=short,
        )

    # Query Celery result backend
    try:
        result = AsyncResult(run_id, app=celery_app)
        state = result.state
        meta = result.info or {}
    except Exception:  # noqa: BLE001
        state = "PENDING"
        meta = {}

    if state == "PROGRESS":
        percent = float(meta.get("percent", 0.0))
        frame = meta.get("frame", 0)
        total = meta.get("total", 0)
        return StatusResponse(
            runId=run_id,
            status="running",
            progress=round(percent / 100.0, 4),
            message=f"Running frame {frame}/{total}.",
        )

    if state == "FAILURE":
        return StatusResponse(
            runId=run_id,
            status="failed",
            progress=0.0,
            message="Simulation task failed.",
        )

    # PENDING, STARTED, or anything else → pending
    return StatusResponse(
        runId=run_id,
        status="pending",
        progress=0.0,
        message="Simulation queued.",
    )


# ── routes ─────────────────────────────────────────────────────────────────────

@router.post("/simulate", response_model=SimulateResponse, status_code=202)
def submit_simulation(
    request: Request,
    body: SimulateRequest,
    settings: Settings = Depends(get_settings),
):
    """Submit a new simulation run. Returns 202 with a runId immediately."""
    # In-flight check
    inflight = _count_inflight(settings.data_dir)
    if inflight >= settings.max_concurrent_simulations:
        logger.warning(
            "POST /api/simulate rejected: %d/%d in-flight",
            inflight,
            settings.max_concurrent_simulations,
        )
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "TOO_MANY_RUNS", "message": "A simulation is already running. Retry later."}},
            headers={"Retry-After": "60"},
        )

    if not _check_rate_limit(request, settings.rate_limit_per_minute):
        logger.warning("POST /api/simulate rejected: rate limit exceeded for %s", request.client.host if request.client else "unknown")
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "TOO_MANY_RUNS", "message": "Rate limit exceeded. Retry later."}},
            headers={"Retry-After": "60"},
        )

    run_id = uuid.uuid4().hex
    run_dir = Path(settings.data_dir) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Build params dict (matching SimulationParams field names)
    params_dict = {
        "region": body.region.model_dump(),
        "time": body.time.model_dump(),
        "particles": body.particles.model_dump(),
    }

    # Rename camelCase keys to match SimulationParams expectations
    # (SimulationParams uses raw dicts, so keys must match what runner.py reads)
    # Particles keys come in camelCase from the schema — pass them straight through;
    # runner.py uses .get() with the same camelCase keys.

    try:
        from src.worker.tasks import run_simulation_task  # lazy: avoids Redis at import
        run_simulation_task.apply_async(
            args=[run_id, params_dict],
            task_id=run_id,  # use run_id as the Celery task id for easy lookup
        )
    except Exception as exc:
        # Clean up the directory we just created
        shutil.rmtree(run_dir, ignore_errors=True)
        logger.error("Failed to enqueue simulation task: %s", exc)
        raise HTTPException(status_code=503, detail={"code": "INTERNAL", "message": "Could not enqueue simulation task."}) from exc

    logger.info(
        "Enqueued simulation run_id=%s particles=%s timeStepHours=%s",
        run_id,
        body.particles.count,
        body.time.timeStepHours,
    )

    return SimulateResponse(runId=run_id, status="pending")


@router.get("/simulate/{run_id}/status", response_model=StatusResponse)
def get_simulation_status(
    run_id: str,
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis),
):
    """Poll the status of a simulation run."""
    try:
        run_dir = get_run_dir(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_RUN_ID", "message": str(e)})

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run '{run_id}' not found."})

    return _resolve_status(run_id, run_dir, redis_client)
