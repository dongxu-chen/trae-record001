import logging
import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("Jieba not available. Chinese tokenization will use fallback method.")


class MultilingualAnalyzer:
    def __init__(self):
        self.language_keywords = {
            'zh': ['的', '是', '在', '了', '有', '和', '与', '及', '等', '也', '都', '就', '而', '这', '那'],
            'en': ['the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with'],
            'ja': ['の', 'に', 'を', 'は', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ', 'あ', 'る', 'な'],
            'ko': ['은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', '의', '로', '으로', '도', '만'],
            'es': ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'ser', 'se', 'no', 'haber', 'por', 'con', 'su', 'para'],
            'fr': ['le', 'la', 'de', 'et', 'un', 'être', 'en', 'que', 'pour', 'dans', 'ce', 'il', 'qui', 'ne', 'pas'],
            'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'auf', 'für', 'ist', 'ein', 'eine'],
        }
        
        self.code_mapping = {
            'zh': 'chinese', 'zh-CN': 'chinese', 'zh-TW': 'chinese',
            'en': 'english', 'en-US': 'english', 'en-GB': 'english',
            'ja': 'japanese', 'ko': 'korean',
            'es': 'spanish', 'fr': 'french', 'de': 'german',
        }
        
        self.stopwords = {
            'zh': {'的', '是', '在', '了', '有', '和', '与', '及', '等', '也', '都', '就', '而', '这', '那',
                   '我', '你', '他', '她', '它', '我们', '你们', '他们', '一个', '一些', '一样', '什么', '怎么',
                   '如果', '因为', '所以', '但是', '然后', '还是', '或者', '以及', '这种', '那个', '这个'},
            'en': {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                   'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                   'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used',
                   'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'up', 'about',
                   'into', 'over', 'after', 'under', 'again', 'further', 'then', 'once',
                   'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
                   'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                   'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
                   'and', 'but', 'if', 'or', 'because', 'until', 'while', 'this', 'that',
                   'these', 'those', 'am', 'i', 'me', 'my', 'we', 'our', 'you', 'your',
                   'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they', 'them', 'their'},
            'ja': {'の', 'に', 'を', 'は', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ',
                   'あ', 'る', 'な', 'い', 'か', 'も', 'け', 'ず', 'ま', 'よ', 'ん', 'つ',
                   'だ', 'ね', 'ば', 'や', 'てる', 'ない', 'ます', 'です', 'たい', 'なる',
                   'ある', 'いる', 'する', 'くる', 'おく', 'いく', 'これ', 'それ', 'あれ',
                   'この', 'その', 'あの', '何', 'どこ', 'いつ', 'だれ', 'なぜ', 'どう'},
            'ko': {'은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', '의', '로',
                   '으로', '도', '만', '부터', '까지', '처럼', '같이', '만큼', '보다', '듯이',
                   '에게', '께', '한테', '로서', '로써', '이고', '이며', '그러나', '그래서',
                   '그러면', '그러니까', '이지만', '지만', '는데', 'ㄴ데', '어야', '아야',
                   '겠다', '을까', 'ㄹ까', '나', '다', '마', '라', '자', '네', '요', '습니다'},
        }
        
        self.cross_language_keywords = {
            '产品': {'product', '制品', '제품'},
            '质量': {'quality', '品質', '품질'},
            '服务': {'service', 'サービス', '서비스'},
            '价格': {'price', '価格', '가격'},
            '手机': {'phone', 'smartphone', '携帯', '휴대폰'},
            '相机': {'camera', 'カメラ', '카메라'},
            '功能': {'feature', 'function', '機能', '기능'},
            '设计': {'design', 'デザイン', '디자인'},
            '品牌': {'brand', 'ブランド', '브랜드'},
            '用户': {'user', 'customer', 'ユーザー', '사용자'},
            '体验': {'experience', '体験', '체험'},
            '推荐': {'recommend', '推奨', '추천'},
            '满意': {'satisfied', '満足', '만족'},
            '失望': {'disappointed', '失望', '실망'},
            '问题': {'problem', 'issue', '問題', '문제'},
            '好用': {'useful', 'easy to use', '使いやすい', '쓰기 좋다'},
            '糟糕': {'terrible', 'awful', 'ひどい', '끔찍하다'},
            '惊喜': {'surprise', '驚き', '놀라움'},
            '期待': {'expect', '期待', '기대'},
            '热门': {'popular', 'hot', '人気', '인기'},
        }
        
        self.sentiment_keywords_cross_lang = {
            'good': {'zh': ['好', '棒', '优', '佳', '良'], 'ja': ['良い', '素晴らしい', '優れた'], 'ko': ['좋다', '훌륭하다']},
            'bad': {'zh': ['差', '烂', '劣', '糟'], 'ja': ['悪い', 'ひどい', '劣った'], 'ko': ['나쁘다', '끔찍하다']},
            'happy': {'zh': ['开心', '高兴', '快乐', '幸福'], 'ja': ['嬉しい', '幸せ', '満足'], 'ko': ['행복하다', '기쁘다']},
            'sad': {'zh': ['难过', '伤心', '失望', '痛苦'], 'ja': ['悲しい', 'がっかり', '失望'], 'ko': ['슬프다', '실망하다']},
            'angry': {'zh': ['愤怒', '生气', '恼火', '气愤'], 'ja': ['怒っている', '腹立たしい'], 'ko': ['화가 나다', '짜증나다']},
        }
    
    def detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return 'unknown'
        
        zh_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        ja_chars = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]', text))
        ko_chars = len(re.findall(r'[\uac00-\ud7af]', text))
        en_chars = len(re.findall(r'[a-zA-Z]', text))
        
        total_chars = max(len(text.strip()), 1)
        
        zh_ratio = zh_chars / total_chars
        ja_ratio = ja_chars / total_chars
        ko_ratio = ko_chars / total_chars
        en_ratio = en_chars / total_chars
        
        if zh_ratio > 0.3:
            return 'zh'
        elif ko_ratio > 0.3:
            return 'ko'
        elif ja_ratio > 0.3:
            return 'ja'
        elif en_ratio > 0.3:
            return 'en'
        
        lang_scores = {}
        for lang, keywords in self.language_keywords.items():
            score = 0
            text_lower = text.lower()
            for kw in keywords:
                if kw in text_lower:
                    score += 1
            lang_scores[lang] = score / len(keywords) if keywords else 0
        
        if lang_scores:
            best_lang = max(lang_scores, key=lang_scores.get)
            if lang_scores[best_lang] > 0.01:
                return best_lang
        
        if en_chars > 0:
            return 'en'
        
        return 'unknown'
    
    def tokenize_multilingual(self, text: str, language: str = None) -> List[str]:
        if not text:
            return []
        
        if not language:
            language = self.detect_language(text)
        
        if language == 'zh':
            if JIEBA_AVAILABLE:
                tokens = list(jieba.cut(text))
            else:
                tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
        elif language == 'ja':
            tokens = re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]+|[a-zA-Z]+', text)
        elif language == 'ko':
            tokens = re.findall(r'[\uac00-\ud7af]+|[a-zA-Z]+', text)
        else:
            tokens = re.findall(r'[a-zA-Z]+', text.lower())
        
        stopwords = self.stopwords.get(language, set())
        tokens = [t for t in tokens if t.strip() and t.lower() not in stopwords]
        
        return tokens
    
    def extract_keywords_multilingual(self, text: str, language: str = None, top_k: int = 20) -> List[Tuple[str, int]]:
        if not language:
            language = self.detect_language(text)
        
        tokens = self.tokenize_multilingual(text, language)
        word_freq = Counter(tokens)
        
        return word_freq.most_common(top_k)
    
    def cross_language_keyword_mapping(self, keyword: str, source_lang: str) -> Dict[str, List[str]]:
        translations = {}
        
        if source_lang == 'zh':
            for zh_keyword, translations_set in self.cross_language_keywords.items():
                if keyword == zh_keyword or keyword in zh_keyword:
                    translations['en'] = []
                    translations['ja'] = []
                    translations['ko'] = []
                    for term in translations_set:
                        if re.match(r'^[a-zA-Z\s]+$', term):
                            translations['en'].append(term)
                        elif re.match(r'^[\u3040-\u30ff\u4e00-\u9fff]+$', term) and any('\u3040' <= c <= '\u30ff' for c in term):
                            translations['ja'].append(term)
                        elif re.match(r'^[\uac00-\ud7af]+$', term):
                            translations['ko'].append(term)
                    break
        else:
            for zh_keyword, translations_set in self.cross_language_keywords.items():
                if keyword.lower() in {t.lower() for t in translations_set}:
                    translations['zh'] = [zh_keyword]
                    translations['en'] = []
                    translations['ja'] = []
                    translations['ko'] = []
                    for term in translations_set:
                        if keyword.lower() != term.lower():
                            if re.match(r'^[a-zA-Z\s]+$', term):
                                translations['en'].append(term)
                            elif re.match(r'^[\u3040-\u30ff\u4e00-\u9fff]+$', term) and any('\u3040' <= c <= '\u30ff' for c in term):
                                translations['ja'].append(term)
                            elif re.match(r'^[\uac00-\ud7af]+$', term):
                                translations['ko'].append(term)
                    translations = {k: v for k, v in translations.items() if v}
                    break
        
        return translations
    
    def analyze_cross_language_sentiment(self, text: str, language: str = None) -> Dict:
        if not language:
            language = self.detect_language(text)
        
        tokens = self.tokenize_multilingual(text, language)
        
        sentiment_scores = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for token in tokens:
            token_lower = token.lower()
            
            for base_sentiment, translations in self.sentiment_keywords_cross_lang.items():
                if base_sentiment in ['good', 'happy']:
                    if token_lower == base_sentiment:
                        sentiment_scores['positive'] += 1
                    if language in translations and token in translations[language]:
                        sentiment_scores['positive'] += 1
                elif base_sentiment in ['bad', 'sad', 'angry']:
                    if token_lower == base_sentiment:
                        sentiment_scores['negative'] += 1
                    if language in translations and token in translations[language]:
                        sentiment_scores['negative'] += 1
        
        total = sum(sentiment_scores.values())
        
        if total == 0:
            sentiment_scores['neutral'] = 1
            total = 1
        
        return {
            'language': language,
            'sentiment': 'positive' if sentiment_scores['positive'] > sentiment_scores['negative'] else 'negative' if sentiment_scores['negative'] > sentiment_scores['positive'] else 'neutral',
            'positive': round(sentiment_scores['positive'] / total, 4),
            'negative': round(sentiment_scores['negative'] / total, 4),
            'neutral': round(sentiment_scores['neutral'] / total, 4),
            'matched_keywords': self._match_sentiment_keywords(tokens, language)
        }
    
    def _match_sentiment_keywords(self, tokens: List[str], language: str) -> Dict[str, List[str]]:
        matched = {'positive': [], 'negative': []}
        
        for token in tokens:
            token_lower = token.lower()
            for base_sentiment, translations in self.sentiment_keywords_cross_lang.items():
                if base_sentiment in ['good', 'happy']:
                    if token_lower == base_sentiment or (language in translations and token in translations[language]):
                        matched['positive'].append(token)
                elif base_sentiment in ['bad', 'sad', 'angry']:
                    if token_lower == base_sentiment or (language in translations and token in translations[language]):
                        matched['negative'].append(token)
        
        return matched
    
    def correlate_cross_language_posts(self, posts: List[Dict]) -> Dict:
        if not posts:
            return {}
        
        language_groups = defaultdict(list)
        for post in posts:
            content = post.get('content', '')
            lang = self.detect_language(content)
            post['language'] = lang
            language_groups[lang].append(post)
        
        all_keywords_by_lang = {}
        for lang, lang_posts in language_groups.items():
            all_content = ' '.join([p.get('content', '') for p in lang_posts])
            keywords = self.extract_keywords_multilingual(all_content, lang, top_k=30)
            all_keywords_by_lang[lang] = keywords
        
        cross_lang_matches = []
        for source_lang, source_keywords in all_keywords_by_lang.items():
            for target_lang, target_keywords in all_keywords_by_lang.items():
                if source_lang >= target_lang:
                    continue
                
                for src_kw, src_freq in source_keywords:
                    translations = self.cross_language_keyword_mapping(src_kw, source_lang)
                    
                    for tgt_kw, tgt_freq in target_keywords:
                        if target_lang in translations:
                            if tgt_kw in translations[target_lang] or tgt_kw.lower() in {t.lower() for t in translations[target_lang]}:
                                cross_lang_matches.append({
                                    'source_language': source_lang,
                                    'target_language': target_lang,
                                    'source_keyword': src_kw,
                                    'target_keyword': tgt_kw,
                                    'source_frequency': src_freq,
                                    'target_frequency': tgt_freq,
                                    'combined_volume': src_freq + tgt_freq
                                })
        
        cross_lang_matches.sort(key=lambda x: x['combined_volume'], reverse=True)
        
        sentiment_by_lang = {}
        for lang, lang_posts in language_groups.items():
            sentiments = []
            for p in lang_posts:
                sent_result = self.analyze_cross_language_sentiment(p.get('content', ''), lang)
                sentiments.append(sent_result['sentiment'])
            
            sentiment_counts = Counter(sentiments)
            total = len(sentiments) if sentiments else 1
            sentiment_by_lang[lang] = {
                'post_count': len(lang_posts),
                'sentiment_counts': dict(sentiment_counts),
                'sentiment_percentages': {
                    k: round(v / total, 4) for k, v in sentiment_counts.items()
                }
            }
        
        total_posts = len(posts)
        return {
            'language_distribution': {
                lang: {
                    'count': len(lang_posts),
                    'percentage': round(len(lang_posts) / total_posts, 4) if total_posts > 0 else 0
                }
                for lang, lang_posts in language_groups.items()
            },
            'top_keywords_by_language': {
                lang: [{'keyword': kw, 'frequency': freq} for kw, freq in kws[:10]]
                for lang, kws in all_keywords_by_lang.items()
            },
            'cross_language_matches': cross_lang_matches[:20],
            'sentiment_by_language': sentiment_by_lang,
            'total_languages': len(language_groups)
        }
    
    def generate_multilingual_report(self, posts: List[Dict]) -> Dict:
        correlation = self.correlate_cross_language_posts(posts)
        
        multilingual_keywords = {}
        for match in correlation.get('cross_language_matches', []):
            key = f"{match['source_keyword']}_{match['source_language']}"
            if key not in multilingual_keywords:
                multilingual_keywords[key] = {
                    'base_keyword': match['source_keyword'],
                    'base_language': match['source_language'],
                    'translations': {},
                    'total_volume': 0
                }
            
            target_lang = match['target_language']
            if target_lang not in multilingual_keywords[key]['translations']:
                multilingual_keywords[key]['translations'][target_lang] = []
            
            multilingual_keywords[key]['translations'][target_lang].append({
                'keyword': match['target_keyword'],
                'frequency': match['target_frequency']
            })
            multilingual_keywords[key]['total_volume'] += match['combined_volume']
        
        sorted_multilingual = sorted(
            multilingual_keywords.values(),
            key=lambda x: x['total_volume'],
            reverse=True
        )
        
        return {
            'correlation_analysis': correlation,
            'multilingual_trending_topics': sorted_multilingual[:10],
            'languages_covered': list(correlation.get('language_distribution', {}).keys()),
            'summary': {
                'total_posts': len(posts),
                'total_languages': correlation.get('total_languages', 0),
                'cross_language_matches_found': len(correlation.get('cross_language_matches', [])),
                'multilingual_topics': len(sorted_multilingual)
            }
        }
