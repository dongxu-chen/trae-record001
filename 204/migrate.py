from sqlalchemy import text
from database import engine
import os
from dotenv import load_dotenv

load_dotenv()

def create_indexes():
    print("正在创建数据库索引...")
    
    db_name = os.getenv("MYSQL_DATABASE", "sales_dashboard")
    
    with engine.connect() as conn:
        conn.execute(text(f"USE {db_name}"))
        
        existing_indexes = conn.execute(text("SHOW INDEX FROM orders")).fetchall()
        existing_index_names = [idx[2] for idx in existing_indexes]
        
        indexes_to_create = [
            ('idx_date_category', 'CREATE INDEX idx_date_category ON orders(order_date, category)'),
            ('idx_date_region', 'CREATE INDEX idx_date_region ON orders(order_date, region)'),
            ('idx_date_category_region', 'CREATE INDEX idx_date_category_region ON orders(order_date, category, region)'),
        ]
        
        for idx_name, idx_sql in indexes_to_create:
            if idx_name not in existing_index_names:
                print(f"创建索引: {idx_name}")
                conn.execute(text(idx_sql))
                conn.commit()
            else:
                print(f"索引已存在: {idx_name}")
        
        print("索引创建完成！")
        print("\n当前索引列表:")
        indexes = conn.execute(text("SHOW INDEX FROM orders")).fetchall()
        for idx in indexes:
            print(f"  - {idx[2]} (列: {idx[4]})")

if __name__ == "__main__":
    create_indexes()
