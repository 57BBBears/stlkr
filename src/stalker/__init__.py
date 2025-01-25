import os
from typing import Callable

from scrapy import signals, spiderloader
from scrapy.crawler import Crawler, CrawlerProcess
from scrapy.utils.project import get_project_settings


class Stalker:
    """
    Stalker handles crawlers and init/start/stop process of crawling.
    """

    def __getitem__(self, item):
        return self._crawlers[item]

    def __init__(
        self,
        name: str = None,
        settings: dict = None,
        extra_settings: dict = None,
        **kwargs,
    ):
        """
        Initialisation of scrapy project settings to get available spiders
        and prepare crawler process.
        :param name: Name of a scrapy spider.
        :param settings: Common project settings for crawl process and spider loader.
        :param extra_settings: Settings for a spider if param 'name' is set.
        :param kwargs: Other params for a spider 'name' if set.
        """
        # Scrapy
        # project settings
        if settings:
            self.settings = settings.copy()
        else:
            # stalker settings module with a path to project spiders accessible from
            # out of the project root folder
            stalker_settings = os.environ.get(
                "STLKR_SETTINGS_MODULE", "src.stalker.settings"
            )

            # if there is an env var 'SCRAPY_SETTINGS_MODULE' rewrite it
            # and restore after settings initialisation
            scrapy_envvar = "SCRAPY_SETTINGS_MODULE"
            cur_scrapy_envvar = os.environ.get(scrapy_envvar)

            # rewrite env 'SCRAPY_SETTINGS_MODULE' to get_project_settings
            os.environ[scrapy_envvar] = stalker_settings
            self.settings = get_project_settings()

            # restore SCRAPY_SETTINGS_MODULE
            if cur_scrapy_envvar is not None:
                os.environ[scrapy_envvar] = cur_scrapy_envvar

        # get spiders and process
        self._spider_loader = spiderloader.SpiderLoader.from_settings(self.settings)
        self._project_spiders = self._spider_loader.list()
        self._process = CrawlerProcess(self.settings)

        # set crawlers
        self._crawlers = {}
        if name:
            # trying to add a spider
            self.add(name, extra_settings, **kwargs)

    def __iter__(self):
        for name in self._crawlers:
            yield self._crawlers[name]

    def _get_spider_by_name(self, name: str):
        if name in self._project_spiders:
            return self._spider_loader.load(name)

        return

    def add(self, name: str, settings: dict = None, **kwargs):
        """
        Add a stalker crawler to crawl with while run.
        Raise an error if spider does not exist.
        :param name: Name of a project spider. Must exists.
        :param settings: Crawler settings.
        """
        if spider := self._get_spider_by_name(name):
            self._crawlers[name] = StalkerCrawler(
                spider,
                self.settings.update(settings) if settings else self.settings,
                **kwargs,
            )
        else:
            raise ValueError(f"Crawler '{name}' doesn't exist.")

    def all(self):
        """
        :return: A list of available spiders that can be added to the Stalker to crawl.
        """
        return self._project_spiders

    def list(self):
        """
        :return: A list of Stalker crawlers that will be used in run.
        """
        return list(self._crawlers.keys())

    def remove(self, name: str):
        """
        Remove a crawler from future crawling process.
        :param name: Name of a project spider.
        """
        if name in self._crawlers:
            del self._crawlers[name]
        else:
            raise ValueError(f"Crawler '{name}' doesn't exist.")

    def run(self):
        """
        Run crawling.
        """
        for name in self._crawlers:
            self._process.crawl(self._crawlers[name], **self._crawlers[name].params)
        self._process.start()

    def stop(self):
        """
        Stop crawling.
        """
        return self._process.stop()


class StalkerCrawler(Crawler):
    """
    A crawler class with its params as dictionary i.e. start_urls, domain etc.
    Params are used in a crawler process crawl() to initiate crawler spider.
    """

    def __init__(self, spidercls, settings=None, init_reactor: bool = False, **kwargs):
        super().__init__(spidercls, settings, init_reactor)
        self.params = kwargs

    def __str__(self):
        return f"StalkerCrawler({self.spidercls})"

    def handle_item(self, callback: Callable):
        # Connect spider with a function to save url data
        self.signals.connect(callback, signal=signals.item_scraped)

    def handle_start(self, callback: Callable):
        self.signals.connect(callback, signal=signals.spider_opened)

    def handle_stop(self, callback: Callable):
        self.signals.connect(callback, signal=signals.spider_closed)

    def handle_error(self, callback: Callable):
        self.signals.connect(callback, signal=signals.spider_error)
