import logging
import re
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)

try:
    from snownlp import SnowNLP
    SNOWNLP_AVAILABLE = True
except ImportError:
    SNOWNLP_AVAILABLE = False
    logger.warning("SnowNLP not installed. Will use fallback sentiment analysis.")

from config import Config
from .text_processor import TextProcessor


class SentimentAnalyzer:
    def __init__(self):
        self.text_processor = TextProcessor()
        self.threshold = Config.SENTIMENT_THRESHOLD
        
        self.emoji_sentiment = self._init_emoji_sentiment()
        
        self.positive_keywords = {
            '好', '棒', '优秀', '喜欢', '爱', '满意', '开心', '快乐', '高兴', '幸福',
            '赞', '推荐', '支持', '感谢', '感激', '精彩', '完美', '出色', '厉害', '强',
            'good', 'great', 'excellent', 'amazing', 'love', 'like', 'best', 'wonderful',
            'fantastic', 'awesome', 'happy', 'satisfied', 'recommend', 'thank', 'perfect',
            'brilliant', 'outstanding', 'superb', 'nice', 'pleasant', 'positive',
            '惊喜', '震撼', '惊艳', '舒服', '治愈', '温馨', '感动', '振奋', '鼓舞'
        }
        
        self.negative_keywords = {
            '差', '烂', '糟糕', '失望', '讨厌', '恨', '不满', '难过', '伤心', '痛苦',
            '坑', '避雷', '垃圾', '无语', '愤怒', '生气', '后悔', '失败', '崩溃', '焦虑',
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'worst', 'poor',
            'disappointed', 'angry', 'upset', 'sad', 'frustrated', 'annoyed', 'negative',
            'useless', 'waste', 'avoid', 'failed', 'broken', 'rude', 'unhelpful',
            '恶心', '变态', '垃圾', '骗子', '虚假', '诈骗', '恐惧', '绝望', '沮丧'
        }
        
        self.negation_words = {
            '不', '没', '没有', '别', '勿', '非', '无', '未', '否',
            'not', "don't", "doesn't", "didn't", "won't", "can't", "couldn't",
            "wouldn't", "shouldn't", "isn't", "aren't", "wasn't", "weren't",
            'never', 'no', 'none', 'nobody', 'nowhere', 'neither', 'nor'
        }
        
        self.intensifiers = {
            '非常': 2.0, '很': 1.5, '太': 2.0, '特别': 1.8, '极其': 2.5,
            '十分': 1.8, '相当': 1.5, '格外': 1.6, '分外': 1.5, '更加': 1.5,
            '越发': 1.4, '多么': 1.8, '真的': 1.5, '确实': 1.4, '实在': 1.6,
            '绝对': 2.0, '完全': 1.8, '彻底': 2.0, '超级': 2.0, '巨': 2.5,
            '超': 1.8, '爆': 2.0, '炸': 2.0,
            'very': 1.5, 'really': 1.5, 'extremely': 2.0, 'absolutely': 2.0,
            'totally': 1.8, 'completely': 1.8, 'incredibly': 2.0, 'unbelievably': 2.0
        }
        
        self.diminishers = {
            '有点': 0.7, '稍微': 0.7, '略微': 0.7, '一点': 0.7, '些微': 0.8,
            '稍稍': 0.7, '略': 0.7, '比较': 0.8, '还算': 0.7, '勉强': 0.6,
            '稍微': 0.7, 'a bit': 0.7, 'slightly': 0.7, 'somewhat': 0.7,
            'relatively': 0.8, 'fairly': 0.7, 'quite': 0.8
        }
        
        self.context_window = 3
    
    def _init_emoji_sentiment(self) -> Dict[str, float]:
        emoji_map = {}
        
        positive_emojis = {
            '😀': 0.9, '😃': 0.9, '😄': 0.9, '😁': 0.9, '😆': 0.9, '😅': 0.7,
            '😂': 0.85, '🤣': 0.9, '😊': 0.8, '😇': 0.85, '🥰': 0.95, '😍': 0.95,
            '🤩': 0.9, '😘': 0.9, '😗': 0.8, '😚': 0.8, '😙': 0.8, '🥲': 0.6,
            '😋': 0.8, '😛': 0.7, '😜': 0.7, '🤪': 0.7, '😝': 0.7, '🤑': 0.7,
            '🤗': 0.85, '🤭': 0.7, '🤫': 0.6, '🤔': 0.5, '🤐': 0.5, '🤨': 0.5,
            '😐': 0.5, '😑': 0.4, '😶': 0.4, '😏': 0.6, '😒': 0.4, '🙄': 0.3,
            '😬': 0.4, '🤥': 0.3, '😌': 0.75, '😔': 0.35, '😪': 0.4, '🤤': 0.65,
            '😴': 0.5, '😷': 0.3, '🤒': 0.25, '🤕': 0.25, '🤢': 0.2, '🤮': 0.15,
            '🤧': 0.3, '🥵': 0.4, '🥶': 0.35, '🥴': 0.4, '😵': 0.35, '🤯': 0.3,
            '🤠': 0.75, '🥳': 0.9, '🥸': 0.6, '😎': 0.8, '🤓': 0.7, '🧐': 0.6,
            '😕': 0.35, '😟': 0.3, '🙁': 0.25, '😮': 0.5, '😯': 0.55, '😲': 0.6,
            '😳': 0.4, '🥺': 0.5, '😦': 0.3, '😧': 0.25, '😨': 0.2, '😰': 0.25,
            '😥': 0.3, '😢': 0.2, '😭': 0.15, '😱': 0.1, '😖': 0.25, '😣': 0.25,
            '😞': 0.25, '😓': 0.3, '😩': 0.2, '😫': 0.15, '🥱': 0.45, '😤': 0.2,
            '😡': 0.1, '😠': 0.15, '🤬': 0.05, '😈': 0.4, '👿': 0.3, '💀': 0.2,
            '☠️': 0.1, '💩': 0.1, '🤡': 0.5, '👹': 0.3, '👺': 0.3, '👻': 0.5,
            '👽': 0.55, '👾': 0.6, '🤖': 0.6, '😺': 0.85, '😸': 0.8, '😹': 0.85,
            '😻': 0.95, '😼': 0.75, '😽': 0.8, '🙀': 0.3, '😿': 0.2, '😾': 0.15,
            '❤️': 0.95, '🧡': 0.9, '💛': 0.9, '💚': 0.9, '💙': 0.9, '💜': 0.9,
            '🖤': 0.7, '🤍': 0.8, '🤎': 0.8, '💔': 0.15, '❣️': 0.9, '💕': 0.9,
            '💞': 0.9, '💓': 0.9, '💗': 0.9, '💖': 0.9, '💘': 0.9, '💝': 0.9,
            '👍': 0.85, '👎': 0.15, '👏': 0.85, '🙌': 0.9, '👐': 0.75, '🤲': 0.7,
            '🤝': 0.8, '🙏': 0.8, '✌️': 0.75, '🤞': 0.7, '🤟': 0.85, '🤘': 0.8,
            '🤙': 0.75, '👋': 0.7, '🖐️': 0.6, '✋': 0.6, '👌': 0.8, '🤌': 0.7,
            '🤏': 0.6, '✊': 0.7, '👊': 0.65, '🤛': 0.65, '🤜': 0.65, '👏': 0.85,
            '🔥': 0.85, '💯': 0.9, '✨': 0.8, '🌟': 0.85, '⭐': 0.8, '🎉': 0.9,
            '🎊': 0.9, '🎁': 0.8, '🏆': 0.85, '🥇': 0.85, '💪': 0.85, '🦾': 0.8,
        }
        
        neutral_emojis = {
            '😐': 0.5, '😑': 0.5, '😶': 0.5, '🤔': 0.5, '🤐': 0.5, '🤨': 0.5,
            '😮': 0.5, '😯': 0.5, '🙄': 0.5, '🤭': 0.5, '🤫': 0.5,
            '👻': 0.5, '👽': 0.5, '👾': 0.5, '🤖': 0.5, '🤡': 0.5,
            '🖐️': 0.5, '✋': 0.5, '🤏': 0.5,
        }
        
        for emoji, score in positive_emojis.items():
            emoji_map[emoji] = score
        
        for emoji, score in neutral_emojis.items():
            if emoji not in emoji_map:
                emoji_map[emoji] = score
        
        return emoji_map
    
    def _extract_emojis(self, text: str) -> List[Tuple[str, float]]:
        emojis = []
        for char in text:
            if char in self.emoji_sentiment:
                emojis.append((char, self.emoji_sentiment[char]))
        return emojis
    
    def _analyze_context(self, tokens: List[str], target_index: int, window_size: int = 3) -> Dict:
        start = max(0, target_index - window_size)
        end = min(len(tokens), target_index + window_size + 1)
        context_tokens = tokens[start:end]
        
        context_score = 1.0
        has_negation = False
        intensifier_multiplier = 1.0
        
        for token in context_tokens:
            if token in self.negation_words:
                has_negation = True
            if token in self.intensifiers:
                intensifier_multiplier *= self.intensifiers[token]
            if token in self.diminishers:
                intensifier_multiplier *= self.diminishers[token]
        
        if has_negation:
            context_score *= -0.7
        
        context_score *= intensifier_multiplier
        
        return {
            'score': context_score,
            'has_negation': has_negation,
            'intensifier': intensifier_multiplier,
            'context_tokens': context_tokens
        }
    
    def analyze(self, text: str) -> Dict:
        if not text or not text.strip():
            return {
                'sentiment': 'neutral',
                'positive': 0.5,
                'negative': 0.5,
                'neutral': 0.0,
                'confidence': 0.0,
                'emoji_features': [],
                'context_features': []
            }
        
        is_chinese = self.text_processor.is_chinese(text)
        
        emoji_features = self._extract_emojis(text)
        emoji_sentiment_score = 0.0
        if emoji_features:
            emoji_sentiment_score = sum(score for _, score in emoji_features) / len(emoji_features)
        
        if SNOWNLP_AVAILABLE and is_chinese:
            base_result = self._analyze_with_snownlp(text)
        else:
            base_result = self._analyze_with_keywords(text)
        
        if emoji_features:
            base_pos = base_result['positive']
            base_neg = base_result['negative']
            base_neu = base_result['neutral']
            
            emoji_weight = min(0.3, len(emoji_features) * 0.1)
            
            if emoji_sentiment_score >= 0.6:
                base_pos = base_pos * (1 - emoji_weight) + emoji_sentiment_score * emoji_weight
            elif emoji_sentiment_score <= 0.4:
                base_neg = base_neg * (1 - emoji_weight) + (1 - emoji_sentiment_score) * emoji_weight
            
            total = base_pos + base_neg + base_neu
            base_result['positive'] = round(base_pos / total, 4)
            base_result['negative'] = round(base_neg / total, 4)
            base_result['neutral'] = round(base_neu / total, 4)
            
            if base_result['positive'] >= self.threshold['positive']:
                base_result['sentiment'] = 'positive'
            elif base_result['negative'] >= self.threshold['negative']:
                base_result['sentiment'] = 'negative'
            else:
                base_result['sentiment'] = 'neutral'
            
            base_result['confidence'] = round(max(base_result['positive'], base_result['negative'], base_result['neutral']), 4)
        
        base_result['emoji_features'] = [
            {'emoji': e, 'sentiment_score': s} for e, s in emoji_features
        ]
        base_result['emoji_sentiment'] = round(emoji_sentiment_score, 4) if emoji_features else 0.5
        
        return base_result
    
    def _analyze_with_snownlp(self, text: str) -> Dict:
        try:
            cleaned_text = self.text_processor.clean_text(text)
            if not cleaned_text:
                return self._get_neutral_result()
            
            s = SnowNLP(cleaned_text)
            sentiment_score = s.sentiments
            
            sentences = s.sentences
            sentence_sentiments = []
            for sent in sentences:
                try:
                    sent_s = SnowNLP(sent)
                    sentence_sentiments.append(sent_s.sentiments)
                except:
                    pass
            
            context_aware_score = sentiment_score
            if sentence_sentiments:
                avg_sent = sum(sentence_sentiments) / len(sentence_sentiments)
                context_aware_score = sentiment_score * 0.7 + avg_sent * 0.3
            
            positive_score = context_aware_score
            negative_score = 1 - context_aware_score
            neutral_score = 0.0
            
            if abs(positive_score - 0.5) < 0.1:
                neutral_score = 0.2
                positive_score = (positive_score - 0.5) * 0.8 + 0.5
                negative_score = (negative_score - 0.5) * 0.8 + 0.5
                total = positive_score + negative_score + neutral_score
                positive_score /= total
                negative_score /= total
                neutral_score /= total
            
            if positive_score >= self.threshold['positive']:
                sentiment = 'positive'
            elif negative_score >= (1 - self.threshold['negative']):
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            confidence = max(positive_score, negative_score, neutral_score)
            
            return {
                'sentiment': sentiment,
                'positive': round(positive_score, 4),
                'negative': round(negative_score, 4),
                'neutral': round(neutral_score, 4),
                'confidence': round(confidence, 4),
                'sentence_count': len(sentences),
                'sentence_sentiments': [round(s, 4) for s in sentence_sentiments]
            }
            
        except Exception as e:
            logger.warning(f"Snownlp analysis failed, falling back to keywords: {e}")
            return self._analyze_with_keywords(text)
    
    def _analyze_with_keywords(self, text: str) -> Dict:
        try:
            cleaned_text = self.text_processor.clean_text(text)
            tokens = self.text_processor.tokenize(cleaned_text, remove_stopwords=False)
            
            if not tokens:
                return self._get_neutral_result()
            
            positive_count = 0.0
            negative_count = 0.0
            context_features = []
            
            for i, token in enumerate(tokens):
                if token in self.negation_words:
                    continue
                
                context = self._analyze_context(tokens, i, self.context_window)
                weight = context['score']
                
                if token in self.positive_keywords:
                    positive_count += 1.0 * weight
                    context_features.append({
                        'token': token,
                        'type': 'positive',
                        'context_score': weight,
                        'position': i
                    })
                elif token in self.negative_keywords:
                    negative_count += 1.0 * weight
                    context_features.append({
                        'token': token,
                        'type': 'negative',
                        'context_score': weight,
                        'position': i
                    })
            
            positive_count = max(0, positive_count)
            negative_count = max(0, negative_count)
            
            total = positive_count + negative_count
            
            if total == 0:
                return self._get_neutral_result()
            
            positive_score = positive_count / total
            negative_score = negative_count / total
            neutral_score = 0.0
            
            if abs(positive_score - negative_score) < 0.15:
                neutral_score = 0.3
                positive_score *= 0.7
                negative_score *= 0.7
                total = positive_score + negative_score + neutral_score
                positive_score /= total
                negative_score /= total
                neutral_score /= total
            
            if positive_score >= self.threshold['positive']:
                sentiment = 'positive'
            elif negative_score >= self.threshold['negative']:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            confidence = max(positive_score, negative_score, neutral_score)
            
            return {
                'sentiment': sentiment,
                'positive': round(positive_score, 4),
                'negative': round(negative_score, 4),
                'neutral': round(neutral_score, 4),
                'confidence': round(confidence, 4),
                'context_features': context_features,
                'positive_count': round(positive_count, 2),
                'negative_count': round(negative_count, 2)
            }
            
        except Exception as e:
            logger.error(f"Keyword sentiment analysis failed: {e}")
            return self._get_neutral_result()
    
    def _get_neutral_result(self) -> Dict:
        return {
            'sentiment': 'neutral',
            'positive': 0.33,
            'negative': 0.33,
            'neutral': 0.34,
            'confidence': 0.34,
            'emoji_features': [],
            'context_features': []
        }
    
    def analyze_batch(self, texts: list) -> list:
        results = []
        for text in texts:
            results.append(self.analyze(text))
        return results
    
    def get_sentiment_distribution(self, sentiments: list) -> Dict:
        if not sentiments:
            return {'positive': 0, 'negative': 0, 'neutral': 0}
        
        counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        for s in sentiments:
            sentiment = s.get('sentiment', 'neutral')
            if sentiment in counts:
                counts[sentiment] += 1
        
        total = len(sentiments)
        return {
            'positive': round(counts['positive'] / total, 4),
            'negative': round(counts['negative'] / total, 4),
            'neutral': round(counts['neutral'] / total, 4),
            'counts': counts
        }
    
    def analyze_with_context(self, text: str, context_texts: List[str] = None) -> Dict:
        base_result = self.analyze(text)
        
        if context_texts:
            context_sentiments = []
            for ctx in context_texts:
                ctx_result = self.analyze(ctx)
                context_sentiments.append(ctx_result)
            
            if context_sentiments:
                avg_context_pos = sum(s['positive'] for s in context_sentiments) / len(context_sentiments)
                avg_context_neg = sum(s['negative'] for s in context_sentiments) / len(context_sentiments)
                
                context_weight = 0.2
                base_result['positive'] = round(
                    base_result['positive'] * (1 - context_weight) + avg_context_pos * context_weight, 4
                )
                base_result['negative'] = round(
                    base_result['negative'] * (1 - context_weight) + avg_context_neg * context_weight, 4
                )
                
                total = base_result['positive'] + base_result['negative'] + base_result['neutral']
                base_result['positive'] = round(base_result['positive'] / total, 4)
                base_result['negative'] = round(base_result['negative'] / total, 4)
                base_result['neutral'] = round(base_result['neutral'] / total, 4)
                
                if base_result['positive'] >= self.threshold['positive']:
                    base_result['sentiment'] = 'positive'
                elif base_result['negative'] >= self.threshold['negative']:
                    base_result['sentiment'] = 'negative'
                else:
                    base_result['sentiment'] = 'neutral'
                
                base_result['confidence'] = round(
                    max(base_result['positive'], base_result['negative'], base_result['neutral']), 4
                )
                base_result['context_aware'] = True
                base_result['context_sentiment_count'] = len(context_sentiments)
        
        return base_result
