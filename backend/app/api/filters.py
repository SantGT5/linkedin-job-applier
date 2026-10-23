from datetime import date, datetime, time, timedelta

from sqlalchemy import Select


def date_range(stmt: Select, column, date_from: date | None, date_to: date | None) -> Select:
    """Inclusive day range on a timestamp column (dates in the server's local time)."""
    if date_from:
        stmt = stmt.where(column >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(column < datetime.combine(date_to + timedelta(days=1), time.min))
    return stmt
