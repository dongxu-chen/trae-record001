import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import math

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX not available. Influence analysis will use fallback methods.")


class InfluenceAnalyzer:
    def __init__(self):
        self.verified_media_accounts = {
            '人民日报', '新华社', '央视新闻', '光明日报', '环球时报',
            '中国日报', '澎湃新闻', '界面新闻', '财新网', '第一财经',
            'CNN', 'BBC', 'Reuters', 'AP', 'Bloomberg', 'NYTimes',
            '人民日报评论', '新华社快讯', '央视网', '人民网', '新华网',
            '中新网', '中经网', '中青网', '环球网', '海外网',
        }
        
        self.media_keywords = [
            '新闻', '日报', '时报', '晚报', '晨报', '周刊', '月刊',
            '电视台', '电台', '广播', '通讯社', '传媒', '报业',
            'News', 'Times', 'Daily', 'Post', 'Herald', 'Tribune',
            'Chronicle', 'Journal', 'Register', 'Press', 'Sun', 'Star'
        ]
        
        self.celeb_keywords = [
            '明星', '演员', '歌手', '主持人', '网红', '博主', '达人',
            'KOL', '大V', '名人', '专家', '学者', '教授', '博士',
            'CEO', '创始人', '董事长', '总裁', '总经理',
            'Celebrity', 'Influencer', 'Expert', 'Guru', 'Legend'
        ]
        
        self.node_database = {}
    
    def classify_node_type(self, author_name: str, author_metadata: Dict = None) -> str:
        if not author_name:
            return 'normal'
        
        name_lower = author_name.lower()
        
        for media in self.verified_media_accounts:
            if media.lower() in name_lower:
                return 'media'
        
        for keyword in self.media_keywords:
            if keyword.lower() in name_lower:
                return 'media'
        
        for keyword in self.celeb_keywords:
            if keyword.lower() in name_lower:
                return 'celebrity'
        
        if author_metadata:
            if author_metadata.get('verified', False):
                followers = author_metadata.get('followers_count', 0)
                if followers >= 1000000:
                    return 'celebrity'
                elif followers >= 100000:
                    return 'influencer'
        
        return 'normal'
    
    def calculate_influence_score(self, node_data: Dict) -> float:
        if not node_data:
            return 0.0
        
        followers = node_data.get('followers_count', 0)
        following = node_data.get('following_count', 0)
        total_posts = node_data.get('total_posts', 0)
        avg_likes = node_data.get('avg_likes', 0)
        avg_shares = node_data.get('avg_shares', 0)
        avg_comments = node_data.get('avg_comments', 0)
        verified = node_data.get('verified', False)
        node_type = node_data.get('node_type', 'normal')
        
        followers_score = math.log1p(followers) / math.log1p(1000000) if followers > 0 else 0
        
        engagement = avg_likes + avg_shares * 2 + avg_comments * 3
        engagement_score = math.log1p(engagement) / math.log1p(10000) if engagement > 0 else 0
        
        type_multipliers = {
            'media': 2.0,
            'celebrity': 1.8,
            'influencer': 1.5,
            'normal': 1.0
        }
        type_multiplier = type_multipliers.get(node_type, 1.0)
        
        verified_bonus = 1.5 if verified else 1.0
        
        activity_score = math.log1p(total_posts) / math.log1p(1000) if total_posts > 0 else 0
        
        influence_score = (
            followers_score * 0.4 +
            engagement_score * 0.3 +
            activity_score * 0.1
        ) * type_multiplier * verified_bonus
        
        return min(influence_score, 1.0)
    
    def identify_key_nodes(self, posts: List[Dict], top_k: int = 20) -> List[Dict]:
        node_stats = defaultdict(lambda: {
            'post_count': 0,
            'total_likes': 0,
            'total_shares': 0,
            'total_comments': 0,
            'posts': [],
            'platforms': set()
        })
        
        for post in posts:
            author = post.get('author', '')
            if not author:
                continue
            
            stats = node_stats[author]
            stats['post_count'] += 1
            stats['total_likes'] += post.get('likes', 0)
            stats['total_shares'] += post.get('shares', 0)
            stats['total_comments'] += post.get('comments', 0)
            stats['posts'].append(post)
            stats['platforms'].add(post.get('platform', 'unknown'))
        
        scored_nodes = []
        for author, stats in node_stats.items():
            node_type = self.classify_node_type(author)
            
            node_data = {
                'followers_count': stats.get('followers_count', stats['total_likes']),
                'following_count': stats.get('following_count', 0),
                'total_posts': stats['post_count'],
                'avg_likes': stats['total_likes'] / stats['post_count'] if stats['post_count'] > 0 else 0,
                'avg_shares': stats['total_shares'] / stats['post_count'] if stats['post_count'] > 0 else 0,
                'avg_comments': stats['total_comments'] / stats['post_count'] if stats['post_count'] > 0 else 0,
                'verified': node_type in ['media', 'celebrity'],
                'node_type': node_type
            }
            
            influence_score = self.calculate_influence_score(node_data)
            
            total_engagement = stats['total_likes'] + stats['total_shares'] * 2 + stats['total_comments'] * 3
            
            scored_nodes.append({
                'author': author,
                'node_type': node_type,
                'influence_score': round(influence_score, 6),
                'post_count': stats['post_count'],
                'total_likes': stats['total_likes'],
                'total_shares': stats['total_shares'],
                'total_comments': stats['total_comments'],
                'total_engagement': total_engagement,
                'avg_engagement': total_engagement / stats['post_count'] if stats['post_count'] > 0 else 0,
                'platforms': list(stats['platforms']),
                'first_post_time': min((p.get('timestamp') for p in stats['posts'] if p.get('timestamp')), default=None),
                'last_post_time': max((p.get('timestamp') for p in stats['posts'] if p.get('timestamp')), default=None)
            })
        
        scored_nodes.sort(key=lambda x: x['influence_score'], reverse=True)
        
        return scored_nodes[:top_k]
    
    def analyze_propagation_influence(self, posts: List[Dict], propagation_paths: List[Dict]) -> Dict:
        if not posts or not propagation_paths:
            return {}
        
        key_nodes = self.identify_key_nodes(posts, top_k=50)
        key_node_names = {n['author'] for n in key_nodes}
        
        if not NETWORKX_AVAILABLE:
            return {
                'key_nodes': key_nodes[:20],
                'node_types_distribution': self._get_node_type_distribution(key_nodes),
                'top_influencers': [n for n in key_nodes if n['node_type'] in ['celebrity', 'influencer']][:10],
                'top_media': [n for n in key_nodes if n['node_type'] == 'media'][:10]
            }
        
        try:
            graph = nx.DiGraph()
            
            for path in propagation_paths:
                source = path.get('source_node', '')
                target = path.get('target_node', '')
                if source and target:
                    weight = path.get('weight', 1.0)
                    graph.add_edge(source, target, weight=weight)
            
            for node in key_nodes:
                author = node['author']
                if author in graph.nodes():
                    graph.nodes[author]['influence_score'] = node['influence_score']
                    graph.nodes[author]['node_type'] = node['node_type']
            
            try:
                betweenness = nx.betweenness_centrality(graph, k=100)
            except:
                betweenness = {}
            
            try:
                pagerank = nx.pagerank(graph, alpha=0.85)
            except:
                pagerank = {}
            
            enhanced_nodes = []
            for node in key_nodes:
                author = node['author']
                enhanced = node.copy()
                enhanced['betweenness_centrality'] = round(betweenness.get(author, 0), 6)
                enhanced['pagerank_score'] = round(pagerank.get(author, 0), 6)
                
                if author in graph.nodes():
                    enhanced['out_degree'] = graph.out_degree(author)
                    enhanced['in_degree'] = graph.in_degree(author)
                
                if enhanced.get('betweenness_centrality', 0) > 0:
                    enhanced['bridge_score'] = round(
                        enhanced['influence_score'] * 0.5 + enhanced['betweenness_centrality'] * 0.5, 6
                    )
                else:
                    enhanced['bridge_score'] = enhanced['influence_score']
                
                enhanced_nodes.append(enhanced)
            
            critical_bridges = [
                n for n in enhanced_nodes 
                if n.get('betweenness_centrality', 0) > 0.1
            ]
            
            return {
                'key_nodes': enhanced_nodes[:20],
                'node_types_distribution': self._get_node_type_distribution(enhanced_nodes),
                'top_influencers': [n for n in enhanced_nodes if n['node_type'] in ['celebrity', 'influencer']][:10],
                'top_media': [n for n in enhanced_nodes if n['node_type'] == 'media'][:10],
                'critical_bridges': critical_bridges[:10],
                'graph_stats': {
                    'total_nodes': graph.number_of_nodes(),
                    'total_edges': graph.number_of_edges(),
                    'density': round(nx.density(graph), 6) if graph.number_of_nodes() > 1 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in propagation influence analysis: {e}")
            return {
                'key_nodes': key_nodes[:20],
                'node_types_distribution': self._get_node_type_distribution(key_nodes),
                'top_influencers': [n for n in key_nodes if n['node_type'] in ['celebrity', 'influencer']][:10],
                'top_media': [n for n in key_nodes if n['node_type'] == 'media'][:10]
            }
    
    def _get_node_type_distribution(self, nodes: List[Dict]) -> Dict:
        type_counts = Counter(n['node_type'] for n in nodes)
        total = len(nodes) if nodes else 1
        return {
            t: {
                'count': c,
                'percentage': round(c / total, 4)
            }
            for t, c in type_counts.items()
        }
    
    def analyze_topic_influence(self, posts: List[Dict], topic_keyword: str) -> Dict:
        related_posts = [
            p for p in posts
            if topic_keyword.lower() in p.get('content', '').lower()
        ]
        
        if not related_posts:
            return {}
        
        topic_nodes = self.identify_key_nodes(related_posts, top_k=30)
        
        sentiment_by_type = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
        
        for post in related_posts:
            author = post.get('author', '')
            node_type = 'normal'
            
            for node in topic_nodes:
                if node['author'] == author:
                    node_type = node['node_type']
                    break
            
            sentiment = post.get('sentiment', {}).get('sentiment', 'neutral')
            sentiment_by_type[node_type][sentiment] += 1
        
        type_sentiment_dist = {}
        for node_type, counts in sentiment_by_type.items():
            total = sum(counts.values())
            type_sentiment_dist[node_type] = {
                'counts': dict(counts),
                'percentages': {
                    k: round(v / total, 4) if total > 0 else 0
                    for k, v in counts.items()
                }
            }
        
        early_adopters = []
        sorted_posts = sorted(
            [p for p in related_posts if p.get('timestamp')],
            key=lambda x: x['timestamp']
        )
        
        if sorted_posts:
            first_time = sorted_posts[0]['timestamp']
            for post in sorted_posts[:10]:
                time_diff = (post['timestamp'] - first_time).total_seconds() / 3600 if isinstance(post['timestamp'], datetime) and isinstance(first_time, datetime) else 0
                early_adopters.append({
                    'author': post.get('author', ''),
                    'time_after_first_hours': round(time_diff, 2),
                    'post_content': post.get('content', '')[:100],
                    'timestamp': post['timestamp']
                })
        
        return {
            'topic_keyword': topic_keyword,
            'total_related_posts': len(related_posts),
            'key_nodes': topic_nodes[:15],
            'sentiment_by_type': type_sentiment_dist,
            'early_adopters': early_adopters,
            'first_post_time': sorted_posts[0]['timestamp'] if sorted_posts else None,
            'top_authors_by_posts': [
                {'author': n['author'], 'post_count': n['post_count']}
                for n in topic_nodes[:10]
            ]
        }
    
    def generate_influence_report(self, posts: List[Dict], propagation_paths: List[Dict] = None) -> Dict:
        key_nodes = self.identify_key_nodes(posts, top_k=50)
        
        media_nodes = [n for n in key_nodes if n['node_type'] == 'media']
        celebrity_nodes = [n for n in key_nodes if n['node_type'] == 'celebrity']
        influencer_nodes = [n for n in key_nodes if n['node_type'] == 'influencer']
        
        propagation_analysis = {}
        if propagation_paths:
            propagation_analysis = self.analyze_propagation_influence(posts, propagation_paths)
        
        total_followers_est = sum(
            n['avg_engagement'] * 100 for n in key_nodes
        )
        
        return {
            'total_nodes_analyzed': len(key_nodes),
            'total_posts': len(posts),
            'node_types_distribution': self._get_node_type_distribution(key_nodes),
            'top_influencers': celebrity_nodes[:10] + influencer_nodes[:5],
            'top_media_outlets': media_nodes[:10],
            'estimated_reach': int(total_followers_est),
            'propagation_analysis': propagation_analysis,
            'summary': {
                'media_count': len(media_nodes),
                'celebrity_count': len(celebrity_nodes),
                'influencer_count': len(influencer_nodes),
                'normal_user_count': len(key_nodes) - len(media_nodes) - len(celebrity_nodes) - len(influencer_nodes)
            }
        }
