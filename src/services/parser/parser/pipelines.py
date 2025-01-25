# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from sqlalchemy import NullPool, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.services.dao.url_extract import UrlExtractDAO
from src.services.parser.parser.items import ExtractItem, ParserItem


class ParserPipeline:
    def process_item(self, item, spider):
        return item


class DBPipeline:
    def __init__(self, database_uri: str):
        self.database_uri = database_uri
        self.inserts = []
        self.dao = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            crawler.settings.get("SQLALCHEMY_DATABASE_URI"),
        )

    def open_spider(self, spider):
        session = self._get_session()
        self.dao = UrlExtractDAO(session)

    def _get_session(self):
        return Session(create_engine(self.database_uri, poolclass=NullPool))

    def close_spider(self, spider):
        try:
            self.dao.upsert(self.inserts)
            self.dao.commit()
        except SQLAlchemyError as e:
            spider.logger.error(e)
        finally:
            self.dao.close()

    def process_item(self, item, spider):
        self.inserts += self._get_inserts(item)

        return item

    @staticmethod
    def _get_inserts(item: ParserItem) -> list[dict]:
        inserts = []
        extract_item: ExtractItem
        for extract_item in item.extracts:
            inserts.append(
                {
                    "url_id": item.url_id,
                    "extract_id": extract_item.extract_id,
                    "draft": extract_item.draft,
                }
            )

        return inserts
