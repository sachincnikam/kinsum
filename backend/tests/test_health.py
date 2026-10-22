from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Kinsum"


def test_unknown_api_route_is_404():
    assert client.get("/api/does-not-exist").status_code == 404
