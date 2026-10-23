from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.common import PageParams, paginate, row_dict
from app.api.filters import date_range
from app.api.settings import load_all
from app.compose_email import compose
from app.db import get_session
from app.models import HrEmail

router = APIRouter(prefix="/api/emails", tags=["emails"])

SAMPLE_JOB = {
    "email": "hr@example.com",
    "title": "Senior Full Stack Software Engineer",
    "job_link": "https://www.linkedin.com/jobs/view/1234567890",
}


class Preview(BaseModel):
    subject_template: str
    body_template: str
    my_name: str
    phone_number: str = ""
    linkedin_profile: str = ""


@router.get("")
def list_emails(
    status: Literal["new", "emailed"] | None = None,
    company: str | None = None,
    role: str | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PageParams = Depends(),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(HrEmail).order_by(HrEmail.found_at.desc(), HrEmail.id.desc())
    if status:
        stmt = stmt.where(HrEmail.status == status)
    if company:
        stmt = stmt.where(HrEmail.company.ilike(f"%{company}%"))
    if role:
        stmt = stmt.where(HrEmail.title.ilike(f"%{role}%"))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(HrEmail.email.ilike(like), HrEmail.title.ilike(like), HrEmail.company.ilike(like)))
    stmt = date_range(stmt, HrEmail.found_at, date_from, date_to)
    return paginate(session, stmt, params, row_dict)


def _get(session: Session, email_id: int) -> HrEmail:
    row = session.get(HrEmail, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return row


@router.get("/{email_id}/compose")
def compose_email(email_id: int, session: Session = Depends(get_session)) -> dict:
    row = _get(session, email_id)
    return compose(row_dict(row), load_all(session)["email"]).to_dict()


@router.post("/{email_id}/mark-emailed")
def mark_emailed(email_id: int, session: Session = Depends(get_session)) -> dict:
    row = _get(session, email_id)
    row.status, row.emailed_at = "emailed", datetime.now(timezone.utc)
    session.commit()
    return row_dict(row)


@router.post("/{email_id}/mark-new")
def mark_new(email_id: int, session: Session = Depends(get_session)) -> dict:
    row = _get(session, email_id)
    row.status, row.emailed_at = "new", None
    session.commit()
    return row_dict(row)


@router.post("/preview")
def preview(body: Preview) -> dict:
    """Live preview for Settings → Email, on a sample job."""
    return compose(SAMPLE_JOB, body.model_dump()).to_dict()
