from sqlalchemy import func, select

from app.models import BotControl, Prompt, Run, RunLog


def test_start_creates_queued_run(client, db):
    r = client.post("/api/bot/start")
    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    assert db.get(BotControl, 1).desired == "running"
    status = client.get("/api/bot/status").json()
    assert status["state"] == "queued" and status["run"]["id"] == r.json()["id"]


def test_start_twice_creates_one_run(client, db):
    first = client.post("/api/bot/start").json()
    second = client.post("/api/bot/start").json()
    assert first["id"] == second["id"]
    assert db.scalar(select(func.count()).select_from(Run)) == 1


def test_stop_sets_desired_stopped(client, db):
    client.post("/api/bot/start")
    r = client.post("/api/bot/stop")
    assert r.status_code == 200
    assert db.get(BotControl, 1).desired == "stopped"
    # A run the worker never picked up is cancelled right away.
    assert db.scalar(select(Run)).status == "stopped"
    assert client.get("/api/bot/status").json()["state"] == "idle"


def test_stop_running_run_is_left_to_worker(client, db):
    db.add(Run(status="running"))
    db.commit()
    client.post("/api/bot/stop")
    assert db.scalar(select(Run)).status == "running"


def test_status_idle_shows_last_run(client, db):
    db.add(Run(status="failed", error="Chrome failed to start"))
    db.commit()
    status = client.get("/api/bot/status").json()
    assert status["state"] == "idle"
    assert status["run"]["error"] == "Chrome failed to start"
    assert status["prompt"] is None
    assert status["linkedin_session"]["state"] == "unknown"


def test_status_includes_open_prompt(client, db):
    run = Run(status="waiting")
    db.add(run)
    db.flush()
    db.add(Prompt(run_id=run.id, title="Needs you", text="Solve the captcha", buttons=["Done, continue"]))
    db.commit()
    status = client.get("/api/bot/status").json()
    assert status["state"] == "waiting"
    assert status["prompt"]["title"] == "Needs you"
    assert status["prompt"]["buttons"] == ["Done, continue"]


def test_answer_prompt_validates_button(client, db):
    run = Run(status="waiting")
    db.add(run)
    db.flush()
    prompt = Prompt(run_id=run.id, title="t", text="x", buttons=["Yes", "No"])
    db.add(prompt)
    db.commit()
    url = f"/api/bot/prompts/{prompt.id}/answer"
    assert client.post(url, json={"button": "Maybe"}).status_code == 422
    assert client.post(url, json={"button": "No"}).status_code == 200
    db.refresh(prompt)
    assert prompt.answer == "No" and prompt.answered_at is not None
    assert client.post(url, json={"button": "Yes"}).status_code == 409
    assert client.post("/api/bot/prompts/999999/answer", json={"button": "Yes"}).status_code == 404


def test_runs_pagination(client, db):
    db.add_all([Run(status="finished") for _ in range(3)])
    db.commit()
    page = client.get("/api/runs?page=1&page_size=2").json()
    assert page["total"] == 3 and len(page["items"]) == 2
    assert page["items"][0]["id"] > page["items"][1]["id"]  # newest first


def test_logs_after_id_pagination(client, db):
    run = Run(status="running")
    db.add(run)
    db.flush()
    db.add_all([RunLog(run_id=run.id, line=f"line {i}") for i in range(5)])
    db.commit()
    first = client.get(f"/api/runs/{run.id}/logs?limit=3").json()
    assert [item["line"] for item in first["items"]] == ["line 0", "line 1", "line 2"]
    rest = client.get(f"/api/runs/{run.id}/logs?after_id={first['items'][-1]['id']}").json()
    assert [item["line"] for item in rest["items"]] == ["line 3", "line 4"]


def test_logs_stream_resumes_from_last_event_id(anon_client, committed_db):
    import os

    anon_client.post("/api/auth/login", json={"password": os.environ["UI_PASSWORD"]})
    run = Run(status="finished")
    committed_db.add(run)
    committed_db.flush()
    logs = [RunLog(run_id=run.id, line=f"line {i}") for i in range(3)]
    committed_db.add_all(logs)
    committed_db.commit()
    headers = {"Last-Event-ID": str(logs[0].id)}
    with anon_client.stream("GET", f"/api/runs/{run.id}/logs/stream", headers=headers) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())
    assert "line 0" not in body
    assert f"id: {logs[1].id}\ndata: line 1\n\n" in body
    assert "event: end" in body


def test_bot_routes_require_login(anon_client):
    assert anon_client.post("/api/bot/start").status_code == 401
    assert anon_client.get("/api/runs").status_code == 401
