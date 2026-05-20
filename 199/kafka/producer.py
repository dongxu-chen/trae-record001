import json
import random
import time
import uuid
from kafka import KafkaProducer
from typing import List
import threading

from config import KAFKA_CONFIG, KAFKA_TOPICS
from .topics import (
    ViewerMessage,
    OnlineMessage,
    LikeMessage,
    TransactionMessage,
    ProductClickMessage,
    DanmuMessage,
    DANMU_POOL,
    PRODUCT_POOL,
)


class LiveDataProducer:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
        )
        self._running = False
        self._threads: List[threading.Thread] = []
        self._current_online = 5000

    def _send(self, topic: str, value: dict, key: str = None):
        try:
            self.producer.send(
                topic=topic,
                value=value,
                key=key,
            )
            self.producer.flush(timeout=1)
        except Exception as e:
            print(f"发送消息失败 [{topic}]: {e}")

    def _produce_viewer(self):
        while self._running:
            try:
                action = random.choices(
                    ['enter', 'leave'],
                    weights=[0.7, 0.3]
                )[0]
                msg = ViewerMessage(
                    timestamp=time.time(),
                    viewer_id=str(uuid.uuid4()),
                    action=action,
                )
                self._send(KAFKA_TOPICS['viewer'], msg.to_json(), key=msg.viewer_id)
                time.sleep(random.uniform(0.01, 0.1))
            except Exception as e:
                print(f"观众数据生产错误: {e}")
                time.sleep(1)

    def _produce_online(self):
        while self._running:
            try:
                delta = random.randint(-50, 80)
                self._current_online = max(1000, min(20000, self._current_online + delta))
                msg = OnlineMessage(
                    timestamp=time.time(),
                    online_count=self._current_online,
                )
                self._send(KAFKA_TOPICS['online'], msg.to_json())
                time.sleep(1)
            except Exception as e:
                print(f"在线人数生产错误: {e}")
                time.sleep(1)

    def _produce_like(self):
        while self._running:
            try:
                count = random.randint(1, 10)
                msg = LikeMessage(
                    timestamp=time.time(),
                    user_id=str(uuid.uuid4()),
                    count=count,
                )
                self._send(KAFKA_TOPICS['like'], msg.to_json(), key=msg.user_id)
                time.sleep(random.uniform(0.005, 0.05))
            except Exception as e:
                print(f"点赞数据生产错误: {e}")
                time.sleep(1)

    def _produce_transaction(self):
        while self._running:
            try:
                product = random.choice(PRODUCT_POOL)
                quantity = random.randint(1, 3)
                msg = TransactionMessage(
                    timestamp=time.time(),
                    order_id=str(uuid.uuid4()),
                    user_id=str(uuid.uuid4()),
                    product_id=product['id'],
                    product_name=product['name'],
                    amount=product['price'] * quantity,
                    quantity=quantity,
                )
                self._send(KAFKA_TOPICS['transaction'], msg.to_json(), key=msg.order_id)
                time.sleep(random.uniform(0.2, 1.0))
            except Exception as e:
                print(f"交易数据生产错误: {e}")
                time.sleep(1)

    def _produce_product_click(self):
        while self._running:
            try:
                product = random.choice(PRODUCT_POOL)
                msg = ProductClickMessage(
                    timestamp=time.time(),
                    user_id=str(uuid.uuid4()),
                    product_id=product['id'],
                    product_name=product['name'],
                    duration=random.randint(1, 60),
                )
                self._send(KAFKA_TOPICS['product_click'], msg.to_json(), key=msg.product_id)
                time.sleep(random.uniform(0.05, 0.3))
            except Exception as e:
                print(f"商品点击数据生产错误: {e}")
                time.sleep(1)

    def _produce_danmu(self):
        while self._running:
            try:
                content = random.choice(DANMU_POOL)
                msg = DanmuMessage(
                    timestamp=time.time(),
                    user_id=str(uuid.uuid4()),
                    user_name=f"用户{random.randint(1000, 99999)}",
                    content=content,
                    is_vip=random.random() < 0.1,
                )
                self._send(KAFKA_TOPICS['danmu'], msg.to_json())
                time.sleep(random.uniform(0.1, 0.5))
            except Exception as e:
                print(f"弹幕数据生产错误: {e}")
                time.sleep(1)

    def start(self):
        self._running = True
        producers = [
            self._produce_viewer,
            self._produce_online,
            self._produce_like,
            self._produce_transaction,
            self._produce_product_click,
            self._produce_danmu,
        ]
        for func in producers:
            t = threading.Thread(target=func, daemon=True)
            t.start()
            self._threads.append(t)
        print("Kafka数据生产者已启动，正在模拟直播数据...")
        print(f"Kafka地址: {KAFKA_CONFIG['bootstrap_servers']}")
        print(f"Topics: {list(KAFKA_TOPICS.values())}")

    def stop(self):
        self._running = False
        for t in self._threads:
            t.join(timeout=2)
        self.producer.close()
        print("Kafka数据生产者已停止")

    def wait(self):
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


def main():
    producer = LiveDataProducer()
    producer.start()
    producer.wait()


if __name__ == '__main__':
    main()
