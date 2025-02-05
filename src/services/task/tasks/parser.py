from datetime import UTC, datetime

from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from flask import current_app

from src.models import TaskStatus
from src.services.dao.task import TaskDAO
from src.services.parser import Parser
from src.services.task.worker import celery, session

logger = get_task_logger(__name__)


@celery.task(
    bind=True,
    soft_time_limit=current_app.config["TASK_SOFT_TIME_LIMIT"],
    time_limit=current_app.config["TASK_TIME_LIMIT"],
)
async def parse_urls(
    self, urls: list[tuple[int, str]], selectors: list[tuple[int, str]]
):
    logger.debug(f"Task parse_urls {self.request.id}")
    parser = Parser("url_spider", urls=urls, selectors=selectors)
    try:
        parser.start()

        return self.request.id
    except SoftTimeLimitExceeded:
        # save parsed urls to db
        parser.stop()
        raise


@celery.task
def error_handler(request, exc, traceback):
    logger.error(f"Task {request.id} exception. ", exc_info=exc)
    _set_task_status(request.id, TaskStatus.ERROR)


@celery.task
def complete_task(task_id: str):
    _set_task_status(task_id, TaskStatus.SUCCESS)


def _set_task_status(task_id: str, status: TaskStatus):
    dao = TaskDAO(session)
    if task := dao.get(task_id):
        task.status = status
        task.finished_at = datetime.now(UTC)
        dao.commit()
    dao.close()
