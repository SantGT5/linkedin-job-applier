import csv
import io
from collections.abc import Iterator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AppliedJob, FailedJob, HrEmail
from app.seed import APPLIED_COLUMNS, FAILED_COLUMNS

router = APIRouter(prefix="/api/export", tags=["export"])

# Same headers as the bot's old CSV files, so the spreadsheet workflow keeps working.
EMAIL_COLUMNS = {
    "Job ID": "job_id", "Title": "title", "Company": "company", "Apply Email": "email",
    "Email Subject": "email_subject", "Job Link": "job_link", "Date Found": "found_at",
    "Status": "status", "Emailed At": "emailed_at",
}
EXPORTS = {
    "applied": (AppliedJob, APPLIED_COLUMNS, AppliedJob.date_applied),
    "failed": (FailedJob, FAILED_COLUMNS, FailedJob.date_tried),
    "emails": (HrEmail, EMAIL_COLUMNS, HrEmail.found_at),
}


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    return str(value)


@router.get("/{name}.csv")
def export_csv(name: str, session: Session = Depends(get_session)) -> StreamingResponse:
    if name not in EXPORTS:
        raise HTTPException(status_code=404, detail="Unknown export")
    model, columns, order = EXPORTS[name]
    rows = session.scalars(select(model).order_by(order.desc().nulls_last())).all()

    def lines() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns.keys())
        for row in rows:
            writer.writerow(_cell(getattr(row, field)) for field in columns.values())
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()
        yield buffer.getvalue()

    stamp = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        lines(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}-{stamp}.csv"'},
    )
