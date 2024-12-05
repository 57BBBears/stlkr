from typing import Sequence

from sqlalchemy.dialects.postgresql import insert

from src.models import Url
from src.services.dao.base import BaseDAO


class UrlDAO(BaseDAO[Url]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Url, session, *args, **kwargs)

    def insert_or_skip(self, inserts: list[dict]) -> Sequence[int]:
        do_nothing_stmt = (
            insert(Url)
            .on_conflict_do_nothing(constraint=Url.resource_id_address_key)
            .returning(Url.id)
        )

        result = self.session.scalars(do_nothing_stmt, inserts)

        return result.all()
