import asyncio
import uuid
from typing import List, Optional, Callable, Dict
from datetime import datetime
from models import NewsArticle, ClusterTopic, TopicWarning, PropagationPath, TopicComparisonResult
from online_clustering import OnlineTopicCluster
from topic_evolution import TopicEvolutionTracker
from influence_calculator import InfluenceCalculator
from topic_warning import TopicWarningSystem
from propagation_tracker import PropagationTracker
from topic_comparison import TopicComparisonEngine
from neo4j_store import Neo4jStore
from text_embedding import TextEmbedding
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsStreamProcessor:
    def __init__(self, embedding_model: Optional[TextEmbedding] = None):
        self.embedding = embedding_model or TextEmbedding()
        self.cluster = OnlineTopicCluster(self.embedding)
        self.evolution_tracker = TopicEvolutionTracker(self.embedding)
        self.influence_calc = InfluenceCalculator()
        self.warning_system = TopicWarningSystem()
        self.propagation_tracker = PropagationTracker()
        self.comparison_engine = TopicComparisonEngine()
        self.neo4j = Neo4jStore()
        
        self.article_cache: List[NewsArticle] = []
        self.previous_topics = {}
        self.on_topic_update: Optional[Callable] = None
        self.on_evolution: Optional[Callable] = None
        self.on_graph_incremental_update: Optional[Callable] = None
        self.on_topic_warning: Optional[Callable] = None
        
    def set_callbacks(self, on_topic_update=None, on_evolution=None, 
                      on_graph_incremental_update=None, on_topic_warning=None):
        self.on_topic_update = on_topic_update
        self.on_evolution = on_evolution
        self.on_graph_incremental_update = on_graph_incremental_update
        self.on_topic_warning = on_topic_warning
    
    async def process_article(self, article: NewsArticle) -> Optional[str]:
        try:
            topic_id = self.cluster.add_article(article)
            
            if topic_id:
                self.article_cache.append(article)
                self.neo4j.create_article_node(article, topic_id)
                self.propagation_tracker.add_article(article, topic_id)
                
                topic = self.cluster.topics[topic_id]
                self.neo4j.create_topic_node(topic)
                
                if len(self.article_cache) >= settings.NEWS_BATCH_SIZE:
                    await self._process_batch()
                
                if self.on_topic_update:
                    await self.on_topic_update(topic)
            
            return topic_id
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None
    
    async def _process_batch(self):
        try:
            self.cluster.merge_small_topics()
            
            current_topics = self.cluster.topics.copy()
            if self.previous_topics:
                evolutions = self.evolution_tracker.detect_evolution(
                    current_topics, self.previous_topics
                )
                
                for evolution in evolutions:
                    self.neo4j.create_evolution_relation(evolution)
                    
                    if self.on_evolution:
                        await self.on_evolution(evolution)
            
            incremental_update = self.evolution_tracker.get_incremental_update(
                self.cluster.topics
            )
            
            has_changes = (
                len(incremental_update["added_nodes"]) > 0 or
                len(incremental_update["updated_nodes"]) > 0 or
                len(incremental_update["removed_nodes"]) > 0 or
                len(incremental_update["added_edges"]) > 0 or
                len(incremental_update["updated_edges"]) > 0 or
                len(incremental_update["removed_edges"]) > 0
            )
            
            if has_changes and self.on_graph_incremental_update:
                await self.on_graph_incremental_update(incremental_update)
            
            for topic in self.cluster.topics.values():
                influence = self.influence_calc.calculate_metrics(topic)
                influence_dict = influence.model_dump() if influence else {}
                
                self.warning_system.record_topic_state(topic, influence_dict)
                self.comparison_engine.record_topic_state(topic, influence_dict)
                
                warning = self.warning_system.detect_burst_warning(topic, influence_dict)
                if warning and self.on_topic_warning:
                    await self.on_topic_warning(warning)
                
                self.neo4j.create_topic_node(topic)
            
            self.previous_topics = current_topics
            self.article_cache = []
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
    
    def get_active_topics(self, min_size: int = None) -> List[ClusterTopic]:
        return self.cluster.get_active_topics(min_size)
    
    def get_topic(self, topic_id: str) -> Optional[ClusterTopic]:
        return self.cluster.topics.get(topic_id)
    
    def get_topic_influence(self, topic_id: str):
        topic = self.get_topic(topic_id)
        if topic:
            return self.influence_calc.calculate_metrics(topic)
        return None
    
    def get_evolution_graph(self) -> dict:
        return self.evolution_tracker.get_evolution_graph_data(self.cluster.topics)
    
    def get_full_graph_with_versions(self) -> dict:
        return self.evolution_tracker.get_full_graph_with_versions(self.cluster.topics)
    
    def get_incremental_update(self) -> dict:
        return self.evolution_tracker.get_incremental_update(self.cluster.topics)
    
    def get_evolution_chain(self, topic_id: str) -> List[dict]:
        return self.evolution_tracker.get_evolution_chain(topic_id)
    
    def get_bursting_topics(self) -> List[ClusterTopic]:
        return [
            t for t in self.cluster.topics.values()
            if self.influence_calc.detect_burst(t)
        ]
    
    def get_active_warnings(self, min_level: str = None) -> List[TopicWarning]:
        return self.warning_system.get_active_warnings(min_level)
    
    def acknowledge_warning(self, topic_id: str) -> bool:
        return self.warning_system.acknowledge_warning(topic_id)
    
    def get_warning_history(self, limit: int = 20) -> List[TopicWarning]:
        return self.warning_system.get_warning_history(limit)
    
    def get_propagation_path(self, topic_id: str) -> Optional[PropagationPath]:
        topic = self.get_topic(topic_id)
        if not topic:
            return None
        return self.propagation_tracker.analyze_propagation_path(topic_id, topic)
    
    def get_ignition_articles(self, topic_id: str) -> List[Dict]:
        articles = self.propagation_tracker.get_ignition_articles(topic_id)
        return [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "publish_time": a.publish_time.isoformat(),
                "share_count": a.share_count,
                "like_count": a.like_count,
                "comment_count": a.comment_count
            }
            for a in articles
        ]
    
    def compare_topics(self, topic_ids: List[str], time_range_hours: Optional[int] = None) -> Optional[TopicComparisonResult]:
        return self.comparison_engine.compare_topics(topic_ids, time_range_hours)
    
    def get_comparable_topics(self) -> List[str]:
        return self.comparison_engine.get_comparable_topics()
    
    def find_similar_topics(self, topic_id: str, threshold: float = 0.5) -> List[str]:
        return self.comparison_engine.find_similar_topics(topic_id, threshold)
    
    def close(self):
        self.neo4j.close()

