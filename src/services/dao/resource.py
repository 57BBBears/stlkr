from src.models import Resource
from src.services.dao.base import BaseDAO


class ResourceDAO(BaseDAO[Resource]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Resource, session, *args, **kwargs)
