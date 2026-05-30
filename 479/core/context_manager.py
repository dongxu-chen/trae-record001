import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque
import os
from dotenv import load_dotenv

from .context_encoder import ConversationTurn, SlidingWindowContext, ContextEncoder

load_dotenv()


class ConversationManager:
    def __init__(self, max_history: int = 100):
        self.conversations: Dict[str, deque] = {}
        self.sliding_windows: Dict[str, SlidingWindowContext] = {}
        self.context_encoder = ContextEncoder()
        self.max_history = max_history
        
    def add_turn(self, session_id: str, text: str, speaker: str, 
                 sentiment_result: Dict = None, embedding: np.ndarray = None) -> ConversationTurn:
        if session_id not in self.conversations:
            self.conversations[session_id] = deque(maxlen=self.max_history)
            self.sliding_windows[session_id] = SlidingWindowContext()
            
        import time
        turn = ConversationTurn(
            text=text,
            speaker=speaker,
            sentiment_result=sentiment_result,
            timestamp=time.time()
        )
        turn.embedding = embedding
        
        history = self.get_history(session_id)
        previous_turn = history[-1] if history else None
        
        turn.keywords = self.sliding_windows[session_id].keyword_extractor.extract(text)
        turn.importance_score = self.sliding_windows[session_id].importance_scorer.calculate_score(turn, previous_turn)
        
        self.conversations[session_id].append(turn)
        self.sliding_windows[session_id].add_turn(turn, previous_turn)
        
        return turn
    
    def get_history(self, session_id: str) -> List[ConversationTurn]:
        return list(self.conversations.get(session_id, []))
    
    def get_context_text(self, session_id: str) -> List[str]:
        if session_id in self.sliding_windows:
            return self.sliding_windows[session_id].get_context_text()
        return []
    
    def get_context_summary(self, session_id: str) -> Dict:
        if session_id in self.sliding_windows:
            return self.sliding_windows[session_id].get_summary()
        return {'summary_turns': [], 'recent_turns': [], 'key_topics': [], 'sentiment_summary': {}}
    
    def get_context_embedding(self, session_id: str) -> np.ndarray:
        history = self.get_history(session_id)
        return self.context_encoder.encode_context(history)
    
    def get_sentiment_history(self, session_id: str) -> List[Dict]:
        history = self.get_history(session_id)
        return [
            {
                'turn': i,
                'speaker': turn.speaker,
                'sentiment': turn.sentiment_result,
                'confidence': turn.sentiment_result.get('confidence') if turn.sentiment_result else None,
                'importance_score': turn.importance_score,
                'is_turning_point': turn.is_turning_point
            }
            for i, turn in enumerate(history)
            if turn.speaker == 'customer'
        ]
    
    def get_important_turns(self, session_id: str) -> List[Dict]:
        if session_id in self.sliding_windows:
            return [t.to_dict() for t in self.sliding_windows[session_id].important_turns]
        return []
    
    def clear_conversation(self, session_id: str):
        if session_id in self.conversations:
            self.conversations[session_id].clear()
        if session_id in self.sliding_windows:
            self.sliding_windows[session_id] = SlidingWindowContext()
    
    def remove_conversation(self, session_id: str):
        if session_id in self.conversations:
            del self.conversations[session_id]
        if session_id in self.sliding_windows:
            del self.sliding_windows[session_id]


def create_conversation_manager() -> ConversationManager:
    return ConversationManager()
