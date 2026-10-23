import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

router = APIRouter(prefix="/api/resume", tags=["resume"])

MAX_BYTES = 2 * 1024 * 1024
# Extension -> magic bytes LinkedIn's upload accepts (PDF, legacy Word, Word/zip).
ALLOWED = {".pdf": b"%PDF", ".doc": b"\xd0\xcf\x11\xe0", ".docx": b"PK\x03\x04"}


def resume_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/data")) / "resumes" / "default"


def current_resume() -> Path | None:
    folder = resume_dir()
    files = sorted(p for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []
    return files[0] if files else None


def _safe_name(name: str) -> str:
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = re.sub(r"[^\w .()-]", "_", base)[:120].lstrip(".")
    return base or "resume.pdf"


@router.get("")
def get_resume() -> dict:
    path = current_resume()
    if path is None:
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "filename": path.name,
        "size": stat.st_size,
        "uploaded_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
    }


@router.post("")
async def upload_resume(file: UploadFile) -> dict:
    """The resume the bot uploads to Easy Apply (PDF, DOC or DOCX, at most 2 MB)."""
    name = _safe_name(file.filename or "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=422, detail="Upload a PDF, DOC or DOCX file.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 2 MB.")
    if not data.startswith(ALLOWED[ext]):
        raise HTTPException(status_code=422, detail=f"This doesn't look like a {ext[1:].upper()} file.")
    folder = resume_dir()
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / f".upload-{os.getpid()}"
    tmp.write_bytes(data)
    for old in folder.iterdir():
        if old.is_file() and old != tmp:
            old.unlink()
    tmp.rename(folder / name)
    return get_resume()
