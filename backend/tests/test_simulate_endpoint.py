"""
tests/test_simulate_endpoint.py
================================
Unit tests for POST /api/simulate and GET /api/simulate/{run_id}/status.
Celery tasks are mocked so no real Redis or Parcels needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.settings import settings

client = TestClient(app)

VALID_BODY = {
    "region": {"west": -160, "east": -120, "south": 20, "north": 50},
    "time": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-08T00:00:00Z",
        "timeStepHours": 6,
    },
    "particles": {
        "count": 500,
        "maxAgeDays": 30,
        "windagePercent": 1.5,
        "diffusionM2PerS": 50,
        "beachingEnabled": False,
    },
}


@pytest.fixture
def mock_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    (data_dir / "runs").mkdir(parents=True)
    monkeypatch.setattr(settings, "data_dir", str(data_dir))
    return data_dir


# ── POST /api/simulate ─────────────────────────────────────────────────────────

def test_submit_returns_202(mock_data_dir):
    from src.worker.tasks import run_simulation_task
    with patch.object(run_simulation_task, "apply_async") as mock_apply:
        mock_apply.return_value = MagicMock(id="abc")
        response = client.post("/api/simulate", json=VALID_BODY)
        
    assert response.status_code == 202, response.text
    data = response.json()
    assert "runId" in data
    assert data["status"] == "pending"
    
    mock_apply.assert_called_once()
    args, kwargs = mock_apply.call_args
    assert "args" in kwargs
    run_id, params = kwargs["args"]
    assert len(run_id) == 32  # uuid4 hex
    assert "region" in params
    assert "time" in params
    assert "particles" in params


def test_submit_out_of_range_particles(mock_data_dir):
    body = {**VALID_BODY, "particles": {**VALID_BODY["particles"], "count": 999999}}
    response = client.post("/api/simulate", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMS"


def test_submit_time_range_too_long(mock_data_dir):
    body = {
        **VALID_BODY,
        "time": {
            "start": "2020-01-01T00:00:00Z",
            "end": "2022-01-01T00:00:00Z",
            "timeStepHours": 6,
        },
    }
    response = client.post("/api/simulate", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMS"


def test_submit_west_greater_than_east(mock_data_dir):
    body = {**VALID_BODY, "region": {"west": -120, "east": -160, "south": 20, "north": 50}}
    response = client.post("/api/simulate", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMS"


def test_submit_429_when_inflight_limit_reached(mock_data_dir):
    # Create a fake in-flight run (no DONE/FAILED)
    inflight_dir = Path(settings.data_dir) / "runs" / "inflight-run"
    inflight_dir.mkdir(parents=True)

    response = client.post("/api/simulate", json=VALID_BODY)
    assert response.status_code == 429
    assert response.headers.get("retry-after") == "60"
    assert response.json()["error"]["code"] == "TOO_MANY_RUNS"

def test_rate_limit(mock_data_dir, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_simulations", 10)
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5)
    
    from src.worker.tasks import run_simulation_task
    with patch.object(run_simulation_task, "apply_async"):
        # Reset internal token bucket state to avoid leaking from other tests
        from src.api.routes.simulate import _RATE_LIMIT_STORE
        _RATE_LIMIT_STORE.clear()
        
        for _ in range(5):
            response = client.post("/api/simulate", json=VALID_BODY)
            assert response.status_code == 202
            
        response = client.post("/api/simulate", json=VALID_BODY)
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "TOO_MANY_RUNS"


# ── GET /api/simulate/{run_id}/status ─────────────────────────────────────────

@pytest.fixture
def fake_run(mock_data_dir):
    """Create a minimal run directory, return (run_id, run_dir)."""
    run_id = "test-status-run"
    run_dir = Path(settings.data_dir) / "runs" / run_id
    run_dir.mkdir(parents=True)
    return run_id, run_dir


def test_status_complete(fake_run):
    run_id, run_dir = fake_run
    (run_dir / "DONE").touch()
    response = client.get(f"/api/simulate/{run_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["progress"] == 1.0


def test_status_failed(fake_run):
    run_id, run_dir = fake_run
    (run_dir / "FAILED").write_text("Traceback (most recent call last):\n  ...\nValueError: oops")
    response = client.get(f"/api/simulate/{run_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error"] is not None


def test_status_404_for_nonexistent(mock_data_dir):
    response = client.get("/api/simulate/doesnotexist/status")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"
