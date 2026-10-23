import shutil
from pathlib import Path

from sqlalchemy import func, select

from app.api.settings import load_all
from app.models import AppliedJob, FailedJob, HrEmail, Setting
from app.seed import copy_resume, parse_config_file, secrets_to_env, seed_history, seed_settings

LEGACY = Path(__file__).parent / "fixtures" / "legacy"


def _counts(db) -> tuple[int, int, int, int]:
    return tuple(
        db.scalar(select(func.count()).select_from(model))
        for model in (AppliedJob, FailedJob, HrEmail, Setting)
    )


def test_parse_config_file_literals():
    values = parse_config_file(LEGACY / "config" / "questions.py")
    assert values["desired_salary"] == 120000
    assert values["linkedin_summary"] == "\nLine one.\nLine two.\n"
    search = parse_config_file(LEGACY / "config" / "search.py")
    assert search["search_terms"] == ["Software Engineer", "Backend Engineer"]
    assert search["experience_level"] == []
    assert "computed" not in search


def test_seed_settings_maps_sections(db):
    counts = seed_settings(db, LEGACY)
    values = load_all(db)
    assert values["ai"]["ai_provider"] == "glm"
    assert values["ai"]["use_AI"] is True
    assert values["settings"]["click_gap"] == 2
    assert values["personals"]["first_name"] == "Testy"
    assert values["questions"]["desired_salary"] == 120000
    stored = {row.section: row.values for row in db.scalars(select(Setting))}
    flat = {k for section in stored.values() for k in section}
    # Removed, unknown and secret names are dropped.
    assert not flat & {"llm_model", "keep_screen_awake", "file_name", "ai_log_email_apply",
                       "default_resume_path", "username", "password", "glm_api_key", "computed"}
    assert counts["search"] == 3


def test_seed_is_idempotent(db):
    seed_settings(db, LEGACY)
    first_report = seed_history(db, LEGACY)
    first = _counts(db)
    seed_settings(db, LEGACY)
    second_report = seed_history(db, LEGACY)
    assert _counts(db) == first
    assert first_report == second_report


def test_seed_skips_bad_rows(db):
    report = seed_history(db, LEGACY)
    assert report.skipped_rows == 1
    assert report.applied == 3  # 1001 (dup merged), 1002, 1004
    assert db.scalar(select(func.count()).select_from(AppliedJob)) == 3
    assert db.get(AppliedJob, "1001").title == "Backend Engineer (dup)"
    assert "Caf" in db.get(AppliedJob, "1004").title
    assert db.scalar(select(func.count()).select_from(FailedJob)) == 2
    bad_date = db.scalar(select(FailedJob).where(FailedJob.job_id == "2002"))
    assert bad_date.date_listed is None
    email = db.scalar(select(HrEmail))
    assert (email.email, email.job_id, email.status) == ("jobs@acme.com", "1002", "new")


def test_seed_history_without_csvs(db, tmp_path):
    report = seed_history(db, tmp_path)
    assert (report.applied, report.failed, report.emails, report.skipped_rows) == (0, 0, 0, 0)


def test_copy_resume(tmp_path):
    assert copy_resume(LEGACY, tmp_path) is True
    target = tmp_path / "resumes" / "default" / "resume.pdf"
    assert target.read_bytes().startswith(b"%PDF")
    # An uploaded resume is never overwritten.
    target.write_bytes(b"%PDF uploaded")
    assert copy_resume(LEGACY, tmp_path) is False
    assert target.read_bytes() == b"%PDF uploaded"
    assert copy_resume(tmp_path / "nothing", tmp_path / "x") is False


def test_secrets_to_env_writes_missing_only(tmp_path, capsys):
    env = tmp_path / ".env"
    env.write_text("UI_PASSWORD=pw\nGLM_API_KEY=existing-glm\nLINKEDIN_USERNAME=\n")
    missing = secrets_to_env(LEGACY, env, write=False)
    assert missing == ["LINKEDIN_USERNAME", "LINKEDIN_PASSWORD"]
    assert env.read_text() == "UI_PASSWORD=pw\nGLM_API_KEY=existing-glm\nLINKEDIN_USERNAME=\n"

    assert secrets_to_env(LEGACY, env, write=True) == missing
    text = env.read_text()
    assert "GLM_API_KEY=existing-glm" in text and "fake-glm-key-in-file" not in text
    assert "LINKEDIN_USERNAME='fake-user@example.org'" in text
    assert "LINKEDIN_PASSWORD='fake-password-123'" in text
    assert text.count("LINKEDIN_USERNAME") == 1
    # Nothing left to add; values never printed.
    assert secrets_to_env(LEGACY, env, write=True) == []
    out = capsys.readouterr().out
    assert "fake-password-123" not in out and "fake-user" not in out


def test_secrets_to_env_quotes_special_chars(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(LEGACY / "config", src / "config")
    (src / "config" / "secrets.py").write_text('password = "it\'s $ecret"\n')
    env = tmp_path / ".env"
    env.write_text("")
    secrets_to_env(src, env, write=True)
    assert env.read_text() == 'LINKEDIN_PASSWORD="it\'s $$ecret"\n'


def test_seed_skips_desktop_only_settings(db):
    # safe_mode=True on the desktop meant "guest profile"; in the container that would log you
    # out every run, so the saved profile (default False) is kept.
    seed_settings(db, LEGACY)
    assert load_all(db)["settings"]["safe_mode"] is False
    assert "safe_mode" not in db.get(Setting, "settings").values


def test_copy_resume_keeps_any_uploaded_resume(tmp_path):
    folder = tmp_path / "resumes" / "default"
    folder.mkdir(parents=True)
    (folder / "cv.docx").write_bytes(b"PK\x03\x04")
    assert copy_resume(LEGACY, tmp_path) is False
    assert [p.name for p in folder.iterdir()] == ["cv.docx"]


def test_reseed_keeps_ui_edits(db):
    # Kestrel M2 #3: a second `make seed` turned pause_before_submit back off.
    seed_settings(db, LEGACY)
    row = db.get(Setting, "questions")
    row.values = {**row.values, "pause_before_submit": True, "desired_salary": 99}
    db.commit()
    counts = seed_settings(db, LEGACY)
    values = load_all(db)["questions"]
    assert values["pause_before_submit"] is True and values["desired_salary"] == 99
    assert counts["questions"] == 0  # nothing new to import
    # --overwrite resets them to config/*.py
    seed_settings(db, LEGACY, overwrite=True)
    assert load_all(db)["questions"]["pause_before_submit"] is False
