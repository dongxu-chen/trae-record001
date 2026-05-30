import redis
from rediscluster import RedisCluster
from config import Config
from typing import Union, List, Dict, Any


class RedisConnectionManager:
    def __init__(self):
        self.mode = Config.REDIS_MODE
        self._connections = {}
        self._cluster_connection = None

    def get_connection(self, node_id: str = None) -> Union[redis.Redis, RedisCluster]:
        if self.mode == 'cluster':
            return self._get_cluster_connection()
        else:
            return self._get_standalone_connection()

    def _get_standalone_connection(self) -> redis.Redis:
        if 'standalone' not in self._connections:
            self._connections['standalone'] = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                password=Config.REDIS_PASSWORD,
                db=Config.REDIS_DB,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
        return self._connections['standalone']

    def _get_cluster_connection(self) -> RedisCluster:
        if not self._cluster_connection:
            startup_nodes = []
            for node in Config.REDIS_CLUSTER_NODES:
                host, port = node.split(':')
                startup_nodes.append({'host': host.strip(), 'port': int(port.strip())})
            
            self._cluster_connection = RedisCluster(
                startup_nodes=startup_nodes,
                password=Config.REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                skip_full_coverage_check=True
            )
        return self._cluster_connection

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        if self.mode == 'cluster':
            cluster = self._get_cluster_connection()
            for node_id, node_info in cluster.cluster_nodes().items():
                if 'master' in node_info['flags']:
                    host = node_info['host']
                    port = node_info['port']
                    nodes.append({
                        'id': node_id,
                        'host': host,
                        'port': port,
                        'connection': redis.Redis(
                            host=host,
                            port=port,
                            password=Config.REDIS_PASSWORD,
                            decode_responses=True,
                            socket_timeout=5,
                            socket_connect_timeout=5
                        )
                    })
        else:
            nodes.append({
                'id': 'standalone',
                'host': Config.REDIS_HOST,
                'port': Config.REDIS_PORT,
                'connection': self._get_standalone_connection()
            })
        return nodes

    def close_all(self):
        for conn in self._connections.values():
            conn.close()
        if self._cluster_connection:
            self._cluster_connection.close()
