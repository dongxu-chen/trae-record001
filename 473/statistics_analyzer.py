import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import redis
from config import Config
from memory_defrag import DefragResult
from memory_analyzer import MemoryInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FragmentationTrend:
    node_id: str
    timestamps: List[str]
    fragmentation_ratios: List[float]
    used_memory_mb: List[float]
    rss_memory_mb: List[float]


class StatisticsAnalyzer:
    def __init__(self, storage_url: str = None):
        self.storage_url = storage_url or Config.STORAGE_REDIS_URL
        self._storage = None
        self._connect_storage()

    def _connect_storage(self):
        try:
            self._storage = redis.from_url(self.storage_url)
            self._storage.ping()
            logger.info("Connected to statistics storage Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to statistics storage: {e}")
            self._storage = None

    def _get_storage(self) -> Optional[redis.Redis]:
        if not self._storage:
            self._connect_storage()
        return self._storage

    def store_memory_snapshot(self, mem_info: MemoryInfo):
        storage = self._get_storage()
        if not storage:
            return

        key = f"mem_snapshot:{mem_info.node_id}:{int(datetime.now().timestamp())}"
        data = {
            'node_id': mem_info.node_id,
            'host': mem_info.host,
            'port': mem_info.port,
            'used_memory': mem_info.used_memory,
            'used_memory_rss': mem_info.used_memory_rss,
            'mem_fragmentation_ratio': mem_info.mem_fragmentation_ratio,
            'timestamp': mem_info.timestamp
        }
        
        storage.setex(
            key,
            timedelta(days=30),
            json.dumps(data)
        )
        
        index_key = f"mem_snapshot_index:{mem_info.node_id}"
        storage.zadd(index_key, {key: int(datetime.now().timestamp())})
        storage.zremrangebyrank(index_key, 0, -10000)

    def store_defrag_result(self, result: DefragResult):
        storage = self._get_storage()
        if not storage:
            return

        key = f"defrag_result:{result.node_id}:{int(datetime.now().timestamp())}"
        storage.setex(
            key,
            timedelta(days=90),
            json.dumps(result.to_dict())
        )
        
        index_key = "defrag_result_index"
        storage.zadd(index_key, {key: int(datetime.now().timestamp())})
        
        node_index_key = f"defrag_result_index:{result.node_id}"
        storage.zadd(node_index_key, {key: int(datetime.now().timestamp())})

    def get_memory_history(self, node_id: str, hours: int = 24) -> FragmentationTrend:
        storage = self._get_storage()
        timestamps = []
        ratios = []
        used_mems = []
        rss_mems = []

        if storage:
            end_ts = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
            
            index_key = f"mem_snapshot_index:{node_id}"
            keys = storage.zrangebyscore(index_key, start_ts, end_ts)
            
            for key in keys:
                data = storage.get(key)
                if data:
                    snapshot = json.loads(data)
                    timestamps.append(snapshot['timestamp'])
                    ratios.append(snapshot['mem_fragmentation_ratio'])
                    used_mems.append(snapshot['used_memory'] / (1024 * 1024))
                    rss_mems.append(snapshot['used_memory_rss'] / (1024 * 1024))

        return FragmentationTrend(
            node_id=node_id,
            timestamps=timestamps,
            fragmentation_ratios=ratios,
            used_memory_mb=used_mems,
            rss_memory_mb=rss_mems
        )

    def get_defrag_history(self, node_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        storage = self._get_storage()
        results = []

        if storage:
            index_key = f"defrag_result_index:{node_id}" if node_id else "defrag_result_index"
            keys = storage.zrevrange(index_key, 0, limit - 1)
            
            for key in keys:
                data = storage.get(key)
                if data:
                    results.append(json.loads(data))

        return results

    def calculate_fragmentation_statistics(self, node_id: str, hours: int = 24) -> Dict[str, Any]:
        trend = self.get_memory_history(node_id, hours)
        
        if not trend.fragmentation_ratios:
            return {}

        import numpy as np
        ratios = np.array(trend.fragmentation_ratios)
        
        return {
            'node_id': node_id,
            'data_points': len(ratios),
            'avg_fragmentation': float(np.mean(ratios)),
            'max_fragmentation': float(np.max(ratios)),
            'min_fragmentation': float(np.min(ratios)),
            'std_fragmentation': float(np.std(ratios)),
            'p95_fragmentation': float(np.percentile(ratios, 95)),
            'current_fragmentation': float(ratios[-1]) if len(ratios) > 0 else 0,
            'trend_direction': self._calculate_trend(ratios),
            'hours_analyzed': hours
        }

    def _calculate_trend(self, data: List[float]) -> str:
        if len(data) < 10:
            return "insufficient_data"
        
        first_half = data[:len(data)//2]
        second_half = data[len(data)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        diff = second_avg - first_avg
        if diff > 0.1:
            return "increasing"
        elif diff < -0.1:
            return "decreasing"
        else:
            return "stable"

    def get_cluster_statistics(self, node_ids: List[str], hours: int = 24) -> Dict[str, Any]:
        node_stats = []
        for node_id in node_ids:
            stats = self.calculate_fragmentation_statistics(node_id, hours)
            if stats:
                node_stats.append(stats)

        if not node_stats:
            return {}

        return {
            'node_count': len(node_stats),
            'avg_cluster_fragmentation': sum(s['avg_fragmentation'] for s in node_stats) / len(node_stats),
            'max_cluster_fragmentation': max(s['max_fragmentation'] for s in node_stats),
            'nodes_above_threshold': sum(1 for s in node_stats if s['current_fragmentation'] >= 1.5),
            'nodes_with_increasing_trend': sum(1 for s in node_stats if s['trend_direction'] == 'increasing'),
            'node_statistics': node_stats
        }

    def get_defrag_effectiveness(self, node_id: str = None, limit: int = 20) -> Dict[str, Any]:
        history = self.get_defrag_history(node_id, limit)
        
        if not history:
            return {}

        successful = [r for r in history if r['success']]
        
        if not successful:
            return {'total_defrags': len(history), 'successful_defrags': 0}

        avg_saved = sum(r['memory_saved_mb'] for r in successful) / len(successful)
        avg_improvement = sum(r['fragmentation_improvement'] for r in successful) / len(successful)
        
        return {
            'total_defrags': len(history),
            'successful_defrags': len(successful),
            'success_rate': len(successful) / len(history),
            'average_memory_saved_mb': avg_saved,
            'total_memory_saved_mb': sum(r['memory_saved_mb'] for r in successful),
            'average_fragmentation_improvement': avg_improvement,
            'average_duration_seconds': sum(r['duration_seconds'] for r in successful) / len(successful)
        }

    def generate_daily_report(self, node_ids: List[str]) -> Dict[str, Any]:
        cluster_stats = self.get_cluster_statistics(node_ids, 24)
        
        defrag_effectiveness = {}
        for node_id in node_ids:
            defrag_effectiveness[node_id] = self.get_defrag_effectiveness(node_id, 10)

        high_risk_nodes = [
            stats for stats in cluster_stats.get('node_statistics', [])
            if stats['current_fragmentation'] >= 1.5
        ]

        return {
            'report_date': datetime.now().isoformat(),
            'cluster_summary': cluster_stats,
            'defrag_effectiveness': defrag_effectiveness,
            'high_risk_nodes': high_risk_nodes,
            'recommendations': self._generate_recommendations(cluster_stats, high_risk_nodes)
        }

    def _generate_recommendations(self, cluster_stats: Dict[str, Any], 
                                   high_risk_nodes: List[Dict[str, Any]]) -> List[str]:
        recommendations = []
        
        if cluster_stats.get('nodes_above_threshold', 0) > 0:
            recommendations.append(
                f"Found {cluster_stats['nodes_above_threshold']} nodes with fragmentation >= 1.5, "
                "consider running memory defragmentation"
            )
        
        for node in high_risk_nodes:
            if node['trend_direction'] == 'increasing':
                recommendations.append(
                    f"Node {node['node_id']} has increasing fragmentation trend, "
                    "recommend immediate defragmentation"
                )
        
        if cluster_stats.get('avg_cluster_fragmentation', 0) > 1.3:
            recommendations.append(
                "Average cluster fragmentation is elevated, review memory allocation strategy"
            )
        
        if not recommendations:
            recommendations.append("All nodes have healthy fragmentation levels")
        
        return recommendations
