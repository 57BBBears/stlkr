from src.models import Site
from src.services.dao.base import BaseDAO


class SiteDAO(BaseDAO[Site]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Site, session, *args, **kwargs)
