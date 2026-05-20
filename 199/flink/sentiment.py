import re
import time
from typing import Dict, List, Tuple, Optional
from collections import deque, defaultdict

try:
    from snownlp import SnowNLP
    HAS_SNOWNLP = True
except ImportError:
    HAS_SNOWNLP = False

from config import SENTIMENT_CONFIG
from .live_dictionary import LiveDictionary


class SentimentAnalyzer:
    def __init__(self):
        self.positive_threshold = SENTIMENT_CONFIG['positive_threshold']
        self.negative_threshold = SENTIMENT_CONFIG['negative_threshold']
        self._sentiment_window = deque(maxlen=1000)

        self._dictionary = LiveDictionary()

        self._base_weight = 0.4
        self._jargon_weight = 0.35
        self._keyword_weight = 0.15
        self._emoticon_weight = 0.1

        self._fine_tune_stats = defaultdict(lambda: {'count': 0, 'correct': 0})
        self._dynamic_weights = {}

    def _base_sentiment(self, text: str) -> float:
        clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        if not clean_text:
            return 0.5

        if HAS_SNOWNLP:
            try:
                s = SnowNLP(clean_text)
                return s.sentiments
            except:
                pass

        score = 0.5
        positive_words = self._dictionary.get_jargon_by_sentiment('positive')
        negative_words = self._dictionary.get_jargon_by_sentiment('negative')

        for word, weight in positive_words:
            if word in clean_text:
                score += abs(weight) * 0.1

        for word, weight in negative_words:
            if word in clean_text:
                score -= abs(weight) * 0.1

        return max(0.0, min(1.0, score))

    def _jargon_sentiment(self, text: str) -> Tuple[float, int, List[Tuple[str, float]]]:
        score, count, matches = self._dictionary.match_jargon(text)

        if count == 0:
            return 0.5, 0, []

        normalized = 0.5 + score / (count * 0.4)
        normalized = max(0.0, min(1.0, normalized))

        return normalized, count, matches

    def _keyword_sentiment(self, text: str) -> float:
        score = 0.5
        match_count = 0

        positive_keywords = [
            '好', '棒', '赞', '喜欢', '爱', '不错', '优秀', '完美', '超值', '划算',
            '便宜', '好看', '漂亮', '帅气', '好听', '舒服', '满意', '推荐', '回购',
        ]
        negative_keywords = [
            '差', '烂', '垃圾', '不好', '不行', '失望', '后悔', '退', '差评',
            '贵', '慢', '假的', '骗人', '坑', '难用', '丑陋', '难听', '难受',
        ]

        for word in positive_keywords:
            if word in text:
                score += 0.05
                match_count += 1

        for word in negative_keywords:
            if word in text:
                score -= 0.05
                match_count += 1

        if match_count > 0:
            return max(0.0, min(1.0, score))
        else:
            return 0.5

    def _emoticon_sentiment(self, text: str) -> Tuple[float, int]:
        score, count, _ = self._dictionary.match_emoticons(text)

        if count == 0:
            return 0.0, 0

        normalized = score / (count * 0.3)
        return normalized, count

    def _calculate_dynamic_jargon_weight(self, jargon_count: int) -> float:
        base = self._jargon_weight
        if jargon_count == 0:
            return 0.0
        elif jargon_count == 1:
            return base * 0.7
        elif jargon_count == 2:
            return base * 0.9
        elif jargon_count >= 5:
            return min(base * 1.3, 0.5)
        else:
            return base

    def _calculate_dynamic_keyword_weight(self, keyword_score: float) -> float:
        base = self._keyword_weight
        if abs(keyword_score - 0.5) < 0.05:
            return 0.0
        elif abs(keyword_score - 0.5) > 0.2:
            return min(base * 1.3, 0.4)
        else:
            return base

    def _calculate_dynamic_emoticon_weight(self, emoticon_count: int) -> float:
        base = self._emoticon_weight
        if emoticon_count == 0:
            return 0.0
        elif emoticon_count >= 3:
            return min(base * 1.5, 0.15)
        else:
            return base

    def analyze(self, text: str, event_timestamp: Optional[float] = None) -> Dict:
        original_text = text
        clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)

        base_score = self._base_sentiment(clean_text)
        jargon_score, jargon_count, jargon_matches = self._jargon_sentiment(original_text)
        keyword_score = self._keyword_sentiment(clean_text)
        emoticon_score, emoticon_count = self._emoticon_sentiment(original_text)

        jargon_weight = self._calculate_dynamic_jargon_weight(jargon_count)
        keyword_weight = self._calculate_dynamic_keyword_weight(keyword_score)
        emoticon_weight = self._calculate_dynamic_emoticon_weight(emoticon_count)

        total_weight = self._base_weight + jargon_weight + keyword_weight + emoticon_weight
        if total_weight == 0:
            final_score = 0.5
        else:
            normalized_jargon = jargon_score
            normalized_keyword = keyword_score
            normalized_emoticon = 0.5 + emoticon_score

            final_score = (
                base_score * (self._base_weight / total_weight) +
                normalized_jargon * (jargon_weight / total_weight) +
                normalized_keyword * (keyword_weight / total_weight) +
                normalized_emoticon * (emoticon_weight / total_weight)
            )

        final_score = max(0.0, min(1.0, final_score))

        if final_score >= self.positive_threshold:
            label = 'positive'
        elif final_score <= self.negative_threshold:
            label = 'negative'
        else:
            label = 'neutral'

        concerns = self._dictionary.classify_concern(original_text)
        categories = self._dictionary.classify_product_category(original_text)

        ts = event_timestamp if event_timestamp is not None else time.time()

        result = {
            'text': original_text,
            'clean_text': clean_text,
            'score': round(final_score, 4),
            'label': label,
            'event_timestamp': ts,
            'process_timestamp': time.time(),
            'concerns': concerns,
            'product_categories': categories,
            'jargon_matches': jargon_count,
            'emoticon_matches': emoticon_count,
            'components': {
                'base_score': round(base_score, 4),
                'jargon_score': round(jargon_score, 4),
                'keyword_score': round(keyword_score, 4),
                'emoticon_score': round(emoticon_score, 4),
                'base_weight': round(self._base_weight, 4),
                'jargon_weight': round(jargon_weight, 4),
                'keyword_weight': round(keyword_weight, 4),
                'emoticon_weight': round(emoticon_weight, 4),
            }
        }

        self._sentiment_window.append({
            'score': final_score,
            'label': label,
            'event_timestamp': ts,
            'process_timestamp': time.time(),
            'concerns': concerns,
        })

        return result

    def get_statistics(self, use_event_time: bool = False) -> Dict:
        if not self._sentiment_window:
            return {
                'positive_count': 0,
                'neutral_count': 0,
                'negative_count': 0,
                'avg_score': 0.5,
                'positive_rate': 0.0,
                'negative_rate': 0.0,
                'top_concerns': [],
                'avg_processing_latency': 0.0,
            }

        total = len(self._sentiment_window)
        positive = sum(1 for s in self._sentiment_window if s['label'] == 'positive')
        negative = sum(1 for s in self._sentiment_window if s['label'] == 'negative')
        neutral = total - positive - negative
        avg_score = sum(s['score'] for s in self._sentiment_window) / total

        concern_counter = defaultdict(int)
        for s in self._sentiment_window:
            for c in s.get('concerns', []):
                concern_counter[c] += 1

        top_concerns = sorted(
            concern_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        latencies = [s['process_timestamp'] - s['event_timestamp'] for s in self._sentiment_window if 'event_timestamp' in s]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return {
            'positive_count': positive,
            'neutral_count': neutral,
            'negative_count': negative,
            'avg_score': round(avg_score, 4),
            'positive_rate': round(positive / total, 4),
            'negative_rate': round(negative / total, 4),
            'top_concerns': [{'concern': c, 'count': cnt} for c, cnt in top_concerns],
            'avg_processing_latency': round(avg_latency, 4),
        }

    def fine_tune(self, text: str, expected_label: str, event_timestamp: Optional[float] = None) -> Dict:
        result = self.analyze(text, event_timestamp)
        actual_label = result['label']
        is_correct = actual_label == expected_label

        if result['jargon_matches'] > 0:
            jargon_score = result['components']['jargon_score']
            if expected_label == 'positive' and jargon_score < 0.6:
                self._jargon_weight = min(self._jargon_weight * 1.05, 0.5)
            elif expected_label == 'negative' and jargon_score > 0.4:
                self._jargon_weight = min(self._jargon_weight * 1.05, 0.5)

        for word, weight in self._dictionary.get_jargon_by_sentiment(expected_label):
            if word in text:
                current = self._dictionary.get_word_weight(word)
                if expected_label == 'positive' and current < 0.3:
                    self._dictionary.adjust_word_weight(word, min(current * 1.1, 0.4))
                elif expected_label == 'negative' and current > -0.3:
                    self._dictionary.adjust_word_weight(word, max(current * 1.1, -0.4))

        return {
            'text': text,
            'expected': expected_label,
            'actual': actual_label,
            'is_correct': is_correct,
            'score': result['score'],
            'jargon_matches': result['jargon_matches'],
        }

    def get_dictionary(self) -> LiveDictionary:
        return self._dictionary

    def get_weights(self) -> Dict:
        return {
            'base_weight': self._base_weight,
            'jargon_weight': self._jargon_weight,
            'keyword_weight': self._keyword_weight,
            'emoticon_weight': self._emoticon_weight,
        }

    def set_weights(self, base: Optional[float] = None, jargon: Optional[float] = None,
                    keyword: Optional[float] = None, emoticon: Optional[float] = None):
        if base is not None:
            self._base_weight = max(0.0, min(1.0, base))
        if jargon is not None:
            self._jargon_weight = max(0.0, min(1.0, jargon))
        if keyword is not None:
            self._keyword_weight = max(0.0, min(1.0, keyword))
        if emoticon is not None:
            self._emoticon_weight = max(0.0, min(1.0, emoticon))