class MockNewsGenerator:
    def __init__(self):
        self.news_templates = [
            {
                "base_title": "人工智能{action}医疗行业",
                "base_content": "最新研究表明，人工智能技术正在{detail}医疗行业。专家预测这将带来革命性的变化。",
                "keywords": ["人工智能", "医疗", "技术", "AI", "创新"]
            },
            {
                "base_title": "新能源汽车销量{trend}增长",
                "base_content": "最新数据显示，新能源汽车销量持续{trend}。政策支持和技术进步是主要驱动因素。",
                "keywords": ["新能源", "汽车", "销量", "电动", "环保"]
            },
            {
                "base_title": "股市{direction}波动加剧",
                "base_content": "受多种因素影响，近期股市{direction}波动加剧。投资者需保持谨慎态度。",
                "keywords": ["股市", "投资", "金融", "市场", "经济"]
            },
            {
                "base_title": "5G技术{phase}商用部署",
                "base_content": "5G技术正在{phase}商用部署，预计将为多个行业带来新的发展机遇。",
                "keywords": ["5G", "通信", "技术", "网络", "数字化"]
            },
            {
                "base_title": "区块链应用{expand}各领域",
                "base_content": "区块链技术应用正在{expand}各个领域，展现出巨大的发展潜力。",
                "keywords": ["区块链", "加密", "技术", "金融", "创新"]
            }
        ]
        
        self.actions = ["革新", "改变", "赋能", "重塑", "推动"]
        self.details = ["深刻改变", "积极影响", "逐步渗透", "快速融入", "全面升级"]
        self.trends = ["快速", "持续", "稳步", "加速", "大幅"]
        self.directions = ["持续", "剧烈", "大幅", "异常", "频繁"]
        self.phases = ["加速", "全面", "深入", "稳步", "大规模"]
        self.expands = ["拓展至", "渗透到", "应用于", "覆盖", "进入"]
        self.sources = ["新华社", "人民日报", "央视新闻", "经济日报", "科技日报"]
    
    def generate_news(self) -> NewsArticle:
        import random
        template = random.choice(self.news_templates)
        
        if "人工智能" in template["base_title"]:
            action = random.choice(self.actions)
            detail = random.choice(self.details)
            title = template["base_title"].format(action=action)
            content = template["base_content"].format(detail=detail)
        elif "销量" in template["base_title"]:
            trend = random.choice(self.trends)
            title = template["base_title"].format(trend=trend)
            content = template["base_content"].format(trend=trend + "增长")
        elif "股市" in template["base_title"]:
            direction = random.choice(self.directions)
            title = template["base_title"].format(direction=direction)
            content = template["base_content"].format(direction=direction)
        elif "5G" in template["base_title"]:
            phase = random.choice(self.phases)
            title = template["base_title"].format(phase=phase)
            content = template["base_content"].format(phase=phase)
        else:
            expand = random.choice(self.expands)
            title = template["base_title"].format(expand=expand)
            content = template["base_content"].format(expand=expand)
        
        return NewsArticle(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            source=random.choice(self.sources),
            publish_time=datetime.now(),
            url=f"https://example.com/news/{uuid.uuid4()}",
            author="Mock Author",
            share_count=random.randint(0, 500),
            like_count=random.randint(0, 2000),
            comment_count=random.randint(0, 200)
        )
