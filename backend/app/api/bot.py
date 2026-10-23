from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.common import row_dict
from app.db import get_session
from app.models import ACTIVE_RUN_STATUSES, BotControl, LinkedinSession, Prompt, Run

router = APIRouter(prefix="/api/bot", tags=["bot"])


class Answer(BaseModel):
    button: str


def active_run(session: Session) -> Run | None:
    return session.scalar(
        select(Run).where(Run.status.in_(ACTIVE_RUN_STATUSES)).order_by(Run.id.desc()).limit(1)
    )


@router.post("/start")
def start(session: Session = Depends(get_session)) -> dict:
    # The bot_control row lock serialises concurrent Start clicks: exactly one run.
    control = session.scalar(select(BotControl).where(BotControl.id == 1).with_for_update())
    control.desired = "running"
    run = active_run(session)
    if run is None:
        run = Run(status="queued")
        session.add(run)
    session.commit()
    return row_dict(run)


@router.post("/stop")
def stop(session: Session = Depends(get_session)) -> dict:
    control = session.scalar(select(BotControl).where(BotControl.id == 1).with_for_update())
    control.desired = "stopped"
    # A run the worker hasn't started has no process to stop: cancel it here.
    session.execute(
        update(Run)
        .where(Run.status == "queued")
        .values(status="stopped", ended_at=datetime.now(timezone.utc))
    )
    session.commit()
    return {"desired": "stopped"}


@router.get("/status")
def status(session: Session = Depends(get_session)) -> dict:
    run = active_run(session)
    prompt = None
    if run is not None:
        prompt = session.scalar(
            select(Prompt)
            .where(Prompt.run_id == run.id, Prompt.answer.is_(None))
            .order_by(Prompt.id.desc())
            .limit(1)
        )
    last = run or session.scalar(select(Run).order_by(Run.id.desc()).limit(1))
    linkedin = session.get(LinkedinSession, 1)
    return {
        "state": run.status if run else "idle",
        "run": row_dict(last) if last else None,
        "prompt": {"id": prompt.id, "title": prompt.title, "text": prompt.text, "buttons": prompt.buttons}
        if prompt
        else None,
        "linkedin_session": {
            "state": linkedin.state if linkedin else "unknown",
            "checked_at": linkedin.checked_at if linkedin else None,
        },
    }


@router.post("/prompts/{prompt_id}/answer")
def answer_prompt(prompt_id: int, body: Answer, session: Session = Depends(get_session)) -> dict:
    prompt = session.scalar(select(Prompt).where(Prompt.id == prompt_id).with_for_update())
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if prompt.answer is not None:
        raise HTTPException(status_code=409, detail="Prompt already answered")
    if body.button not in prompt.buttons:
        raise HTTPException(status_code=422, detail=f"button must be one of {prompt.buttons}")
    prompt.answer = body.button
    prompt.answered_at = datetime.now(timezone.utc)
    session.commit()
    return {"id": prompt.id, "answer": prompt.answer}
