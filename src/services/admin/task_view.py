from celery.result import AsyncResult
from sqlalchemy.orm import Session

from src.models import TaskStatus
from src.services.dao.task import TaskDAO
from src.services.task.worker import celery


def revoke_task(task_id: str, session: Session) -> TaskStatus | None:
    result = AsyncResult(task_id, app=celery)
    if result.ready():
        return None
    elif result.status == "STARTED":
        return TaskStatus.STARTED
    else:
        result.revoke()
        dao = TaskDAO(session)
        dao.revoke(task_id)

        return TaskStatus.REVOKED
