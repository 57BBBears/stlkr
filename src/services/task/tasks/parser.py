from celery.utils.log import get_task_logger

from src import create_app
from src.models import db
from src.services.dao.task import TaskDAO
from src.services.parser import Parser
from src.services.task.worker import celery

logger = get_task_logger(__name__)

app = create_app()
app.app_context().push()


@celery.task(bind=True)
async def parse_urls(
    self, urls: list[tuple[int, str]], selectors: list[tuple[int, str]]
):
    logger.debug(f"Task parse_urls {self.request.id}")
    parser = Parser("url_spider", urls=urls, selectors=selectors)
    parser.start()

    return self.request.id


@celery.task
def error_handler(request, exc, traceback):
    logger.error(f"Task {request.id} exception. ", exc_info=exc)
    _set_task_is_complete(request.id, True)


@celery.task
def complete_task(task_id: str):
    _set_task_is_complete(task_id, True)


def _set_task_is_complete(task_id: str, is_complete: bool):
    dao = TaskDAO(db.session)
    if task := dao.get(task_id):
        task.is_complete = is_complete
        dao.commit()
