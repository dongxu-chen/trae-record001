import json
import time
import threading
from typing import Callable, Optional
from kafka import KafkaConsumer
from collections import deque

from config import KAFKA_CONFIG, KAFKA_TOPICS, FLINK_CONFIG
from .aggregation import MetricsAggregator
from .sentiment import SentimentAnalyzer
from .hotwords import HotWordExtractor


class StreamProcessingJob:
    def __init__(self, use_pyflink: bool = False):
        self.use_pyflink = use_pyflink
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks = []

        self.aggregator = MetricsAggregator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.hotword_extractor = HotWordExtractor()

        self._danmu_history = deque(maxlen=100)
        self._consumers = {}

    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def _notify_callbacks(self, data: dict):
        for callback in self._callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"回调执行错误: {e}")

    def _create_consumer(self, topic: str) -> KafkaConsumer:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
            group_id=f"{KAFKA_CONFIG['group_id']}-{topic}",
            auto_offset_reset=KAFKA_CONFIG['auto_offset_reset'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
        )
        return consumer

    def _process_message(self, topic: str, value):
        try:
            if isinstance(value, str):
                data = json.loads(value)
            else:
                data = value

            event_timestamp = data.get('event_timestamp', data.get('timestamp', time.time()))
            data['event_timestamp'] = event_timestamp

            if topic == KAFKA_TOPICS['viewer']:
                self.aggregator.add_viewer(data)

            elif topic == KAFKA_TOPICS['online']:
                self.aggregator.add_online(data)

            elif topic == KAFKA_TOPICS['like']:
                self.aggregator.add_like(data)

            elif topic == KAFKA_TOPICS['transaction']:
                self.aggregator.add_transaction(data)

            elif topic == KAFKA_TOPICS['product_click']:
                self.aggregator.add_product_click(data)

            elif topic == KAFKA_TOPICS['danmu']:
                sentiment = self.sentiment_analyzer.analyze(
                    data.get('content', ''),
                    event_timestamp=event_timestamp
                )
                self.hotword_extractor.extract(data.get('content', ''))

                danmu_id = data.get('danmu_id', int(time.time() * 1000))
                danmu_data = {
                    'danmu_id': danmu_id,
                    'user_name': data.get('user_name', ''),
                    'content': data.get('content', ''),
                    'is_vip': data.get('is_vip', False),
                    'timestamp': data.get('timestamp', time.time()),
                    'event_timestamp': event_timestamp,
                    'sentiment': sentiment,
                }
                self._danmu_history.append(danmu_data)

        except Exception as e:
            print(f"处理消息错误 [{topic}]: {e}")

    def _consume_topic(self, topic: str):
        try:
            consumer = self._create_consumer(topic)
            self._consumers[topic] = consumer

            for message in consumer:
                if not self._running:
                    break
                self._process_message(topic, message.value)

        except Exception as e:
            print(f"消费主题错误 [{topic}]: {e}")
        finally:
            if topic in self._consumers:
                self._consumers[topic].close()

    def _aggregate_and_push(self):
        while self._running:
            try:
                metrics = self.aggregator.get_metrics()
                sentiment_stats = self.sentiment_analyzer.get_statistics(use_event_time=True)
                hotwords = self.hotword_extractor.get_hotwords()
                trend = self.aggregator.get_trend_data(use_event_time=True)
                top_products = self.aggregator.get_top_products()
                watermark_info = self.aggregator.get_watermark_info()

                latest_danmu = list(self._danmu_history)[-10:]
                last_processed_danmu_id = 0
                if latest_danmu:
                    last_processed_danmu_id = max(d.get('danmu_id', 0) for d in latest_danmu)

                incremental_info = {
                    'last_processed_danmu_id': last_processed_danmu_id,
                    'total_danmu_in_window': len(self._danmu_history),
                }

                result = {
                    'type': 'metrics_update',
                    'metrics': metrics,
                    'sentiment': sentiment_stats,
                    'hotwords': hotwords,
                    'trend': trend,
                    'top_products': top_products,
                    'latest_danmu': latest_danmu,
                    'watermark': watermark_info,
                    'incremental_info': incremental_info,
                    'timestamp': time.time(),
                }

                self._notify_callbacks(result)
                time.sleep(FLINK_CONFIG['window_slide'])

            except Exception as e:
                print(f"聚合推送错误: {e}")
                time.sleep(1)

    def _run_pure_python(self):
        threads = []

        for topic in KAFKA_TOPICS.values():
            t = threading.Thread(target=self._consume_topic, args=(topic,), daemon=True)
            t.start()
            threads.append(t)

        aggregate_thread = threading.Thread(target=self._aggregate_and_push, daemon=True)
        aggregate_thread.start()
        threads.append(aggregate_thread)

        print("流处理作业已启动（Python模式），正在处理实时数据...")
        print(f"窗口大小: {FLINK_CONFIG['window_size']}s, 滑动间隔: {FLINK_CONFIG['window_slide']}s")

        for t in threads:
            t.join()

    def _run_pyflink(self):
        print("正在启动PyFlink作业...")
        try:
            self._run_pyflink_job()
        except Exception as e:
            print(f"PyFlink启动失败，切换到Python模式: {e}")
            self._run_pure_python()

    def _run_pyflink_job(self):
        from pyflink.datastream import StreamExecutionEnvironment
        from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer
        from pyflink.common.serialization import SimpleStringSchema
        from pyflink.common.typeinfo import Types

        env = StreamExecutionEnvironment.get_execution_environment()
        env.set_parallelism(FLINK_CONFIG['parallelism'])
        env.enable_checkpointing(FLINK_CONFIG['checkpoint_interval'])

        kafka_consumer = FlinkKafkaConsumer(
            topics=list(KAFKA_TOPICS.values()),
            deserialization_schema=SimpleStringSchema(),
            properties={
                'bootstrap.servers': KAFKA_CONFIG['bootstrap_servers'],
                'group.id': KAFKA_CONFIG['group_id'],
            }
        )

        ds = env.add_source(kafka_consumer)

        def process_element(value):
            self._process_message('unknown', value)
            return value

        ds.map(process_element, output_type=Types.STRING())

        aggregate_thread = threading.Thread(target=self._aggregate_and_push, daemon=True)
        aggregate_thread.start()

        print("PyFlink作业已启动")
        env.execute("LiveStreamProcessing")

    def start(self):
        self._running = True
        target = self._run_pyflink if self.use_pyflink else self._run_pure_python
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        for consumer in self._consumers.values():
            try:
                consumer.close()
            except:
                pass
        if self._thread:
            self._thread.join(timeout=5)
        print("流处理作业已停止")

    def wait(self):
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


def main():
    job = StreamProcessingJob(use_pyflink=False)
    job.register_callback(lambda data: print(f"收到数据: {data['metrics']['current_online']}人在线"))
    job.start()
    job.wait()


if __name__ == '__main__':
    main()
