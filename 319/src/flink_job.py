import json
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

try:
    from pyflink.common import Types, Row, Time
    from pyflink.common.serialization import SimpleStringSchema
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.datastream.connectors.kafka import (
        FlinkKafkaConsumer,
        FlinkKafkaProducer,
        KafkaRecordSerializationSchema,
    )
    from pyflink.datastream.window import TumblingProcessingTimeWindows
    from pyflink.common.typeinfo import Types
    PYFLINK_AVAILABLE = True
except ImportError:
    PYFLINK_AVAILABLE = False
    print("PyFlink not available, running in simulation mode")

from config import config


class FlinkRTBJob:
    def __init__(self):
        self.config = config
        self.kafka_config = config.kafka
        if PYFLINK_AVAILABLE:
            self.env = StreamExecutionEnvironment.get_execution_environment()
            self.env.set_parallelism(4)
            self.env.enable_checkpointing(60000)

    def _create_kafka_consumer(self, topic: str, group_id: str):
        if not PYFLINK_AVAILABLE:
            return None
        consumer_props = {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "latest",
        }
        return FlinkKafkaConsumer(
            topic,
            SimpleStringSchema(),
            consumer_props,
        )

    def _create_kafka_producer(self, topic: str):
        if not PYFLINK_AVAILABLE:
            return None
        producer_props = {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "transaction.timeout.ms": "3600000",
        }
        return FlinkKafkaProducer(
            topic,
            KafkaRecordSerializationSchema.builder()
            .set_topic(topic)
            .set_value_serialization_schema(SimpleStringSchema())
            .build(),
            producer_props,
            FlinkKafkaProducer.Semantic.AT_LEAST_ONCE,
        )

    def run_bid_analytics_job(self):
        if not PYFLINK_AVAILABLE:
            print("PyFlink not available, cannot run Flink job")
            return

        bid_requests_stream = self.env.add_source(
            self._create_kafka_consumer(
                self.kafka_config.bid_request_topic, "bid_analytics_group"
            )
        )

        bid_responses_stream = self.env.add_source(
            self._create_kafka_consumer(
                self.kafka_config.bid_response_topic, "bid_analytics_group"
            )
        )

        impressions_stream = self.env.add_source(
            self._create_kafka_consumer(
                self.kafka_config.impression_topic, "bid_analytics_group"
            )
        )

        clicks_stream = self.env.add_source(
            self._create_kafka_consumer(
                self.kafka_config.click_topic, "bid_analytics_group"
            )
        )

        conversions_stream = self.env.add_source(
            self._create_kafka_consumer(
                self.kafka_config.conversion_topic, "bid_analytics_group"
            )
        )

        def parse_json(value):
            try:
                return json.loads(value)
            except:
                return None

        parsed_bid_requests = bid_requests_stream.map(parse_json).filter(lambda x: x is not None)
        parsed_bid_responses = bid_responses_stream.map(parse_json).filter(lambda x: x is not None)
        parsed_impressions = impressions_stream.map(parse_json).filter(lambda x: x is not None)
        parsed_clicks = clicks_stream.map(parse_json).filter(lambda x: x is not None)
        parsed_conversions = conversions_stream.map(parse_json).filter(lambda x: x is not None)

        def map_to_bid_count(data):
            return Row(
                data.get("campaign_id", "default"),
                1,
                1 if data.get("success", False) else 0,
                float(data.get("bid_price", 0.0)),
            )

        bid_agg_stream = parsed_bid_responses.map(map_to_bid_count)

        def map_to_event_count(data, event_type):
            return Row(
                data.get("campaign_id", "default"),
                event_type,
                1,
            )

        impression_agg = parsed_impressions.map(lambda x: map_to_event_count(x, "impression"))
        click_agg = parsed_clicks.map(lambda x: map_to_event_count(x, "click"))
        conversion_agg = parsed_conversions.map(lambda x: map_to_event_count(x, "conversion"))

        def aggregate_bids(iterator):
            total_bids = 0
            successful_bids = 0
            total_spend = 0.0
            campaign_id = None
            for row in iterator:
                campaign_id = row[0]
                total_bids += row[1]
                successful_bids += row[2]
                total_spend += row[3]
            win_rate = successful_bids / total_bids if total_bids > 0 else 0.0
            avg_bid = total_spend / successful_bids if successful_bids > 0 else 0.0
            yield Row(
                campaign_id,
                "bid_stats",
                total_bids,
                successful_bids,
                win_rate,
                total_spend,
                avg_bid,
                int(time.time() * 1000),
            )

        bid_windowed = bid_agg_stream.key_by(lambda x: x[0]).window(
            TumblingProcessingTimeWindows.of(Time.minutes(1))
        ).apply(aggregate_bids)

        def aggregate_events(iterator):
            counts = {"impression": 0, "click": 0, "conversion": 0}
            campaign_id = None
            for row in iterator:
                campaign_id = row[0]
                event_type = row[1]
                counts[event_type] += row[2]
            ctr = counts["click"] / counts["impression"] if counts["impression"] > 0 else 0.0
            cvr = counts["conversion"] / counts["click"] if counts["click"] > 0 else 0.0
            yield Row(
                campaign_id,
                "event_stats",
                counts["impression"],
                counts["click"],
                counts["conversion"],
                ctr,
                cvr,
                int(time.time() * 1000),
            )

        event_stream = impression_agg.union(click_agg, conversion_agg)
        event_windowed = event_stream.key_by(lambda x: x[0]).window(
            TumblingProcessingTimeWindows.of(Time.minutes(1))
        ).apply(aggregate_events)

        def to_json(row):
            data = {}
            for i, field in enumerate(row):
                data[f"field_{i}"] = field
            return json.dumps(data)

        bid_windowed.map(to_json).add_sink(
            self._create_kafka_producer("bid_analytics_result")
        )
        event_windowed.map(to_json).add_sink(
            self._create_kafka_producer("event_analytics_result")
        )

        print("Starting Flink RTB Analytics Job...")
        self.env.execute("RTB Real-time Analytics")

    def run_budget_pace_control_job(self):
        if not PYFLINK_AVAILABLE:
            print("PyFlink not available, cannot run Flink job")
            return

        bid_responses_stream = self.env.add_source(
            self._create_kafka_consumer(
                self.kafka_config.bid_response_topic, "budget_pace_group"
            )
        )

        def parse_and_extract(value):
            try:
                data = json.loads(value)
                if data.get("success", False):
                    return Row(
                        data.get("campaign_id", "default"),
                        float(data.get("bid_price", 0.0)),
                        int(time.time() * 1000),
                    )
                return None
            except:
                return None

        spend_stream = bid_responses_stream.map(parse_and_extract).filter(lambda x: x is not None)

        def aggregate_spend(iterator):
            total_spend = 0.0
            count = 0
            campaign_id = None
            for row in iterator:
                campaign_id = row[0]
                total_spend += row[1]
                count += 1
            current_hour = datetime.now().hour
            hour_progress = current_hour / 24.0
            daily_budget = config.budget.daily_budget
            target_spend = daily_budget * hour_progress
            pace = total_spend / target_spend if target_spend > 0 else 1.0
            pace_factor = max(0.5, min(1.5, 1.0 / pace)) if pace > 0 else 1.0
            yield Row(
                campaign_id,
                total_spend,
                count,
                target_spend,
                pace,
                pace_factor,
                int(time.time() * 1000),
            )

        pace_windowed = spend_stream.key_by(lambda x: x[0]).window(
            TumblingProcessingTimeWindows.of(Time.seconds(30))
        ).apply(aggregate_spend)

        def update_redis_pace(row):
            try:
                from src.redis_client import RedisClient
                redis_client = RedisClient()
                campaign_id = row[0]
                pace_factor = row[5]
                redis_client.update_pace(campaign_id, pace_factor)
                print(f"Updated pace for {campaign_id}: {pace_factor}")
            except Exception as e:
                print(f"Error updating pace: {e}")
            return row

        pace_windowed.map(update_redis_pace).print()

        print("Starting Flink Budget Pace Control Job...")
        self.env.execute("Budget Pace Control")

    def run_frequency_monitoring_job(self):
        if not PYFLINK_AVAILABLE:
            print("PyFlink not available, cannot run Flink job")
            return

        impressions_stream = self.env.add_source(
            self._create_kafka_consumer(
                self.kafka_config.impression_topic, "frequency_monitor_group"
            )
        )

        def parse_impression(value):
            try:
                data = json.loads(value)
                return Row(
                    data.get("user_id", ""),
                    data.get("ad_id", ""),
                    data.get("campaign_id", "default"),
                    int(time.time() * 1000),
                )
            except:
                return None

        parsed_stream = impressions_stream.map(parse_impression).filter(lambda x: x is not None)

        def count_user_ad(iterator):
            count = 0
            user_id = None
            ad_id = None
            campaign_id = None
            for row in iterator:
                user_id = row[0]
                ad_id = row[1]
                campaign_id = row[2]
                count += 1
            yield Row(user_id, ad_id, campaign_id, count, int(time.time() * 1000))

        frequency_windowed = parsed_stream.key_by(lambda x: (x[0], x[1])).window(
            TumblingProcessingTimeWindows.of(Time.hours(1))
        ).apply(count_user_ad)

        def alert_high_frequency(row):
            user_id, ad_id, campaign_id, count, timestamp = row
            if count >= config.frequency.limits.get("1h", (3, 3600))[0]:
                try:
                    from src.redis_client import RedisClient
                    redis_client = RedisClient()
                    redis_client.setex(f"freq_alert:{user_id}:{ad_id}", 3600, count)
                    print(f"Frequency alert: User {user_id}, Ad {ad_id}, Count {count}")
                except Exception as e:
                    print(f"Error setting frequency alert: {e}")
            return row

        frequency_windowed.map(alert_high_frequency).print()

        print("Starting Flink Frequency Monitoring Job...")
        self.env.execute("Frequency Monitoring")

    def run_all_jobs(self):
        print("Starting all Flink jobs...")
        self.run_bid_analytics_job()


class SimulatedFlinkJob:
    def __init__(self):
        self.running = False
        from src.redis_client import RedisClient
        self.redis_client = RedisClient()

    def simulate_realtime_analytics(self, interval: int = 60):
        self.running = True
        print("Starting simulated Flink realtime analytics...")
        while self.running:
            try:
                from src.bid_engine import BidEngine
                engine = BidEngine()
                status = engine.get_engine_status()
                print(f"\n=== Realtime Analytics at {datetime.now()} ===")
                print(json.dumps(status, indent=2, default=str))
                time.sleep(interval)
            except KeyboardInterrupt:
                print("Stopping simulated analytics...")
                self.running = False
                break
            except Exception as e:
                print(f"Error in simulated analytics: {e}")
                time.sleep(interval)

    def stop(self):
        self.running = False
