import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

from analysis import SentimentAnalyzer, TopicModeler, PropagationAnalyzer, TextProcessor
from database import get_session, save_post, save_sentiment, save_topics, save_propagation_path
from kafka_manager import KafkaManager
from alert_manager import AlertManager
from config import Config


class DataPipeline:
    def __init__(self, use_kafka: bool = False):
        self.text_processor = TextProcessor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.topic_modeler = TopicModeler()
        self.propagation_analyzer = PropagationAnalyzer()
        
        self.kafka_manager = KafkaManager() if use_kafka or Config.ENABLE_KAFKA else None
        self.alert_manager = AlertManager(self.kafka_manager)
        
        self._setup_kafka_consumers()
        
        self.processed_count = 0
        self.sentiment_cache = []
        self.max_cache_size = 100
    
    def _setup_kafka_consumers(self):
        if self.kafka_manager and self.kafka_manager.enabled:
            self.kafka_manager.start_consumer_thread(
                Config.KAFKA_RAW_DATA_TOPIC,
                self._process_kafka_message
            )
    
    def _process_kafka_message(self, message: Dict):
        try:
            self.process_post(message)
        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")
    
    def process_post(self, post_data: Dict, analyze_propagation: bool = False) -> Dict:
        if not post_data or 'content' not in post_data:
            logger.warning("Invalid post data received")
            return {}
        
        try:
            timestamp = post_data.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.utcnow()
            
            post_data['timestamp'] = timestamp
            
            sentiment_result = self.sentiment_analyzer.analyze(post_data['content'])
            
            topic_results = self.topic_modeler.get_topics(post_data['content'])
            
            keywords = self.text_processor.extract_keywords(post_data['content'], top_k=5)
            
            result = {
                'post_id': post_data.get('post_id'),
                'platform': post_data.get('platform'),
                'content': post_data['content'],
                'author': post_data.get('author', ''),
                'timestamp': post_data['timestamp'].isoformat(),
                'sentiment': sentiment_result,
                'topics': topic_results,
                'keywords': keywords,
                'engagement': {
                    'likes': post_data.get('likes', 0),
                    'shares': post_data.get('shares', 0),
                    'comments': post_data.get('comments', 0),
                    'views': post_data.get('views', 0)
                },
                'processed_at': datetime.utcnow().isoformat()
            }
            
            self._save_to_database(post_data, sentiment_result, topic_results)
            
            self.sentiment_cache.append({
                **sentiment_result,
                'post_id': post_data.get('post_id'),
                'timestamp': post_data['timestamp']
            })
            
            if len(self.sentiment_cache) > self.max_cache_size:
                self.sentiment_cache = self.sentiment_cache[-self.max_cache_size:]
            
            if len(self.sentiment_cache) >= 20:
                self.alert_manager.check_alerts(
                    self.sentiment_cache,
                    platform=post_data.get('platform', 'all')
                )
            
            if self.kafka_manager and self.kafka_manager.enabled:
                self.kafka_manager.send_analyzed_data(result)
            
            self.processed_count += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing post: {e}", exc_info=True)
            return {}
    
    def _save_to_database(self, post_data: Dict, sentiment_result: Dict, topic_results: List[Dict]):
        try:
            session = get_session()
            
            post_db = save_post(session, post_data)
            
            save_sentiment(session, post_db.id, sentiment_result)
            
            save_topics(session, post_db.id, topic_results)
            
            session.commit()
            session.close()
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
    
    def process_batch(self, posts: List[Dict]) -> List[Dict]:
        results = []
        for post in posts:
            result = self.process_post(post)
            if result:
                results.append(result)
        
        if len(posts) >= 10:
            texts = [post.get('content', '') for post in posts if post.get('content')]
            self.topic_modeler.train(texts)
        
        return results
    
    def train_topic_model(self, texts: List[str]) -> bool:
        return self.topic_modeler.train(texts)
    
    def analyze_propagation(self, root_post_id: str, paths: List[Dict]) -> Dict:
        for path in paths:
            try:
                session = get_session()
                save_propagation_path(session, path)
                session.commit()
                session.close()
            except Exception as e:
                logger.error(f"Failed to save propagation path: {e}")
        
        return self.propagation_analyzer.analyze_propagation(root_post_id, paths)
    
    def get_sentiment_distribution(self, platform: str = None, hours: int = 24) -> Dict:
        try:
            session = get_session()
            
            from database import SocialMediaPost, SentimentResult
            from sqlalchemy import func
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(
                SentimentResult.sentiment,
                func.count(SentimentResult.id)
            ).join(SocialMediaPost).filter(
                SocialMediaPost.timestamp >= cutoff
            )
            
            if platform:
                query = query.filter(SocialMediaPost.platform == platform)
            
            results = query.group_by(SentimentResult.sentiment).all()
            
            total = sum(count for _, count in results) if results else 0
            
            distribution = {'positive': 0, 'negative': 0, 'neutral': 0}
            for sentiment, count in results:
                distribution[sentiment] = count
            
            session.close()
            
            return {
                'counts': distribution,
                'percentages': {
                    k: round(v / total, 4) if total > 0 else 0
                    for k, v in distribution.items()
                },
                'total': total
            }
        except Exception as e:
            logger.error(f"Failed to get sentiment distribution: {e}")
            return {'counts': {}, 'percentages': {}, 'total': 0}
    
    def get_trend_data(self, platform: str = None, hours: int = 24) -> List[Dict]:
        try:
            session = get_session()
            
            from database import SocialMediaPost, SentimentResult
            from sqlalchemy import func, case
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            try:
                query = session.query(
                    func.strftime('%Y-%m-%d %H:00:00', SocialMediaPost.timestamp).label('hour'),
                    func.count(SocialMediaPost.id).label('total'),
                    func.sum(case((SentimentResult.sentiment == 'positive', 1), else_=0)).label('positive'),
                    func.sum(case((SentimentResult.sentiment == 'negative', 1), else_=0)).label('negative'),
                    func.sum(case((SentimentResult.sentiment == 'neutral', 1), else_=0)).label('neutral')
                ).join(SentimentResult).filter(
                    SocialMediaPost.timestamp >= cutoff
                )
            except TypeError:
                query = session.query(
                    func.strftime('%Y-%m-%d %H:00:00', SocialMediaPost.timestamp).label('hour'),
                    func.count(SocialMediaPost.id).label('total'),
                    func.sum(case([(SentimentResult.sentiment == 'positive', 1)], else_=0)).label('positive'),
                    func.sum(case([(SentimentResult.sentiment == 'negative', 1)], else_=0)).label('negative'),
                    func.sum(case([(SentimentResult.sentiment == 'neutral', 1)], else_=0)).label('neutral')
                ).join(SentimentResult).filter(
                    SocialMediaPost.timestamp >= cutoff
                )
            
            if platform:
                query = query.filter(SocialMediaPost.platform == platform)
            
            results = query.group_by('hour').order_by('hour').all()
            
            trend_data = []
            for hour, total, positive, negative, neutral in results:
                trend_data.append({
                    'hour': hour,
                    'total': total,
                    'positive': positive,
                    'negative': negative,
                    'neutral': neutral,
                    'sentiment_score': (positive - negative) / total if total > 0 else 0
                })
            
            session.close()
            return trend_data
        except Exception as e:
            logger.error(f"Failed to get trend data: {e}")
            return []
    
    def get_top_keywords(self, platform: str = None, hours: int = 24, top_k: int = 20) -> List[Dict]:
        try:
            session = get_session()
            
            from database import SocialMediaPost
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(SocialMediaPost.content).filter(
                SocialMediaPost.timestamp >= cutoff
            )
            
            if platform:
                query = query.filter(SocialMediaPost.platform == platform)
            
            posts = query.all()
            
            all_texts = [post.content for post in posts if post.content]
            
            keywords = self.topic_modeler.extract_keywords(all_texts, top_k=top_k)
            
            session.close()
            
            return [{'keyword': kw, 'frequency': freq} for kw, freq in keywords]
        except Exception as e:
            logger.error(f"Failed to get top keywords: {e}")
            return []
    
    def get_platform_stats(self, hours: int = 24) -> Dict:
        try:
            session = get_session()
            
            from database import SocialMediaPost
            from sqlalchemy import func
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            results = session.query(
                SocialMediaPost.platform,
                func.count(SocialMediaPost.id),
                func.sum(SocialMediaPost.likes),
                func.sum(SocialMediaPost.shares),
                func.sum(SocialMediaPost.comments)
            ).filter(
                SocialMediaPost.timestamp >= cutoff
            ).group_by(SocialMediaPost.platform).all()
            
            stats = {}
            for platform, count, likes, shares, comments in results:
                stats[platform] = {
                    'posts_count': count,
                    'total_likes': likes or 0,
                    'total_shares': shares or 0,
                    'total_comments': comments or 0,
                    'avg_engagement': (likes + shares + comments) / count if count > 0 else 0
                }
            
            session.close()
            return stats
        except Exception as e:
            logger.error(f"Failed to get platform stats: {e}")
            return {}
    
    def close(self):
        if self.kafka_manager:
            self.kafka_manager.close()
