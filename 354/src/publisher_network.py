import time
import numpy as np
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
import yaml
import json


@dataclass
class PublisherNode:
    publisher_id: str
    fraud_rate: float = 0.0
    total_clicks: int = 0
    fraud_clicks: int = 0
    shared_ips: Set[str] = field(default_factory=set)
    shared_devices: Set[str] = field(default_factory=set)
    shared_sessions: Set[str] = field(default_factory=set)
    neighbors: Set[str] = field(default_factory=set)
    risk_score: float = 0.0
    community_id: int = -1
    is_suspicious: bool = False


@dataclass
class CommunityGroup:
    community_id: int
    members: List[str]
    avg_fraud_rate: float
    total_clicks: int
    risk_level: str
    is_collusive: bool


class PublisherNetworkAnalyzer:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.publishers: Dict[str, PublisherNode] = {}
        self.ip_to_publishers: Dict[str, Set[str]] = defaultdict(set)
        self.device_to_publishers: Dict[str, Set[str]] = defaultdict(set)
        self.session_to_publishers: Dict[str, Set[str]] = defaultdict(set)
        self.communities: List[CommunityGroup] = []
        self.community_detected = False
        
        self.edge_weights: Dict[Tuple[str, str], Dict] = {}
        
        self.min_shared_ips = self.config.get('network_analysis', {}).get('min_shared_ips', 5)
        self.min_shared_devices = self.config.get('network_analysis', {}).get('min_shared_devices', 3)
        self.collusion_threshold = self.config.get('network_analysis', {}).get('collusion_threshold', 0.7)
        self.suspicious_fraud_rate = self.config.get('network_analysis', {}).get('suspicious_fraud_rate', 0.3)

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if 'network_analysis' not in config:
                config['network_analysis'] = {
                    'min_shared_ips': 5,
                    'min_shared_devices': 3,
                    'collusion_threshold': 0.7,
                    'suspicious_fraud_rate': 0.3
                }
            return config

    def record_click(self, publisher_id: str, ip: str, device_id: str, 
                     session_id: str = None, is_fraud: bool = False):
        if publisher_id not in self.publishers:
            self.publishers[publisher_id] = PublisherNode(publisher_id=publisher_id)
        
        node = self.publishers[publisher_id]
        node.total_clicks += 1
        if is_fraud:
            node.fraud_clicks += 1
        node.fraud_rate = node.fraud_clicks / max(1, node.total_clicks)
        
        self.ip_to_publishers[ip].add(publisher_id)
        self.device_to_publishers[device_id].add(publisher_id)
        if session_id:
            self.session_to_publishers[session_id].add(publisher_id)
        
        node.shared_ips.add(ip)
        node.shared_devices.add(device_id)
        if session_id:
            node.shared_sessions.add(session_id)
        
        self.community_detected = False

    def build_network(self):
        for publishers in self.ip_to_publishers.values():
            if len(publishers) >= 2:
                pub_list = list(publishers)
                for i in range(len(pub_list)):
                    for j in range(i + 1, len(pub_list)):
                        self._add_edge(pub_list[i], pub_list[j], 'ip')
        
        for publishers in self.device_to_publishers.values():
            if len(publishers) >= 2:
                pub_list = list(publishers)
                for i in range(len(pub_list)):
                    for j in range(i + 1, len(pub_list)):
                        self._add_edge(pub_list[i], pub_list[j], 'device')
        
        for publishers in self.session_to_publishers.values():
            if len(publishers) >= 2:
                pub_list = list(publishers)
                for i in range(len(pub_list)):
                    for j in range(i + 1, len(pub_list)):
                        self._add_edge(pub_list[i], pub_list[j], 'session')
        
        self._update_edge_weights()
        self._update_risk_scores()

    def _add_edge(self, pub1: str, pub2: str, edge_type: str):
        if pub1 == pub2:
            return
        
        key = tuple(sorted([pub1, pub2]))
        if key not in self.edge_weights:
            self.edge_weights[key] = {'ip': 0, 'device': 0, 'session': 0}
        
        self.edge_weights[key][edge_type] += 1
        
        if pub1 in self.publishers:
            self.publishers[pub1].neighbors.add(pub2)
        if pub2 in self.publishers:
            self.publishers[pub2].neighbors.add(pub1)

    def _update_edge_weights(self):
        for (pub1, pub2), counts in self.edge_weights.items():
            ip_count = counts['ip']
            device_count = counts['device']
            session_count = counts['session']
            
            weight = 0
            if ip_count >= self.min_shared_ips:
                weight += 0.5 * min(1.0, ip_count / 20)
            if device_count >= self.min_shared_devices:
                weight += 0.35 * min(1.0, device_count / 10)
            if session_count > 0:
                weight += 0.15 * min(1.0, session_count / 5)
            
            counts['weight'] = weight

    def _update_risk_scores(self):
        for pub_id, node in self.publishers.items():
            base_risk = node.fraud_rate
            
            neighbor_risk = 0
            if node.neighbors:
                neighbor_risks = [
                    self.publishers[n].fraud_rate 
                    for n in node.neighbors 
                    if n in self.publishers
                ]
                if neighbor_risks:
                    neighbor_risk = np.mean(neighbor_risks)
            
            edge_risk = 0
            for neighbor in node.neighbors:
                key = tuple(sorted([pub_id, neighbor]))
                if key in self.edge_weights:
                    edge_weight = self.edge_weights[key].get('weight', 0)
                    if edge_weight > 0.3:
                        neighbor_fraud = self.publishers.get(neighbor, PublisherNode('')).fraud_rate
                        edge_risk += edge_weight * neighbor_fraud
            
            if node.neighbors:
                edge_risk /= len(node.neighbors)
            
            node.risk_score = 0.5 * base_risk + 0.3 * neighbor_risk + 0.2 * edge_risk
            node.is_suspicious = (node.fraud_rate > self.suspicious_fraud_rate or 
                                 node.risk_score > self.suspicious_fraud_rate)

    def detect_communities(self):
        self.build_network()
        
        visited = set()
        community_id = 0
        
        for pub_id in self.publishers:
            if pub_id not in visited:
                community = self._bfs_community(pub_id, visited)
                if len(community) >= 2:
                    self._process_community(community_id, community)
                    community_id += 1
        
        self.community_detected = True
        return self.communities

    def _bfs_community(self, start: str, visited: Set[str]) -> List[str]:
        community = []
        queue = deque([start])
        visited.add(start)
        
        while queue:
            current = queue.popleft()
            community.append(current)
            
            if current in self.publishers:
                for neighbor in self.publishers[current].neighbors:
                    if neighbor not in visited:
                        key = tuple(sorted([current, neighbor]))
                        if key in self.edge_weights:
                            weight = self.edge_weights[key].get('weight', 0)
                            if weight > 0.2:
                                visited.add(neighbor)
                                queue.append(neighbor)
        
        return community

    def _process_community(self, community_id: int, members: List[str]):
        fraud_rates = []
        total_clicks = 0
        suspicious_count = 0
        
        for pub_id in members:
            if pub_id in self.publishers:
                node = self.publishers[pub_id]
                node.community_id = community_id
                fraud_rates.append(node.fraud_rate)
                total_clicks += node.total_clicks
                if node.is_suspicious:
                    suspicious_count += 1
        
        avg_fraud_rate = np.mean(fraud_rates) if fraud_rates else 0
        
        suspicious_ratio = suspicious_count / len(members) if members else 0
        is_collusive = (avg_fraud_rate > self.collusion_threshold or 
                       suspicious_ratio > self.collusion_threshold)
        
        if is_collusive:
            risk_level = "高风险"
        elif avg_fraud_rate > 0.3:
            risk_level = "中风险"
        else:
            risk_level = "低风险"
        
        community = CommunityGroup(
            community_id=community_id,
            members=members,
            avg_fraud_rate=avg_fraud_rate,
            total_clicks=total_clicks,
            risk_level=risk_level,
            is_collusive=is_collusive
        )
        self.communities.append(community)

    def get_suspicious_communities(self) -> List[CommunityGroup]:
        if not self.community_detected:
            self.detect_communities()
        return [c for c in self.communities if c.is_collusive]

    def get_publisher_connections(self, publisher_id: str) -> Dict[str, Any]:
        if publisher_id not in self.publishers:
            return {}
        
        node = self.publishers[publisher_id]
        connections = []
        
        for neighbor in node.neighbors:
            key = tuple(sorted([publisher_id, neighbor]))
            if key in self.edge_weights:
                connections.append({
                    'publisher_id': neighbor,
                    'shared_ips': self.edge_weights[key]['ip'],
                    'shared_devices': self.edge_weights[key]['device'],
                    'shared_sessions': self.edge_weights[key]['session'],
                    'connection_strength': self.edge_weights[key].get('weight', 0),
                    'neighbor_fraud_rate': self.publishers.get(neighbor, PublisherNode('')).fraud_rate
                })
        
        connections.sort(key=lambda x: x['connection_strength'], reverse=True)
        
        return {
            'publisher_id': publisher_id,
            'fraud_rate': node.fraud_rate,
            'risk_score': node.risk_score,
            'is_suspicious': node.is_suspicious,
            'community_id': node.community_id,
            'connection_count': len(connections),
            'connections': connections[:20]
        }

    def get_network_statistics(self) -> Dict[str, Any]:
        if not self.community_detected:
            self.detect_communities()
        
        total_publishers = len(self.publishers)
        suspicious_publishers = sum(1 for n in self.publishers.values() if n.is_suspicious)
        collusive_communities = sum(1 for c in self.communities if c.is_collusive)
        
        total_edges = len(self.edge_weights)
        avg_connections = np.mean([len(n.neighbors) for n in self.publishers.values()]) if self.publishers else 0
        
        return {
            'total_publishers': total_publishers,
            'suspicious_publishers': suspicious_publishers,
            'suspicious_ratio': suspicious_publishers / max(1, total_publishers),
            'total_communities': len(self.communities),
            'collusive_communities': collusive_communities,
            'total_edges': total_edges,
            'avg_connections_per_publisher': float(avg_connections),
            'communities': [
                {
                    'community_id': c.community_id,
                    'size': len(c.members),
                    'avg_fraud_rate': float(c.avg_fraud_rate),
                    'total_clicks': c.total_clicks,
                    'risk_level': c.risk_level,
                    'is_collusive': c.is_collusive,
                    'members': c.members
                }
                for c in self.communities
            ]
        }

    def export_network_json(self) -> str:
        nodes = []
        edges = []
        
        for pub_id, node in self.publishers.items():
            nodes.append({
                'id': pub_id,
                'name': pub_id,
                'fraud_rate': float(node.fraud_rate),
                'risk_score': float(node.risk_score),
                'is_suspicious': node.is_suspicious,
                'community_id': node.community_id,
                'value': node.total_clicks
            })
        
        for (pub1, pub2), weights in self.edge_weights.items():
            if weights.get('weight', 0) > 0.1:
                edges.append({
                    'source': pub1,
                    'target': pub2,
                    'value': float(weights.get('weight', 0)),
                    'shared_ips': weights['ip'],
                    'shared_devices': weights['device'],
                    'shared_sessions': weights['session']
                })
        
        return json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False, indent=2)

    def reset(self):
        self.publishers.clear()
        self.ip_to_publishers.clear()
        self.device_to_publishers.clear()
        self.session_to_publishers.clear()
        self.edge_weights.clear()
        self.communities.clear()
        self.community_detected = False
