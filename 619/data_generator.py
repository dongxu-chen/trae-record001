import random
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class DataGenerator:
    def __init__(self, seed=42):
        random.seed(seed)
        np.random.seed(seed)
        self.users = []
        self.orders = []
        self.devices = []
        self.addresses = []
        self.ip_records = []

    def generate(self, n_normal_users=200, n_fraud_users=40, orders_per_normal=3, orders_per_fraud=12):
        self._generate_users(n_normal_users, n_fraud_users)
        self._generate_devices()
        self._generate_addresses()
        self._generate_orders(orders_per_normal, orders_per_fraud)
        self._generate_ip_records()
        return self._to_dataframes()

    def _generate_users(self, n_normal, n_fraud):
        provinces = ["北京", "上海", "广东", "浙江", "江苏", "四川", "湖北", "福建", "山东", "河南"]
        user_id = 1
        for i in range(n_normal):
            reg_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
            self.users.append({
                "user_id": f"U{user_id:05d}",
                "username": f"user_{user_id}",
                "register_date": reg_date.strftime("%Y-%m-%d"),
                "account_age_days": (datetime(2025, 1, 1) - reg_date).days,
                "is_fraud": False,
                "user_type": "normal"
            })
            user_id += 1
        for i in range(n_fraud):
            reg_date = datetime(2024, 8, 1) + timedelta(days=random.randint(0, 120))
            self.users.append({
                "user_id": f"U{user_id:05d}",
                "username": f"user_{user_id}",
                "register_date": reg_date.strftime("%Y-%m-%d"),
                "account_age_days": (datetime(2025, 1, 1) - reg_date).days,
                "is_fraud": True,
                "user_type": "fraud"
            })
            user_id += 1

    def _generate_devices(self):
        device_id = 1
        normal_users = [u for u in self.users if not u["is_fraud"]]
        fraud_users = [u for u in self.users if u["is_fraud"]]

        for u in normal_users:
            device_hash = hashlib.md5(f"device_{device_id}".encode()).hexdigest()[:12]
            self.devices.append({
                "device_id": f"D{device_id:05d}",
                "device_hash": device_hash,
                "user_id": u["user_id"],
                "device_type": random.choice(["mobile", "pc", "tablet"]),
                "os": random.choice(["iOS", "Android", "Windows", "MacOS"])
            })
            device_id += 1

        fraud_groups = [fraud_users[i:i + random.randint(3, 8)] for i in range(0, len(fraud_users), random.randint(3, 8))]
        for group in fraud_groups:
            n_devices = random.randint(1, 3)
            group_devices = []
            for _ in range(n_devices):
                device_hash = hashlib.md5(f"fraud_device_{device_id}".encode()).hexdigest()[:12]
                dev = {
                    "device_id": f"D{device_id:05d}",
                    "device_hash": device_hash,
                    "device_type": random.choice(["mobile", "pc"]),
                    "os": random.choice(["Android", "Windows"])
                }
                group_devices.append(dev)
                device_id += 1
            for u in group:
                dev = random.choice(group_devices)
                self.devices.append({
                    **dev,
                    "user_id": u["user_id"]
                })

    def _generate_addresses(self):
        cities_by_province = {
            "北京": ["朝阳区", "海淀区", "东城区", "西城区"],
            "上海": ["浦东新区", "黄浦区", "徐汇区", "静安区"],
            "广东": ["天河区", "南山区", "福田区", "越秀区"],
            "浙江": ["西湖区", "上城区", "江干区", "拱墅区"],
            "江苏": ["鼓楼区", "玄武区", "秦淮区", "建邺区"],
            "四川": ["武侯区", "锦江区", "青羊区", "成华区"],
            "湖北": ["武昌区", "江汉区", "洪山区", "硚口区"],
            "福建": ["思明区", "鼓楼区", "台江区", "仓山区"],
            "山东": ["历下区", "市中区", "槐荫区", "天桥区"],
            "河南": ["金水区", "二七区", "中原区", "管城区"]
        }
        addr_id = 1
        normal_users = [u for u in self.users if not u["is_fraud"]]
        fraud_users = [u for u in self.users if u["is_fraud"]]

        for u in normal_users:
            province = random.choice(list(cities_by_province.keys()))
            city = random.choice(cities_by_province[province])
            detail = f"{province}{city}{random.randint(1, 999)}号"
            self.addresses.append({
                "address_id": f"A{addr_id:05d}",
                "user_id": u["user_id"],
                "province": province,
                "city": city,
                "detail": detail,
                "full_address": detail
            })
            addr_id += 1

        fraud_groups = [fraud_users[i:i + random.randint(3, 8)] for i in range(0, len(fraud_users), random.randint(3, 8))]
        for group in fraud_groups:
            n_addresses = random.randint(1, 2)
            group_addrs = []
            for _ in range(n_addresses):
                province = random.choice(["广东", "浙江", "福建"])
                city = random.choice(cities_by_province[province])
                detail = f"{province}{city}{random.randint(1, 50)}号"
                addr = {
                    "address_id": f"A{addr_id:05d}",
                    "province": province,
                    "city": city,
                    "detail": detail,
                    "full_address": detail
                }
                group_addrs.append(addr)
                addr_id += 1
            for u in group:
                addr = random.choice(group_addrs)
                self.addresses.append({
                    **addr,
                    "user_id": u["user_id"]
                })

    def _generate_orders(self, normal_count, fraud_count):
        products = [
            {"name": "手机壳", "price_range": (15, 80), "cat": "数码配件"},
            {"name": "充电宝", "price_range": (30, 150), "cat": "数码配件"},
            {"name": "蓝牙耳机", "price_range": (50, 300), "cat": "数码配件"},
            {"name": "面膜", "price_range": (20, 100), "cat": "美妆护肤"},
            {"name": "洗面奶", "price_range": (30, 120), "cat": "美妆护肤"},
            {"name": "运动鞋", "price_range": (100, 500), "cat": "服装鞋帽"},
            {"name": "T恤", "price_range": (30, 150), "cat": "服装鞋帽"},
            {"name": "零食大礼包", "price_range": (20, 80), "cat": "食品"},
            {"name": "保温杯", "price_range": (25, 100), "cat": "家居"},
            {"name": "数据线", "price_range": (5, 30), "cat": "数码配件"},
        ]
        order_id = 1
        normal_users = [u for u in self.users if not u["is_fraud"]]
        fraud_users = [u for u in self.users if u["is_fraud"]]

        for u in normal_users:
            for _ in range(random.randint(1, normal_count * 2)):
                prod = random.choice(products)
                price = round(random.uniform(*prod["price_range"]), 2)
                quantity = random.randint(1, 3)
                order_date = datetime(2024, 6, 1) + timedelta(days=random.randint(0, 300))
                user_addrs = [a for a in self.addresses if a["user_id"] == u["user_id"]]
                addr = random.choice(user_addrs) if user_addrs else None
                self.orders.append({
                    "order_id": f"O{order_id:06d}",
                    "user_id": u["user_id"],
                    "product_name": prod["name"],
                    "category": prod["cat"],
                    "amount": price * quantity,
                    "quantity": quantity,
                    "unit_price": price,
                    "order_time": order_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "order_hour": order_date.hour,
                    "address_id": addr["address_id"] if addr else None,
                    "address_detail": addr["full_address"] if addr else "",
                    "is_fraud": False
                })
                order_id += 1

        fraud_products = [p for p in products if p["price_range"][0] < 50]
        for u in fraud_users:
            n_orders = random.randint(fraud_count, fraud_count * 2)
            burst_start = datetime(2024, 9, 1) + timedelta(days=random.randint(0, 90))
            for j in range(n_orders):
                prod = random.choice(fraud_products)
                price = round(random.uniform(*prod["price_range"]), 2)
                quantity = random.randint(1, 2)
                order_date = burst_start + timedelta(
                    minutes=random.randint(0, 7200)
                )
                user_addrs = [a for a in self.addresses if a["user_id"] == u["user_id"]]
                addr = random.choice(user_addrs) if user_addrs else None
                self.orders.append({
                    "order_id": f"O{order_id:06d}",
                    "user_id": u["user_id"],
                    "product_name": prod["name"],
                    "category": prod["cat"],
                    "amount": price * quantity,
                    "quantity": quantity,
                    "unit_price": price,
                    "order_time": order_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "order_hour": order_date.hour,
                    "address_id": addr["address_id"] if addr else None,
                    "address_detail": addr["full_address"] if addr else "",
                    "is_fraud": True
                })
                order_id += 1

    def _generate_ip_records(self):
        ip_id = 1
        normal_users = [u for u in self.users if not u["is_fraud"]]
        fraud_users = [u for u in self.users if u["is_fraud"]]

        for u in normal_users:
            n_ips = random.randint(1, 3)
            for _ in range(n_ips):
                ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
                self.ip_records.append({
                    "ip_id": f"IP{ip_id:05d}",
                    "user_id": u["user_id"],
                    "ip_address": ip,
                    "ip_type": random.choice(["住宅", "移动", "企业"]),
                    "login_time": (datetime(2024, 6, 1) + timedelta(days=random.randint(0, 300))).strftime("%Y-%m-%d %H:%M:%S")
                })
                ip_id += 1

        fraud_groups = [fraud_users[i:i + random.randint(3, 8)] for i in range(0, len(fraud_users), random.randint(3, 8))]
        for group in fraud_users:
            ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            self.ip_records.append({
                "ip_id": f"IP{ip_id:05d}",
                "user_id": group["user_id"],
                "ip_address": ip,
                "ip_type": random.choice(["VPN", "代理", "机房"]),
                "login_time": (datetime(2024, 9, 1) + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
            })
            ip_id += 1

        shared_ips = []
        for group in [fraud_users[i:i + random.randint(3, 6)] for i in range(0, len(fraud_users), random.randint(3, 6))]:
            if len(group) < 2:
                continue
            ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            shared_ips.append(ip)
            for u in group:
                self.ip_records.append({
                    "ip_id": f"IP{ip_id:05d}",
                    "user_id": u["user_id"],
                    "ip_address": ip,
                    "ip_type": random.choice(["VPN", "代理", "机房"]),
                    "login_time": (datetime(2024, 9, 1) + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d %H:%M:%S")
                })
                ip_id += 1

    def _to_dataframes(self):
        return {
            "users": pd.DataFrame(self.users),
            "orders": pd.DataFrame(self.orders),
            "devices": pd.DataFrame(self.devices),
            "addresses": pd.DataFrame(self.addresses),
            "ip_records": pd.DataFrame(self.ip_records)
        }
