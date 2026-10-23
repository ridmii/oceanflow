"""
src/api/routes/ws.py
====================
WS /api/ws/simulate/{run_id}

Connection lifecycle:
  1. Validate run_id (regex + path traversal check)
  2. Subscribe to Redis BEFORE fetching snapshot (no missed events)
  3. Buffer messages into asyncio.Queue via a background reader task
  4. Send snapshot
  5. Drain queue (messages that arrived between subscribe and snapshot)
  6. Streaming loop: forward progress, send ping on heartbeat timeout,
     poll marker files every ws_marker_poll_seconds seconds.
  7. On DONE → send complete, close 1000
     On FAILED → send error, close 1011
  8. finally: cancel reader task, unsubscribe, close pubsub connection

Close codes:
  1000 — normal completion
  1008 — invalid run_id / run not found (policy violation)
  1011 — server error / simulation failed

Message shapes the client receives:
  { "type": "snapshot",  "status": str, "progress": float, "message": str, "error": str|null }
  { "type": "progress",  "frame": int,  "totalFrames": int, "percent": float }
  { "type": "ping" }
  { "type": "complete",  "metaUrl": str }
  { "type": "error",     "message": str }
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.deps import get_async_redis
from src.settings import settings
from src.storage.runs import RUN_ID_REGEX

logger = logging.getLogger(__name__)

router = APIRouter()

# ── helpers ────────────────────────────────────────────────────────────────────

def _run_dir(run_id: str) -> Path:
    return Path(settings.data_dir) / "runs" / run_id


def _snapshot_payload(run_id: str, run_dir: Path) -> dict:
    """Build the initial snapshot from marker files (same logic as status endpoint)."""
    if (run_dir / "DONE").exists():
        return {
            "type": "snapshot",
            "status": "complete",
            "progress": 1.0,
            "message": "Simulation complete.",
            "error": None,
        }
    if (run_dir / "FAILED").exists():
        tb = (run_dir / "FAILED").read_text(encoding="utf-8", errors="replace")
        short = tb.strip().splitlines()[-1] if tb.strip() else "Unknown error."
        return {
            "type": "snapshot",
            "status": "failed",
            "progress": 0.0,
            "message": "Simulation failed.",
            "error": short,
        }
    # No marker yet — query Celery state for richer progress info
    try:
        from celery.result import AsyncResult
        from src.worker.celery_app import celery_app
        result = AsyncResult(run_id, app=celery_app)
        if result.state == "PROGRESS":
            meta = result.info or {}
            pct = float(meta.get("percent", 0.0))
            frame = meta.get("frame", 0)
            total = meta.get("total", 0)
            return {
                "type": "snapshot",
                "status": "running",
                "progress": round(pct / 100.0, 4),
                "message": f"Running frame {frame}/{total}.",
                "error": None,
            }
    except Exception:  # noqa: BLE001
        pass
    return {
        "type": "snapshot",
        "status": "pending",
        "progress": 0.0,
        "message": "Simulation queued.",
        "error": None,
    }


async def _check_marker(run_dir: Path) -> str | None:
    """
    Returns 'complete' if DONE exists, 'failed' if FAILED exists, None otherwise.
    Uses asyncio thread executor to avoid blocking the event loop on file I/O.
    """
    loop = asyncio.get_event_loop()
    done_exists = await loop.run_in_executor(None, lambda: (run_dir / "DONE").exists())
    if done_exists:
        return "complete"
    failed_exists = await loop.run_in_executor(None, lambda: (run_dir / "FAILED").exists())
    if failed_exists:
        return "failed"
    return None


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@router.websocket("/ws/simulate/{run_id}")
async def ws_simulate(websocket: WebSocket, run_id: str) -> None:  # noqa: C901
    """
    Stream simulation progress to the client via WebSocket.
    See module docstring for full lifecycle description.
    """
    # ── Step 1: Validate run_id ────────────────────────────────────────────────
    if not RUN_ID_REGEX.match(run_id):
        await websocket.accept()
        await websocket.close(code=1008, reason="invalid run_id")
        return

    run_dir = _run_dir(run_id)

    # Path-traversal guard: resolved path must stay inside runs/
    runs_root = Path(settings.data_dir).resolve() / "runs"
    try:
        run_dir.resolve().relative_to(runs_root)
    except ValueError:
        await websocket.accept()
        await websocket.close(code=1008, reason="invalid run_id")
        return

    if not run_dir.exists():
        await websocket.accept()
        await websocket.close(code=1008, reason="run not found")
        return

    await websocket.accept()

    redis_client = get_async_redis()
    pubsub = redis_client.pubsub()
    channel = f"run:{run_id}:progress"

    # asyncio.Queue buffers messages while the snapshot is being built
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def _reader() -> None:
        """Background task: drain the pubsub socket and enqueue parsed messages."""
        try:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    try:
                        data = json.loads(raw["data"])
                        await queue.put(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("ws reader task error for %s: %s", run_id, exc)
        finally:
            await queue.put(None)  # sentinel: reader is done

    reader_task: asyncio.Task | None = None

    try:
        # ── Step 2: Subscribe BEFORE computing snapshot ────────────────────────
        await pubsub.subscribe(channel)

        # ── Step 3: Start buffering reader ────────────────────────────────────
        reader_task = asyncio.create_task(_reader())

        # ── Step 4: Fetch + send snapshot ─────────────────────────────────────
        snapshot = _snapshot_payload(run_id, run_dir)
        await websocket.send_json(snapshot)

        # If already terminal, we're done — no need to enter the loop
        if snapshot["status"] in ("complete", "failed"):
            if snapshot["status"] == "complete":
                await websocket.send_json(
                    {"type": "complete", "metaUrl": f"/api/runs/{run_id}/meta"}
                )
                await websocket.close(code=1000)
            else:
                short_err = snapshot.get("error") or "Simulation failed."
                await websocket.send_json({"type": "error", "message": short_err})
                await websocket.close(code=1011)
            return

        # ── Step 5: Drain buffered messages ───────────────────────────────────
        while not queue.empty():
            item = queue.get_nowait()
            if item is None:
                return
            await websocket.send_json(
                {
                    "type": "progress",
                    "frame": item.get("frame", 0),
                    "totalFrames": item.get("total", 0),
                    "percent": item.get("percent", 0.0),
                }
            )

        # ── Step 6: Streaming loop ─────────────────────────────────────────────
        heartbeat_secs = settings.ws_heartbeat_seconds
        marker_poll_secs = settings.ws_marker_poll_seconds
        last_marker_check = asyncio.get_event_loop().time()

        while True:
            # Wait for a message or heartbeat timeout
            try:
                item = await asyncio.wait_for(queue.get(), timeout=heartbeat_secs)
            except asyncio.TimeoutError:
                # Heartbeat
                await websocket.send_json({"type": "ping"})
                item = None

            if item is None and not isinstance(item, dict):
                # Sentinel from reader: pubsub closed or timed-out ping was sent
                # For ping case (TimeoutError above sets item = None via except),
                # continue the loop. For sentinel (queue.put(None) from reader),
                # check marker and exit.
                if queue.empty():
                    pass  # it was a ping timeout; continue
                else:
                    # Drain any remaining real messages before checking marker
                    pass
                # Fall through to marker check below
            elif item is not None:
                # Forward progress event
                await websocket.send_json(
                    {
                        "type": "progress",
                        "frame": item.get("frame", 0),
                        "totalFrames": item.get("total", 0),
                        "percent": item.get("percent", 0.0),
                    }
                )

            # Periodic marker check (at most every marker_poll_secs)
            now = asyncio.get_event_loop().time()
            if now - last_marker_check >= marker_poll_secs:
                last_marker_check = now
                marker = await _check_marker(run_dir)
                if marker == "complete":
                    await websocket.send_json(
                        {"type": "complete", "metaUrl": f"/api/runs/{run_id}/meta"}
                    )
                    await websocket.close(code=1000)
                    return
                if marker == "failed":
                    loop = asyncio.get_event_loop()
                    tb = await loop.run_in_executor(
                        None,
                        lambda: (run_dir / "FAILED").read_text(
                            encoding="utf-8", errors="replace"
                        ),
                    )
                    short = tb.strip().splitlines()[-1] if tb.strip() else "Unknown error."
                    await websocket.send_json({"type": "error", "message": short})
                    await websocket.close(code=1011)
                    return

    except WebSocketDisconnect:
        logger.info("ws_simulate: client disconnected run_id=%s", run_id)

    except Exception as exc:  # noqa: BLE001
        import traceback as _tb
        logger.error(
            "ws_simulate unhandled error run_id=%s:\n%s",
            run_id,
            _tb.format_exc(),
        )
        try:
            await websocket.send_json({"type": "error", "message": "Internal server error."})
            await websocket.close(code=1011)
        except Exception:  # noqa: BLE001
            pass

    finally:
        # Always clean up: cancel reader, unsubscribe, close pubsub
        if reader_task is not None and not reader_task.done():
            reader_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(reader_task), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        try:
            await pubsub.unsubscribe(channel)
        except Exception:  # noqa: BLE001
            pass
        try:
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass
        logger.debug("ws_simulate: cleaned up pubsub run_id=%s", run_id)
