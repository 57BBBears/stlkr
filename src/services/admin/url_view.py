from typing import Sequence
from uuid import uuid4

from sqlalchemy.orm import Session

from src.models import Task
from src.services.dao.resource import ResourceDAO
from src.services.dao.task import TaskDAO
from src.services.dao.url import UrlDAO
from src.services.task.tasks.parser import complete_task, error_handler, parse_urls


def run_parse_urls_task(
    user_id: int, resource_id: int, url_ids: Sequence[int], session: Session
):
    url_dao = UrlDAO(session)
    urls = url_dao.get_by_ids(url_ids)
    urls = [(url.id, url.address) for url in urls]

    resource_dao = ResourceDAO(session)
    resource = resource_dao.get(resource_id)
    selectors = [
        (selector.extract_id, selector.selector) for selector in resource.selectors
    ]
    task_id = uuid4()
    task_dao = TaskDAO(session)
    task_dao.add(Task(id=task_id, user_id=user_id, project_id=resource.project_id))
    parse_urls.apply_async(
        (urls, selectors),
        task_id=task_id,
        link=complete_task.s(),
        link_error=error_handler.s(),
    )
