from typing import Any

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


class PageParams:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200)):
        self.page = page
        self.page_size = page_size


def paginate(session: Session, stmt: Select, params: PageParams, to_dict) -> dict[str, Any]:
    """`{items, total, page, page_size}` for an ordered select of ORM rows."""
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = session.scalars(stmt.limit(params.page_size).offset((params.page - 1) * params.page_size))
    return {
        "items": [to_dict(row) for row in rows],
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
    }


def row_dict(row, exclude: tuple[str, ...] = ()) -> dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in row.__mapper__.column_attrs if c.key not in exclude}
