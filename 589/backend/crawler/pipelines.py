import logging
from datetime import datetime, date
from itemadapter import ItemAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class DataCleaningPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if adapter.get('name'):
            adapter['name'] = adapter['name'].strip()[:255]

        if adapter.get('price'):
            try:
                price_str = str(adapter['price']).replace('¥', '').replace('￥', '')
                price_str = price_str.replace(',', '').strip()
                adapter['price'] = Decimal(price_str)
            except (InvalidOperation, ValueError):
                logger.warning(f"Invalid price: {adapter.get('price')} for {adapter.get('name')}")
                adapter['price'] = Decimal('0')

        if adapter.get('original_price'):
            try:
                price_str = str(adapter['original_price']).replace('¥', '').replace('￥', '')
                price_str = price_str.replace(',', '').strip()
                adapter['original_price'] = Decimal(price_str)
            except (InvalidOperation, ValueError):
                adapter['original_price'] = adapter.get('price')

        if adapter.get('rating'):
            try:
                rating = float(adapter['rating'])
                adapter['rating'] = round(rating, 1) if 0 <= rating <= 5 else None
            except (ValueError, TypeError):
                adapter['rating'] = None

        if adapter.get('sales'):
            try:
                sales_str = str(adapter['sales'])
                if '万' in sales_str:
                    adapter['sales'] = int(float(sales_str.replace('万', '')) * 10000)
                elif '+' in sales_str:
                    adapter['sales'] = int(sales_str.replace('+', ''))
                else:
                    adapter['sales'] = int(''.join(filter(str.isdigit, sales_str)) or 0)
            except ValueError:
                adapter['sales'] = 0

        if adapter.get('product_url'):
            adapter['product_url'] = adapter['product_url'].split('?')[0][:1000]

        if adapter.get('in_stock') is None:
            adapter['in_stock'] = True

        return item


class DatabasePipeline:
    def __init__(self, database_url):
        self.database_url = database_url
        self.engine = None
        self.Session = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get('DATABASE_URL'))

    def open_spider(self, spider):
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)

    def close_spider(self, spider):
        if self.engine:
            self.engine.dispose()

    def process_item(self, item, spider):
        session = self.Session()
        try:
            from ..app.models.product import Product
            from ..app.models.price import PlatformPrice

            adapter = ItemAdapter(item)
            product_name = adapter.get('name')
            platform = adapter.get('platform')
            platform_price = adapter.get('price')

            if not product_name or not platform or platform_price == 0:
                return item

            product = session.query(Product).filter(
                Product.name == product_name
            ).first()

            if not product:
                product = Product(
                    name=product_name,
                    category=adapter.get('category', '其他'),
                    brand=adapter.get('brand'),
                    model=adapter.get('model'),
                    image_url=adapter.get('image_url'),
                    description=adapter.get('description')
                )
                session.add(product)
                session.flush()

            existing_price = session.query(PlatformPrice).filter(
                PlatformPrice.product_id == product.id,
                PlatformPrice.platform == platform
            ).first()

            platform_name = {
                'taobao': '淘宝',
                'jd': '京东',
                'pdd': '拼多多',
                'suning': '苏宁',
                'tmall': '天猫'
            }.get(platform, platform)

            if existing_price:
                price_changed = abs(float(existing_price.price) - float(platform_price)) > 0.01
                existing_price.price = platform_price
                existing_price.original_price = adapter.get('original_price', platform_price)
                existing_price.product_url = adapter.get('product_url', existing_price.product_url)
                existing_price.in_stock = adapter.get('in_stock', True)
                existing_price.rating = adapter.get('rating')
                existing_price.sales = adapter.get('sales', 0)
                existing_price.last_updated = datetime.utcnow()

                if price_changed:
                    spider.logger.info(
                        f"Price updated: {product_name} on {platform_name}: "
                        f"¥{existing_price.price} → ¥{platform_price}"
                    )
                    item['price_changed'] = True
                    item['old_price'] = float(existing_price.price)
                    item['new_price'] = float(platform_price)
            else:
                new_price = PlatformPrice(
                    product_id=product.id,
                    platform=platform,
                    platform_name=platform_name,
                    price=platform_price,
                    original_price=adapter.get('original_price', platform_price),
                    product_url=adapter.get('product_url', ''),
                    in_stock=adapter.get('in_stock', True),
                    rating=adapter.get('rating'),
                    sales=adapter.get('sales', 0)
                )
                session.add(new_price)
                spider.logger.info(f"New price record: {product_name} on {platform_name}: ¥{platform_price}")

            session.commit()
            item['product_id'] = product.id

        except IntegrityError as e:
            logger.error(f"Integrity error: {e}")
            session.rollback()
        except Exception as e:
            logger.error(f"Database error: {e}")
            session.rollback()
        finally:
            session.close()

        return item


class PriceHistoryPipeline:
    def __init__(self, sqlite_url):
        self.sqlite_url = sqlite_url
        self.engine = None
        self.Session = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get('SQLITE_URL'))

    def open_spider(self, spider):
        self.engine = create_engine(self.sqlite_url, connect_args={"check_same_thread": False})
        self.Session = sessionmaker(bind=self.engine)

        from ..app.models.price import PriceHistory
        from ..app.database import HistoryBase
        HistoryBase.metadata.create_all(bind=self.engine)

    def close_spider(self, spider):
        if self.engine:
            self.engine.dispose()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        product_id = adapter.get('product_id')
        price = adapter.get('price')

        if not product_id or price == 0:
            return item

        session = self.Session()
        try:
            from ..app.models.price import PriceHistory

            today = date.today()
            existing_record = session.query(PriceHistory).filter(
                PriceHistory.product_id == product_id,
                PriceHistory.platform == adapter.get('platform'),
                PriceHistory.record_date == today
            ).first()

            if not existing_record:
                history = PriceHistory(
                    product_id=product_id,
                    platform=adapter.get('platform'),
                    price=price,
                    record_date=today
                )
                session.add(history)
                session.commit()
                spider.logger.debug(
                    f"Price history recorded: {product_id} "
                    f"on {adapter.get('platform')}: ¥{price}"
                )

        except Exception as e:
            logger.error(f"Price history error: {e}")
            session.rollback()
        finally:
            session.close()

        return item
