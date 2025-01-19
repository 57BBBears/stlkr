from typing import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import joinedload

from src.models import Page, PageUrl, Site, Url, UrlExtract
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

    def get_by_slug(self, domain: str, page_slug: str, url_slug: str) -> Page | None:
        query = (
            select(Url)
            .options(
                joinedload(Url.pages).joinedload(Page.site).joinedload(Site.extracts),
                joinedload(Url.url_extracts).joinedload(UrlExtract.extract),
            )
            .join(PageUrl, PageUrl.url_id == Url.id)
            .join(Page, Page.id == PageUrl.page_id)
            .join(Site, Page.site_id == Site.id)
            .where(
                Site.domain == domain, Page.slug == page_slug, Url.id == int(url_slug)
            )
        )

        return self.session.scalars(query).unique().one_or_none()
