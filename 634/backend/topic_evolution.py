import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from models import ClusterTopic, TopicEvolution
from text_embedding import TextEmbedding
from config import settings

class TopicEvolutionTracker:
    def __init__(self, embedding_model: TextEmbedding):
        self.embedding = embedding_model
        self.evolution_history: List[TopicEvolution] = []
        self._last_nodes: Dict[str, Dict] = {}
        self._last_edges: Dict[str, Dict] = {}
        self._node_version: Dict[str, int] = {}
        self._edge_version: Dict[str, int] = {}
    
    def _get_edge_key(self, source: str, target: str) -> str:
        return f"{source}->{target}"
    
    def detect_evolution(self, current_topics: Dict[str, ClusterTopic], 
                         previous_topics: Dict[str, ClusterTopic]) -> List[TopicEvolution]:
        evolutions = []
        
        for curr_id, curr_topic in current_topics.items():
            best_match = None
            best_similarity = 0
            
            for prev_id, prev_topic in previous_topics.items():
                if curr_id == prev_id:
                    continue
                
                sim = self.embedding.cosine_similarity(
                    np.array(curr_topic.centroid),
                    np.array(prev_topic.centroid)
                )
                
                if sim > best_similarity and sim >= 0.6:
                    best_similarity = sim
                    best_match = prev_topic
            
            if best_match:
                evolution_type = self._classify_evolution_type(
                    curr_topic, best_match, best_similarity
                )
                
                common_keywords = list(
                    set(curr_topic.keywords) & set(best_match.keywords)
                )
                
                evolution = TopicEvolution(
                    from_topic=best_match.topic_id,
                    to_topic=curr_topic.topic_id,
                    evolution_type=evolution_type,
                    similarity=best_similarity,
                    timestamp=datetime.now(),
                    common_keywords=common_keywords
                )
                
                evolutions.append(evolution)
                self.evolution_history.append(evolution)
        
        return evolutions
    
    def _classify_evolution_type(self, curr_topic: ClusterTopic, 
                                 prev_topic: ClusterTopic, 
                                 similarity: float) -> str:
        if similarity >= 0.9:
            if curr_topic.size > prev_topic.size * 1.5:
                return "growth"
            elif curr_topic.size < prev_topic.size * 0.7:
                return "shrink"
            else:
                return "continuation"
        elif similarity >= 0.7:
            return "split"
        elif similarity >= 0.6:
            return "merge"
        else:
            return "emergence"
    
    def get_evolution_chain(self, topic_id: str, max_depth: int = 5) -> List[Dict]:
        chain = []
        current_id = topic_id
        
        for _ in range(max_depth):
            ancestors = [
                e for e in self.evolution_history
                if e.to_topic == current_id
            ]
            
            if not ancestors:
                break
            
            ancestors.sort(key=lambda x: x.similarity, reverse=True)
            ancestor = ancestors[0]
            
            chain.append({
                "from_topic": ancestor.from_topic,
                "to_topic": ancestor.to_topic,
                "type": ancestor.evolution_type,
                "similarity": ancestor.similarity,
                "timestamp": ancestor.timestamp
            })
            
            current_id = ancestor.from_topic
        
        return chain
    
    def get_evolution_graph_data(self, topics: Dict[str, ClusterTopic]) -> Dict:
        nodes = []
        edges = []
        
        for topic_id, topic in topics.items():
            nodes.append({
                "id": topic_id,
                "name": topic.name,
                "keywords": topic.keywords,
                "size": topic.size,
                "lifecycle": topic.lifecycle.value,
                "influence": topic.influence_score,
                "total_shares": getattr(topic, 'total_shares', 0),
                "total_likes": getattr(topic, 'total_likes', 0),
                "total_comments": getattr(topic, 'total_comments', 0)
            })
        
        for evolution in self.evolution_history:
            edges.append({
                "source": evolution.from_topic,
                "target": evolution.to_topic,
                "type": evolution.evolution_type,
                "weight": evolution.similarity,
                "common_keywords": evolution.common_keywords
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_incremental_update(self, topics: Dict[str, ClusterTopic]) -> Dict:
        current_nodes = {}
        for topic_id, topic in topics.items():
            node_data = {
                "id": topic_id,
                "name": topic.name,
                "keywords": topic.keywords,
                "size": topic.size,
                "lifecycle": topic.lifecycle.value,
                "influence": topic.influence_score,
                "total_shares": getattr(topic, 'total_shares', 0),
                "total_likes": getattr(topic, 'total_likes', 0),
                "total_comments": getattr(topic, 'total_comments', 0)
            }
            current_nodes[topic_id] = node_data
        
        current_edges = {}
        for evolution in self.evolution_history:
            edge_key = self._get_edge_key(evolution.from_topic, evolution.to_topic)
            edge_data = {
                "source": evolution.from_topic,
                "target": evolution.to_topic,
                "type": evolution.evolution_type,
                "weight": evolution.similarity,
                "common_keywords": evolution.common_keywords
            }
            current_edges[edge_key] = edge_data
        
        added_nodes = []
        updated_nodes = []
        removed_nodes = []
        
        for node_id, node_data in current_nodes.items():
            if node_id not in self._last_nodes:
                if node_id not in self._node_version:
                    self._node_version[node_id] = 0
                added_nodes.append(self._node_with_version(node_data, self._node_version[node_id]))
            else:
                if not self._nodes_equal(node_data, self._last_nodes[node_id]):
                    self._node_version[node_id] += 1
                updated_nodes.append(self._node_with_version(node_data, self._node_version[node_id]))
        
        for node_id in self._last_nodes:
            if node_id not in current_nodes:
                removed_nodes.append({"id": node_id, "version": self._node_version.get(node_id, 0)})
        
        added_edges = []
        updated_edges = []
        removed_edges = []
        
        for edge_key, edge_data in current_edges.items():
            if edge_key not in self._last_edges:
                if edge_key not in self._edge_version:
                    self._edge_version[edge_key] = 0
                added_edges.append(self._edge_with_version(edge_data, self._edge_version[edge_key]))
            else:
                if not self._edges_equal(edge_data, self._last_edges[edge_key]):
                    self._edge_version[edge_key] += 1
                updated_edges.append(self._edge_with_version(edge_data, self._edge_version[edge_key]))
        
        for edge_key in self._last_edges:
            if edge_key not in current_edges:
                source, target = edge_key.split('->')
                removed_edges.append({
                    "source": source,
                    "target": target,
                    "version": self._edge_version.get(edge_key, 0)
                })
        
        self._last_nodes = current_nodes
        self._last_edges = current_edges
        
        return {
            "added_nodes": added_nodes,
            "updated_nodes": updated_nodes,
            "removed_nodes": removed_nodes,
            "added_edges": added_edges,
            "updated_edges": updated_edges,
            "removed_edges": removed_edges,
            "timestamp": datetime.now().isoformat()
        }
    
    def _node_with_version(self, node_data: Dict, version: int) -> Dict:
        return {**node_data, "version": version}
    
    def _edge_with_version(self, edge_data: Dict, version: int) -> Dict:
        return {**edge_data, "version": version}
    
    def _nodes_equal(self, n1: Dict, n2: Dict) -> bool:
        return (n1["name"] == n2["name"] and \
               n1["size"] == n2["size"] and \
               n1["lifecycle"] == n2["lifecycle"] and \
               abs(n1["influence"] - n2["influence"]) < 0.001 and \
               n1["total_shares"] == n2.get("total_shares", 0) and \
               n1["total_likes"] == n2.get("total_likes", 0) and \
               n1["total_comments"] == n2.get("total_comments", 0))
    
    def _edges_equal(self, e1: Dict, e2: Dict) -> bool:
        return e1["type"] == e2["type"] and \
               abs(e1["weight"] - e2["weight"]) < 0.001
    
    def get_full_graph_with_versions(self, topics: Dict[str, ClusterTopic]) -> Dict:
        graph_data = self.get_evolution_graph_data(topics)
        
        nodes_with_version = []
        for node in graph_data["nodes"]:
            node_id = node["id"]
            if node_id not in self._node_version:
                self._node_version[node_id] = 0
            nodes_with_version.append(self._node_with_version(node, self._node_version[node_id]))
        
        edges_with_version = []
        for edge in graph_data["edges"]:
            edge_key = self._get_edge_key(edge["source"], edge["target"])
            if edge_key not in self._edge_version:
                self._edge_version[edge_key] = 0
            edges_with_version.append(self._edge_with_version(edge, self._edge_version[edge_key]))
        
        return {
            "nodes": nodes_with_version,
            "edges": edges_with_version,
            "timestamp": datetime.now().isoformat()
        }
