"""Import the legacy `config/*.py` settings and CSV history into the DB.

    python -m app.seed --source /legacy [--env-file /legacy-env/.env] [--write-env]

Config files are parsed with `ast`, never imported. Secrets from `config/secrets.py`
are never stored in the DB: they are only reported (by name) as missing from `.env`,
and appended there with `--write-env`. Re-running is idempotent.
"""

from __future__ import annotations

import argparse
import ast
import csv
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import AppliedJob, FailedJob, HrEmail, Setting
from app.settings_schema import FIELDS, SECRET_ENV, SettingsError, validate

csv.field_size_limit(10_000_000)

# config file -> settings section
CONFIG_FILES = {
    "personals.py": "personals",
    "questions.py": "questions",
    "search.py": "search",
    "settings.py": "settings",
    "secrets.py": "ai",
}

# Desktop-only values not carried over: safe_mode=True meant "guest Chrome profile", which in
# the container would throw away the saved LinkedIn login on every run.
DESKTOP_ONLY = {("settings", "safe_mode")}

APPLIED_CSV = "all excels/all_applied_applications_history.csv"
FAILED_CSV = "all excels/all_failed_applications_history.csv"
EMAILS_CSV = "all excels/email_apply_jobs.csv"
RESUME = "all resumes/default/resume.pdf"

