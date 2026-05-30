import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import re


@dataclass
class SentimentChangeEvent:
    turn_index: int
    change_type: str
    change_magnitude: float
    from_sentiment: str
    to_sentiment: str
    cause_turn_index: int
    cause_text: str
    cause_speaker: str
    evidence: List[str]
    confidence: float
    
    def to_dict(self) -> Dict:
        return {
            'turn_index': self.turn_index,
            'change_type': self.change_type,
            'change_magnitude': self.change_magnitude,
            'from_sentiment': self.from_sentiment,
            'to_sentiment': self.to_sentiment,
            'cause_turn_index': self.cause_turn_index,
            'cause_text': self.cause_text,
            'cause_speaker': self.cause_speaker,
            'evidence': self.evidence,
            'confidence': self.confidence
        }


class AttributionAnalyzer:
    def __init__(self):
        self.negative_triggers = {
            'refuse': ['不能', '无法', '不行', '不可以', '没办法', '做不到', '不符合', '不满足'],
            'delay': ['等一下', '稍后', '明天', '下周', '需要时间', '处理中', '排队'],
            'blame': ['是你', '你应该', '你没有', '你的问题', '你自己'],
            'procedure': ['流程', '规定', '制度', '必须', '需要先', '按照要求'],
            'transfer': ['转接', '其他部门', '不是我们', '找别人', '不归我们管']
        }
        
        self.positive_triggers = {
            'solve': ['解决了', '可以了', '好了', '处理完成', '已解决', '成功'],
            'compensate': ['补偿', '赠送', '优惠券', '减免', '退款', '赔偿', '折扣'],
            'empathy': ['理解', '抱歉', '对不起', '确实是我们', '给您添麻烦'],
            'efficient': ['马上', '立刻', '立即', '已经', '很快', '第一时间'],
            'respect': ['您说的对', '感谢您', '非常理解', '您放心', '我们重视']
        }
        
        self.emotion_intensifiers = {
            'strong': ['非常', '极其', '特别', '简直', '太', '真的', '实在', '居然', '竟然'],
            'weak': ['有点', '稍微', '可能', '也许', '大概', '似乎', '好像']
        }

    def _calculate_sentiment_score(self, sentiment_result: Dict) -> float:
        scores = sentiment_result.get('scores', {})
        positive = scores.get('satisfied', 0)
        negative = scores.get('angry', 0) + scores.get('disappointed', 0) + scores.get('anxious', 0)
        return positive - negative

    def _detect_emotional_change(self, current: Dict, previous: Dict) -> Tuple[bool, str, float]:
        if not previous or not current:
            return False, 'stable', 0.0
        
        curr_score = self._calculate_sentiment_score(current)
        prev_score = self._calculate_sentiment_score(previous)
        change = curr_score - prev_score
        
        curr_label = current.get('predicted_label', 'neutral')
        prev_label = previous.get('predicted_label', 'neutral')
        
        if change > 0.3 and curr_label == 'satisfied' and prev_label != 'satisfied':
            return True, 'positive_turn', abs(change)
        elif change < -0.3 and curr_label in ['angry', 'disappointed', 'anxious'] and prev_label not in ['angry', 'disappointed', 'anxious']:
            return True, 'negative_turn', abs(change)
        elif change < -0.2 and curr_label in ['angry', 'disappointed', 'anxious']:
            return True, 'further_deterioration', abs(change)
        elif change > 0.2 and curr_label == 'satisfied':
            return True, 'further_improvement', abs(change)
        
        return False, 'stable', abs(change)

    def _find_trigger_words(self, text: str, triggers: Dict[str, List[str]]) -> List[str]:
        found = []
        text_lower = text.lower()
        for category, words in triggers.items():
            for word in words:
                if word in text_lower:
                    found.append(f"[{category}] {word}")
        return found

    def _calculate_cause_confidence(self, cause_turn: Dict, change_magnitude: float, 
                                    evidence: List[str], time_decay: float) -> float:
        base_confidence = min(change_magnitude * 0.8, 0.8)
        evidence_bonus = min(len(evidence) * 0.1, 0.3)
        decay_penalty = time_decay * 0.2
        
        sentiment = cause_turn.get('sentiment', {})
        speaker = cause_turn.get('speaker', '')
        speaker_bonus = 0.1 if speaker == 'agent' else 0
        
        confidence = base_confidence + evidence_bonus + speaker_bonus - decay_penalty
        return max(0.1, min(1.0, confidence))

    def attribute_sentiment_change(self, conversation_history: List[Dict], 
                                    change_turn_index: int) -> Optional[SentimentChangeEvent]:
        if change_turn_index < 1 or change_turn_index >= len(conversation_history):
            return None
        
        current_turn = conversation_history[change_turn_index]
        previous_turn = conversation_history[change_turn_index - 1]
        
        if not current_turn.get('sentiment') or not previous_turn.get('sentiment'):
            return None
        
        has_change, change_type, magnitude = self._detect_emotional_change(
            current_turn['sentiment'], previous_turn['sentiment']
        )
        
        if not has_change:
            return None
        
        search_window = min(5, change_turn_index)
        candidate_causes = []
        
        for i in range(search_window):
            cause_idx = change_turn_index - i - 1
            cause_turn = conversation_history[cause_idx]
            
            if cause_turn.get('speaker') != 'agent':
                continue
            
            cause_text = cause_turn.get('text', '')
            time_decay = i / search_window
            
            if change_type.startswith('negative'):
                triggers = self.negative_triggers
            else:
                triggers = self.positive_triggers
            
            evidence = self._find_trigger_words(cause_text, triggers)
            
            if evidence or cause_turn.get('sentiment'):
                confidence = self._calculate_cause_confidence(
                    cause_turn, magnitude, evidence, time_decay
                )
                candidate_causes.append((cause_idx, cause_turn, evidence, confidence, time_decay))
        
        if not candidate_causes:
            for i in range(search_window):
                cause_idx = change_turn_index - i - 1
                cause_turn = conversation_history[cause_idx]
                cause_text = cause_turn.get('text', '')
                time_decay = i / search_window
                
                if change_type.startswith('negative'):
                    triggers = self.negative_triggers
                else:
                    triggers = self.positive_triggers
                
                evidence = self._find_trigger_words(cause_text, triggers)
                
                if evidence:
                    confidence = self._calculate_cause_confidence(
                        cause_turn, magnitude, evidence, time_decay
                    )
                    candidate_causes.append((cause_idx, cause_turn, evidence, confidence, time_decay))
                    break
        
        if not candidate_causes:
            cause_idx = change_turn_index - 1
            cause_turn = conversation_history[cause_idx]
            candidate_causes.append((
                cause_idx, cause_turn, 
                ['上下文关联'], 
                min(magnitude * 0.5, 0.5), 
                0
            ))
        
        best_cause = max(candidate_causes, key=lambda x: x[3])
        cause_idx, cause_turn, evidence, confidence, _ = best_cause
        
        return SentimentChangeEvent(
            turn_index=change_turn_index,
            change_type=change_type,
            change_magnitude=magnitude,
            from_sentiment=previous_turn['sentiment'].get('predicted_label_cn', ''),
            to_sentiment=current_turn['sentiment'].get('predicted_label_cn', ''),
            cause_turn_index=cause_idx,
            cause_text=cause_turn.get('text', ''),
            cause_speaker=cause_turn.get('speaker', ''),
            evidence=evidence,
            confidence=confidence
        )

    def analyze_all_changes(self, conversation_history: List[Dict]) -> List[SentimentChangeEvent]:
        changes = []
        for i in range(1, len(conversation_history)):
            if conversation_history[i].get('speaker') == 'customer':
                change_event = self.attribute_sentiment_change(conversation_history, i)
                if change_event:
                    changes.append(change_event)
        return changes

    def get_change_statistics(self, changes: List[SentimentChangeEvent]) -> Dict:
        if not changes:
            return {
                'total_changes': 0,
                'positive_changes': 0,
                'negative_changes': 0,
                'top_causes': [],
                'average_confidence': 0.0
            }
        
        positive = sum(1 for c in changes if c.change_type.startswith('positive'))
        negative = len(changes) - positive
        
        cause_counts = defaultdict(int)
        for change in changes:
            for evidence in change.evidence:
                if evidence.startswith('['):
                    category = evidence.split(']')[0][1:]
                    cause_counts[category] += 1
        
        top_causes = sorted(cause_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        avg_confidence = np.mean([c.confidence for c in changes])
        
        return {
            'total_changes': len(changes),
            'positive_changes': positive,
            'negative_changes': negative,
            'top_causes': [{'category': c, 'count': n} for c, n in top_causes],
            'average_confidence': float(avg_confidence)
        }


def create_attribution_analyzer() -> AttributionAnalyzer:
    return AttributionAnalyzer()
