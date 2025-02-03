from sqlalchemy import select

from src.models import Task
from src.services.dao.base import BaseDAO


class TaskDAO(BaseDAO[Task]):
    def __init__(self, session, *args, **kwargs):
        super().__init__(Task, session, *args, **kwargs)

    def get(self, model_id: str) -> Task | None:
        """
        :param model_id: input id
        :return:
        """
        result = self.session.scalars(
            select(self.model).where(self.model.id == model_id)
        )

        return result.one_or_none()
