from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import Page, Site
from src.services.dao.base import BaseDAO


class PageDAO(BaseDAO[Page]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Page, session, *args, **kwargs)

    def get_by_slug(self, domain: str, page_slug: str) -> Page | None:
        query = (
            select(Page)
            .options(joinedload(Page.site).joinedload(Site.extracts))
            .join(Site, Page.site_id == Site.id)
            .where(Site.domain == domain, Page.slug == page_slug)
        )

        return self.session.scalars(query).unique().one_or_none()
