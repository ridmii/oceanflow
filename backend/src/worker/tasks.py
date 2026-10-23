"""
src/worker/tasks.py
===================
Celery task that wraps run_simulation.
"""

from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path

import redis

from src.settings import settings
from src.simulation.runner import SimulationParams, run_simulation
from src.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="run_simulation")
def run_simulation_task(self, run_id: str, params_dict: dict) -> dict:
    """
    Celery task that executes one simulation run.

    Writes DONE on success, FAILED (with traceback) on error, then re-raises
    so Celery marks the task as FAILED.
    """
    params = SimulationParams(**params_dict)
    run_dir = Path(settings.data_dir) / "runs" / run_id
    redis_client = redis.from_url(settings.redis_url)

    logger.info(
        "run_simulation_task started: run_id=%s particles=%s timeStepHours=%s",
        run_id,
        params.particles.get("count"),
        params.time.get("timeStepHours"),
    )

    def progress_cb(frame: int, total: int, percent: float) -> None:
        self.update_state(
            state="PROGRESS",
            meta={"frame": frame, "total": total, "percent": percent},
        )
        try:
            redis_client.publish(
                f"run:{run_id}:progress",
                json.dumps({"frame": frame, "total": total, "percent": percent}),
            )
        except Exception:  # noqa: BLE001
            pass  # publishing is best-effort; never crash the simulation

    try:
        run_simulation(
            run_id=run_id,
            params=params,
            progress_cb=progress_cb,
            data_dir=settings.data_dir,
        )
        (run_dir / "DONE").touch()
        logger.info("run_simulation_task completed: run_id=%s", run_id)
        return {"runId": run_id, "status": "complete"}
    except Exception:
        tb = traceback.format_exc()
        try:
            (run_dir / "FAILED").write_text(tb)
        except Exception:  # noqa: BLE001
            pass
        logger.error("run_simulation_task FAILED: run_id=%s\n%s", run_id, tb)
        raise
