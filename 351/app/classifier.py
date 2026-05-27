import os
import joblib
import re
import string
from typing import Dict, List, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import numpy as np
from config import Config
from app.text_cleaner import TextCleaner


class SpamClassifier:
    def __init__(self):
        self.vectorizer = None
        self.model = None
        self._load_or_init_model()
    
    def _load_or_init_model(self):
        os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)
        
        if os.path.exists(Config.MODEL_PATH) and os.path.exists(Config.VECTORIZER_PATH):
            self.model = joblib.load(Config.MODEL_PATH)
            self.vectorizer = joblib.load(Config.VECTORIZER_PATH)
        else:
            self._init_new_model()
    
    def _init_new_model(self):
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words='english',
            lowercase=True
        )
        self.model = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )
        
        sample_data = self._get_sample_training_data()
        texts, labels = sample_data['texts'], sample_data['labels']
        
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        
        self._save_model()
    
    def _get_sample_training_data(self) -> Dict[str, List]:
        spam_texts = [
            "free money now click here claim your prize",
            "win free iphone giveaway limited time offer",
            "urgent your account has been suspended verify now",
            "congratulations you won lottery click to claim",
            "cheap viagra pills best price free shipping",
            "make money fast work from home earn $500 daily",
            "exclusive deal discount 90% off today only",
            "your password has been compromised click to reset",
            "free rolex watch just pay shipping",
            "hot singles in your area chat now",
            "get rich quick scheme no experience needed",
            "debt consolidation loan guaranteed approval",
            "you have won $1000000 claim your prize now",
            "weight loss pill lose 30 lbs in 30 days",
            "secret crypto investment earn 1000% returns"
        ]
        
        ham_texts = [
            "meeting tomorrow at 10am conference room a",
            "please review attached document and provide feedback",
            "thank you for your order it will be shipped soon",
            "project update please see attached progress report",
            "lunch this week what day works for you",
            "your account statement is ready to view",
            "welcome to the team we are excited to have you",
            "reminder appointment scheduled for next week",
            "happy birthday hope you have a great day",
            "please confirm receipt of this email",
            "weekly team meeting agenda attached below",
            "your subscription has been successfully renewed",
            "job application update we have received your resume",
            "invoice attached payment due within 30 days",
            "newsletter check out our latest updates"
        ]
        
        texts = spam_texts + ham_texts
        labels = [1] * len(spam_texts) + [0] * len(ham_texts)
        
        return {'texts': texts, 'labels': labels}
    
    def _save_model(self):
        joblib.dump(self.model, Config.MODEL_PATH)
        joblib.dump(self.vectorizer, Config.VECTORIZER_PATH)
    
    def preprocess_text(self, text: str) -> str:
        if not text:
            return ""
        
        text = text.lower()
        text = re.sub(r'http\S+|www\S+|https\S+', ' ', text)
        text = re.sub(r'\S+@\S+', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        text = text.translate(str.maketrans('', '', string.punctuation))
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_email_features(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        attachments = email_data.get('attachments', [])
        sender = email_data.get('sender', '')
        ip = email_data.get('sender_ip', '')
        is_html = email_data.get('is_html', False)
        
        cleaned_result = TextCleaner.extract_plain_text(email_data)
        cleaned_text = cleaned_result['cleaned_text']
        
        combined_text = f"{subject} {body}"
        processed_text = self.preprocess_text(cleaned_text)
        
        features = {
            'text': processed_text,
            'cleaned_text': cleaned_text,
            'subject_length': len(subject),
            'body_length': len(body),
            'cleaned_text_length': len(cleaned_text),
            'num_attachments': len(attachments),
            'subject_all_caps': subject.isupper() and len(subject) > 5,
            'num_links': len(re.findall(r'http\S+|www\S+', body + subject)),
            'num_special_chars': sum(1 for c in combined_text if c in '!$%&*@#'),
            'attachment_extensions': [a.split('.')[-1].lower() for a in attachments if '.' in a],
            'is_html': is_html
        }
        
        return features
    
    def predict_proba(self, text: str) -> Tuple[float, float]:
        processed_text = self.preprocess_text(text)
        X = self.vectorizer.transform([processed_text])
        probabilities = self.model.predict_proba(X)[0]
        
        ham_prob = probabilities[0]
        spam_prob = probabilities[1]
        
        return ham_prob, spam_prob
    
    def classify_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        features = self.extract_email_features(email_data)
        ham_prob, spam_prob = self.predict_proba(features['text'])
        
        adjusted_spam_prob = self._adjust_prob_with_features(spam_prob, features)
        
        is_spam = adjusted_spam_prob >= Config.SPAM_THRESHOLD
        
        return {
            'spam_probability': float(adjusted_spam_prob),
            'ham_probability': float(1 - adjusted_spam_prob),
            'is_spam': bool(is_spam),
            'threshold': Config.SPAM_THRESHOLD,
            'model_type': type(self.model).__name__,
            'feature_analysis': self._get_feature_analysis(features)
        }
    
    def _adjust_prob_with_features(self, base_prob: float, features: Dict[str, Any]) -> float:
        adjustment = 0.0
        
        if features['subject_all_caps']:
            adjustment += 0.1
        
        if features['num_links'] > 5:
            adjustment += 0.15
        elif features['num_links'] > 2:
            adjustment += 0.05
        
        if features['num_special_chars'] > 10:
            adjustment += 0.1
        
        suspicious_extensions = {'exe', 'scr', 'bat', 'com', 'pif', 'zip', 'rar'}
        if any(ext in suspicious_extensions for ext in features['attachment_extensions']):
            adjustment += 0.15
        
        if features['body_length'] < 20:
            adjustment += 0.05
        
        adjusted_prob = base_prob + adjustment
        return max(0.0, min(1.0, adjusted_prob))
    
    def _get_feature_analysis(self, features: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'num_links': features['num_links'],
            'num_special_chars': features['num_special_chars'],
            'subject_all_caps': features['subject_all_caps'],
            'num_attachments': features['num_attachments'],
            'body_length': features['body_length']
        }
    
    def train(self, texts: List[str], labels: List[int], save: bool = True) -> Dict[str, float]:
        processed_texts = [self.preprocess_text(t) for t in texts]
        
        X_train, X_test, y_train, y_test = train_test_split(
            processed_texts, labels, test_size=0.2, random_state=42
        )
        
        X_train_vec = self.vectorizer.fit_transform(X_train)
        self.model.fit(X_train_vec, y_train)
        
        X_test_vec = self.vectorizer.transform(X_test)
        y_pred = self.model.predict(X_test_vec)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }
        
        if save:
            self._save_model()
        
        return metrics
    
    def retrain_with_feedback(self, feedback_data: List[Dict[str, Any]]) -> Dict[str, float]:
        texts = []
        labels = []
        
        for item in feedback_data:
            email_data = item.get('email', {})
            is_spam_correct = item.get('is_spam_correct', False)
            original_result = item.get('original_result', {})
            
            combined_text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
            texts.append(combined_text)
            
            if is_spam_correct:
                labels.append(1 if original_result.get('is_spam') else 0)
            else:
                labels.append(0 if original_result.get('is_spam') else 1)
        
        if len(texts) >= 5:
            return self.train(texts, labels)
        
        return {'error': 'Not enough feedback data for training', 'samples': len(texts)}
    
    def get_top_spam_words(self, n: int = 20) -> List[Tuple[str, float]]:
        feature_names = self.vectorizer.get_feature_names_out()
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            indices = np.argsort(importances)[-n:]
            return [(feature_names[i], float(importances[i])) for i in reversed(indices)]
        elif hasattr(self.model, 'coef_'):
            coef = self.model.coef_[0]
            indices = np.argsort(coef)[-n:]
            return [(feature_names[i], float(coef[i])) for i in reversed(indices)]
        
        return []
    
    def partial_fit(self, texts: List[str], labels: List[int], save: bool = True) -> Dict[str, Any]:
        if not hasattr(self.model, 'partial_fit'):
            return self.train(texts, labels, save)
        
        processed_texts = [self.preprocess_text(t) for t in texts]
        X = self.vectorizer.transform(processed_texts)
        
        if not hasattr(self, '_classes_'):
            self._classes_ = np.array([0, 1])
        
        self.model.partial_fit(X, labels, classes=self._classes_)
        
        if save:
            self._save_model()
        
        return {
            'method': 'partial_fit',
            'samples': len(texts),
            'success': True
        }
    
    def online_learn_single(self, text: str, label: int, save: bool = True) -> Dict[str, Any]:
        processed_text = self.preprocess_text(text)
        X = self.vectorizer.transform([processed_text])
        
        if hasattr(self.model, 'partial_fit'):
            if not hasattr(self, '_classes_'):
                self._classes_ = np.array([0, 1])
            self.model.partial_fit(X, [label], classes=self._classes_)
        else:
            from sklearn.linear_model import SGDClassifier
            new_model = SGDClassifier(loss='log_loss', random_state=42)
            X_current = self.vectorizer.transform(self._get_sample_training_data()['texts'])
            y_current = np.array(self._get_sample_training_data()['labels'])
            new_model.partial_fit(X_current, y_current, classes=np.array([0, 1]))
            new_model.partial_fit(X, [label], classes=np.array([0, 1]))
            self.model = new_model
            self._classes_ = np.array([0, 1])
        
        if save:
            self._save_model()
        
        return {
            'method': 'online_learning',
            'label': label,
            'success': True
        }
