from src.models import Page
from src.services.dao.base import BaseDAO


class PageDAO(BaseDAO[Page]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Page, session, *args, **kwargs)
