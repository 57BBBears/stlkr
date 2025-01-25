from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


class Parser:
    def __init__(self, spider_name: str, *args, **kwargs):
        self.process = CrawlerProcess(settings=get_project_settings())
        self.process.crawl(spider_name, *args, **kwargs)

    def start(self):
        # Start the crawling process (blocking call)
        self.process.start()
