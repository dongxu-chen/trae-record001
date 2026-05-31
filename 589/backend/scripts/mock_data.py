import sys
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, HistorySessionLocal
from app.models import Product, PlatformPrice, Coupon, User, PriceHistory
from app.services import CouponMatcher


def generate_mock_data():
    db = SessionLocal()
    history_db = HistorySessionLocal()

    try:
        print("Generating mock data...")

        user = User(
            id="user-001",
            email="demo@example.com",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
            nickname="比价达人"
        )
        db.add(user)
        db.commit()

        products_data = [
            {
                "name": "Apple iPhone 15 Pro Max 256GB",
                "category": "手机",
                "brand": "Apple",
                "model": "A3108",
                "description": "A17 Pro芯片，钛金属设计",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20iPhone%2015%20smartphone%20product%20photo&image_size=square_hd",
                "base_price": 8999
            },
            {
                "name": "Apple MacBook Pro 14英寸 M3 Pro",
                "category": "笔记本电脑",
                "brand": "Apple",
                "model": "A2918",
                "description": "M3 Pro芯片，18GB内存，512GB存储",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=MacBook%20Pro%20laptop%20product%20photo&image_size=square_hd",
                "base_price": 14999
            },
            {
                "name": "Apple AirPods Pro 2",
                "category": "耳机",
                "brand": "Apple",
                "model": "A2968",
                "description": "主动降噪，自适应通透模式",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=AirPods%20Pro%20wireless%20earbuds%20product%20photo&image_size=square_hd",
                "base_price": 1899
            },
            {
                "name": "小米14 Ultra 16GB+512GB",
                "category": "手机",
                "brand": "小米",
                "model": "23116PN5BC",
                "description": "徕卡光学全焦段四摄，骁龙8 Gen3",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Xiaomi%2014%20smartphone%20product%20photo&image_size=square_hd",
                "base_price": 6499
            },
            {
                "name": "华为 Mate 60 Pro 12GB+512GB",
                "category": "手机",
                "brand": "华为",
                "model": "ALN-AL00",
                "description": "麒麟9000S芯片，卫星通话",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Huawei%20Mate%2060%20Pro%20smartphone%20product%20photo&image_size=square_hd",
                "base_price": 6999
            },
            {
                "name": "索尼WH-1000XM5 头戴式降噪耳机",
                "category": "耳机",
                "brand": "索尼",
                "model": "WH-1000XM5",
                "description": "业界领先降噪，30小时续航",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Sony%20WH1000XM5%20headphones%20product%20photo&image_size=square_hd",
                "base_price": 2699
            },
            {
                "name": "戴森V15 Detect吸尘器",
                "category": "家电",
                "brand": "戴森",
                "model": "V15",
                "description": "激光探测，智能感应",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Dyson%20V15%20cordless%20vacuum%20cleaner%20product%20photo&image_size=square_hd",
                "base_price": 5990
            },
            {
                "name": "戴森Airwrap多功能美发棒",
                "category": "个护",
                "brand": "戴森",
                "model": "HS05",
                "description": "空气动力学卷发棒造型套装",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Dyson%20Airwrap%20hair%20styler%20product%20photo&image_size=square_hd",
                "base_price": 3690
            },
            {
                "name": "iPhone 15 128GB",
                "category": "手机",
                "brand": "Apple",
                "model": "A3092",
                "description": "A16仿生芯片，灵动岛设计",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Apple%20iPhone%2015%20blue%20smartphone%20product%20photo&image_size=square_hd",
                "base_price": 5999
            },
            {
                "name": "iPad Air 5代 256GB WiFi",
                "category": "平板电脑",
                "brand": "Apple",
                "model": "A2588",
                "description": "M1芯片，10.9英寸显示屏",
                "image_url": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=iPad%20Air%20tablet%20product%20photo&image_size=square_hd",
                "base_price": 5499
            },
        ]

        platforms = [
            {"key": "taobao", "name": "淘宝", "price_multiplier": 1.0},
            {"key": "jd", "name": "京东", "price_multiplier": 1.02},
            {"key": "pdd", "name": "拼多多", "price_multiplier": 0.95},
            {"key": "suning", "name": "苏宁", "price_multiplier": 1.01},
        ]

        created_products = []
        for prod_data in products_data:
            product = Product(
                name=prod_data["name"],
                category=prod_data["category"],
                brand=prod_data["brand"],
                model=prod_data["model"],
                image_url=prod_data["image_url"],
                description=prod_data["description"],
            )
            db.add(product)
            db.flush()
            created_products.append((product, prod_data["base_price"]))

            for platform in platforms:
                price_variance = random.uniform(-0.1, 0.1)
                final_multiplier = platform["price_multiplier"] * (1 + price_variance)
                price = float(prod_data["base_price"] * final_multiplier)
                original_price = price * random.uniform(1.05, 1.15)

                platform_price = PlatformPrice(
                    product_id=product.id,
                    platform=platform["key"],
                    platform_name=platform["name"],
                    price=Decimal(str(round(price, 2))),
                    original_price=Decimal(str(round(original_price, 2))),
                    product_url=f"https://example.com/{platform['key']/{product.id}",
                    in_stock=random.choice([True, True, True, True, False]),
                    rating=round(random.uniform(4.0, 5.0), 1),
                    sales=random.randint(100, 50000),
                )
                db.add(platform_price)

        coupons_data = [
            {"platform": "taobao", "code": "NEW100", "discount": 100, "type": "fixed", "min": 500},
            {"platform": "taobao", "code": "VIP10", "discount": 10, "type": "percentage", "min": 1000, "max": 200},
            {"platform": "jd", "code": "JD50", "discount": 50, "type": "fixed", "min": 300},
            {"platform": "jd", "code": "PLUS15", "discount": 15, "type": "percentage", "min": 2000, "max": 300},
            {"platform": "pdd", "code": "PDD200", "discount": 200, "type": "fixed", "min": 1000},
            {"platform": "pdd", "code": "NEWUSER", "discount": 20, "type": "percentage", "min": 500, "max": 100},
            {"platform": "suning", "code": "SUNING80", "discount": 80, "type": "fixed", "min": 400},
            {"platform": "suning", "code": "VIP5", "discount": 5, "type": "percentage", "min": 1500, "max": 150},
        ]

        today = datetime.now().date()
        for coup_data in coupons_data:
            coupon = Coupon(
                platform=coup_data["platform"],
                code=coup_data["code"],
                discount=Decimal(str(coup_data["discount"])),
                discount_type=coup_data["type"],
                min_amount=Decimal(str(coup_data["min"])),
                max_discount=Decimal(str(coup_data.get("max", 0))),
                valid_from=today - timedelta(days=random.randint(0, 30)),
                valid_to=today + timedelta(days=random.randint(30, 90)),
                is_active=True
            )
            db.add(coupon)

        db.commit()

        print(f"Created {len(products_data)} products, {len(platforms)*len(products_data)} prices, {len(coupons_data)} coupons")

        print("Generating price history data...")
        for product, base_price in created_products:
            for days_ago in range(90, 0, -1):
                record_date = today - timedelta(days=days_ago)
                for platform in platforms:
                    price_factor = 1 + random.uniform(-0.15, 0.1)
                    price = float(base_price) * platform["price_multiplier"] * price_factor

                    history = PriceHistory(
                        product_id=product.id,
                        platform=platform["key"],
                        price=Decimal(str(round(price, 2))),
                        record_date=record_date
                    )
                    history_db.add(history)

        history_db.commit()
        print("Price history generated!")

        print("\nMock data generation complete!")
        print(f"Demo user: demo@example.com / password123")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        history_db.rollback()
    finally:
        db.close()
        history_db.close()


if __name__ == "__main__":
    generate_mock_data()
