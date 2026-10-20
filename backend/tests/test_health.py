from fastapi.testclient import TestClient
from app.main import app


def test_root_endpoint():
    """Verify GET / returns standard operational response."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["health_check"] == "/api/health"


def test_health_endpoint():
    """Verify GET /api/health returns healthy status for system, database, and storage."""
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()

        # Check top-level health
        assert data["status"] == "healthy"
        assert data["app_name"] == "Secure LAN Chat Backend"
        assert "version" in data
        assert "timestamp" in data

        # Check database health
        db_data = data["database"]
        assert db_data["status"] == "healthy"
        assert db_data["dialect"] == "sqlite"
        assert isinstance(db_data["tables"], list)

        # Check storage health
        storage_data = data["storage"]
        assert storage_data["status"] == "healthy"
        assert storage_data["exists"] is True
        assert storage_data["is_writable"] is True
