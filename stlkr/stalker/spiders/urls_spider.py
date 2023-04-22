import scrapy


class UrlsSpider(scrapy.Spider):
    name = 'urls'
    handle_httpstatus_list = [301, 302, 404]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.start_urls = []
        # Trying to get start_urls from kwargs
        start_urls = kwargs.get('start_urls', None)
        if start_urls is not None:
            if type(start_urls) == str:
                # string
                start_urls = start_urls.replace(' ', '')
                self.start_urls = start_urls.split(',')
            elif hasattr(start_urls, '__iter__'):
                # iterable
                self.start_urls = start_urls

    def parse(self, response, **kwargs):
        nodata_statuses = [302, 404]
        if response.status in nodata_statuses:
            data = ''
        else:
            data = response.text

        yield {'url': response.url, 'status': response.status, 'data': data}
