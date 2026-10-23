import json

from app.settings_schema import SCHEMA, SECRET_ENV, SECTIONS, defaults


def test_schema_lists_every_field(client):
    r = client.get("/api/settings/schema")
    assert r.status_code == 200
    assert {(f["section"], f["key"]) for f in r.json()} == {(f.section, f.key) for f in SCHEMA}


def test_get_returns_defaults_when_empty(client):
    assert client.get("/api/settings").json() == defaults()


def test_put_then_get_roundtrip(client):
    r = client.put("/api/settings/search", json={"search_terms": ["Go Developer"], "switch_number": "12"})
    assert r.status_code == 200
    assert r.json()["search_terms"] == ["Go Developer"] and r.json()["switch_number"] == 12
    got = client.get("/api/settings").json()["search"]
    assert got["search_terms"] == ["Go Developer"]
    assert got["switch_number"] == 12
    # Fields not sent keep their value.
    assert got["easy_apply_only"] == defaults()["search"]["easy_apply_only"]


def test_invalid_setting_rejected_nothing_saved(client):
    before = client.get("/api/settings").json()
    r = client.put("/api/settings/questions", json={"desired_salary": "abc", "website": "https://x.dev"})
    assert r.status_code == 422
    assert "desired_salary" in r.json()["detail"]["field_errors"]
    assert client.get("/api/settings").json() == before


def test_unknown_section_404(client):
    assert client.put("/api/settings/nope", json={}).status_code == 404


def test_secrets_endpoint_never_returns_values(client, monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-test")
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    r = client.get("/api/settings/secrets")
    assert r.status_code == 200
    assert "sk-test" not in r.text
    by_env = {s["env_var"]: s for s in r.json()}
    assert by_env["CLAUDE_API_KEY"]["set"] is True
    assert by_env["GLM_API_KEY"]["set"] is False
    assert set(by_env) >= {"LINKEDIN_USERNAME", "LINKEDIN_PASSWORD", "UI_PASSWORD", "SESSION_SECRET"}


def _import(client, data, name="applier-settings.json"):
    body = data if isinstance(data, (str, bytes)) else json.dumps(data)
    return client.post("/api/settings/import", files={"file": (name, body, "application/json")})


def test_export_has_every_section_and_no_secrets(client, monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-secret-value")
    monkeypatch.setenv("LINKEDIN_PASSWORD", "hunter22")
    client.put("/api/settings/email", json={"my_name": "Jane Doe"})
    r = client.get("/api/settings/export")
    assert r.status_code == 200
    assert 'filename="applier-settings.json"' in r.headers["content-disposition"]
    data = r.json()
    assert data["version"] == 1
    assert set(data) == {"version", *SECTIONS}
    assert data["email"]["my_name"] == "Jane Doe"
    assert {k: v for k, v in data.items() if k != "version"} == client.get("/api/settings").json()
    assert "sk-secret-value" not in r.text and "hunter22" not in r.text
    assert not {k for section in SECTIONS for k in data[section]} & set(SECRET_ENV)


def test_import_roundtrip(client):
    client.put("/api/settings/search", json={"search_terms": ["Go Developer"]})
    exported = client.get("/api/settings/export").json()
    client.put("/api/settings/search", json={"search_terms": ["Something else"]})
    client.put("/api/settings/email", json={"my_name": "Changed"})
    r = _import(client, exported)
    assert r.status_code == 200, r.text
    assert r.json() == {k: v for k, v in exported.items() if k != "version"}
    got = client.get("/api/settings").json()
    assert got["search"]["search_terms"] == ["Go Developer"]
    assert got["email"]["my_name"] == exported["email"]["my_name"]


def test_import_partial_file_keeps_other_sections(client):
    client.put("/api/settings/email", json={"my_name": "Jane Doe"})
    r = _import(client, {"version": 1, "search": {"switch_number": 7}})
    assert r.status_code == 200
    got = client.get("/api/settings").json()
    assert got["search"]["switch_number"] == 7 and got["email"]["my_name"] == "Jane Doe"


def test_import_validates_everything_first_nothing_saved(client):
    before = client.get("/api/settings").json()
    r = _import(client, {
        "version": 1,
        "search": {"search_terms": ["Valid change"]},
        "questions": {"desired_salary": "abc"},
        "personals": {"nope": 1},
        "ai": {"claude_api_key": "sk-x"},
        "secrets": {},
        "email": "not an object",
    })
    assert r.status_code == 422
    errors = r.json()["detail"]["field_errors"]
    assert set(errors) == {"questions.desired_salary", "personals.nope", "ai.claude_api_key", "secrets", "email"}
    assert client.get("/api/settings").json() == before


def test_import_rejects_bad_files(client):
    cases = [
        ("{not json", "file"),
        ("[1, 2]", "file"),
        (json.dumps({"search": {}}), "version"),
        (json.dumps({"version": 2, "search": {}}), "version"),
    ]
    for body, key in cases:
        r = _import(client, body)
        assert r.status_code == 422, body
        assert key in r.json()["detail"]["field_errors"], body
    assert _import(client, b"x" * (1024 * 1024 + 1)).status_code == 413


def test_export_and_import_need_login(anon_client):
    assert anon_client.get("/api/settings/export").status_code == 401
    assert _import(anon_client, {"version": 1}).status_code == 401
