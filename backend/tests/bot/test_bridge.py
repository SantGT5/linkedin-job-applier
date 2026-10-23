import threading
import time

import pytest
from sqlalchemy import select

from app.models import AppliedJob, FailedJob, HrEmail, LinkedinSession, Prompt, Run, UnansweredQuestion


@pytest.fixture
def bridge(engine, committed_db, monkeypatch):
    run = Run(status="running")
    committed_db.add(run)
    committed_db.commit()
    monkeypatch.setenv("APPLIER_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setenv("APPLIER_RUN_ID", str(run.id))
    from modules import bridge as module

    module.POLL_SECONDS = 0.1
    module.run = run
    return module


def test_bridge_disabled_without_env(monkeypatch):
    monkeypatch.delenv("APPLIER_DATABASE_URL", raising=False)
    from modules import bridge

    assert bridge.enabled() is False
    assert bridge.applied_job_ids() == set()


def test_bridge_ask_returns_answer(bridge, committed_db):
    result = {}
    thread = threading.Thread(target=lambda: result.update(answer=bridge.ask("T", "Text", ["Yes", "No"])))
    thread.start()
    deadline = time.monotonic() + 5
    prompt = None
    while prompt is None and time.monotonic() < deadline:
        committed_db.expire_all()
        prompt = committed_db.scalar(select(Prompt))
        time.sleep(0.05)
    assert prompt.title == "T" and prompt.buttons == ["Yes", "No"]
    assert committed_db.get(Run, bridge.run.id).status == "waiting"
    prompt.answer = "No"
    committed_db.commit()
    thread.join(5)
    assert result["answer"] == "No"
    committed_db.expire_all()
    assert committed_db.get(Run, bridge.run.id).status == "running"


def test_bridge_ask_stopped_exits(bridge, committed_db):
    result = {}

    def target():
        try:
            bridge.ask("T", "Text", ["OK"])
        except SystemExit as e:
            result["exit"] = e.code

    thread = threading.Thread(target=target)
    thread.start()
    time.sleep(0.5)
    committed_db.expire_all()
    committed_db.scalar(select(Prompt)).answer = "__stopped__"
    committed_db.commit()
    thread.join(5)
    assert result == {"exit": 0}


def test_bridge_records(bridge, committed_db):
    bridge.record_session("logged_in")
    bridge.save_applied({"job_id": "11", "title": "Dev", "company": "Acme", "date_applied": "2026-10-22 10:00:00"})
    bridge.save_applied({"job_id": "11", "title": "Dev 2", "company": "Acme"})
    bridge.save_failed({"job_id": "12", "assumed_reason": "x", "stack_trace": "y"})
    n = bridge.save_emails({"job_id": "11", "title": "Dev", "company": "Acme", "job_link": "l"}, ["a@b.io", "a@b.io"], "Subj")
    bridge.save_emails({"job_id": "11", "title": "Dev", "company": "Acme", "job_link": "l"}, ["a@b.io"], "Subj")
    bridge.record_unanswered("Proficiency in German?", "select", ["None", "Basic"], "11")
    bridge.record_unanswered("Proficiency in German?", "select", ["None", "Basic"], "13")
    bridge.bump_counts(applied=1, skipped=2)
    bridge.bump_counts(applied=1)
    committed_db.expire_all()
    assert committed_db.get(LinkedinSession, 1).state == "logged_in"
    assert committed_db.get(AppliedJob, "11").title == "Dev 2"
    assert bridge.applied_job_ids() == {"11"}
    assert committed_db.scalar(select(FailedJob)).assumed_reason == "x"
    assert n == 1
    assert [e.email for e in committed_db.scalars(select(HrEmail))] == ["a@b.io"]
    q = committed_db.scalar(select(UnansweredQuestion))
    assert q.seen_count == 2 and q.job_id == "13"
    run = committed_db.get(Run, bridge.run.id)
    assert (run.applied_count, run.failed_count, run.skipped_count) == (2, 0, 2)


def test_helpers_route_dialogs_through_bridge(monkeypatch, capsys):
    from modules import bridge, helpers

    asked = []
    monkeypatch.setenv("APPLIER_DATABASE_URL", "postgresql://unused")
    monkeypatch.setattr(bridge, "ask", lambda title, text, buttons: asked.append((title, text, list(buttons))) or buttons[-1])
    # Confirms are questions: they wait for the owner in the UI.
    assert helpers.safe_confirm("Pick one", "Choose", ("A", "B")) == "B"
    # Pauses wait for the owner too.
    assert helpers.pause_for_user("Solve the captcha", "Login", "Done, continue") == "Done, continue"
    # Plain alerts are information only: logged, never blocking.
    assert helpers.safe_alert("Resume missing", "Missing Resume", "OK") == "OK"
    assert asked == [("Choose", "Pick one", ["A", "B"]), ("Login", "Solve the captcha", ["Done, continue"])]
    assert "Resume missing" in capsys.readouterr().out


def test_dialogs_outside_worker_use_the_terminal(monkeypatch, capsys):
    # runAiBot replaces pyautogui.alert/confirm with these helpers: they must not call back into
    # pyautogui (that recursed whenever tkinter was installed).
    import sys
    import types

    from modules import helpers

    monkeypatch.delenv("APPLIER_DATABASE_URL", raising=False)
    monkeypatch.setitem(sys.modules, "tkinter", types.ModuleType("tkinter"))
    monkeypatch.setitem(sys.modules, "pyautogui", types.SimpleNamespace(alert=helpers.safe_alert, confirm=helpers.safe_confirm))
    answers = iter(["2"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert helpers.safe_confirm("Pick one", "Choose", ("A", "B")) == "B"
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError))
    assert helpers.safe_alert("Resume missing", "Missing Resume", "OK") == "OK"
    assert helpers.safe_confirm("Pick one", "Choose", ("A", "B")) == "A"
    out = capsys.readouterr().out
    assert "[Missing Resume]" in out and "1. A" in out
