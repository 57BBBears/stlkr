from typing import Any

from flask_sqlalchemy.pagination import SelectPagination
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


class JoinedPagination(SelectPagination):
    def _query_items(self) -> list[Any]:
        select = self._query_args["select"]
        select = select.limit(self.per_page).offset(self._query_offset)
        session = self._query_args["session"]
        return list(session.execute(select).unique())


def paginate(
    session: Session,
    select: Select[Any],
    *,
    page: int | None = None,
    per_page: int | None = None,
    max_per_page: int | None = None,
    error_out: bool = True,
    count: bool = True,
) -> JoinedPagination:
    """
    Code is from flask_sqlalchemy.extension SelectPagination.paginate
    """
    return JoinedPagination(
        select=select,
        session=session,
        page=page,
        per_page=per_page,
        max_per_page=max_per_page,
        error_out=error_out,
        count=count,
    )
