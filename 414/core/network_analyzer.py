import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from core.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.redis = redis_manager or RedisManager()
        self._ip_users: Dict[str, Set[str]] = defaultdict(set)
        self._device_users: Dict[str, Set[str]] = defaultdict(set)
        self._merchant_users: Dict[str, Set[str]] = defaultdict(set)
        self._user_connections: Dict[str, Set[str]] = defaultdict(set)
        self._fraud_rings: List[Set[str]] = []
        self._last_analysis = 0

    def record_transaction(self, transaction: Dict):
        customer_id = transaction.get("customer_id", "")
        ip = transaction.get("ip_address", "")
        device = transaction.get("device_type", "")
        merchant_id = transaction.get("merchant_id", "")
        if not customer_id:
            return
        if ip:
            self._ip_users[ip].add(customer_id)
        if device:
            self._device_users[device].add(customer_id)
        if merchant_id:
            self._merchant_users[merchant_id].add(customer_id)
        self._update_connections(customer_id, ip, device, merchant_id)

    def _update_connections(self, customer_id: str, ip: str, device: str, merchant_id: str):
        connected_users: Set[str] = set()
        if ip and ip in self._ip_users:
            connected_users.update(self._ip_users[ip] - {customer_id})
        if device and device in self._device_users:
            connected_users.update(self._device_users[device] - {customer_id})
        if merchant_id and merchant_id in self._merchant_users:
            connected_users.update(self._merchant_users[merchant_id] - {customer_id})
        if connected_users:
            self._user_connections[customer_id].update(connected_users)
            for uid in connected_users:
                self._user_connections[uid].add(customer_id)

    def analyze_network(self) -> Dict:
        logger.info("Analyzing fraud network...")
        self._fraud_rings = []
        visited: Set[str] = set()
        for user_id in self._user_connections:
            if user_id not in visited:
                ring = self._find_connected_ring(user_id, visited)
                if len(ring) >= 2:
                    self._fraud_rings.append(ring)
        self._last_analysis = time.time()
        return {
            "total_users_tracked": len(self._user_connections),
            "total_connections": sum(len(v) for v in self._user_connections.values()) // 2,
            "potential_fraud_rings": len(self._fraud_rings),
            "rings_detail": [list(ring) for ring in self._fraud_rings[:10]],
            "analysis_timestamp": self._last_analysis,
        }

    def _find_connected_ring(self, start_user: str, visited: Set[str]) -> Set[str]:
        ring: Set[str] = set()
        stack = [start_user]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            ring.add(current)
            for neighbor in self._user_connections.get(current, set()):
                if neighbor not in visited:
                    stack.append(neighbor)
        return ring

    def check_related_to_fraud(self, customer_id: str) -> Dict:
        related_users = self._user_connections.get(customer_id, set())
        fraud_related_rings = []
        for ring in self._fraud_rings:
            if customer_id in ring:
                fraud_related_rings.append(list(ring))
        return {
            "customer_id": customer_id,
            "related_users_count": len(related_users),
            "related_users": list(related_users)[:20],
            "fraud_ring_membership": fraud_related_rings,
            "is_in_fraud_ring": len(fraud_related_rings) > 0,
            "risk_multiplier": 1.0 + len(fraud_related_rings) * 0.3 + min(len(related_users), 10) * 0.05,
        }

    def get_shared_entities(self, customer_id: str) -> Dict:
        shared_ips = set()
        shared_devices = set()
        shared_merchants = set()
        for ip, users in self._ip_users.items():
            if customer_id in users:
                shared_ips.add(ip)
        for device, users in self._device_users.items():
            if customer_id in users:
                shared_devices.add(device)
        for merchant, users in self._merchant_users.items():
            if customer_id in users:
                shared_merchants.add(merchant)
        return {
            "customer_id": customer_id,
            "shared_ips": list(shared_ips),
            "shared_devices": list(shared_devices),
            "shared_merchants": list(shared_merchants)[:20],
            "total_shared_entities": len(shared_ips) + len(shared_devices) + len(shared_merchants),
        }

    def compute_ring_risk_score(self, customer_id: str) -> float:
        network_info = self.check_related_to_fraud(customer_id)
        base_score = 0.0
        if network_info["is_in_fraud_ring"]:
            base_score += 0.3
        base_score += min(network_info["related_users_count"] * 0.02, 0.2)
        shared = self.get_shared_entities(customer_id)
        base_score += min(shared["total_shared_entities"] * 0.01, 0.1)
        return min(base_score, 0.5)

    def get_network_stats(self) -> Dict:
        return {
            "total_unique_ips": len(self._ip_users),
            "total_unique_devices": len(self._device_users),
            "total_unique_merchants": len(self._merchant_users),
            "total_users_with_connections": len(self._user_connections),
            "total_connections": sum(len(v) for v in self._user_connections.values()) // 2,
            "potential_fraud_rings": len(self._fraud_rings),
            "last_analysis": self._last_analysis,
        }
