from sqlalchemy.dialects.postgresql import insert

from src.models import UrlExtract
from src.services.dao.base import BaseDAO


class UrlExtractDAO(BaseDAO[UrlExtract]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(UrlExtract, session, *args, **kwargs)

    def upsert(self, inserts: list[dict]):
        insert_stmt = insert(UrlExtract).values(inserts)

        update_stmt = insert_stmt.on_conflict_do_update(
            constraint=UrlExtract.url_id_extract_id_key,
            set_=dict(draft=insert_stmt.excluded.draft),
        )

        self.session.execute(update_stmt)
