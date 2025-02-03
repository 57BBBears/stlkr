from sqlalchemy import select

from src.models import Resource, ResourceExtract
from src.services.dao.base import BaseDAO


class ResourceDAO(BaseDAO[Resource]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Resource, session, *args, **kwargs)

    def get_selectors(self, resource_id: int):
        query = select(ResourceExtract).where(
            ResourceExtract.resource_id == resource_id
        )
        return self.session.scalars(query).all()
