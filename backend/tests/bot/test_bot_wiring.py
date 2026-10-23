import importlib
import json
import re
import sys
from pathlib import Path

import pytest

BOT = Path(__file__).resolve().parents[2] / "bot"


def _fresh(name: str):
    for mod in [m for m in sys.modules if m in (name, "modules.validator") or m == "config" or m.startswith("config.")]:
        del sys.modules[mod]
    return importlib.import_module(name)


@pytest.mark.parametrize(
    "module",
    [
        "modules.ai.openaiConnections",
        "modules.ai.deepseekConnections",
        "modules.ai.geminiConnections",
        "modules.resumes.generator",
    ],
)
def test_removed_modules_gone(module):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)


def test_applied_ids_come_from_bridge(monkeypatch):
    from modules import bridge, history

    monkeypatch.setattr(bridge, "applied_job_ids", lambda: {"1", "2"})
    assert history.get_applied_job_ids() == {"1", "2"}


def test_failed_job_saves_through_bridge(monkeypatch):
    from modules import bridge, history

    saved, bumps = [], []
    monkeypatch.setattr(bridge, "save_failed", saved.append)
    monkeypatch.setattr(bridge, "bump_counts", lambda **kw: bumps.append(kw))
    history.failed_job("9", "https://l/9", "Pending", "Unknown", "Bad word", ValueError("C#"), "Skipped", "Not Available")
    assert saved[0]["job_id"] == "9"
    assert saved[0]["assumed_reason"] == "Bad word"
    assert saved[0]["stack_trace"] == "C#"
    assert saved[0]["external_job_link"] == "Skipped"
    assert saved[0]["date_tried"] is not None
    assert bumps == []  # counting is the caller's call: skips and failures differ


def test_submitted_jobs_saves_through_bridge(monkeypatch):
    from modules import bridge, history

    saved = []
    monkeypatch.setattr(bridge, "save_applied", saved.append)
    history.submitted_jobs(
        "7", "Dev", "Acme", "Remote", "Remote", "desc", 3, ["py"], "Ann", "https://hr", "Previous resume",
        False, "Unknown", "2026-10-22 10:00:00", "https://l/7", "Easy Applied", {("Q", "A", "text", "")}, "In Development",
    )
    row = saved[0]
    assert row["job_id"] == "7" and row["title"] == "Dev" and row["about_job"] == "desc"
    assert row["skills"] == "['py']" and row["reposted"] == "False"
    assert row["questions_found"].startswith("{(")


def test_validator_accepts_defaults(tmp_path, monkeypatch):
    # Defaults have no PII, so fill the three fields the bot can't apply without.
    from app.settings_schema import defaults

    values = defaults()
    values["personals"].update(first_name="Ada", last_name="Lovelace", phone_number="0612345678")
    snapshot = tmp_path / "run.json"
    snapshot.write_text(json.dumps(values))
    monkeypatch.setenv("APPLIER_CONFIG_FILE", str(snapshot))
    validator = _fresh("modules.validator")
    assert validator.validate_config() is True


def test_validator_names_the_bad_setting(tmp_path, monkeypatch):
    snapshot = tmp_path / "run.json"
    snapshot.write_text(json.dumps({"personals": {"first_name": "", "last_name": "L", "phone_number": "0612345678"}}))
    monkeypatch.setenv("APPLIER_CONFIG_FILE", str(snapshot))
    validator = _fresh("modules.validator")
    with pytest.raises(ValueError, match="first_name"):
        validator.validate_config()


def test_validator_requires_ai_key_only_when_ai_on(tmp_path, monkeypatch):
    from app.settings_schema import defaults

    values = defaults()
    values["personals"].update(first_name="Ada", last_name="Lovelace", phone_number="0612345678")
    values["ai"].update(use_AI=True, ai_provider="claude")
    snapshot = tmp_path / "run.json"
    snapshot.write_text(json.dumps(values))
    monkeypatch.setenv("APPLIER_CONFIG_FILE", str(snapshot))
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CLAUDE_API_KEY"):
        _fresh("modules.validator").validate_config()


def test_no_direct_pyautogui_dialogs():
    # `from pyautogui import confirm` grabs the real desktop popup, which nobody sees under Xvfb.
    offenders = [
        str(path.relative_to(BOT))
        for path in BOT.rglob("*.py")
        if re.search(r"from pyautogui import .*\b(alert|confirm)\b", path.read_text(encoding="utf-8"))
        and path.name != "helpers.py"
    ]
    assert offenders == []


def test_no_sponsor_popup_or_screen_awake():
    source = (BOT / "runAiBot.py").read_text(encoding="utf-8")
    assert 'pyautogui.alert(\n        "Please consider sponsoring' not in source
    assert "Please consider sponsoring" not in source
    assert "keep_screen_awake" not in source
    assert "use_resume_generator" not in source and "chatGPT" not in source


def test_bot_has_no_csv_history():
    source = (BOT / "runAiBot.py").read_text(encoding="utf-8")
    assert "csv.DictWriter" not in source and "email_apply_job" not in source
    assert "ai_log_email_apply" not in source


def test_bot_compiles():
    compile((BOT / "runAiBot.py").read_text(encoding="utf-8"), "runAiBot.py", "exec")


def test_container_chrome_kwargs(tmp_path, monkeypatch):
    from modules import helpers

    driver = tmp_path / "chromedriver"
    driver.write_bytes(b"driver")
    monkeypatch.setattr(helpers, "chrome_major_version", lambda binary: 141)
    env = {"CHROME_BINARY": "/usr/bin/chromium", "CHROMEDRIVER": str(driver), "CHROME_PROFILE_DIR": str(tmp_path / "profile")}
    kwargs = helpers.container_chrome_kwargs(env, work_dir=tmp_path / "work")
    assert kwargs["browser_executable_path"] == "/usr/bin/chromium"
    assert kwargs["version_main"] == 141
    assert kwargs["user_data_dir"] == str(tmp_path / "profile")
    # undetected-chromedriver patches the driver in place, so it gets a writable copy.
    copied = Path(kwargs["driver_executable_path"])
    assert copied != driver and copied.read_bytes() == b"driver"
    assert helpers.container_chrome_kwargs({}, work_dir=tmp_path) == {}


def test_clear_profile_locks(tmp_path):
    from modules import helpers

    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        (tmp_path / name).symlink_to("/nonexistent")
    (tmp_path / "Default").mkdir()
    helpers.clear_profile_locks(str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Default"]


def test_easy_apply_failure_reason():
    # Kestrel E2E (ii): a job the owner discarded was logged as "Problem in Easy Applying".
    from modules.history import easy_apply_failure_reason

    assert easy_apply_failure_reason(Exception("Job application discarded by user!")) == "Discarded by user"
    assert easy_apply_failure_reason(ValueError("boom")) == "Problem in Easy Applying"
