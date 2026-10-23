import os

PASSWORD = os.environ["UI_PASSWORD"]


def test_health_is_public(anon_client):
    r = anon_client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_requires_login(anon_client):
    assert anon_client.get("/api/settings").status_code == 401


def test_login_wrong_password_401(anon_client):
    r = anon_client.post("/api/auth/login", json={"password": "nope"})
    assert r.status_code == 401
    assert anon_client.get("/api/settings").status_code == 401


def test_login_then_access(anon_client):
    r = anon_client.post("/api/auth/login", json={"password": PASSWORD})
    assert r.status_code == 204
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert anon_client.get("/api/settings").status_code == 200


def test_auth_check_endpoint(anon_client):
    assert anon_client.get("/api/auth/check").status_code == 401
    anon_client.post("/api/auth/login", json={"password": PASSWORD})
    assert anon_client.get("/api/auth/check").status_code == 204


def test_logout(client):
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/settings").status_code == 401


def test_empty_ui_password_never_logs_in(anon_client, monkeypatch):
    monkeypatch.setenv("UI_PASSWORD", "")
    assert anon_client.post("/api/auth/login", json={"password": ""}).status_code == 401
