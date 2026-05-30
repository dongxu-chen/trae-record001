import numpy as np
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv

load_dotenv()


class SentimentAnalyzer:
    def __init__(self, model_name: str = None, num_labels: int = 4):
        import torch
        import torch.nn as nn
        from transformers import BertModel, BertTokenizer
        
        self.torch = torch
        self.nn = nn
        
        self.model_name = model_name or os.getenv('MODEL_NAME', 'bert-base-chinese')
        self.num_labels = num_labels
        self.max_seq_length = int(os.getenv('MAX_SEQ_LENGTH', 128))
        
        self.bert = BertModel.from_pretrained(self.model_name)
        self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
        
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_labels)
        self.softmax = nn.Softmax(dim=1)
        
        self.sentiment_labels = ['satisfied', 'angry', 'disappointed', 'anxious']
        self.sentiment_cn = {
            'satisfied': '满意',
            'angry': '愤怒',
            'disappointed': '失望',
            'anxious': '焦虑'
        }
        
    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        pooled_output = outputs[1]
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        return logits
    
    def tokenize(self, text: str) -> Dict[str, object]:
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_seq_length,
            return_token_type_ids=True,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        return encoding
    
    def predict(self, text: str, context: List[str] = None) -> Dict:
        full_text = text
        if context:
            context_text = ' [SEP] '.join(context[-3:])
            full_text = f"{context_text} [SEP] {text}"
        
        encoding = self.tokenize(full_text)
        
        with self.torch.no_grad():
            logits = self.forward(
                input_ids=encoding['input_ids'],
                attention_mask=encoding['attention_mask'],
                token_type_ids=encoding['token_type_ids']
            )
            probabilities = self.softmax(logits)
            
        scores = probabilities.numpy()[0]
        predicted_idx = np.argmax(scores)
        
        result = {
            'text': text,
            'predicted_label': self.sentiment_labels[predicted_idx],
            'predicted_label_cn': self.sentiment_cn[self.sentiment_labels[predicted_idx]],
            'confidence': float(scores[predicted_idx]),
            'scores': {
                self.sentiment_labels[i]: float(scores[i])
                for i in range(self.num_labels)
            },
            'scores_cn': {
                self.sentiment_cn[self.sentiment_labels[i]]: float(scores[i])
                for i in range(self.num_labels)
            }
        }
        
        return result
    
    def batch_predict(self, texts: List[str]) -> List[Dict]:
        return [self.predict(text) for text in texts]
    
    def get_sentiment_embedding(self, text: str) -> np.ndarray:
        encoding = self.tokenize(text)
        
        with self.torch.no_grad():
            outputs = self.bert(
                input_ids=encoding['input_ids'],
                attention_mask=encoding['attention_mask']
            )
            pooled_output = outputs[1]
            
        return pooled_output.numpy()[0]


def create_sentiment_analyzer() -> SentimentAnalyzer:
    return SentimentAnalyzer()


class RuleBasedSentiment:
    def __init__(self):
        self.sentiment_keywords = {
            'satisfied': ['满意', '很好', '不错', '棒', '赞', '感谢', '谢谢', '解决了', '好评'],
            'angry': ['愤怒', '生气', '投诉', '垃圾', '烂', '滚', '混蛋', '他妈', '可恶', '恶劣'],
            'disappointed': ['失望', '遗憾', '可惜', '没想到', '算了', '不行', '太差', '糟糕'],
            'anxious': ['着急', '担心', '焦虑', '紧张', '快点', '很急', '怎么办', '什么时候', '急死']
        }
        
    def analyze(self, text: str) -> Dict:
        scores = {'satisfied': 0.0, 'angry': 0.0, 'disappointed': 0.0, 'anxious': 0.0}
        
        for sentiment, keywords in self.sentiment_keywords.items():
            count = sum(1 for kw in keywords if kw in text)
            scores[sentiment] = min(count * 0.2, 1.0)
        
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        else:
            scores = {k: 0.25 for k in scores}
        
        predicted_idx = np.argmax(list(scores.values()))
        labels = list(scores.keys())
        sentiment_cn = {
            'satisfied': '满意',
            'angry': '愤怒',
            'disappointed': '失望',
            'anxious': '焦虑'
        }
        
        return {
            'text': text,
            'predicted_label': labels[predicted_idx],
            'predicted_label_cn': sentiment_cn[labels[predicted_idx]],
            'confidence': scores[labels[predicted_idx]],
            'scores': scores,
            'scores_cn': {sentiment_cn[k]: v for k, v in scores.items()}
        }
