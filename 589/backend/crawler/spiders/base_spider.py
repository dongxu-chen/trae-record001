import scrapy
from datetime import datetime
from abc import abstractmethod
from urllib.parse import quote
from ..items import ProductItem


class BaseEcommerceSpider(scrapy.Spider):
    platform = None
    platform_name = None
    search_url_template = None

    def __init__(self, keyword=None, max_pages=3, *args, **kwargs):
        super(BaseEcommerceSpider, self).__init__(*args, **kwargs)
        self.keyword = keyword
        self.max_pages = int(max_pages)

    def start_requests(self):
        if self.keyword:
            keywords = [self.keyword]
        else:
            keywords = [
                'iPhone 15',
                'MacBook Pro',
                'AirPods Pro',
                'iPad Air',
                '小米14',
                '华为Mate 60',
                '一加12',
                '荣耀Magic6',
                'S24 Ultra',
                'OPPO Find X7'
            ]

        for keyword in keywords:
            for page in range(1, self.max_pages + 1):
                url = self.build_search_url(keyword, page)
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    meta={'keyword': keyword, 'page': page},
                    errback=self.errback_handler
                )

    def build_search_url(self, keyword, page=1):
        return self.search_url_template.format(keyword=quote(keyword), page=page)

    @abstractmethod
    def parse(self, response):
        pass

    def errback_handler(self, failure):
        self.logger.error(f"Request failed: {failure.request.url}")
        self.logger.error(failure.value)

    def create_item(self, **kwargs):
        item = ProductItem()
        item['platform'] = self.platform
        item['crawled_at'] = datetime.utcnow().isoformat()
        for key, value in kwargs.items():
            if key in item.fields and value is not None:
                item[key] = value
        return item

    def extract_price(self, selector):
        if not selector:
            return None
        text = selector.get()
        if not text:
            return None
        return text.replace('¥', '').replace('￥', '').replace(',', '').strip()
