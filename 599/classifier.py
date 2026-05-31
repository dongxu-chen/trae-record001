import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

from merchant_db import MerchantDatabase, CATEGORIES, MerchantInfo
from rule_engine import RuleEngine

class TransactionClassifier:
    def __init__(self, model_path: str = "data/classifier_model.pkl"):
        self.model_path = model_path
        self.merchant_db = MerchantDatabase()
        self.rule_engine = RuleEngine()
        self.model: Optional[Pipeline] = None
        self._load_or_train_model()
        self.is_cold_start = not os.path.exists(self.model_path)
    
    def _load_or_train_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_cold_start = False
            except Exception:
                self._train_model()
        else:
            self.is_cold_start = True
            self._train_model()
    
    def _train_model(self):
        texts, labels = self._generate_training_data()
        
        if len(texts) < 10:
            self.model = None
            return
        
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 2),
                analyzer='char_wb',
                max_features=5000
            )),
            ('clf', MultinomialNB(alpha=0.1))
        ])
        
        self.model.fit(texts, labels)
        self._save_model()
    
    def _save_model(self):
        if self.model is None:
            return
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        self.is_cold_start = False
    
    def _generate_training_data(self) -> Tuple[List[str], List[str]]:
        texts = []
        labels = []
        
        merchants = self.merchant_db.get_all_merchants()
        for merchant in merchants:
            texts.append(merchant.name)
            labels.append(merchant.category)
            for _ in range(2):
                texts.append(f"{merchant.name}消费")
                labels.append(merchant.category)
                texts.append(f"{merchant.name}支付")
                labels.append(merchant.category)
            if merchant.brand:
                texts.append(merchant.brand)
                labels.append(merchant.category)
            if merchant.city:
                texts.append(f"{merchant.name}{merchant.city}")
                labels.append(merchant.category)
        
        additional_data = [
            ("美团外卖订单", "餐饮"),
            ("饿了么订餐", "餐饮"),
            ("滴滴出行快车", "交通"),
            ("滴滴专车", "交通"),
            ("淘宝购物", "购物"),
            ("京东商城", "购物"),
            ("爱奇艺会员", "娱乐"),
            ("腾讯视频", "娱乐"),
            ("医院挂号", "医疗"),
            ("药房买药", "医疗"),
        ]
        
        for text, label in additional_data:
            texts.append(text)
            labels.append(label)
            for _ in range(2):
                texts.append(text)
                labels.append(label)
        
        return texts, labels
    
    def classify(self, transaction: Dict) -> Dict:
        merchant = transaction.get('merchant', '')
        location = transaction.get('location', '')
        amount = transaction.get('amount', 0)
        
        result = {
            'category': None,
            'sub_category': None,
            'confidence': 0.0,
            'method': None,
            'tags': [],
            'anomaly_flags': [],
            'matched_merchant': None,
            'city': None
        }
        
        rule_result = self.rule_engine.apply_rules(transaction)
        
        exact_category, exact_merchant = self.merchant_db.exact_match(merchant, location)
        if exact_category:
            result['category'] = exact_category
            result['confidence'] = 1.0
            result['method'] = 'exact_match'
            if exact_merchant:
                result['sub_category'] = exact_merchant.sub_category
                result['matched_merchant'] = exact_merchant.name
                result['city'] = exact_merchant.city
        
        if result['category'] is None:
            fuzzy_category, fuzzy_score, fuzzy_merchant = self.merchant_db.fuzzy_match(
                merchant, location, threshold=70
            )
            if fuzzy_category:
                result['category'] = fuzzy_category
                result['confidence'] = fuzzy_score / 100.0
                result['method'] = 'fuzzy_match'
                if fuzzy_merchant:
                    result['sub_category'] = fuzzy_merchant.sub_category
                    result['matched_merchant'] = fuzzy_merchant.name
                    result['city'] = fuzzy_merchant.city
        
        if self.is_cold_start and result['category'] is None:
            parent_category = self.merchant_db.cold_start_classify(merchant)
            if parent_category:
                result['category'] = parent_category
                result['confidence'] = 0.6
                result['method'] = 'parent_category_fallback'
                result['tags'].append('父类兜底')
        
        if result['category'] is None and self.model:
            pred_category = self.model.predict([merchant])[0]
            pred_proba = self.model.predict_proba([merchant])
            confidence = np.max(pred_proba)
            result['category'] = pred_category
            result['confidence'] = float(confidence)
            result['method'] = 'ml_model'
        
        if rule_result['category'] and result['method'] != 'exact_match':
            if result['confidence'] < 0.7:
                result['category'] = rule_result['category']
                result['method'] = 'rule_based'
                result['confidence'] = 0.8
        
        result['tags'].extend(rule_result['tags'])
        result['anomaly_flags'].extend(rule_result['anomaly_flags'])
        
        if result['category'] is None:
            result['category'] = '其他'
            result['confidence'] = 0.5
            result['method'] = 'default'
        
        if location and not result['city']:
            for city in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆"]:
                if city in location:
                    result['city'] = city
                    break
        
        return result
    
    def classify_batch(self, transactions: List[Dict]) -> List[Dict]:
        results = []
        for transaction in transactions:
            result = self.classify(transaction)
            result.update(transaction)
            results.append(result)
        return results
    
    def retrain_model(self, training_data: List[Tuple[str, str]]) -> Dict:
        texts = [item[0] for item in training_data]
        labels = [item[1] for item in training_data]
        
        if len(texts) < 10:
            return {'success': False, 'message': '训练数据不足，至少需要10条'}
        
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 2),
                analyzer='char_wb',
                max_features=5000
            )),
            ('clf', MultinomialNB(alpha=0.1))
        ])
        
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        self._save_model()
        
        return {
            'success': True,
            'accuracy': accuracy,
            'classification_report': classification_report(y_test, y_pred)
        }
    
    def get_model_info(self) -> Dict:
        return {
            'categories': CATEGORIES,
            'model_path': self.model_path,
            'model_exists': os.path.exists(self.model_path),
            'is_cold_start': self.is_cold_start,
            'category_hierarchy': self.merchant_db.get_category_hierarchy()
        }
