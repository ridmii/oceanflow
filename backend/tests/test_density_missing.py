import pytest
from fastapi.testclient import TestClient
import json

from src.api.main import app
from src.settings import settings

client = TestClient(app)

@pytest.fixture
def mock_runs_dir_no_density(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(settings, "data_dir", str(data_dir))
    
    runs_dir = data_dir / "runs"
    runs_dir.mkdir()
    
    run_id = "test-no-density"
    run_dir = runs_dir / run_id
    run_dir.mkdir()
    
    meta = {
        "frameCount": 2,
        "heatmapGrid": {"cols": 720, "rows": 360}
    }
    with open(run_dir / "meta.json", "w") as f:
        json.dump(meta, f)
        
    return run_id

def test_density_missing_returns_404(mock_runs_dir_no_density):
    response = client.get(f"/api/runs/{mock_runs_dir_no_density}/density/0")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Density frame not found."
    assert response.json()["error"]["code"] == "DENSITY_NOT_FOUND"

def test_density_out_of_range(mock_runs_dir_no_density):
    response = client.get(f"/api/runs/{mock_runs_dir_no_density}/density/999")
    assert response.status_code == 400
