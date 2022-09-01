import scrapy


class QuotesSpider(scrapy.Spider):
    name = 'test'
    start_urls = ['https://quotes.toscrape.com']
    """
    def start_requests(self):
        urls = [
            'https://quotes.toscrape.com/page/1/',
            'https://quotes.toscrape.com/page/2/',
        ]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
    """
    def parse(self, response, **kwargs):
        for quote in response.css('div.quote'):
            author = quote.css('small.author::text').get()
            text = quote.css('span.text::text').get()
            tags = quote.css('div.tags a.tag::text').getall()

            yield dict(author=author, text=text, tags=tags)

            for href in response.css('li.next a::attr(href)'):
                yield response.follow(href, self.parse)
            """
            next_page = response.css('li.next a::attr(href)').get()
            if next_page is not None:                
                #next_page = response.urljoin(next_page)
                #yield scrapy.Request(url=next_page, callback=self.parse)
                
                yield response.follow(next_page, callback=self.parse)
            """
    def parse_page(self, response, **kwargs):
        page = response.url.split('/')[-2]
        filename = f'quotes-{page}.html'

        with open(filename, 'wb') as f:
            f.write(response.body)
            self.log(f'Saved file {filename}')
