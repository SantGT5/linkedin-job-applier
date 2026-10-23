"""The bot's link to the app database (set up by the worker through env vars).

Replaces the desktop popups and CSV files: pauses become prompts the UI answers, history
goes to postgres. Without `APPLIER_DATABASE_URL` (tests, local runs) it is disabled:
`ask` falls back to the terminal and the save functions do nothing.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any

POLL_SECONDS = 1.0
STOPPED = "__stopped__"

APPLIED_FIELDS = (
    "job_id", "title", "company", "work_location", "work_style", "about_job",
    "experience_required", "skills", "hr_name", "hr_link", "resume", "reposted",
    "date_posted", "date_applied", "job_link", "external_job_link", "questions_found",
    "connect_request",
)
FAILED_FIELDS = (
    "job_id", "job_link", "resume_tried", "date_listed", "date_tried", "assumed_reason",
    "stack_trace", "external_job_link", "screenshot_name",
)
DATE_FIELDS = {"date_posted", "date_applied", "date_listed", "date_tried"}


def enabled() -> bool:
    return bool(os.environ.get("APPLIER_DATABASE_URL"))


def _run_id() -> int | None:
    value = os.environ.get("APPLIER_RUN_ID", "")
    return int(value) if value.isdigit() else None


def _connect():
    import psycopg

    url = os.environ["APPLIER_DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(url, autocommit=True)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


def _date(value: Any):
    """datetime from a datetime or ISO string; None for 'Unknown', 'Pending' and the like."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).strip())
    except ValueError:
        return None


def _clean(row: dict, fields: tuple[str, ...]) -> dict:
    return {
        k: (_date(row[k]) if k in DATE_FIELDS else _text(row[k]))
        for k in fields
        if k in row
    }


def ask(title: str, text: str, buttons: list[str]) -> str:
    """Pauses the bot until the owner answers in the UI. Returns the chosen button.

    Raises SystemExit(0) when the run is stopped while waiting.
    """
    if not enabled():
        from modules.helpers import safe_confirm

        return safe_confirm(text, title, buttons) or buttons[0]
    run_id = _run_id()
    print(f"[Waiting for you] {title}: {text}", flush=True)
    with _connect() as conn:
        prompt_id = conn.execute(
            "INSERT INTO prompts (run_id, title, text, buttons) VALUES (%s, %s, %s, %s) RETURNING id",
            (run_id, title, text, json.dumps(list(buttons))),
        ).fetchone()[0]
        conn.execute("UPDATE runs SET status = 'waiting' WHERE id = %s AND status = 'running'", (run_id,))
        while True:
            answer = conn.execute("SELECT answer FROM prompts WHERE id = %s", (prompt_id,)).fetchone()[0]
            if answer is not None:
                break
            time.sleep(POLL_SECONDS)
        if answer == STOPPED:
            print("Run stopped while waiting for you.", flush=True)
            raise SystemExit(0)
        conn.execute("UPDATE runs SET status = 'running' WHERE id = %s AND status = 'waiting'", (run_id,))
    print(f"[You answered] {answer}", flush=True)
    return answer


def record_session(state: str) -> None:
    if not enabled():
        return
    with _connect() as conn:
        conn.execute("UPDATE linkedin_session SET state = %s, checked_at = now() WHERE id = 1", (state,))


def record_unanswered(label: str, question_type: str, options: list[str] | None, job_id: str | None) -> None:
    if not enabled():
        return
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO unanswered_questions (label, question_type, options, job_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (label, question_type) DO UPDATE SET
                seen_count = unanswered_questions.seen_count + 1,
                last_seen = now(),
                job_id = EXCLUDED.job_id,
                options = EXCLUDED.options
            """,
            (label, question_type, json.dumps(options) if options is not None else None, job_id),
        )


def save_applied(row: dict) -> None:
    if not enabled():
        return
    values = _clean(row, APPLIED_FIELDS)
    cols = list(values)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "job_id") or "job_id = EXCLUDED.job_id"
    with _connect() as conn:
        conn.execute(
            f"INSERT INTO applied_jobs ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
            f"ON CONFLICT (job_id) DO UPDATE SET {updates}",
            list(values.values()),
        )


def save_failed(row: dict) -> None:
    if not enabled():
        return
    values = _clean(row, FAILED_FIELDS)
    if values.get("date_tried") is None:
        values["date_tried"] = datetime.now()
    cols = list(values)
    with _connect() as conn:
        conn.execute(
            f"INSERT INTO failed_jobs ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
            list(values.values()),
        )


def save_emails(job: dict, emails: list[str], subject: str) -> int:
    """Saves each new (email, job) pair as status 'new'. Returns how many were new."""
    if not enabled() or not emails:
        return 0
    added = 0
    with _connect() as conn:
        for email in dict.fromkeys(e.strip().lower() for e in emails if e and e.strip()):
            cur = conn.execute(
                """
                INSERT INTO hr_emails (email, job_id, title, company, job_link, email_subject, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'new')
                ON CONFLICT (email, job_id) DO NOTHING
                """,
                (email, _text(job.get("job_id")), _text(job.get("title")), _text(job.get("company")),
                 _text(job.get("job_link")), subject or None),
            )
            added += cur.rowcount
    return added


def applied_job_ids() -> set[str]:
    if not enabled():
        return set()
    with _connect() as conn:
        return {row[0] for row in conn.execute("SELECT job_id FROM applied_jobs")}


def bump_counts(applied: int = 0, failed: int = 0, skipped: int = 0) -> None:
    run_id = _run_id()
    if not enabled() or run_id is None:
        return
    with _connect() as conn:
        conn.execute(
            "UPDATE runs SET applied_count = applied_count + %s, failed_count = failed_count + %s, "
            "skipped_count = skipped_count + %s WHERE id = %s",
            (applied, failed, skipped, run_id),
        )
