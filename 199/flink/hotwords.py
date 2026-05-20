import jieba
import re
from collections import Counter, deque
import time
from typing import List, Dict

from config import HOTWORDS_CONFIG


class HotWordExtractor:
    def __init__(self):
        self.top_n = HOTWORDS_CONFIG['top_n']
        self.window_size = HOTWORDS_CONFIG['window_size']
        self._word_window = deque()
        self._stopwords = set([
            '的', '了', '啊', '呀', '吧', '呢', '吗', '哦', '嗯', '哈哈',
            '我', '你', '他', '她', '它', '们', '是', '在', '有', '和',
            '就', '都', '也', '还', '要', '会', '可以', '这个', '那个',
            '一个', '什么', '怎么', '为什么', '没有', '不是', '就是',
            '主播', '直播间', '宝宝', '买', '抢', '点', '关注', '点赞',
            '666', '233', '哈哈哈', '冲冲冲', '买它买它',
        ])
        jieba.setLogLevel(60)

    def extract(self, text: str) -> List[str]:
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        if not text:
            return []

        words = jieba.lcut(text)
        words = [w for w in words if w not in self._stopwords and len(w) > 1]

        current_time = time.time()
        for word in words:
            self._word_window.append({
                'word': word,
                'timestamp': current_time,
            })

        self._clean_old()
        return words

    def _clean_old(self):
        current_time = time.time()
        while self._word_window:
            if current_time - self._word_window[0]['timestamp'] > self.window_size:
                self._word_window.popleft()
            else:
                break

    def get_hotwords(self) -> List[Dict]:
        self._clean_old()
        if not self._word_window:
            return []

        counter = Counter(item['word'] for item in self._word_window)
        total = len(self._word_window)
        hotwords = []
        for word, count in counter.most_common(self.top_n):
            hotwords.append({
                'word': word,
                'count': count,
                'rate': round(count / total, 4),
            })
        return hotwords
