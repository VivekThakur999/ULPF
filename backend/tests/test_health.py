def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"


def test_openapi_available(client):
    assert client.get("/openapi.json").status_code == 200
