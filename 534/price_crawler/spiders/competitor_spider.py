import scrapy
from datetime import datetime
from price_crawler.items import CompetitorPriceItem


class CompetitorSpider(scrapy.Spider):
    name = 'competitor'
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
    }

    def __init__(self, product_name=None, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product_name = product_name or '智能手机'
        self.category = category or '数码产品'

    def start_requests(self):
        demo_urls = [
            'https://example-shop-1.com/search?q=phone',
            'https://example-shop-2.com/search?q=phone',
            'https://example-shop-3.com/search?q=phone',
        ]
        for url in demo_urls:
            yield scrapy.Request(url, callback=self.parse, meta={
                'product_name': self.product_name,
                'category': self.category,
            }, dont_filter=True, errback=self.errback_handler)

    def errback_handler(self, failure):
        self.logger.info(f'Crawl failed (expected for demo): {failure.request.url}')
        from price_crawler.demo_data import generate_demo_crawl_data
        for item_data in generate_demo_crawl_data(self.product_name, self.category):
            item = CompetitorPriceItem()
            for key, value in item_data.items():
                item[key] = value
            yield item

    def parse(self, response):
        pass
