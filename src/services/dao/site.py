from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import Site
from src.services.dao.base import BaseDAO


class SiteDAO(BaseDAO[Site]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Site, session, *args, **kwargs)

    def get_by_domain(self, domain: str) -> Site | None:
        query = (
            select(Site)
            .options(
                joinedload(Site.index_page, innerjoin=True),
                joinedload(Site.project, innerjoin=True),
            )
            .where(Site.domain == domain)
        )

        return self.session.scalars(query).one_or_none()
