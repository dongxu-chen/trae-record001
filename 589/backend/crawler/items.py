import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
from decimal import Decimal


def clean_text(value):
    if value:
        return ' '.join(str(value).split()).strip()
    return value


def parse_price(value):
    if value:
        value = str(value).replace('¥', '').replace('￥', '').replace(',', '').strip()
        try:
            return Decimal(value)
        except:
            return Decimal('0')
    return Decimal('0')


def parse_rating(value):
    if value:
        try:
            rating = float(str(value).replace('分', '').strip())
            return round(rating, 1)
        except:
            return None
    return None


def parse_sales(value):
    if value:
        value = str(value)
        try:
            if '万' in value:
                return int(float(value.replace('万', '')) * 10000)
            elif '+' in value:
                return int(value.replace('+', ''))
            else:
                return int(''.join(filter(str.isdigit, value)) or 0)
        except:
            return 0
    return 0


def parse_bool(value):
    if value:
        value = str(value).lower()
        return value not in ('无货', '缺货', 'out of stock', 'false', '0')
    return True


class ProductItem(scrapy.Item):
    name = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    category = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    brand = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    model = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    description = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join(' ')
    )
    image_url = scrapy.Field(output_processor=TakeFirst())
    product_url = scrapy.Field(output_processor=TakeFirst())
    platform = scrapy.Field(output_processor=TakeFirst())
    price = scrapy.Field(
        input_processor=MapCompose(parse_price),
        output_processor=TakeFirst()
    )
    original_price = scrapy.Field(
        input_processor=MapCompose(parse_price),
        output_processor=TakeFirst()
    )
    rating = scrapy.Field(
        input_processor=MapCompose(parse_rating),
        output_processor=TakeFirst()
    )
    sales = scrapy.Field(
        input_processor=MapCompose(parse_sales),
        output_processor=TakeFirst()
    )
    in_stock = scrapy.Field(
        input_processor=MapCompose(parse_bool),
        output_processor=TakeFirst()
    )
    product_id = scrapy.Field(output_processor=TakeFirst())
    crawled_at = scrapy.Field(output_processor=TakeFirst())
