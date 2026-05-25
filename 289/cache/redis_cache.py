import json
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime
from config import Config


class RedisCache:
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        try:
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True
            )
            self.redis_client.ping()
            print("Redis连接成功")
        except Exception as e:
            print(f"Redis连接失败: {e}")
            self.redis_client = None
    
    def _execute(self, operation, *args, **kwargs):
        if self.redis_client is None:
            self._connect()
            if self.redis_client is None:
                return None
        
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            print(f"Redis操作失败: {e}")
            self._connect()
            return None
    
    def set_gps_data(self, bus_id: str, gps_data: Dict):
        key = f"gps:{bus_id}"
        data = json.dumps(gps_data)
        self._execute(self.redis_client.setex, key, 3600, data)
    
    def get_gps_data(self, bus_id: str) -> Optional[Dict]:
        key = f"gps:{bus_id}"
        data = self._execute(self.redis_client.get, key)
        return json.loads(data) if data else None
    
    def get_all_gps_data(self) -> List[Dict]:
        keys = self._execute(self.redis_client.keys, "gps:*")
        if not keys:
            return []
        
        data_list = []
        for key in keys:
            data = self._execute(self.redis_client.get, key)
            if data:
                data_list.append(json.loads(data))
        
        return data_list
    
    def set_prediction(self, bus_id: str, prediction: Dict):
        key = f"prediction:{bus_id}"
        data = json.dumps(prediction)
        self._execute(self.redis_client.setex, key, 300, data)
    
    def get_prediction(self, bus_id: str) -> Optional[Dict]:
        key = f"prediction:{bus_id}"
        data = self._execute(self.redis_client.get, key)
        return json.loads(data) if data else None
    
    def get_all_predictions(self) -> List[Dict]:
        keys = self._execute(self.redis_client.keys, "prediction:*")
        if not keys:
            return []
        
        predictions = []
        for key in keys:
            data = self._execute(self.redis_client.get, key)
            if data:
                predictions.append(json.loads(data))
        
        return predictions
    
    def add_delay_warning(self, warning: Dict):
        key = "delay_warnings"
        warning['timestamp'] = datetime.now().isoformat()
        self._execute(
            self.redis_client.zadd,
            key,
            {json.dumps(warning): datetime.now().timestamp()}
        )
        self._execute(self.redis_client.zremrangebyrank, key, 0, -101)
    
    def get_delay_warnings(self, limit: int = 20) -> List[Dict]:
        key = "delay_warnings"
        data = self._execute(self.redis_client.zrevrange, key, 0, limit - 1)
        return [json.loads(d) for d in data] if data else []
    
    def add_station_history(self, history: Dict):
        key = f"history:{history['route_id']}:{history['station_id']}"
        self._execute(
            self.redis_client.lpush,
            key,
            json.dumps(history)
        )
        self._execute(self.redis_client.ltrim, key, 0, 999)
    
    def get_station_history(self, route_id: str, station_id: str, limit: int = 100) -> List[Dict]:
        key = f"history:{route_id}:{station_id}"
        data = self._execute(self.redis_client.lrange, key, 0, limit - 1)
        return [json.loads(d) for d in data] if data else []
    
    def set_traffic_data(self, route_id: str, traffic_data: List[Dict]):
        key = f"traffic:{route_id}"
        data = json.dumps({
            'data': traffic_data,
            'timestamp': datetime.now().isoformat()
        })
        self._execute(self.redis_client.setex, key, 300, data)
    
    def get_traffic_data(self, route_id: str) -> Optional[Dict]:
        key = f"traffic:{route_id}"
        data = self._execute(self.redis_client.get, key)
        return json.loads(data) if data else None
    
    def set_punctuality_stats(self, stats: Dict):
        key = "punctuality:stats"
        self._execute(self.redis_client.setex, key, 3600, json.dumps(stats))
    
    def get_punctuality_stats(self) -> Optional[Dict]:
        key = "punctuality:stats"
        data = self._execute(self.redis_client.get, key)
        return json.loads(data) if data else None
    
    def set_bus_state(self, bus_id: str, state: Dict):
        key = f"state:{bus_id}"
        self._execute(self.redis_client.setex, key, 60, json.dumps(state))
    
    def get_bus_state(self, bus_id: str) -> Optional[Dict]:
        key = f"state:{bus_id}"
        data = self._execute(self.redis_client.get, key)
        return json.loads(data) if data else None
    
    def get_all_bus_states(self) -> List[Dict]:
        keys = self._execute(self.redis_client.keys, "state:*")
        if not keys:
            return []
        
        states = []
        for key in keys:
            data = self._execute(self.redis_client.get, key)
            if data:
                states.append(json.loads(data))
        
        return states
    
    def publish_update(self, channel: str, data: Dict):
        message = json.dumps(data)
        self._execute(self.redis_client.publish, channel, message)
    
    def clear_cache(self):
        self._execute(self.redis_client.flushdb)
