import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field
import re
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ConversationTurn:
    text: str
    speaker: str
    sentiment_result: Dict = None
    timestamp: float = None
    embedding: np.ndarray = None
    importance_score: float = 0.0
    is_turning_point: bool = False
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'text': self.text,
            'speaker': self.speaker,
            'sentiment': self.sentiment_result,
            'timestamp': self.timestamp,
            'importance_score': self.importance_score,
            'is_turning_point': self.is_turning_point,
            'keywords': self.keywords
        }


class KeywordExtractor:
    def __init__(self):
        self.sentiment_keywords = {
            'positive': ['满意', '感谢', '解决', '很好', '不错', '棒', '赞', '好评', '优秀', '专业'],
            'negative': ['生气', '愤怒', '投诉', '失望', '糟糕', '太差', '垃圾', '退款', '赔偿', '恶劣'],
            'anxiety': ['着急', '快点', '紧急', '怎么办', '什么时候', '急死', '担心', '紧张', '焦虑'],
            'issue': ['问题', '故障', '错误', '失败', '无法', '不能', '异常', '崩溃', '卡顿', '延迟']
        }
        
    def extract(self, text: str) -> List[str]:
        keywords = []
        for category, words in self.sentiment_keywords.items():
            for word in words:
                if word in text:
                    keywords.append(word)
        return list(set(keywords))


class ImportanceScorer:
    def __init__(self):
        self.weights = {
            'sentiment_extreme': 0.3,
            'sentiment_change': 0.25,
            'keyword_density': 0.2,
            'length_factor': 0.1,
            'turning_point': 0.15
        }
    
    def calculate_score(self, turn: ConversationTurn, previous_turn: ConversationTurn = None) -> float:
        score = 0.0
        
        if turn.sentiment_result:
            scores = turn.sentiment_result.get('scores', {})
            max_score = max(scores.values()) if scores else 0
            if max_score > 0.8:
                score += self.weights['sentiment_extreme'] * (max_score - 0.8) / 0.2
        
        if previous_turn and previous_turn.sentiment_result and turn.sentiment_result:
            prev_scores = previous_turn.sentiment_result.get('scores', {})
            curr_scores = turn.sentiment_result.get('scores', {})
            
            prev_sentiment = max(prev_scores, key=prev_scores.get) if prev_scores else None
            curr_sentiment = max(curr_scores, key=curr_scores.get) if curr_scores else None
            
            if prev_sentiment != curr_sentiment:
                score += self.weights['sentiment_change']
        
        keyword_count = len(turn.keywords)
        score += self.weights['keyword_density'] * min(keyword_count / 3, 1.0)
        
        text_length = len(turn.text)
        if text_length > 20:
            score += self.weights['length_factor'] * min((text_length - 20) / 100, 1.0)
        
        if turn.is_turning_point:
            score += self.weights['turning_point']
        
        return min(score, 1.0)


class SlidingWindowContext:
    def __init__(self, window_size: int = None, summary_size: int = None):
        self.window_size = window_size or int(os.getenv('CONTEXT_WINDOW', 8))
        self.summary_size = summary_size or int(os.getenv('SUMMARY_SIZE', 5))
        self.recent_turns: deque = deque(maxlen=self.window_size)
        self.important_turns: List[ConversationTurn] = []
        self.keyword_extractor = KeywordExtractor()
        self.importance_scorer = ImportanceScorer()
    
    def add_turn(self, turn: ConversationTurn, previous_turn: ConversationTurn = None) -> None:
        turn.keywords = self.keyword_extractor.extract(turn.text)
        turn.importance_score = self.importance_scorer.calculate_score(turn, previous_turn)
        
        self.recent_turns.append(turn)
        
        if turn.importance_score > 0.5:
            self.important_turns.append(turn)
            self.important_turns.sort(key=lambda x: x.importance_score, reverse=True)
            self.important_turns = self.important_turns[:self.summary_size]
    
    def get_context_text(self) -> List[str]:
        context = []
        
        for turn in self.important_turns:
            marker = "⭐" if turn.importance_score > 0.7 else "📌"
            context.append(f"{marker}[{turn.speaker}]: {turn.text}")
        
        recent = list(self.recent_turns)[-3:]
        for turn in recent:
            if turn not in self.important_turns:
                context.append(f"[{turn.speaker}]: {turn.text}")
        
        return context
    
    def get_summary(self) -> Dict:
        return {
            'summary_turns': [t.to_dict() for t in self.important_turns],
            'recent_turns': [t.to_dict() for t in list(self.recent_turns)[-3:]],
            'key_topics': self._extract_key_topics(),
            'sentiment_summary': self._summarize_sentiment()
        }
    
    def _extract_key_topics(self) -> List[str]:
        all_keywords = []
        for turn in self.important_turns:
            all_keywords.extend(turn.keywords)
        return list(set(all_keywords))[:5]
    
    def _summarize_sentiment(self) -> Dict:
        if not self.recent_turns:
            return {'dominant': 'neutral', 'trend': 'stable'}
        
        sentiments = []
        for turn in self.recent_turns:
            if turn.sentiment_result:
                sentiments.append(turn.sentiment_result.get('predicted_label'))
        
        if not sentiments:
            return {'dominant': 'neutral', 'trend': 'stable'}
        
        from collections import Counter
        dominant = Counter(sentiments).most_common(1)[0][0]
        
        if len(sentiments) >= 3:
            first_half = sentiments[:len(sentiments)//2]
            second_half = sentiments[len(sentiments)//2:]
            
            first_neg = sum(1 for s in first_half if s in ['angry', 'disappointed', 'anxious'])
            second_neg = sum(1 for s in second_half if s in ['angry', 'disappointed', 'anxious'])
            
            if second_neg > first_neg:
                trend = 'deteriorating'
            elif second_neg < first_neg:
                trend = 'improving'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {'dominant': dominant, 'trend': trend}


class ContextEncoder:
    def __init__(self, context_window: int = None, summary_size: int = None):
        self.context_window = context_window or int(os.getenv('CONTEXT_WINDOW', 8))
        self.summary_size = summary_size or int(os.getenv('SUMMARY_SIZE', 5))
        self.embedding_dim = 768
    
    def encode_context(self, conversation_history: List[ConversationTurn]) -> np.ndarray:
        if not conversation_history:
            return np.zeros(self.embedding_dim)
            
        recent_turns = conversation_history[-self.context_window:]
        
        embeddings = [turn.embedding for turn in recent_turns if turn.embedding is not None]
        
        if embeddings:
            weights = [getattr(turn, 'importance_score', 0.5) + 0.5 
                      for turn in recent_turns if turn.embedding is not None]
            weights = np.array(weights) / sum(weights)
            return np.average(embeddings, axis=0, weights=weights)
        
        return np.zeros(self.embedding_dim)
    
    def get_context_text(self, conversation_history: List[ConversationTurn]) -> List[str]:
        return [f"{turn.speaker}: {turn.text}" for turn in conversation_history[-self.context_window:]]


def create_sliding_window_context() -> SlidingWindowContext:
    return SlidingWindowContext()
