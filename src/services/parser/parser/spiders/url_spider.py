import scrapy
from scrapy.loader import ItemLoader

from src.services.parser.parser.items import ExtractItem, ParserItem


class UrlsSpider(scrapy.Spider):
    name = "url_spider"

    def __init__(
        self,
        urls: list[tuple[int, str]],
        selectors: list[tuple[int, str]],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.urls = {url_address: url_id for url_id, url_address in urls}
        self.start_urls = list(self.urls.keys())
        self.selectors = selectors

    def parse(self, response, **kwargs):
        il = ItemLoader(item=ParserItem)
        il.add_value("url_id", self.urls[response.request.url])
        il.add_value("url", response.request.url)
        il.add_value("status", response.status)

        extracts = []
        extract = ItemLoader(item=ExtractItem)
        for extract_id, selector in self.selectors:
            extract.add_value("extract_id", extract_id)
            extract.add_value("draft", response.xpath(selector).get(""))
            extracts.append(extract.load_item())
        il.add_value("extracts", extracts)

        yield il.load_item()
