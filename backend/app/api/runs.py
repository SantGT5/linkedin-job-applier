import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import PageParams, paginate, row_dict
from app.db import get_session, session_factory
from app.models import ACTIVE_RUN_STATUSES, Run, RunLog

router = APIRouter(prefix="/api/runs", tags=["runs"])

STREAM_POLL_SECONDS = 0.5
KEEPALIVE_SECONDS = 15


def _log_dict(log: RunLog) -> dict:
    return {"id": log.id, "ts": log.ts, "line": log.line}


def _logs_after(session: Session, run_id: int, after_id: int, limit: int) -> list[RunLog]:
    return list(
        session.scalars(
            select(RunLog)
            .where(RunLog.run_id == run_id, RunLog.id > after_id)
            .order_by(RunLog.id)
            .limit(limit)
        )
    )


@router.get("")
def list_runs(params: PageParams = Depends(), session: Session = Depends(get_session)) -> dict:
    return paginate(session, select(Run).order_by(Run.id.desc()), params, row_dict)


@router.get("/{run_id}/logs")
def get_logs(
    run_id: int,
    after_id: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    session: Session = Depends(get_session),
) -> dict:
    if session.get(Run, run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"items": [_log_dict(log) for log in _logs_after(session, run_id, after_id, limit)]}


def _sse_data(line: str) -> str:
    # Each line of a multi-line message needs its own `data:` prefix.
    return "".join(f"data: {part}\n" for part in line.split("\n"))


@router.get("/{run_id}/logs/stream")
async def stream_logs(
    run_id: int,
    request: Request,
    after_id: int = Query(0, ge=0),
    last_event_id: str | None = Header(None),
) -> StreamingResponse:
    """Server-sent events of a run's log lines; ends with `event: end` once the run is over."""
    cursor = int(last_event_id) if last_event_id and last_event_id.isdigit() else after_id
    with session_factory()() as session:
        if session.get(Run, run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")

    async def events():
        nonlocal cursor
        idle = 0.0
        while True:
            if await request.is_disconnected():
                return
            with session_factory()() as session:
                logs = _logs_after(session, run_id, cursor, 500)
                run = session.get(Run, run_id)
                finished = run is None or run.status not in ACTIVE_RUN_STATUSES
            for log in logs:
                cursor = log.id
                yield f"id: {log.id}\n{_sse_data(log.line)}\n"
            if logs:
                idle = 0.0
                continue
            if finished:
                yield "event: end\ndata: \n\n"
                return
            await asyncio.sleep(STREAM_POLL_SECONDS)
            idle += STREAM_POLL_SECONDS
            if idle >= KEEPALIVE_SECONDS:
                idle = 0.0
                yield ": keepalive\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
