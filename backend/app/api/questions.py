from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import PageParams, paginate, row_dict
from app.api.settings import load_all, save_section
from app.db import get_session
from app.models import UnansweredQuestion

router = APIRouter(prefix="/api/questions", tags=["questions"])


class Answer(BaseModel):
    answer: str


@router.get("/unanswered")
def list_unanswered(
    q: str | None = Query(None),
    params: PageParams = Depends(),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(UnansweredQuestion).order_by(UnansweredQuestion.last_seen.desc(), UnansweredQuestion.id.desc())
    if q:
        stmt = stmt.where(UnansweredQuestion.label.ilike(f"%{q}%"))
    return paginate(session, stmt, params, row_dict)


@router.post("/unanswered/{question_id}/answer")
def answer_unanswered(question_id: int, body: Answer, session: Session = Depends(get_session)) -> dict:
    """Adds the answer to Settings → Questions → custom answers, so the bot stops asking."""
    question = session.get(UnansweredQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if not body.answer.strip():
        raise HTTPException(status_code=422, detail={"field_errors": {"answer": "must not be empty"}})
    custom = list(load_all(session)["questions"]["custom_answers"])
    custom.append({"match": question.label, "answer": body.answer.strip()})
    session.delete(question)
    saved = save_section(session, "questions", {"custom_answers": custom})
    return {"custom_answers": saved["custom_answers"]}


@router.delete("/unanswered/{question_id}", status_code=204)
def dismiss_unanswered(question_id: int, session: Session = Depends(get_session)) -> Response:
    question = session.get(UnansweredQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    session.delete(question)
    session.commit()
    return Response(status_code=204)
