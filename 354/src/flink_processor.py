import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import yaml

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.datastream.functions import MapFunction, KeyedProcessFunction, RuntimeContext
    from pyflink.datastream.window import TumblingProcessingTimeWindows, SlidingProcessingTimeWindows
    from pyflink.common.time import Time
    from pyflink.common.typeinfo import Types
    PYLINDA_AVAILABLE = True
except ImportError:
    PYLINDA_AVAILABLE = False
    print("警告: PyFlink 未安装，Flink功能将不可用")


class ClickFraudProcessFunction:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.rules_config = self.config['rules']
        self.ip_click_history: Dict[str, List[float]] = {}
        self.device_click_history: Dict[str, List[float]] = {}

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def process_click(self, click_data: Dict) -> Dict:
        ip = click_data.get('ip', '')
        device_id = click_data.get('device_id', '')
        timestamp = click_data.get('timestamp', time.time())
        
        fraud_score = 0.0
        reasons = []
        rule_scores = {}

        self._update_history(ip, device_id, timestamp)
        
        high_freq_score = self._check_high_frequency(ip, device_id)
        if high_freq_score > 0:
            fraud_score += high_freq_score * 0.3
            rule_scores['high_frequency'] = high_freq_score
            reasons.append("高频点击")
        
        interval_score = self._check_fixed_intervals(ip, device_id)
        if interval_score > 0:
            fraud_score += interval_score * 0.3
            rule_scores['fixed_interval'] = interval_score
            reasons.append("固定间隔点击")
        
        ua_score = self._check_user_agent(click_data.get('user_agent', ''))
        if ua_score > 0:
            fraud_score += ua_score * 0.25
            rule_scores['user_agent'] = ua_score
            reasons.append("可疑User-Agent")
        
        fraud_score = min(1.0, fraud_score)
        is_fraud = fraud_score >= self.config['output'].get('fraud_threshold', 0.7)

        return {
            'click_id': click_data.get('click_id', ''),
            'fraud_score': fraud_score,
            'is_fraud': is_fraud,
            'reasons': reasons,
            'rule_scores': rule_scores,
            'timestamp': timestamp,
            'ip': ip,
            'device_id': device_id,
            'publisher_id': click_data.get('publisher_id', '')
        }

    def _update_history(self, ip: str, device_id: str, timestamp: float):
        if ip not in self.ip_click_history:
            self.ip_click_history[ip] = []
        self.ip_click_history[ip].append(timestamp)
        if len(self.ip_click_history[ip]) > 100:
            self.ip_click_history[ip] = self.ip_click_history[ip][-100:]
        
        if device_id not in self.device_click_history:
            self.device_click_history[device_id] = []
        self.device_click_history[device_id].append(timestamp)
        if len(self.device_click_history[device_id]) > 100:
            self.device_click_history[device_id] = self.device_click_history[device_id][-100:]

    def _check_high_frequency(self, ip: str, device_id: str) -> float:
        current_time = time.time()
        window_60s = current_time - 60
        
        ip_clicks_60s = len([t for t in self.ip_click_history.get(ip, []) if t >= window_60s])
        device_clicks_60s = len([t for t in self.device_click_history.get(device_id, []) if t >= window_60s])
        
        max_ip_clicks = self.rules_config['high_frequency']['max_clicks_per_ip']
        max_device_clicks = self.rules_config['high_frequency']['max_clicks_per_device']
        
        score = 0.0
        if ip_clicks_60s > max_ip_clicks:
            score = max(score, min(1.0, ip_clicks_60s / (max_ip_clicks * 2)))
        if device_clicks_60s > max_device_clicks:
            score = max(score, min(1.0, device_clicks_60s / (max_device_clicks * 2)))
        
        return score

    def _check_fixed_intervals(self, ip: str, device_id: str) -> float:
        history = self.ip_click_history.get(ip, [])
        if len(history) < 5:
            return 0.0
        
        recent = history[-10:]
        intervals = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        
        if not intervals:
            return 0.0
        
        import statistics
        mean_interval = statistics.mean(intervals)
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
        
        tolerance = self.rules_config['fixed_interval']['tolerance_seconds']
        if std_interval < tolerance and mean_interval > 0:
            cv = std_interval / mean_interval
            return min(1.0, 1.0 - cv * 2)
        
        return 0.0

    def _check_user_agent(self, user_agent: str) -> float:
        ua_lower = user_agent.lower()
        suspicious_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'phantomjs', 'headless']
        
        if any(pattern in ua_lower for pattern in suspicious_patterns):
            return 0.9
        if len(user_agent.strip()) < 10:
            return 0.5
        
        return 0.0


