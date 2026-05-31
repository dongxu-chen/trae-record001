from neo4j import GraphDatabase
from typing import List, Dict, Optional
from datetime import datetime
from models import ClusterTopic, TopicEvolution, NewsArticle, TopicLifeCycle
from config import settings
import json

class Neo4jStore:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    def close(self):
        self.driver.close()
    
    def create_topic_node(self, topic: ClusterTopic):
        with self.driver.session() as session:
            session.execute_write(
                self._create_topic_node,
                topic
            )
    
    @staticmethod
    def _create_topic_node(tx, topic: ClusterTopic):
        query = """
        MERGE (t:Topic {topic_id: $topic_id})
        SET t.name = $name,
            t.keywords = $keywords,
            t.size = $size,
            t.lifecycle = $lifecycle,
            t.influence_score = $influence_score,
            t.trend_score = $trend_score,
            t.created_at = $created_at,
            t.updated_at = $updated_at,
            t.burst_count = $burst_count,
            t.centroid = $centroid,
            t.total_shares = $total_shares,
            t.total_likes = $total_likes,
            t.total_comments = $total_comments
        """
        tx.run(
            query,
            topic_id=topic.topic_id,
            name=topic.name,
            keywords=json.dumps(topic.keywords),
            size=topic.size,
            lifecycle=topic.lifecycle.value,
            influence_score=topic.influence_score,
            trend_score=topic.trend_score,
            created_at=topic.created_at.isoformat(),
            updated_at=topic.updated_at.isoformat(),
            burst_count=topic.burst_count,
            centroid=json.dumps(topic.centroid),
            total_shares=getattr(topic, 'total_shares', 0),
            total_likes=getattr(topic, 'total_likes', 0),
            total_comments=getattr(topic, 'total_comments', 0)
        )
    
    def create_article_node(self, article: NewsArticle, topic_id: str):
        with self.driver.session() as session:
            session.execute_write(
                self._create_article_node,
                article,
                topic_id
            )
    
    @staticmethod
    def _create_article_node(tx, article: NewsArticle, topic_id: str):
        query = """
        MERGE (a:Article {article_id: $article_id})
        SET a.title = $title,
            a.content = $content,
            a.source = $source,
            a.publish_time = $publish_time,
            a.url = $url,
            a.author = $author
        WITH a
        MATCH (t:Topic {topic_id: $topic_id})
        MERGE (a)-[:BELONGS_TO]->(t)
        """
        tx.run(
            query,
            article_id=article.id,
            title=article.title,
            content=article.content[:500],
            source=article.source,
            publish_time=article.publish_time.isoformat(),
            url=article.url,
            author=article.author,
            topic_id=topic_id
        )
    
    def create_evolution_relation(self, evolution: TopicEvolution):
        with self.driver.session() as session:
            session.execute_write(
                self._create_evolution_relation,
                evolution
            )
    
    @staticmethod
    def _create_evolution_relation(tx, evolution: TopicEvolution):
        query = """
        MATCH (t1:Topic {topic_id: $from_topic})
        MATCH (t2:Topic {topic_id: $to_topic})
        MERGE (t1)-[e:EVOLVES_TO]->(t2)
        SET e.evolution_type = $evolution_type,
            e.similarity = $similarity,
            e.timestamp = $timestamp,
            e.common_keywords = $common_keywords
        """
        tx.run(
            query,
            from_topic=evolution.from_topic,
            to_topic=evolution.to_topic,
            evolution_type=evolution.evolution_type,
            similarity=evolution.similarity,
            timestamp=evolution.timestamp.isoformat(),
            common_keywords=json.dumps(evolution.common_keywords)
        )
    
    def get_topic(self, topic_id: str) -> Optional[Dict]:
        with self.driver.session() as session:
            return session.execute_read(
                self._get_topic,
                topic_id
            )
    
    @staticmethod
    def _get_topic(tx, topic_id: str) -> Optional[Dict]:
        query = """
        MATCH (t:Topic {topic_id: $topic_id})
        RETURN t
        """
        result = tx.run(query, topic_id=topic_id)
        record = result.single()
        if record:
            node = record['t']
            return dict(node)
        return None
    
    def get_all_topics(self, limit: int = 100) -> List[Dict]:
        with self.driver.session() as session:
            return session.execute_read(
                self._get_all_topics,
                limit
            )
    
    @staticmethod
    def _get_all_topics(tx, limit: int) -> List[Dict]:
        query = """
        MATCH (t:Topic)
        RETURN t
        ORDER BY t.updated_at DESC
        LIMIT $limit
        """
        result = tx.run(query, limit=limit)
        return [dict(record['t']) for record in result]
    
    def get_evolution_graph(self) -> Dict:
        with self.driver.session() as session:
            return session.execute_read(
                self._get_evolution_graph
            )
    
    @staticmethod
    def _get_evolution_graph(tx) -> Dict:
        nodes_query = """
        MATCH (t:Topic)
        RETURN t.topic_id as id, t.name as name, t.lifecycle as lifecycle, 
               t.influence_score as influence, t.size as size,
               t.total_shares as total_shares, t.total_likes as total_likes,
               t.total_comments as total_comments
        """
        nodes_result = tx.run(nodes_query)
        nodes = [dict(record) for record in nodes_result]
        
        edges_query = """
        MATCH (t1:Topic)-[e:EVOLVES_TO]->(t2:Topic)
        RETURN t1.topic_id as source, t2.topic_id as target, 
               e.evolution_type as type, e.similarity as weight
        """
        edges_result = tx.run(edges_query)
        edges = [dict(record) for record in edges_result]
        
        return {"nodes": nodes, "edges": edges}
    
    def get_topic_articles(self, topic_id: str, limit: int = 20) -> List[Dict]:
        with self.driver.session() as session:
            return session.execute_read(
                self._get_topic_articles,
                topic_id,
                limit
            )
    
    @staticmethod
    def _get_topic_articles(tx, topic_id: str, limit: int) -> List[Dict]:
        query = """
        MATCH (a:Article)-[:BELONGS_TO]->(t:Topic {topic_id: $topic_id})
        RETURN a.article_id as id, a.title as title, a.source as source,
               a.publish_time as publish_time, a.url as url
        ORDER BY a.publish_time DESC
        LIMIT $limit
        """
        result = tx.run(query, topic_id=topic_id, limit=limit)
        return [dict(record) for record in result]
    
    def get_topics_by_lifecycle(self, lifecycle: TopicLifeCycle) -> List[Dict]:
        with self.driver.session() as session:
            return session.execute_read(
                self._get_topics_by_lifecycle,
                lifecycle.value
            )
    
    @staticmethod
    def _get_topics_by_lifecycle(tx, lifecycle: str) -> List[Dict]:
        query = """
        MATCH (t:Topic {lifecycle: $lifecycle})
        RETURN t
        ORDER BY t.influence_score DESC
        """
        result = tx.run(query, lifecycle=lifecycle)
        return [dict(record['t']) for record in result]
    
    def update_topic_lifecycle(self, topic_id: str, lifecycle: TopicLifeCycle):
        with self.driver.session() as session:
            session.execute_write(
                self._update_topic_lifecycle,
                topic_id,
                lifecycle.value
            )
    
    @staticmethod
    def _update_topic_lifecycle(tx, topic_id: str, lifecycle: str):
        query = """
        MATCH (t:Topic {topic_id: $topic_id})
        SET t.lifecycle = $lifecycle
        """
        tx.run(query, topic_id=topic_id, lifecycle=lifecycle)
