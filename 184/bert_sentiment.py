import os
import re
import numpy as np
from config import DATA_DIR

STOPWORDS_PATH = os.path.join(DATA_DIR, 'stopwords.txt')


def load_stopwords():
    stopwords = set()
    if os.path.exists(STOPWORDS_PATH):
        with open(STOPWORDS_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word:
                    stopwords.add(word)
    return stopwords


STOPWORDS = load_stopwords()


def clean_text(text):
    if not isinstance(text, str):
        return ''
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：""''（）\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def remove_stopwords(text):
    words = text.split()
    filtered = [w for w in words if w not in STOPWORDS]
    return ' '.join(filtered)


class BertSentimentAnalyzer:
    _instance = None
    _model = None
    _tokenizer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_model()
        return cls._instance
    
    def _init_model(self):
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            model_name = 'uer/roberta-base-finetuned-dianping-chinese'
            
            print(f'加载BERT情感分析模型: {model_name}')
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self._model.to(self._device)
            self._model.eval()
            
            print(f'BERT模型加载成功，使用设备: {self._device}')
            self._available = True
            
        except Exception as e:
            print(f'BERT模型加载失败，将使用SnowNLP作为备选: {e}')
            self._available = False
            from snownlp import SnowNLP
            self._snownlp = SnowNLP
    
    def analyze(self, text):
        cleaned_text = clean_text(text)
        if not cleaned_text:
            return {
                'score': 0.5,
                'label': 'neutral',
                'label_cn': '中性',
                'positive_prob': 0.5,
                'negative_prob': 0.5
            }
        
        if self._available:
            return self._analyze_bert(cleaned_text)
        else:
            return self._analyze_snownlp(cleaned_text)
    
    def _analyze_bert(self, text):
        try:
            import torch
            
            inputs = self._tokenizer(
                text,
                truncation=True,
                padding=True,
                max_length=128,
                return_tensors='pt'
            ).to(self._device)
            
            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)
                
                positive_prob = probs[0][1].item()
                negative_prob = probs[0][0].item()
            
            score = positive_prob
            
            if score >= 0.6:
                label = 'positive'
                label_cn = '正向'
            elif score <= 0.4:
                label = 'negative'
                label_cn = '负向'
            else:
                label = 'neutral'
                label_cn = '中性'
            
            return {
                'score': round(score, 4),
                'label': label,
                'label_cn': label_cn,
                'positive_prob': round(positive_prob, 4),
                'negative_prob': round(negative_prob, 4)
            }
            
        except Exception as e:
            print(f'BERT分析失败，使用SnowNLP: {e}')
            return self._analyze_snownlp(text)
    
    def _analyze_snownlp(self, text):
        try:
            from snownlp import SnowNLP
            s = SnowNLP(text)
            score = s.sentiments
            
            if score >= 0.6:
                label = 'positive'
                label_cn = '正向'
            elif score <= 0.4:
                label = 'negative'
                label_cn = '负向'
            else:
                label = 'neutral'
                label_cn = '中性'
            
            return {
                'score': round(score, 4),
                'label': label,
                'label_cn': label_cn,
                'positive_prob': round(score, 4),
                'negative_prob': round(1 - score, 4)
            }
        except Exception as e:
            return {
                'score': 0.5,
                'label': 'neutral',
                'label_cn': '中性',
                'positive_prob': 0.5,
                'negative_prob': 0.5
            }


_analyzer = None


def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = BertSentimentAnalyzer()
    return _analyzer


def analyze_sentiment(text):
    analyzer = get_analyzer()
    return analyzer.analyze(text)


def analyze_batch(texts):
    analyzer = get_analyzer()
    results = []
    for text in texts:
        results.append(analyzer.analyze(text))
    return results


if __name__ == '__main__':
    test_texts = [
        '这款手机性价比很高，质量也很好，物流也很快！',
        '价格太贵了，而且质量很差，物流还慢，不推荐！',
        '价格还行，质量一般吧，没什么特别的。',
        '客服态度很好，有问必答，很专业！',
        '用了几天就坏了，质量太差，非常失望！'
    ]
    
    for text in test_texts:
        print(f'文本: {text}')
        result = analyze_sentiment(text)
        print(f'分析结果: {result}')
        print('-' * 50)
