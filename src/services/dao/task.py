from datetime import UTC, datetime

from sqlalchemy import select, update

from src.models import Task, TaskStatus
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

    def revoke(self, task_id: str) -> bool:
        stmt = (
            update(Task)
            .where(Task.id == task_id, Task.finished_at.is_(None))
            .values(finished_at=datetime.now(UTC), status=TaskStatus.REVOKED)
            .returning(1)
        )
        return bool(self.session.execute(stmt).scalar_one_or_none())
