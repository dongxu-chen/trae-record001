import json
import time
import random
from kafka import KafkaProducer
from datetime import datetime
import config


class LiveDataProducer:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
        )
        self.current_viewers = 1000
        self.current_product_index = 0

    def generate_viewer_event(self):
        change = random.randint(-50, 80)
        self.current_viewers = max(100, self.current_viewers + change)
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'viewer_count': self.current_viewers,
            'new_enter': max(0, change),
            'exit_count': max(0, -change)
        }
        self.producer.send(config.KAFKA_TOPIC_VIEWER, value=event)
        return event

    def generate_click_event(self):
        product = random.choice(config.PRODUCTS)
        event = {
            'timestamp': datetime.now().isoformat(),
            'product_id': product['id'],
            'product_name': product['name'],
            'category': product['category'],
            'click_count': random.randint(1, 20)
        }
        self.producer.send(config.KAFKA_TOPIC_CLICK, value=event)
        return event

    def generate_order_event(self):
        product = random.choice(config.PRODUCTS)
        quantity = random.randint(1, 5)
        event = {
            'timestamp': datetime.now().isoformat(),
            'product_id': product['id'],
            'product_name': product['name'],
            'category': product['category'],
            'price': product['price'],
            'quantity': quantity,
            'total_amount': product['price'] * quantity
        }
        self.producer.send(config.KAFKA_TOPIC_ORDER, value=event)
        return event

    def generate_chat_event(self):
        chat_types = ['question', 'praise', 'complaint', 'neutral']
        chat_type = random.choice(chat_types)
        
        chat_messages = {
            'question': ['这个有优惠吗？', '适合什么肤质？', '包邮吗？', '有赠品吗？'],
            'praise': ['主播讲得好！', '产品真不错', '已下单！', '回购多次了'],
            'complaint': ['价格有点贵', '上次买的还没到', '颜色不太喜欢'],
            'neutral': ['看看再说', '先加购物车', '对比一下']
        }
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'chat_type': chat_type,
            'message': random.choice(chat_messages[chat_type]),
            'user_id': random.randint(10000, 99999)
        }
        self.producer.send(config.KAFKA_TOPIC_CHAT, value=event)
        return event

    def generate_competitor_event(self):
        competitor = random.choice(config.COMPETITORS)
        price_variation = random.uniform(-10, 10)
        current_price = competitor['base_price'] + price_variation
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'competitor_id': competitor['id'],
            'competitor_name': competitor['name'],
            'product': competitor['product'],
            'current_price': round(current_price, 2),
            'viewer_count': random.randint(500, 5000),
            'sales_volume': random.randint(10, 200)
        }
        self.producer.send(config.KAFKA_TOPIC_COMPETITOR, value=event)
        return event

    def run(self):
        print("开始生成直播数据...")
        try:
            while True:
                self.generate_viewer_event()
                self.generate_click_event()
                
                if random.random() < 0.3:
                    self.generate_order_event()
                
                if random.random() < 0.6:
                    self.generate_chat_event()
                
                if random.random() < 0.2:
                    self.generate_competitor_event()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("停止生成数据")
            self.producer.close()


if __name__ == '__main__':
    producer = LiveDataProducer()
    producer.run()
