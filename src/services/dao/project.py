from src.models import Project
from src.services.dao.base import BaseDAO


class ProjectDAO(BaseDAO[Project]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Project, session, *args, **kwargs)
