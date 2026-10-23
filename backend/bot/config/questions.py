import os

from config._loader import data_dir, load

globals().update(load("questions"))


def _resume_path() -> str:
    """The resume uploaded in Settings (any name), on the data volume."""
    folder = f"{data_dir()}/resumes/default"
    try:
        files = sorted(f for f in os.listdir(folder) if not f.startswith(".") and os.path.isfile(f"{folder}/{f}"))
    except OSError:
        files = []
    return f"{folder}/{files[0] if files else 'resume.pdf'}"


default_resume_path = _resume_path()
