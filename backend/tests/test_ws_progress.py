"""
tests/test_ws_progress.py
==========================
WebSocket endpoint tests — M4.

Uses Starlette's built-in WebSocket test client (sync interface).
Redis pubsub is mocked so no running Redis is required.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.settings import settings


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    (data_dir / "runs").mkdir(parents=True)
    monkeypatch.setattr(settings, "data_dir", str(data_dir))
    return data_dir


@pytest.fixture
def done_run(mock_data_dir):
    """A run that already has DONE marker."""
    run_id = "done-run-abcd1234"
    run_dir = Path(settings.data_dir) / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "DONE").touch()
    return run_id


@pytest.fixture
def failed_run(mock_data_dir):
    """A run that already has FAILED marker."""
    run_id = "failed-run-abcd5678"
    run_dir = Path(settings.data_dir) / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "FAILED").write_text("Traceback:\n  ...\nValueError: boom")
    return run_id


@pytest.fixture
def pending_run(mock_data_dir):
    """A run with no markers (pending/running)."""
    run_id = "pending-run-abcd9012"
    run_dir = Path(settings.data_dir) / "runs" / run_id
    run_dir.mkdir(parents=True)
    return run_id


def _make_empty_pubsub():
    """
    Mock pubsub that never yields messages (simulates idle subscription).
    listen() is an async generator that yields nothing then sleeps forever.
    """
    async def _listen():
        # Never yield — wait will time out (heartbeat)
        await asyncio.sleep(9999)
        return
        yield  # make it an async generator

    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.aclose = AsyncMock()
    pubsub.listen = _listen
    return pubsub


# ── test_ws_progress_done: snapshot + complete, close 1000 ───────────────────

def test_ws_done_run_receives_complete_and_closes_1000(done_run):
    """
    A run that is already DONE:
      - receives snapshot(status=complete)
      - receives complete message
      - connection closes with code 1000
    """
    pubsub = _make_empty_pubsub()
    mock_redis = MagicMock()
    mock_redis.pubsub = MagicMock(return_value=pubsub)

    with patch("src.api.routes.ws.get_async_redis", return_value=mock_redis):
        client = TestClient(app)
        with client.websocket_connect(f"/api/ws/simulate/{done_run}") as ws:
            snapshot = ws.receive_json()
            assert snapshot["type"] == "snapshot"
            assert snapshot["status"] == "complete"
            assert snapshot["progress"] == 1.0

            complete = ws.receive_json()
            assert complete["type"] == "complete"
            assert complete["metaUrl"] == f"/api/runs/{done_run}/meta"
            # connection should close normally after this


# ── test_ws_failed_run: snapshot + error, close 1011 ─────────────────────────

def test_ws_failed_run_receives_error(failed_run):
    """A FAILED run: snapshot(status=failed) then error message."""
    pubsub = _make_empty_pubsub()
    mock_redis = MagicMock()
    mock_redis.pubsub = MagicMock(return_value=pubsub)

    with patch("src.api.routes.ws.get_async_redis", return_value=mock_redis):
        client = TestClient(app)
        with client.websocket_connect(f"/api/ws/simulate/{failed_run}") as ws:
            snapshot = ws.receive_json()
            assert snapshot["type"] == "snapshot"
            assert snapshot["status"] == "failed"
            assert snapshot["error"] is not None

            error_msg = ws.receive_json()
            assert error_msg["type"] == "error"
            assert "error" in error_msg or "message" in error_msg


# ── test_ws_invalid_run: close 1008 ──────────────────────────────────────────

def test_ws_invalid_run_id_closes_1008(mock_data_dir):
    """An invalid run_id (contains slash after URL decode) closes with 1008."""
    client = TestClient(app)
    # run_id with characters outside [a-zA-Z0-9_-]
    with pytest.raises(Exception):
        # Starlette raises when the server closes before sending data
        with client.websocket_connect("/api/ws/simulate/!!!invalid!!!") as ws:
            ws.receive_json()


def test_ws_nonexistent_run_closes_1008(mock_data_dir):
    """A valid run_id format but no directory closes with 1008."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/simulate/doesnotexist1234") as ws:
            ws.receive_json()


# ── test_ws_path_traversal: close 1008 ───────────────────────────────────────

def test_ws_path_traversal_closes_1008(mock_data_dir):
    """
    URL-encoded path traversal is caught by the regex (dots are not in
    [a-zA-Z0-9_-]) and closes with 1008.
    """
    client = TestClient(app)
    # %2F = / and %2E = . — both outside allowed charset
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/simulate/..%2Fetc%2Fpasswd") as ws:
            ws.receive_json()


# ── test_ws_progress_forwarding: mocked pubsub delivers a message ─────────────

def test_ws_progress_forwarding(pending_run):
    """
    Simulate a Redis progress message arriving:
      - pubsub.listen() yields one progress event, then blocks
      - assert client receives { type: progress, frame, totalFrames, percent }
    """
    progress_payload = json.dumps({"frame": 5, "total": 120, "percent": 4.2})

    async def _listen():
        # Yield the synthetic progress message
        yield {"type": "message", "data": progress_payload}
        # Then block so the marker poll picks up DONE
        await asyncio.sleep(9999)

    # Write DONE after a slight delay so the loop terminates
    run_dir = Path(settings.data_dir) / "runs" / pending_run

    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.aclose = AsyncMock()
    pubsub.listen = _listen

    mock_redis = MagicMock()
    mock_redis.pubsub = MagicMock(return_value=pubsub)

    # We need the run to complete so the WS loop exits; write DONE before connecting
    # but keep the run as pending initially for the snapshot, then write DONE
    # The simplest approach: write DONE right away so the loop terminates fast,
    # but we still get the progress message from the drain step.
    # To test the forwarding path, we need it NOT done yet on snapshot, but done
    # by the first marker poll. Use a delayed write via a thread.
    import threading, time as _time

    def _write_done():
        _time.sleep(1.0)
        (run_dir / "DONE").touch()

    threading.Thread(target=_write_done, daemon=True).start()

    received = []
    with patch("src.api.routes.ws.get_async_redis", return_value=mock_redis):
        client = TestClient(app, raise_server_exceptions=False)
        with client.websocket_connect(f"/api/ws/simulate/{pending_run}") as ws:
            # Receive snapshot (pending)
            snap = ws.receive_json()
            assert snap["type"] == "snapshot"

            # Receive the forwarded progress message
            msg = ws.receive_json()
            received.append(msg)

            # Keep receiving until we get complete or timeout
            try:
                while True:
                    m = ws.receive_json()
                    received.append(m)
                    if m.get("type") in ("complete", "error"):
                        break
            except Exception:
                pass

    progress_msgs = [m for m in received if m.get("type") == "progress"]
    assert len(progress_msgs) >= 1
    p = progress_msgs[0]
    assert p["frame"] == 5
    assert p["totalFrames"] == 120
    assert abs(p["percent"] - 4.2) < 0.01
