import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.settings import settings
# Use the fixture from test_runs_endpoints or recreate here, but since it's tests we can just import the fixture
from tests.test_runs_endpoints import mock_runs_dir

client = TestClient(app)

def test_flux_endpoint(mock_runs_dir):
    run_id = mock_runs_dir
    
    # 1. Valid query
    response = client.get(f"/api/runs/{run_id}/flux?lon=145.2&lat=32.1&radiusKm=100")
    assert response.status_code == 200
    data = response.json()
    assert data["runId"] == run_id
    assert "query" in data
    assert "totalPasses" in data
    assert "uniqueParticles" in data
    assert "fraction" in data
    assert "estimatedTons" in data
    assert "bySource" in data
    assert "timeSeries" in data

    # 2. Out of range lon
    response = client.get(f"/api/runs/{run_id}/flux?lon=200&lat=32.1")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PARAM"

    # 3. Nonexistent run
    response = client.get("/api/runs/nonexistent-run/flux?lon=145.2&lat=32.1")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"

    # 4. Out of range radius
    response = client.get(f"/api/runs/{run_id}/flux?lon=145.2&lat=32.1&radius_km=2000")
    assert response.status_code == 400
