import scrapy


class CompetitorPriceItem(scrapy.Item):
    product_name = scrapy.Field()
    platform = scrapy.Field()
    competitor_name = scrapy.Field()
    original_price = scrapy.Field()
    current_price = scrapy.Field()
    discount = scrapy.Field()
    promo_tags = scrapy.Field()
    stock_status = scrapy.Field()
    crawl_time = scrapy.Field()
    product_category = scrapy.Field()
    url = scrapy.Field()
