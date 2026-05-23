import random
from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine, Base, SessionLocal
from models import Order, Subscription
import os

CATEGORIES = ["电子产品", "服装鞋帽", "家居用品", "食品饮料", "美妆护肤", "运动户外"]
REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北"]
PRODUCTS = {
    "电子产品": ["智能手机", "笔记本电脑", "平板电脑", "智能手表", "蓝牙耳机", "充电宝"],
    "服装鞋帽": ["T恤", "牛仔裤", "运动鞋", "羽绒服", "连衣裙", "休闲鞋"],
    "家居用品": ["床上用品", "收纳箱", "台灯", "坐垫", "窗帘", "厨具套装"],
    "食品饮料": ["进口零食", "有机牛奶", "咖啡豆", "红酒", "坚果礼盒", "矿泉水"],
    "美妆护肤": ["精华液", "面霜", "口红", "面膜", "防晒霜", "粉底液"],
    "运动户外": ["瑜伽垫", "跑步机", "登山包", "帐篷", "羽毛球拍", "运动手环"]
}

def create_database():
    conn = engine.connect()
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {os.getenv('MYSQL_DATABASE', 'sales_dashboard')}"))
    conn.close()

def generate_orders(days=730, orders_per_day=50):
    db = SessionLocal()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    start_date = datetime.now().date() - timedelta(days=days)
    order_counter = 1
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        daily_orders = orders_per_day + random.randint(-20, 30)
        
        for _ in range(daily_orders):
            category = random.choice(CATEGORIES)
            product = random.choice(PRODUCTS[category])
            region = random.choice(REGIONS)
            quantity = random.randint(1, 5)
            unit_price = round(random.uniform(50, 2000), 2)
            total_amount = round(quantity * unit_price, 2)
            
            order = Order(
                order_id=f"ORD{order_counter:08d}",
                order_date=current_date,
                category=category,
                region=region,
                product_name=product,
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total_amount,
                customer_id=f"CUST{random.randint(1000, 9999)}"
            )
            db.add(order)
            order_counter += 1
        
        if day % 10 == 0:
            db.commit()
    
    db.commit()
    db.close()
    print(f"生成了 {order_counter - 1} 条订单数据，覆盖 {days} 天（约2年）")

if __name__ == "__main__":
    create_database()
    generate_orders()
