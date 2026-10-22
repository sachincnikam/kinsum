def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Kinsum"


def test_unknown_api_route_is_404(unlocked):
    assert unlocked.get("/api/does-not-exist").status_code == 404


def test_api_routes_are_locked_by_default(client):
    # Deny by default: without a session even unknown routes say "locked", not "not found".
    assert client.get("/api/does-not-exist").status_code == 423


def test_other_host_names_are_refused(app):
    from fastapi.testclient import TestClient

    evil = TestClient(app, base_url="http://attacker.example")
    assert evil.get("/api/health").status_code == 400
