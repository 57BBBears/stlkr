import csv
import os
from contextlib import contextmanager
from typing import Iterable, Sequence

import validators
from werkzeug.datastructures import FileStorage

from src.services.dao.url import UrlDAO


def get_urls_from_text(
    text: str, delimiter: str = "\r\n"
) -> tuple[set[str], list[str]]:
    url_list = text.split(delimiter)
    urls = set()
    not_urls = []
    for url in url_list:
        url = url.strip()
        if validators.url(url):
            urls.add(url)
        else:
            not_urls.append(url)

    return urls, not_urls


def save_urls(urls: Iterable[str], resource_id: int, dao: UrlDAO) -> Sequence[int]:
    return dao.insert_or_skip(get_url_insert_data(urls, resource_id)) if urls else []


def get_url_insert_data(urls: Iterable[str], resource_id: int) -> list[dict]:
    """
    Prepare data for insertion into db.
    :param urls:
    :param resource_id:
    :return:
    """
    return [{"resource_id": resource_id, "address": url} for url in urls]


@contextmanager
def open_temp_file(file_path: os.path, file: FileStorage, mode: str = "rt") -> os.path:
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    file.save(file_path)

    try:
        with open(file_path, mode=mode) as file:
            yield file
    finally:
        os.remove(file_path)


def get_urls_from_csv(
    csv_file: Iterable[str], delimiter: str = ","
) -> tuple[set[str], list[str]]:
    urls = set()
    not_urls = []

    reader = csv.reader(csv_file, delimiter=delimiter)

    for row in reader:
        url = row[0]

        if validators.url(url):
            urls.add(url)
        else:
            not_urls.append(url)

    return urls, not_urls
