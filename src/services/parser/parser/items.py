# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import MapCompose
from w3lib.html import remove_tags

# def remove_tags_from_data(data: dict[str, str]):
#     for key, value in data.items():
#         data[key] = remove_tags(value)
#
#     return data


class ExtractItem(scrapy.Item):
    extract_id = scrapy.Field()
    draft = scrapy.Field(input_processor=MapCompose(remove_tags))


class ParserItem(scrapy.Item):
    url_id = scrapy.Field()
    url = scrapy.Field()
    status = scrapy.Field()
    extracts = list[ExtractItem]
    # data = scrapy.Field(input_processor=MapCompose(remove_tags_from_data))