class FlinkFraudDetector:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.env: Optional[StreamExecutionEnvironment] = None
        self.processor = ClickFraudProcessFunction(config_path)

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def setup_environment(self):
        if not PYLINDA_AVAILABLE:
            raise ImportError("PyFlink 未安装，请安装 pyflink 包")
        
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_parallelism(self.config['flink'].get('parallelism', 2))
        checkpoint_interval = self.config['flink'].get('checkpoint_interval', 60000)
        self.env.enable_checkpointing(checkpoint_interval)
        
        return self.env

    def process_from_collection(self, click_data_list: List[Dict]) -> List[Dict]:
        results = []
        for click_data in click_data_list:
            result = self.processor.process_click(click_data)
            results.append(result)
        return results

    def process_stream_from_kafka(self, kafka_bootstrap_servers: str, topic: str, output_callback=None):
        if not PYLINDA_AVAILABLE:
            print("PyFlink 不可用，使用模拟模式...")
            return self._simulate_kafka_processing(kafka_bootstrap_servers, topic, output_callback)
        
        env = self.setup_environment()
        
        try:
            from pyflink.datastream.connectors import FlinkKafkaConsumer
            from pyflink.common.serialization import SimpleStringSchema
            
            kafka_props = {
                'bootstrap.servers': kafka_bootstrap_servers,
                'group.id': self.config['kafka']['consumer_group_id']
            }
            
            kafka_consumer = FlinkKafkaConsumer(
                topic,
                SimpleStringSchema(),
                kafka_props
            )
            
            stream = env.add_source(kafka_consumer)
            
            def parse_json(json_str: str) -> Dict:
                try:
                    return json.loads(json_str)
                except:
                    return {}
            
            parsed_stream = stream.map(parse_json, output_type=Types.MAP(Types.STRING(), Types.STRING()))
            
            fraud_stream = parsed_stream.map(
                self.processor.process_click,
                output_type=Types.MAP(Types.STRING(), Types.STRING())
            )
            
            if output_callback:
                fraud_stream.map(output_callback, output_type=Types.VOID())
            
            job_name = self.config['flink'].get('job_name', 'ClickFraudDetection')
            env.execute(job_name)
        except Exception as e:
            print(f"Flink 执行错误: {e}")
            raise

    def _simulate_kafka_processing(self, kafka_bootstrap_servers: str, topic: str, output_callback=None):
        print(f"模拟Flink处理 - 连接Kafka: {kafka_bootstrap_servers}, Topic: {topic}")
        print("按 Ctrl+C 停止处理...")
        
        try:
            while True:
                mock_click = self._generate_mock_click()
                result = self.processor.process_click(mock_click)
                if output_callback:
                    output_callback(result)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("模拟处理已停止")

    def _generate_mock_click(self) -> Dict:
        import random
        return {
            'click_id': f"click_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            'timestamp': time.time(),
            'ip': f"192.168.{random.randint(0, 255)}.{random.randint(0, 255)}",
            'device_id': f"device_{random.randint(1, 100)}",
            'user_agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
                'curl/7.68.0'
            ]),
            'publisher_id': f"pub_{random.randint(1, 10)}",
            'campaign_id': f"camp_{random.randint(1, 5)}",
            'ad_id': f"ad_{random.randint(1, 20)}",
            'referrer': f"https://example{random.randint(1, 10)}.com"
        }
