from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

RUN_STATUSES = ("queued", "running", "waiting", "stopping", "finished", "failed", "stopped")
ACTIVE_RUN_STATUSES = ("queued", "running", "waiting", "stopping")
EMAIL_STATUSES = ("new", "emailed")
SESSION_STATES = ("logged_in", "logged_out", "unknown")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, list[Any]: JSONB}


class Setting(Base):
    __tablename__ = "settings"
    section: Mapped[str] = mapped_column(String(32), primary_key=True)
    values: Mapped[dict[str, Any]] = mapped_column(default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (CheckConstraint(_in("status", RUN_STATUSES), name="runs_status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    applied_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class RunLog(Base):
    __tablename__ = "run_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    line: Mapped[str] = mapped_column(Text)


class BotControl(Base):
    __tablename__ = "bot_control"
    __table_args__ = (CheckConstraint("desired IN ('running', 'stopped')", name="bot_control_desired"),)
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    desired: Mapped[str] = mapped_column(String(16), default="stopped")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    buttons: Mapped[list[Any]] = mapped_column(default=list)
    answer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppliedJob(Base):
    __tablename__ = "applied_jobs"
    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text, index=True)
    work_location: Mapped[str | None] = mapped_column(Text)
    work_style: Mapped[str | None] = mapped_column(Text)
    about_job: Mapped[str | None] = mapped_column(Text)
    experience_required: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[str | None] = mapped_column(Text)
    hr_name: Mapped[str | None] = mapped_column(Text)
    hr_link: Mapped[str | None] = mapped_column(Text)
    resume: Mapped[str | None] = mapped_column(Text)
    reposted: Mapped[str | None] = mapped_column(Text)
    date_posted: Mapped[datetime | None] = mapped_column(DateTime)
    date_applied: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    job_link: Mapped[str | None] = mapped_column(Text)
    external_job_link: Mapped[str | None] = mapped_column(Text)
    questions_found: Mapped[str | None] = mapped_column(Text)
    connect_request: Mapped[str | None] = mapped_column(Text)


class FailedJob(Base):
    __tablename__ = "failed_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    job_link: Mapped[str | None] = mapped_column(Text)
    resume_tried: Mapped[str | None] = mapped_column(Text)
    date_listed: Mapped[datetime | None] = mapped_column(DateTime)
    date_tried: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    assumed_reason: Mapped[str | None] = mapped_column(Text)
    stack_trace: Mapped[str | None] = mapped_column(Text)
    external_job_link: Mapped[str | None] = mapped_column(Text)
    screenshot_name: Mapped[str | None] = mapped_column(Text)


class HrEmail(Base):
    __tablename__ = "hr_emails"
    __table_args__ = (
        UniqueConstraint("email", "job_id", name="hr_emails_email_job"),
        CheckConstraint(_in("status", EMAIL_STATUSES), name="hr_emails_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    job_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text, index=True)
    job_link: Mapped[str | None] = mapped_column(Text)
    email_subject: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="new", server_default="new", index=True)
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"
    __table_args__ = (UniqueConstraint("label", "question_type", name="unanswered_label_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(32))
    options: Mapped[list[Any] | None] = mapped_column(JSONB)
    job_id: Mapped[str | None] = mapped_column(String(64))
    seen_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LinkedinSession(Base):
    __tablename__ = "linkedin_session"
    __table_args__ = (CheckConstraint(_in("state", SESSION_STATES), name="linkedin_session_state"),)
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    state: Mapped[str] = mapped_column(String(16), default="unknown")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
