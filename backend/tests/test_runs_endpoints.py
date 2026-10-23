import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json

from src.api.main import app
from src.settings import settings

client = TestClient(app)

@pytest.fixture
def mock_runs_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Override settings
    monkeypatch.setattr(settings, "data_dir", str(data_dir))
    
    runs_dir = data_dir / "runs"
    runs_dir.mkdir()
    
    # Create fake complete run
    run_id = "test-run-123"
    run_dir = runs_dir / run_id
    run_dir.mkdir()
    
    # Create meta.json
    meta = {
        "schemaVersion": 1,
        "generatedAt": "2026-01-01T00:00:00Z",
        "startDate": "2026-01-01T00:00:00Z",
        "timeStepHours": 6,
        "frameCount": 2,
        "particleCount": 500,
        "sources": [],
        "bounds": {"west": -160, "east": -120, "south": 20, "north": 50},
        "heatmapGrid": {"cols": 720, "rows": 360}
    }
    with open(run_dir / "meta.json", "w") as f:
        json.dump(meta, f)
        
    # Create DONE
    (run_dir / "DONE").touch()
    
    # Create fake frames
    frames_dir = run_dir / "frames"
    frames_dir.mkdir()
    # Write 19 * 500 bytes = 9500 bytes for frame 0
    with open(frames_dir / "0.bin", "wb") as f:
        f.write(b"A" * (500 * 19))
        
    return run_id

def test_get_runs(mock_runs_dir):
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["runId"] == mock_runs_dir
    assert runs[0]["status"] == "complete"
    assert runs[0]["particleCount"] == 500
    assert runs[0]["frameCount"] == 2

def test_get_run_meta(mock_runs_dir):
    response = client.get(f"/api/runs/{mock_runs_dir}/meta")
    assert response.status_code == 200
    meta = response.json()
    assert meta["particleCount"] == 500
    assert "schemaVersion" in meta

def test_get_run_meta_not_found(mock_runs_dir):
    response = client.get("/api/runs/nonexistent/meta")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"

def test_get_run_meta_path_traversal(mock_runs_dir):
    response = client.get("/api/runs/%2E%2E/meta")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RUN_ID"

def test_get_frame_success(mock_runs_dir):
    response = client.get(f"/api/runs/{mock_runs_dir}/frames/0")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/octet-stream"
    assert int(response.headers["Content-Length"]) == 500 * 19
    assert response.headers["X-Frame-Index"] == "0"
    assert response.headers["X-Particle-Count"] == "500"
    assert len(response.content) == 500 * 19

def test_get_frame_out_of_range(mock_runs_dir):
    response = client.get(f"/api/runs/{mock_runs_dir}/frames/999")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "FRAME_OUT_OF_RANGE"

def test_delete_run(mock_runs_dir):
    response = client.delete(f"/api/runs/{mock_runs_dir}")
    assert response.status_code == 204
    
    # Verify it's gone
    assert not (Path(settings.data_dir) / "runs" / mock_runs_dir).exists()

def test_delete_run_in_progress(mock_runs_dir):
    # Remove DONE marker to simulate running
    (Path(settings.data_dir) / "runs" / mock_runs_dir / "DONE").unlink()
    
    response = client.delete(f"/api/runs/{mock_runs_dir}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RUN_IN_PROGRESS"
