import importlib
import json
import sys


def _fresh(module_name: str):
    for name in [n for n in sys.modules if n == "config" or n.startswith("config.")]:
        del sys.modules[name]
    return importlib.import_module(module_name)


def test_loader_reads_snapshot(tmp_path, monkeypatch):
    snapshot = tmp_path / "run.json"
    snapshot.write_text(json.dumps({"search": {"search_terms": ["X"]}}))
    monkeypatch.setenv("APPLIER_CONFIG_FILE", str(snapshot))
    search = _fresh("config.search")
    assert search.search_terms == ["X"]
    # Keys missing from the snapshot fall back to defaults.
    assert search.easy_apply_only is True
    _fresh("config.search")


def test_loader_defaults_without_snapshot(monkeypatch):
    monkeypatch.delenv("APPLIER_CONFIG_FILE", raising=False)
    from app.settings_schema import defaults

    settings = _fresh("config.settings")
    assert settings.click_gap == defaults()["settings"]["click_gap"]


def test_fixed_paths_come_from_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings = _fresh("config.settings")
    questions = _fresh("config.questions")
    assert settings.logs_folder_path == f"{tmp_path}/logs/"
    assert questions.default_resume_path == f"{tmp_path}/resumes/default/resume.pdf"


def test_secrets_from_env(monkeypatch):
    monkeypatch.setenv("LINKEDIN_PASSWORD", "hunter22")
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    secrets = _fresh("config.secrets")
    assert secrets.password == "hunter22"
    assert secrets.claude_api_key == ""
    assert secrets.ai_provider in ("claude", "glm")


def test_resume_path_is_the_uploaded_file(tmp_path, monkeypatch):
    folder = tmp_path / "resumes" / "default"
    folder.mkdir(parents=True)
    (folder / "My CV.pdf").write_bytes(b"%PDF")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    questions = _fresh("config.questions")
    assert questions.default_resume_path == f"{tmp_path}/resumes/default/My CV.pdf"