APPLIED_COLUMNS = {
    "Job ID": "job_id", "Title": "title", "Company": "company", "Work Location": "work_location",
    "Work Style": "work_style", "About Job": "about_job", "Experience required": "experience_required",
    "Skills required": "skills", "HR Name": "hr_name", "HR Link": "hr_link", "Resume": "resume",
    "Re-posted": "reposted", "Date Posted": "date_posted", "Date Applied": "date_applied",
    "Job Link": "job_link", "External Job link": "external_job_link",
    "Questions Found": "questions_found", "Connect Request": "connect_request",
}
FAILED_COLUMNS = {
    "Job ID": "job_id", "Job Link": "job_link", "Resume Tried": "resume_tried",
    "Date listed": "date_listed", "Date Tried": "date_tried", "Assumed Reason": "assumed_reason",
    "Stack Trace": "stack_trace", "External Job link": "external_job_link",
    "Screenshot Name": "screenshot_name",
}
DATE_FIELDS = {"date_posted", "date_applied", "date_listed", "date_tried"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass(frozen=True)
class SeedReport:
    applied: int = 0
    failed: int = 0
    emails: int = 0
    skipped_rows: int = 0


def parse_config_file(path: Path) -> dict[str, Any]:
    """Top-level `name = <literal>` assignments. Anything that isn't a literal is skipped."""
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    values: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            target, value = node.target.id, node.value
        else:
            continue
        try:
            values[target] = ast.literal_eval(value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            continue
    return values


def seed_settings(session: Session, source: Path, overwrite: bool = False) -> dict[str, int]:
    """Imports known settings from `source/config/*.py`. Returns the count saved per section.

    Values already in the DB (edited in the UI or seeded before) are kept unless `overwrite`.
    """
    saved: dict[str, int] = {}
    for file_name, section in CONFIG_FILES.items():
        path = source / "config" / file_name
        if not path.is_file():
            continue
        parsed = parse_config_file(path)
        clean: dict[str, Any] = {}
        for key, value in parsed.items():
            if (section, key) not in FIELDS or (section, key) in DESKTOP_ONLY:
                continue  # removed, unknown, secret or desktop-only
            if isinstance(value, tuple):
                value = list(value)
            try:
                clean.update(validate(section, {key: value}))
            except SettingsError as e:
                print(f"  skipped {section}.{key}: {e.field_errors[key]}")
        row = session.get(Setting, section)
        if row is None:
            row = Setting(section=section, values={})
            session.add(row)
        if not overwrite:
            clean = {k: v for k, v in clean.items() if k not in row.values}
        merged = {**row.values, **clean}
        row.values = {k: v for k, v in merged.items() if (section, k) not in DESKTOP_ONLY}
        saved[section] = len(clean)
    session.commit()
    return saved


def _read_csv(path: Path, columns: dict[str, str]) -> tuple[list[dict[str, Any]], int]:
    """Rows mapped to model fields, plus the number of rows skipped as malformed."""
    if not path.is_file():
        return [], 0
    rows, skipped = [], 0
    with open(path, encoding="utf-8", errors="replace", newline="") as file:
        for raw in csv.DictReader(file):
            if None in raw or any(raw.get(col) is None for col in columns) or not (raw.get("Job ID") or "").strip():
                skipped += 1
                continue
            row = {field: raw[col] for col, field in columns.items()}
            row["job_id"] = row["job_id"].strip()
            for field in DATE_FIELDS & row.keys():
                row[field] = _parse_date(row[field])
            rows.append(row)
    return rows, skipped


def _parse_date(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((value or "").strip())
    except ValueError:
        return None


def seed_history(session: Session, source: Path) -> SeedReport:
    applied_rows, skipped_applied = _read_csv(source / APPLIED_CSV, APPLIED_COLUMNS)
    # Last row wins for a repeated Job ID (same as the upsert).
    by_id = {row["job_id"]: row for row in applied_rows}
    for row in by_id.values():
        stmt = insert(AppliedJob).values(**row)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[AppliedJob.job_id],
                set_={k: stmt.excluded[k] for k in row if k != "job_id"},
            )
        )

    failed_rows, skipped_failed = _read_csv(source / FAILED_CSV, FAILED_COLUMNS)
    fields = list(FAILED_COLUMNS.values())
    existing = {
        tuple(getattr(r, f) for f in fields) for r in session.scalars(select(FailedJob))
    }
    failed_seen = set()
    for row in failed_rows:
        key = tuple(row[f] for f in fields)
        failed_seen.add(key)
        if key not in existing:
            existing.add(key)
            session.add(FailedJob(**row))

    email_count, skipped_emails = 0, 0
    path = source / EMAILS_CSV
    if path.is_file():
        with open(path, encoding="utf-8", errors="replace", newline="") as file:
            for raw in csv.DictReader(file):
                addresses = EMAIL_RE.findall(raw.get("Apply Email") or "")
                job_id = (raw.get("Job ID") or "").strip()
                if None in raw or not job_id or not addresses:
                    skipped_emails += 1
                    continue
                found = _parse_date(raw.get("Date Found"))
                for address in dict.fromkeys(a.lower() for a in addresses):
                    values = {
                        "email": address, "job_id": job_id, "title": raw.get("Title"),
                        "company": raw.get("Company"), "job_link": raw.get("Job Link"),
                        "email_subject": raw.get("Email Subject"), "status": "new",
                    }
                    if found:
                        values["found_at"] = found.astimezone()
                    session.execute(insert(HrEmail).values(**values).on_conflict_do_nothing())
                    email_count += 1
    session.commit()
    return SeedReport(
        applied=len(by_id),
        failed=len(failed_seen),
        emails=email_count,
        skipped_rows=skipped_applied + skipped_failed + skipped_emails,
    )


def copy_resume(source: Path, data_dir: Path) -> bool:
    """Copies the legacy default resume unless one is already on the data volume."""
    src = source / RESUME
    dest = data_dir / "resumes" / "default" / "resume.pdf"
    if not src.is_file() or (dest.parent.is_dir() and any(p.is_file() for p in dest.parent.iterdir())):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return True


def _read_env(env_file: Path) -> list[str]:
    return env_file.read_text(encoding="utf-8").splitlines() if env_file.is_file() else []


def _env_value(lines: list[str], key: str) -> str | None:
    for line in lines:
        name, sep, value = line.partition("=")
        if sep and name.strip() == key:
            return value.strip().strip("'\"")
    return None


def _quote(value: str) -> str:
    """Quotes for docker compose env_file: single quotes are literal; else escape for double."""
    if "'" not in value and "\n" not in value:
        return f"'{value}'"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$").replace("\n", "\\n")
    return f'"{escaped}"'


def secrets_to_env(source: Path, env_file: Path, write: bool) -> list[str]:
    """Env var names that `config/secrets.py` has a value for but `.env` lacks.

    With `write`, fills them into `.env` (replacing an empty `KEY=` line or appending).
    Never prints or returns values.
    """
    path = source / "config" / "secrets.py"
    if not path.is_file():
        return []
    parsed = parse_config_file(path)
    lines = _read_env(env_file)
    missing: list[str] = []
    for name, env_var in SECRET_ENV.items():
        value = parsed.get(name)
        if not isinstance(value, str) or not value.strip():
            continue
        if value in ("username@example.com", "example_password"):
            continue  # upstream placeholders
        if _env_value(lines, env_var):
            continue
        missing.append(env_var)
        if write:
            new_line = f"{env_var}={_quote(value)}"
            for i, line in enumerate(lines):
                if line.partition("=")[0].strip() == env_var:
                    lines[i] = new_line
                    break
            else:
                lines.append(new_line)
    if write and missing:
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True, help="Folder with config/ and all excels/")
    parser.add_argument("--env-file", type=Path, help=".env to check for missing secrets")
    parser.add_argument("--write-env", action="store_true", help="Append missing secrets to --env-file")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace settings already in the app with config/*.py values"
    )
    args = parser.parse_args(argv)

    from app.config import get_env
    from app.db import session_factory

    data_dir = args.data_dir or Path(get_env().data_dir)
    with session_factory()() as session:
        print("Settings:" + ("" if args.overwrite else " (values already in the app are kept; --overwrite replaces them)"))
        for section, count in seed_settings(session, args.source, overwrite=args.overwrite).items():
            print(f"  {section}: {count} values imported")
        report = seed_history(session, args.source)
        print(
            f"History: {report.applied} applied, {report.failed} failed, "
            f"{report.emails} HR emails, {report.skipped_rows} bad rows skipped"
        )
    print("Resume:", "copied" if copy_resume(args.source, data_dir) else "not copied (missing, or already uploaded)")
    if args.env_file:
        missing = secrets_to_env(args.source, args.env_file, args.write_env)
        if not missing:
            print("Secrets: .env already has every secret found in config/secrets.py")
        elif args.write_env:
            print("Secrets: added to .env:", ", ".join(missing), "(restart with `make up`)")
        else:
            print("Secrets missing from .env:", ", ".join(missing), "(re-run with --write-env to add them)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
