"""
Scrapy Item定义
"""
import scrapy


class ProductItem(scrapy.Item):
    product_id = scrapy.Field()
    name = scrapy.Field()
    brand = scrapy.Field()
    category = scrapy.Field()
    source = scrapy.Field()
    url = scrapy.Field()
    image_url = scrapy.Field()
    current_price = scrapy.Field()
    original_price = scrapy.Field()
    currency = scrapy.Field()
    in_stock = scrapy.Field()
    stock_level = scrapy.Field()
    promotion_info = scrapy.Field()
    promotion_type = scrapy.Field()
    is_on_promotion = scrapy.Field()
    rating = scrapy.Field()
    review_count = scrapy.Field()
    seller = scrapy.Field()
    sku = scrapy.Field()
    extra_info = scrapy.Field()


class PriceSnapshotItem(scrapy.Item):
    product_id = scrapy.Field()
    source = scrapy.Field()
    price = scrapy.Field()
    original_price = scrapy.Field()
    currency = scrapy.Field()
    in_stock = scrapy.Field()
    is_on_promotion = scrapy.Field()
    promotion_info = scrapy.Field()