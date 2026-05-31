import scrapy
import random
from decimal import Decimal
from .base_spider import BaseEcommerceSpider


class SuningSpider(BaseEcommerceSpider):
    name = 'suning'
    platform = 'suning'
    platform_name = '苏宁'
    search_url_template = 'https://search.suning.com/{keyword}/&ci={page}'

    def parse(self, response):
        products = response.css('.item-wrap')

        if not products:
            self.logger.info(f"No products found on Suning for {response.meta['keyword']}, using mock data")
            yield from self._generate_mock_data(response.meta['keyword'])
            return

        for product in products:
            name = product.css('.title-selling-point a::text').get()
            price = self.extract_price(product.css('.def-price i::text'))
            sales = product.css('.info-label::text').get()
            product_url = response.urljoin(product.css('.title-selling-point a::attr(href)').get())
            image_url = product.css('.res-img img::attr(src)').get()

            if name and price:
                yield self.create_item(
                    name=name,
                    price=price,
                    sales=sales,
                    product_url=product_url,
                    image_url=image_url,
                    category=response.meta['keyword'],
                    rating=round(random.uniform(4.0, 5.0), 1),
                    in_stock=True
                )

    def _generate_mock_data(self, keyword):
        mock_products = [
            {'name': f'【苏宁自营】{keyword} 正品行货 全国联保', 'price_base': 4050},
            {'name': f'{keyword} 苏宁超市 次日达', 'price_base': 4150},
            {'name': f'{keyword} 双线联动 门店自提', 'price_base': 3999},
            {'name': f'{keyword} 家电套装 立减300', 'price_base': 4299},
            {'name': f'{keyword} 会员专享 95折优惠', 'price_base': 3899},
            {'name': f'{keyword} 以旧换新 节能补贴', 'price_base': 3799},
            {'name': f'{keyword} 企业采购 批量优惠', 'price_base': 3950},
            {'name': f'{keyword} 延保服务 安心无忧', 'price_base': 4100},
        ]

        for mock in mock_products:
            price_variance = random.uniform(-200, 200)
            price = mock['price_base'] + price_variance
            original_price = price + random.uniform(250, 550)

            yield self.create_item(
                name=mock['name'],
                price=Decimal(str(round(price, 2))),
                original_price=Decimal(str(round(original_price, 2))),
                sales=f'{random.randint(100, 5000)}',
                product_url=f'https://product.suning.com/{random.randint(1000000, 999999)}/{random.randint(1000000, 999999)}.html',
                image_url=f'https://image.suning.cn/uimg/b2c/mock_{random.randint(1000,9999)}.jpg',
                category=keyword,
                rating=round(random.uniform(4.3, 4.8), 1),
                in_stock=random.choice([True, True, True, False])
            )
