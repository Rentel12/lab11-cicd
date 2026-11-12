from app import app, greet


def test_greet():
    assert greet("  aidana ") == "Hello, Aidana!"


def test_healthz():
    client = app.test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_version_default():
    client = app.test_client()
    assert client.get("/version").get_json()["version"] == "dev"
