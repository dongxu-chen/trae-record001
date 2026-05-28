import logging
import re
import hashlib
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import networkx as nx

logger = logging.getLogger(__name__)


class OriginalityDetector:
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.content_hash_map = {}
        self.original_posts = {}
    
    def _get_text_fingerprint(self, text: str) -> str:
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', text.lower())
        return hashlib.md5(cleaned.encode('utf-8')).hexdigest()
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        words1 = set(re.findall(r'[\w\u4e00-\u9fff]+', text1.lower()))
        words2 = set(re.findall(r'[\w\u4e00-\u9fff]+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _ngram_similarity(self, text1: str, text2: str, n: int = 3) -> float:
        def get_ngrams(text: str, n: int) -> set:
            words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
            ngrams = set()
            for i in range(len(words) - n + 1):
                ngrams.add(' '.join(words[i:i+n]))
            return ngrams
        
        ngrams1 = get_ngrams(text1, n)
        ngrams2 = get_ngrams(text2, n)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_similarity(self, text1: str, text2: str) -> Dict:
        jaccard = self._jaccard_similarity(text1, text2)
        bigram = self._ngram_similarity(text1, text2, 2)
        trigram = self._ngram_similarity(text1, text2, 3)
        
        combined = (jaccard * 0.3 + bigram * 0.3 + trigram * 0.4)
        
        return {
            'jaccard_similarity': round(jaccard, 4),
            'bigram_similarity': round(bigram, 4),
            'trigram_similarity': round(trigram, 4),
            'combined_similarity': round(combined, 4),
            'is_duplicate': combined >= self.similarity_threshold
        }
    
    def check_originality(self, post_id: str, content: str, timestamp: datetime, 
                          existing_posts: List[Dict]) -> Dict:
        fingerprint = self._get_text_fingerprint(content)
        
        if fingerprint in self.content_hash_map:
            original_id = self.content_hash_map[fingerprint]
            return {
                'is_original': False,
                'original_post_id': original_id,
                'similarity_score': 1.0,
                'duplicate_type': 'exact'
            }
        
        most_similar = None
        highest_similarity = 0.0
        
        for existing in existing_posts:
            existing_id = existing.get('post_id')
            existing_content = existing.get('content', '')
            existing_timestamp = existing.get('timestamp')
            
            if existing_id == post_id:
                continue
            
            if existing_timestamp and existing_timestamp > timestamp:
                continue
            
            similarity = self.calculate_similarity(content, existing_content)
            
            if similarity['combined_similarity'] > highest_similarity:
                highest_similarity = similarity['combined_similarity']
                most_similar = {
                    'post_id': existing_id,
                    'similarity': similarity,
                    'timestamp': existing_timestamp
                }
        
        if most_similar and highest_similarity >= self.similarity_threshold:
            time_diff = (timestamp - most_similar['timestamp']).total_seconds() / 3600 if most_similar['timestamp'] else None
            
            return {
                'is_original': False,
                'original_post_id': most_similar['post_id'],
                'similarity_score': highest_similarity,
                'duplicate_type': 'near_duplicate',
                'time_delay_hours': round(time_diff, 2) if time_diff else None,
                'similarity_details': most_similar['similarity']
            }
        
        self.content_hash_map[fingerprint] = post_id
        self.original_posts[post_id] = {
            'content': content,
            'timestamp': timestamp,
            'fingerprint': fingerprint
        }
        
        return {
            'is_original': True,
            'original_post_id': post_id,
            'similarity_score': 0.0,
            'duplicate_type': None
        }


class PropagationAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.originality_detector = OriginalityDetector()
        self.posts_database = []
        self.originality_results = {}
        self.plagiarism_chains = defaultdict(list)
    
    def add_path(self, source: str, target: str, timestamp: datetime = None, **kwargs):
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.graph.add_edge(
            source, target,
            timestamp=timestamp,
            weight=kwargs.get('weight', 1.0),
            content_snippet=kwargs.get('content_snippet', ''),
            is_plagiarism=kwargs.get('is_plagiarism', False),
            similarity_score=kwargs.get('similarity_score', 0.0)
        )
    
    def build_from_paths(self, paths: List[Dict]):
        for path in paths:
            try:
                source = path.get('source_node')
                target = path.get('target_node')
                if not source or not target:
                    continue
                
                timestamp = path.get('propagation_time')
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except:
                        timestamp = datetime.utcnow()
                elif timestamp is None:
                    timestamp = datetime.utcnow()
                
                self.add_path(
                    source, target,
                    timestamp=timestamp,
                    weight=path.get('weight', 1.0),
                    content_snippet=path.get('content_snippet', ''),
                    is_plagiarism=path.get('is_plagiarism', False),
                    similarity_score=path.get('similarity_score', 0.0)
                )
            except Exception as e:
                logger.error(f"Error adding propagation path: {e}")
    
    def add_posts_for_originality_check(self, posts: List[Dict]):
        self.posts_database.extend(posts)
        
        for post in sorted(posts, key=lambda x: x.get('timestamp', datetime.min)):
            post_id = post.get('post_id')
            content = post.get('content', '')
            timestamp = post.get('timestamp', datetime.utcnow())
            
            if not post_id or not content:
                continue
            
            result = self.originality_detector.check_originality(
                post_id, content, timestamp, self.posts_database
            )
            
            self.originality_results[post_id] = result
            
            if not result['is_original']:
                original_id = result['original_post_id']
                self.plagiarism_chains[original_id].append({
                    'plagiarized_post_id': post_id,
                    'similarity_score': result['similarity_score'],
                    'timestamp': timestamp,
                    'duplicate_type': result['duplicate_type']
                })
    
    def get_originality_report(self, post_id: str = None) -> Dict:
        if post_id:
            return self.originality_results.get(post_id, {})
        
        total_posts = len(self.originality_results)
        original_count = sum(1 for r in self.originality_results.values() if r.get('is_original', False))
        duplicate_count = total_posts - original_count
        
        duplicate_types = defaultdict(int)
        for r in self.originality_results.values():
            if not r.get('is_original', True):
                dtype = r.get('duplicate_type', 'unknown')
                duplicate_types[dtype] += 1
        
        return {
            'total_posts': total_posts,
            'original_count': original_count,
            'duplicate_count': duplicate_count,
            'original_ratio': round(original_count / total_posts, 4) if total_posts > 0 else 0,
            'duplicate_types': dict(duplicate_types),
            'plagiarism_chains': dict(self.plagiarism_chains),
            'top_original_posts': self._get_top_original_posts(10)
        }
    
    def _get_top_original_posts(self, top_k: int = 10) -> List[Dict]:
        sorted_chains = sorted(
            self.plagiarism_chains.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        top_posts = []
        for original_id, plagiarisms in sorted_chains[:top_k]:
            top_posts.append({
                'original_post_id': original_id,
                'plagiarism_count': len(plagiarisms),
                'plagiarisms': plagiarisms,
                'total_similarity': round(sum(p['similarity_score'] for p in plagiarisms), 4)
            })
        
        return top_posts
    
    def analyze_plagiarism_propagation(self, original_post_id: str) -> Dict:
        if original_post_id not in self.plagiarism_chains:
            return {}
        
        plagiarisms = self.plagiarism_chains[original_post_id]
        
        if not plagiarisms:
            return {}
        
        timestamps = [p['timestamp'] for p in plagiarisms if p.get('timestamp')]
        if timestamps:
            time_range = {
                'first_plagiarism': min(timestamps).isoformat(),
                'last_plagiarism': max(timestamps).isoformat(),
                'duration_hours': round((max(timestamps) - min(timestamps)).total_seconds() / 3600, 2)
            }
        else:
            time_range = {}
        
        similarity_scores = [p['similarity_score'] for p in plagiarisms]
        
        return {
            'original_post_id': original_post_id,
            'total_plagiarisms': len(plagiarisms),
            'time_range': time_range,
            'similarity_stats': {
                'min': round(min(similarity_scores), 4),
                'max': round(max(similarity_scores), 4),
                'avg': round(sum(similarity_scores) / len(similarity_scores), 4)
            },
            'duplicate_type_distribution': self._count_duplicate_types(plagiarisms),
            'propagation_path': self._build_plagiarism_propagation_path(original_post_id, plagiarisms),
            'influence_score': self._calculate_plagiarism_influence(len(plagiarisms), similarity_scores)
        }
    
    def _count_duplicate_types(self, plagiarisms: List[Dict]) -> Dict:
        types = defaultdict(int)
        for p in plagiarisms:
            types[p.get('duplicate_type', 'unknown')] += 1
        return dict(types)
    
    def _build_plagiarism_propagation_path(self, original_id: str, plagiarisms: List[Dict]) -> List[Dict]:
        sorted_plagiarisms = sorted(plagiarisms, key=lambda x: x.get('timestamp', datetime.min))
        
        path = [{'node': original_id, 'type': 'original', 'order': 0}]
        
        for i, p in enumerate(sorted_plagiarisms, 1):
            path.append({
                'node': p['plagiarized_post_id'],
                'type': p.get('duplicate_type', 'plagiarism'),
                'similarity_score': p['similarity_score'],
                'timestamp': p.get('timestamp', '').isoformat() if p.get('timestamp') else '',
                'order': i
            })
        
        return path
    
    def _calculate_plagiarism_influence(self, count: int, similarities: List[float]) -> float:
        if count == 0 or not similarities:
            return 0.0
        
        avg_similarity = sum(similarities) / len(similarities)
        influence = count * avg_similarity
        
        return round(influence, 4)
    
    def get_propagation_depth(self, root_node: str, max_depth: int = 10) -> Dict[int, List[str]]:
        if root_node not in self.graph:
            return {}
        
        depths = {}
        visited = {root_node: 0}
        queue = deque([(root_node, 0)])
        
        while queue:
            node, depth = queue.popleft()
            if depth > max_depth:
                continue
            
            if depth not in depths:
                depths[depth] = []
            depths[depth].append(node)
            
            for neighbor in self.graph.successors(node):
                if neighbor not in visited:
                    visited[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))
        
        return depths
    
    def get_influence_score(self, node: str) -> Dict:
        if node not in self.graph:
            return {'out_degree': 0, 'in_degree': 0, 'betweenness': 0, 'pagerank': 0}
        
        try:
            betweenness = nx.betweenness_centrality(self.graph, k=100)
        except:
            betweenness = {}
        
        try:
            pagerank = nx.pagerank(self.graph, alpha=0.85)
        except:
            pagerank = {}
        
        return {
            'out_degree': self.graph.out_degree(node),
            'in_degree': self.graph.in_degree(node),
            'betweenness': round(betweenness.get(node, 0), 4),
            'pagerank': round(pagerank.get(node, 0), 4)
        }
    
    def get_top_influencers(self, top_k: int = 10) -> List[Dict]:
        try:
            pagerank = nx.pagerank(self.graph, alpha=0.85)
        except:
            pagerank = {node: 0 for node in self.graph.nodes()}
        
        sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
        
        influencers = []
        for node, score in sorted_nodes[:top_k]:
            originality_info = self.originality_results.get(node, {})
            influencers.append({
                'node': node,
                'influence_score': round(score, 6),
                'out_degree': self.graph.out_degree(node),
                'in_degree': self.graph.in_degree(node),
                'is_original': originality_info.get('is_original', None),
                'plagiarism_count': len(self.plagiarism_chains.get(node, []))
            })
        
        return influencers
    
    def get_propagation_speed(self, root_node: str, time_window_minutes: int = 60) -> Dict:
        if root_node not in self.graph:
            return {'speed': 0, 'nodes_reached': 0, 'avg_depth': 0}
        
        depths = self.get_propagation_depth(root_node)
        if not depths:
            return {'speed': 0, 'nodes_reached': 0, 'avg_depth': 0}
        
        total_nodes = sum(len(nodes) for nodes in depths.values())
        weighted_depth = sum(depth * len(nodes) for depth, nodes in depths.items())
        avg_depth = weighted_depth / total_nodes if total_nodes > 0 else 0
        
        speed = total_nodes / time_window_minutes
        
        return {
            'speed': round(speed, 4),
            'nodes_reached': total_nodes,
            'avg_depth': round(avg_depth, 2),
            'max_depth': max(depths.keys()) if depths else 0
        }
    
    def find_critical_nodes(self, threshold: float = 0.1) -> List[str]:
        try:
            betweenness = nx.betweenness_centrality(self.graph)
            critical = [node for node, score in betweenness.items() if score >= threshold]
            return critical
        except Exception as e:
            logger.error(f"Error finding critical nodes: {e}")
            return []
    
    def get_plagiarism_edges(self) -> List[Dict]:
        plagiarism_edges = []
        
        for source, target, data in self.graph.edges(data=True):
            if data.get('is_plagiarism', False):
                plagiarism_edges.append({
                    'source': source,
                    'target': target,
                    'similarity_score': data.get('similarity_score', 0.0),
                    'timestamp': data.get('timestamp', '').isoformat() if isinstance(data.get('timestamp'), datetime) else str(data.get('timestamp', ''))
                })
        
        return plagiarism_edges
    
    def get_propagation_graph_data(self, include_plagiarism: bool = True) -> Dict:
        nodes = []
        edges = []
        
        for node in self.graph.nodes():
            originality_info = self.originality_results.get(node, {})
            node_data = {
                'id': node,
                'label': node,
                'out_degree': self.graph.out_degree(node),
                'in_degree': self.graph.in_degree(node),
                'is_original': originality_info.get('is_original', None),
                'plagiarism_count': len(self.plagiarism_chains.get(node, []))
            }
            nodes.append(node_data)
        
        for source, target, data in self.graph.edges(data=True):
            edge_data = {
                'source': source,
                'target': target,
                'timestamp': data.get('timestamp', '').isoformat() if isinstance(data.get('timestamp'), datetime) else str(data.get('timestamp', '')),
                'content_snippet': data.get('content_snippet', ''),
                'is_plagiarism': data.get('is_plagiarism', False),
                'similarity_score': data.get('similarity_score', 0.0)
            }
            edges.append(edge_data)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'plagiarism_edge_count': sum(1 for e in edges if e.get('is_plagiarism', False)),
            'original_node_count': sum(1 for n in nodes if n.get('is_original', False))
        }
    
    def analyze_propagation(self, root_post_id: str, paths: List[Dict] = None, posts: List[Dict] = None) -> Dict:
        self.graph.clear()
        
        if paths:
            self.build_from_paths(paths)
        
        if posts:
            self.add_posts_for_originality_check(posts)
        
        root_nodes = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        if not root_nodes:
            root_nodes = list(self.graph.nodes())[:1]
        
        results = {
            'root_post_id': root_post_id,
            'total_nodes': len(self.graph.nodes()),
            'total_edges': len(self.graph.edges()),
            'propagation_depths': {},
            'top_influencers': self.get_top_influencers(10),
            'propagation_speed': {},
            'critical_nodes': self.find_critical_nodes(),
            'originality_report': self.get_originality_report(),
            'plagiarism_analysis': {}
        }
        
        for root_node in root_nodes[:3]:
            results['propagation_depths'][root_node] = self.get_propagation_depth(root_node)
            results['propagation_speed'][root_node] = self.get_propagation_speed(root_node)
        
        if root_post_id in self.plagiarism_chains:
            results['plagiarism_analysis'] = self.analyze_plagiarism_propagation(root_post_id)
        
        results['graph_data'] = self.get_propagation_graph_data()
        
        return results
    
    def compare_posts(self, post_id1: str, post_id2: str, content1: str, content2: str) -> Dict:
        similarity = self.originality_detector.calculate_similarity(content1, content2)
        
        return {
            'post1_id': post_id1,
            'post2_id': post_id2,
            'similarity': similarity,
            'is_plagiarism': similarity['is_duplicate'],
            'recommendation': self._get_plagiarism_recommendation(similarity['combined_similarity'])
        }
    
    def _get_plagiarism_recommendation(self, similarity: float) -> str:
        if similarity >= 0.9:
            return '高度疑似抄袭，建议标记并追踪来源'
        elif similarity >= 0.8:
            return '中度相似，建议进一步核实'
        elif similarity >= 0.6:
            return '轻度相似，可能存在引用关系'
        else:
            return '内容差异较大，无明显抄袭迹象'
    
    def clear(self):
        self.graph.clear()
        self.posts_database = []
        self.originality_results = {}
        self.plagiarism_chains.clear()
        self.originality_detector = OriginalityDetector()
