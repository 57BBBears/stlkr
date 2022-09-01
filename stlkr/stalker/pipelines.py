# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class StalkerPipeline:
    def process_item(self, item, spider):
        return item


"""
class DBPipeline:
    def __init__(self, db, app):
        self.db = db
        self.app = app

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db=crawler.settings.get('db'),
            app=crawler.settings.get('app')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()
    def process_item(self, item, spider):

        return item
"""