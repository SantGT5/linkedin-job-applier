import json
import time
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import BotControl, Prompt, Run, RunLog, Setting
from app.worker import Worker

FAKE_BOT = Path(__file__).parent / "fakes" / "fake_bot.py"


@pytest.fixture
def worker(engine, committed_db, tmp_path, monkeypatch):
    w = Worker(
        session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        bot_script=FAKE_BOT,
        data_dir=tmp_path,
        database_url=engine.url.render_as_string(hide_password=False),
        kill_grace=5.0,
    )
    yield w
    w.shutdown()


def queue_run(db) -> Run:
    db.get(BotControl, 1).desired = "running"
    run = Run(status="queued")
    db.add(run)
    db.commit()
    return run


def tick_until(worker, db, run, statuses, timeout=15.0) -> Run:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        worker.tick()
        db.expire_all()
        current = db.get(Run, run.id)
        if current.status in statuses:
            return current
        time.sleep(0.1)
    raise AssertionError(f"run stayed {db.get(Run, run.id).status}, wanted {statuses}")


def log_lines(db, run) -> list[str]:
    return list(db.scalars(select(RunLog.line).where(RunLog.run_id == run.id).order_by(RunLog.id)))


def test_queued_run_starts_child_and_captures_logs(worker, committed_db, monkeypatch):
    monkeypatch.setenv("FAKE_BOT_MODE", "print")
    run = queue_run(committed_db)
    worker.tick()
    committed_db.expire_all()
    assert committed_db.get(Run, run.id).status == "running"
    done = tick_until(worker, committed_db, run, {"finished"})
    assert done.ended_at is not None and done.error is None
    assert log_lines(committed_db, run) == ["fake line 0", "fake line 1", "fake line 2"]
    assert worker.child is None
    assert committed_db.get(BotControl, 1).desired == "stopped"


def test_snapshot_contains_saved_settings_not_secrets(worker, committed_db, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_BOT_MODE", "settings")
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-secret-test")
    committed_db.add(Setting(section="search", values={"search_terms": ["Only This"]}))
    run = queue_run(committed_db)
    tick_until(worker, committed_db, run, {"finished"})
    snapshot = (tmp_path / "run" / f"run-{run.id}.json").read_text()
    assert json.loads(snapshot)["search"]["search_terms"] == ["Only This"]
    assert "sk-secret-test" not in snapshot
    lines = log_lines(committed_db, run)
    assert "terms=['Only This']" in lines
    # The bot still gets its secrets, from the environment.
    assert "has_key=True" in lines


def test_child_env_has_no_ui_secrets(worker, tmp_path):
    env = worker.child_env(run_id=1, snapshot=tmp_path / "s.json")
    assert "UI_PASSWORD" not in env and "SESSION_SECRET" not in env
    assert env["APPLIER_RUN_ID"] == "1"


def test_crashing_bot_marks_run_failed(worker, committed_db, monkeypatch):
    monkeypatch.setenv("FAKE_BOT_MODE", "crash")
    run = queue_run(committed_db)
    failed = tick_until(worker, committed_db, run, {"failed"})
    assert "Chrome failed to start" in failed.error
    assert worker.child is None
    # Worker is idle again: the next queued run starts.
    monkeypatch.setenv("FAKE_BOT_MODE", "print")
    nxt = queue_run(committed_db)
    tick_until(worker, committed_db, nxt, {"finished"})


def test_spawn_failure_marks_run_failed(worker, committed_db):
    worker.bot_script = Path("/nonexistent/bot.py")
    worker.python = "/nonexistent/python"
    run = queue_run(committed_db)
    failed = tick_until(worker, committed_db, run, {"failed"})
    assert failed.error
    assert worker.child is None


def test_orphaned_running_run_marked_failed(worker, committed_db):
    run = Run(status="running")
    committed_db.add(run)
    committed_db.commit()
    failed = tick_until(worker, committed_db, run, {"failed"})
    assert "worker" in failed.error.lower()


def test_stop_while_waiting_closes_prompt(worker, committed_db, monkeypatch):
    monkeypatch.setenv("FAKE_BOT_MODE", "ask")
    run = queue_run(committed_db)
    tick_until(worker, committed_db, run, {"waiting"})
    prompt = committed_db.scalar(select(Prompt).where(Prompt.run_id == run.id))
    assert prompt.buttons == ["Done, continue"]
    committed_db.get(BotControl, 1).desired = "stopped"
    committed_db.commit()
    started = time.monotonic()
    stopped = tick_until(worker, committed_db, run, {"stopped"}, timeout=10)
    assert time.monotonic() - started <= 5.5
    committed_db.expire_all()
    assert committed_db.get(Prompt, prompt.id).answer == "__stopped__"
    assert worker.child is None
    assert stopped.ended_at is not None


def test_stop_kills_unresponsive_bot(worker, committed_db, monkeypatch):
    monkeypatch.setenv("FAKE_BOT_MODE", "sleep")
    run = queue_run(committed_db)
    tick_until(worker, committed_db, run, {"running"})
    committed_db.get(BotControl, 1).desired = "stopped"
    committed_db.commit()
    tick_until(worker, committed_db, run, {"stopped"}, timeout=10)
    assert worker.child is None


def _cookie_db(profile: Path, expires_utc: int | None) -> Path:
    import sqlite3

    (profile / "Default").mkdir(parents=True, exist_ok=True)
    path = profile / "Default" / "Cookies"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, expires_utc INTEGER)")
    if expires_utc is not None:
        con.execute("INSERT INTO cookies VALUES ('.www.linkedin.com', 'li_at', ?)", (expires_utc,))
    con.commit()
    con.close()
    return path


def _chrome_time(seconds_from_now: int) -> int:
    # Chrome stores microseconds since 1601-01-01.
    return int((time.time() + 11644473600 + seconds_from_now) * 1_000_000)


@pytest.mark.parametrize(
    "expires, expected",
    [(3600, "logged_in"), (-3600, "logged_out"), (None, "logged_out")],
)
def test_session_state_from_saved_profile(worker, committed_db, tmp_path, expires, expected):
    from app.models import LinkedinSession

    profile = tmp_path / "chrome-profile"
    _cookie_db(profile, _chrome_time(expires) if expires is not None else None)
    worker.profile_dir = profile
    worker.check_session()
    committed_db.expire_all()
    row = committed_db.get(LinkedinSession, 1)
    assert row.state == expected and row.checked_at is not None


def test_session_unknown_without_profile(worker, committed_db, tmp_path):
    from app.models import LinkedinSession

    worker.profile_dir = tmp_path / "missing"
    worker.check_session()
    committed_db.expire_all()
    assert committed_db.get(LinkedinSession, 1).state == "unknown"


def test_newer_bot_check_wins_over_cookie(worker, committed_db, tmp_path):
    from datetime import datetime, timedelta, timezone

    from app.models import LinkedinSession

    profile = tmp_path / "chrome-profile"
    _cookie_db(profile, _chrome_time(3600))
    row = committed_db.get(LinkedinSession, 1)
    # The bot saw a login page after the cookie file was last written: cookie is stale server-side.
    row.state, row.checked_at = "logged_out", datetime.now(timezone.utc) + timedelta(minutes=1)
    committed_db.commit()
    worker.profile_dir = profile
    worker.check_session()
    committed_db.expire_all()
    assert committed_db.get(LinkedinSession, 1).state == "logged_out"
