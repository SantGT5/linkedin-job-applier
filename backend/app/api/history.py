from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.common import PageParams, paginate, row_dict
from app.api.filters import date_range
from app.db import get_session
from app.models import AppliedJob, FailedJob

router = APIRouter(prefix="/api/history", tags=["history"])

APPLIED_HEAVY = ("about_job", "questions_found")
FAILED_HEAVY = ("stack_trace",)


@router.get("/applied")
def list_applied(
    q: str | None = None,
    company: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PageParams = Depends(),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(AppliedJob).order_by(AppliedJob.date_applied.desc().nulls_last(), AppliedJob.job_id.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(AppliedJob.title.ilike(like), AppliedJob.company.ilike(like), AppliedJob.job_id.ilike(like)))
    if company:
        stmt = stmt.where(AppliedJob.company.ilike(f"%{company}%"))
    stmt = date_range(stmt, AppliedJob.date_applied, date_from, date_to)
    return paginate(session, stmt, params, lambda row: row_dict(row, APPLIED_HEAVY))


@router.get("/applied/{job_id}")
def get_applied(job_id: str, session: Session = Depends(get_session)) -> dict:
    row = session.get(AppliedJob, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return row_dict(row)


@router.get("/failed")
def list_failed(
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PageParams = Depends(),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(FailedJob).order_by(FailedJob.date_tried.desc().nulls_last(), FailedJob.id.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(FailedJob.job_id.ilike(like), FailedJob.assumed_reason.ilike(like), FailedJob.job_link.ilike(like)))
    stmt = date_range(stmt, FailedJob.date_tried, date_from, date_to)
    return paginate(session, stmt, params, lambda row: row_dict(row, FAILED_HEAVY))


@router.get("/failed/{failed_id}")
def get_failed(failed_id: int, session: Session = Depends(get_session)) -> dict:
    row = session.get(FailedJob, failed_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return row_dict(row)
