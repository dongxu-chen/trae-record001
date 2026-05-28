import re
import jieba
import logging
import os
from typing import List, Set

logger = logging.getLogger(__name__)


class TextProcessor:
    def __init__(self):
        self.stopwords = self._load_stopwords()
        self._init_jieba()
    
    def _init_jieba(self):
        try:
            jieba.setLogLevel(logging.INFO)
            jieba.initialize()
            logger.info("Jieba initialized successfully")
        except Exception as e:
            logger.warning(f"Jieba initialization failed: {e}")
    
    def _load_stopwords(self) -> Set[str]:
        stopwords = set()
        default_stopwords = {
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要',
            '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他', '她', '它', '们', '这个', '那个', '什么',
            'how', 'why', 'who', 'what', 'which', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'as',
            'of', 'or', 'and', 'but', 'if', 'then', 'else', 'when', 'where', 'what', 'which', 'who', 'whom', 'whose',
            'also', 'too', 'very', 'just', 'so', 'not', 'no', 'yes', 'can', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'once', 'here', 'there',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'only', 'own', 'same',
        }
        stopwords.update(default_stopwords)
        
        custom_stopwords_path = os.path.join(os.path.dirname(__file__), 'stopwords.txt')
        if os.path.exists(custom_stopwords_path):
            try:
                with open(custom_stopwords_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if word:
                            stopwords.add(word)
                logger.info(f"Loaded {len(stopwords)} stopwords")
            except Exception as e:
                logger.warning(f"Failed to load custom stopwords: {e}")
        
        return stopwords
    
    def clean_text(self, text: str) -> str:
        if not text:
            return ''
        
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'<.*?>', '', text)
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def tokenize(self, text: str, remove_stopwords: bool = True) -> List[str]:
        if not text:
            return []
        
        cleaned_text = self.clean_text(text)
        if not cleaned_text:
            return []
        
        words = jieba.lcut(cleaned_text)
        
        if remove_stopwords:
            words = [w for w in words if w not in self.stopwords and len(w) > 1]
        
        return words
    
    def is_chinese(self, text: str) -> bool:
        if not text:
            return False
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return len(chinese_chars) > len(text) * 0.3
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        tokens = self.tokenize(text)
        if not tokens:
            return []
        
        word_freq = {}
        for token in tokens:
            word_freq[token] = word_freq.get(token, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:top_k]]
    
    def split_sentences(self, text: str) -> List[str]:
        if not text:
            return []
        
        sentences = re.split(r'[。！？.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
