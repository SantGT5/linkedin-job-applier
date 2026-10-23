import os
from pathlib import Path


def _data_dir() -> Path:
    return Path(os.environ["DATA_DIR"])


def test_resume_upload_and_metadata(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert client.get("/api/resume").json() == {"exists": False}
    r = client.post("/api/resume", files={"file": ("My CV.pdf", b"%PDF-1.4 hello", "application/pdf")})
    assert r.status_code == 200, r.text
    meta = client.get("/api/resume").json()
    assert meta["exists"] and meta["filename"] == "My CV.pdf" and meta["size"] == 14
    files = list((tmp_path / "resumes" / "default").iterdir())
    assert [f.name for f in files] == ["My CV.pdf"]
    # A new upload replaces the old one.
    client.post("/api/resume", files={"file": ("cv.docx", b"PK\x03\x04docx", "application/octet-stream")})
    assert [f.name for f in (tmp_path / "resumes" / "default").iterdir()] == ["cv.docx"]


def test_resume_rejects_bad_files(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert client.post("/api/resume", files={"file": ("cv.txt", b"hello", "text/plain")}).status_code == 422
    assert client.post("/api/resume", files={"file": ("cv.pdf", b"not a pdf", "application/pdf")}).status_code == 422
    big = b"%PDF" + b"0" * (2 * 1024 * 1024)
    assert client.post("/api/resume", files={"file": ("cv.pdf", big, "application/pdf")}).status_code == 413
    assert client.post("/api/resume", files={"file": ("../../evil.pdf", b"%PDF x", "application/pdf")}).status_code == 200
    assert [f.name for f in (tmp_path / "resumes" / "default").iterdir()] == ["evil.pdf"]
