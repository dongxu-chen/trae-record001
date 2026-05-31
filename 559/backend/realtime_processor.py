import json
import threading
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from kafka import KafkaConsumer
import config
import redis


class RealTimeDataProcessor:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            decode_responses=True
        )
        
        self.viewer_history = deque(maxlen=60)
        self.click_data = defaultdict(int)
        self.order_data = defaultdict(lambda: {'count': 0, 'amount': 0})
        self.category_data = defaultdict(lambda: {'clicks': 0, 'orders': 0})
        
        self.total_clicks = 0
        self.total_orders = 0
        self.conversion_rate = 0
        
        self.chat_analysis = {
            'question': 0,
            'praise': 0,
            'complaint': 0,
            'neutral': 0
        }
        
        self.competitor_data = {}
        
        self.heat_score = 0
        self.heat_history = deque(maxlen=60)
        
        self.running = False

    def calculate_heat_score(self, viewer_count, clicks, orders):
        viewer_weight = 0.4
        click_weight = 0.3
        order_weight = 0.3
        
        normalized_viewers = min(viewer_count / 10000, 1)
        normalized_clicks = min(clicks / 1000, 1)
        normalized_orders = min(orders / 100, 1)
        
        return (
            viewer_weight * normalized_viewers +
            click_weight * normalized_clicks +
            order_weight * normalized_orders
        ) * 100

    def process_viewer_event(self, event):
        viewer_count = event['viewer_count']
        timestamp = event['timestamp']
        
        self.viewer_history.append({
            'timestamp': timestamp,
            'count': viewer_count
        })
        
        self.heat_score = self.calculate_heat_score(
            viewer_count, self.total_clicks, self.total_orders
        )
        self.heat_history.append({
            'timestamp': timestamp,
            'score': self.heat_score
        })
        
        self.redis_client.set('current_viewers', viewer_count)
        self.redis_client.set('heat_score', self.heat_score)

    def process_click_event(self, event):
        product_id = event['product_id']
        product_name = event['product_name']
        category = event['category']
        click_count = event['click_count']
        
        self.click_data[product_name] += click_count
        self.category_data[category]['clicks'] += click_count
        self.total_clicks += click_count
        
        if self.total_clicks > 0:
            self.conversion_rate = (self.total_orders / self.total_clicks) * 100
        
        self.redis_client.hset('product_clicks', product_name, self.click_data[product_name])
        self.redis_client.set('total_clicks', self.total_clicks)
        self.redis_client.set('conversion_rate', round(self.conversion_rate, 2))

    def process_order_event(self, event):
        product_id = event['product_id']
        product_name = event['product_name']
        category = event['category']
        total_amount = event['total_amount']
        
        self.order_data[product_name]['count'] += 1
        self.order_data[product_name]['amount'] += total_amount
        self.category_data[category]['orders'] += 1
        self.total_orders += 1
        
        if self.total_clicks > 0:
            self.conversion_rate = (self.total_orders / self.total_clicks) * 100
        
        self.redis_client.hset('product_orders', product_name, json.dumps(self.order_data[product_name]))
        self.redis_client.set('total_orders', self.total_orders)
        self.redis_client.set('conversion_rate', round(self.conversion_rate, 2))

    def process_chat_event(self, event):
        chat_type = event['chat_type']
        self.chat_analysis[chat_type] += 1
        
        self.redis_client.hset('chat_analysis', chat_type, self.chat_analysis[chat_type])

    def process_competitor_event(self, event):
        competitor_id = event['competitor_id']
        self.competitor_data[competitor_id] = event
        
        self.redis_client.hset(
            'competitor_data',
            competitor_id,
            json.dumps(event, ensure_ascii=False)
        )

    def get_analytics_suggestion(self):
        suggestions = []
        
        if self.conversion_rate < 2:
            suggestions.append({
                'type': 'urgent',
                'content': '转化率偏低，建议主播强调产品核心优势和限时优惠！'
            })
        
        complaint_ratio = self.chat_analysis['complaint'] / max(sum(self.chat_analysis.values()), 1)
        if complaint_ratio > 0.1:
            suggestions.append({
                'type': 'warning',
                'content': '负面评论增多，建议及时回应用户关切问题。'
            })
        
        question_ratio = self.chat_analysis['question'] / max(sum(self.chat_analysis.values()), 1)
        if question_ratio > 0.3:
            suggestions.append({
                'type': 'info',
                'content': '用户问题较多，建议详细讲解产品使用方法和售后服务。'
            })
        
        if self.heat_score < 30:
            suggestions.append({
                'type': 'urgent',
                'content': '热度下降，建议发起互动抽奖或推出限时特价！'
            })
        
        top_product = max(self.click_data.items(), key=lambda x: x[1]) if self.click_data else None
        if top_product and top_product[1] > 100:
            suggestions.append({
                'type': 'success',
                'content': f'{top_product[0]}热度很高，建议延长讲解时间，追加库存！'
            })
        
        return suggestions

    def get_recommended_products(self):
        product_scores = []
        for product in config.PRODUCTS:
            name = product['name']
            clicks = self.click_data.get(name, 0)
            orders = self.order_data.get(name, {}).get('count', 0)
            score = clicks * 0.3 + orders * 0.7
            product_scores.append({**product, 'score': score})
        
        product_scores.sort(key=lambda x: x['score'], reverse=True)
        return product_scores[:3]

    def get_summary_data(self):
        return {
            'current_viewers': self.viewer_history[-1]['count'] if self.viewer_history else 0,
            'total_clicks': self.total_clicks,
            'total_orders': self.total_orders,
            'conversion_rate': round(self.conversion_rate, 2),
            'heat_score': round(self.heat_score, 2),
            'viewer_trend': list(self.viewer_history),
            'heat_trend': list(self.heat_history),
            'product_clicks': dict(self.click_data),
            'product_orders': {k: dict(v) for k, v in self.order_data.items()},
            'category_data': {k: dict(v) for k, v in self.category_data.items()},
            'chat_analysis': self.chat_analysis,
            'competitor_data': self.competitor_data,
            'suggestions': self.get_analytics_suggestion(),
            'recommended_products': self.get_recommended_products(),
            'timestamp': datetime.now().isoformat()
        }

    def consume_kafka_topics(self):
        consumers = []
        
        topics = [
            (config.KAFKA_TOPIC_VIEWER, self.process_viewer_event),
            (config.KAFKA_TOPIC_CLICK, self.process_click_event),
            (config.KAFKA_TOPIC_ORDER, self.process_order_event),
            (config.KAFKA_TOPIC_CHAT, self.process_chat_event),
            (config.KAFKA_TOPIC_COMPETITOR, self.process_competitor_event),
        ]
        
        for topic, processor in topics:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest'
            )
            consumers.append((consumer, processor))
        
        def consume(consumer, processor):
            for message in consumer:
                try:
                    processor(message.value)
                except Exception as e:
                    print(f"处理消息错误: {e}")
        
        threads = []
        for consumer, processor in consumers:
            t = threading.Thread(target=consume, args=(consumer, processor))
            t.daemon = True
            t.start()
            threads.append(t)
        
        return threads

    def start(self):
        self.running = True
        print("启动实时数据处理器...")
        self.consume_kafka_topics()
        print("实时数据处理器已启动")


if __name__ == '__main__':
    processor = RealTimeDataProcessor()
    processor.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("停止处理器")
