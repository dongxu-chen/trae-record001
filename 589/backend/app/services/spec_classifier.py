import os
import json
import pickle
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from collections import Counter

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

from sqlalchemy.orm import Session
from ..models import MLTrainingData, SpecClassificationModel, ProductAttribute


@dataclass
class ClassificationResult:
    predicted_category: str
    confidence: float
    all_probabilities: Dict[str, float]
    used_model: str
    model_version: str
    extracted_features: Dict[str, Any]
    top_attributes: List[Dict[str, Any]]


@dataclass
class ModelTrainingResult:
    model_name: str
    model_version: str
    category: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_samples: int
    test_samples: int
    training_time: float


class ChineseTextProcessor:
    def __init__(self):
        self.stopwords = self._load_stopwords()
        self._init_custom_words()

    def _load_stopwords(self) -> set:
        default_stopwords = {
            "的", "了", "是", "就", "都", "而", "及", "和", "与", "或",
            "在", "有", "个", "上", "下", "中", "这", "那", "你", "我",
            "他", "它", "们", "什么", "怎么", "为什么", "哪", "多少",
            "全新", "正品", "特价", "包邮", "秒杀", "限时", "优惠",
            "折扣", "促销", "热卖", "爆款", "销量", "热销", "新品",
        }
        return default_stopwords

    def _init_custom_words(self):
        if JIEBA_AVAILABLE:
            custom_words = [
                "骁龙", "天玑", "麒麟", "澎湃", "灵动岛", "Pro", "Max",
                "Ultra", "Plus", "青春版", "旗舰版", "标准版", "顶配版",
                "全网通", "双卡双待", "快充", "闪充", "无线充",
            ]
            for word in custom_words:
                jieba.add_word(word)

    def tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        
        text = self._preprocess_text(text)
        
        if JIEBA_AVAILABLE:
            tokens = jieba.lcut(text)
        else:
            tokens = self._simple_tokenize(text)
        
        tokens = [t for t in tokens if t.strip() and t not in self.stopwords and len(t) > 1]
        
        return tokens

    def _preprocess_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _simple_tokenize(self, text: str) -> List[str]:
        tokens = []
        i = 0
        while i < len(text):
            if text[i] == ' ':
                i += 1
                continue
            
            if re.match(r'[a-zA-Z0-9]', text[i]):
                j = i
                while j < len(text) and re.match(r'[a-zA-Z0-9]', text[j]):
                    j += 1
                tokens.append(text[i:j])
                i = j
            elif re.match(r'[\u4e00-\u9fa5]', text[i]):
                max_len = min(4, len(text) - i)
                matched = False
                for l in range(max_len, 1, -1):
                    if text[i:i+l]:
                        tokens.append(text[i:i+l])
                        i += l
                        matched = True
                        break
                if not matched:
                    i += 1
            else:
                i += 1
        
        return tokens


class SpecClassifier:
    def __init__(self, model_dir: Optional[str] = None, db: Optional[Session] = None):
        self.db = db
        self.model_dir = Path(model_dir or "models/spec_classifier")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.text_processor = ChineseTextProcessor()
        self.models: Dict[str, Tuple] = {}
        self.vectorizers: Dict[str, TfidfVectorizer] = {}
        self.label_encoders: Dict[str, LabelEncoder] = {}
        
        self._load_active_models()

    def _load_active_models(self):
        if not self.db or not SKLEARN_AVAILABLE:
            return
        
        try:
            active_models = self.db.query(SpecClassificationModel).filter(
                SpecClassificationModel.is_active == True
            ).all()
            
            for model in active_models:
                self._load_model(model)
        except Exception as e:
            print(f"加载模型失败: {e}")

    def _load_model(self, model_record: SpecClassificationModel):
        try:
            model_path = Path(model_record.model_path) if model_record.model_path else None
            
            if model_path and model_path.exists():
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.models[model_record.category] = (
                    model_data.get('classifier'),
                    model_record.model_version
                )
                self.vectorizers[model_record.category] = model_data.get('vectorizer')
                self.label_encoders[model_record.category] = model_data.get('label_encoder')
        except Exception as e:
            print(f"加载模型 {model_record.model_name} 失败: {e}")

    def classify(self, product_name: str, description: str = "", 
                 raw_specs: Optional[Dict] = None,
                 category: Optional[str] = None) -> ClassificationResult:
        
        combined_text = f"{product_name} {description or ''}"
        
        if raw_specs:
            spec_text = " ".join([f"{k}:{v}" for k, v in raw_specs.items() if v])
            combined_text += f" {spec_text}"
        
        extracted_features = self._extract_features(combined_text, raw_specs or {})
        
        if SKLEARN_AVAILABLE and self.models:
            result = self._ml_classify(combined_text, extracted_features, category)
        else:
            result = self._rule_based_classify(combined_text, extracted_features, category)
        
        return result

    def _extract_features(self, text: str, raw_specs: Dict) -> Dict[str, Any]:
        features = {}
        
        tokens = self.text_processor.tokenize(text)
        features["tokens"] = tokens
        features["token_count"] = len(tokens)
        
        token_counter = Counter(tokens)
        features["top_tokens"] = token_counter.most_common(10)
        
        has_number = bool(re.search(r'\d', text))
        features["has_number"] = has_number
        
        number_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(\w+)', text)
        features["numeric_attributes"] = [
            {"value": float(v), "unit": u} 
            for v, u in number_matches if u and len(u) <= 3
        ]
        
        patterns = {
            "color": r'(黑|白|灰|红|橙|黄|绿|青|蓝|紫|粉|金|银)[色]?',
            "version": r'(Pro|Max|Ultra|Plus|青春版|旗舰版|标准版|高配版|低配版)',
            "year": r'20\d{2}款?',
        }
        
        for feat_name, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            features[f"{feat_name}_matches"] = list(set(matches))
        
        if raw_specs:
            features["raw_spec_keys"] = list(raw_specs.keys())
        
        return features

    def _ml_classify(self, text: str, extracted_features: Dict[str, Any],
                     target_category: Optional[str]) -> ClassificationResult:
        
        category = target_category or "general"
        
        if category not in self.models:
            for cat in self.models.keys():
                if cat in text:
                    category = cat
                    break
            
            if category not in self.models:
                category = list(self.models.keys())[0] if self.models else None
        
        if not category or category not in self.models:
            return self._rule_based_classify(text, extracted_features, target_category)
        
        classifier, model_version = self.models[category]
        vectorizer = self.vectorizers.get(category)
        label_encoder = self.label_encoders.get(category)
        
        if not classifier or not vectorizer:
            return self._rule_based_classify(text, extracted_features, target_category)
        
        tokens = self.text_processor.tokenize(text)
        processed_text = " ".join(tokens)
        
        X = vectorizer.transform([processed_text])
        
        prediction = classifier.predict(X)[0]
        probabilities = classifier.predict_proba(X)[0]
        
        if label_encoder:
            predicted_label = label_encoder.inverse_transform([prediction])[0]
            class_labels = label_encoder.classes_
        else:
            predicted_label = str(prediction)
            class_labels = list(range(len(probabilities)))
        
        probs_dict = {
            str(cls): float(prob) 
            for cls, prob in zip(class_labels, probabilities)
        }
        
        sorted_probs = sorted(probs_dict.items(), key=lambda x: x[1], reverse=True)
        top_attributes = [
            {"category": cat, "probability": prob}
            for cat, prob in sorted_probs[:5]
        ]
        
        confidence = float(max(probabilities))
        
        return ClassificationResult(
            predicted_category=str(predicted_label),
            confidence=confidence,
            all_probabilities=probs_dict,
            used_model=f"ml_{category}",
            model_version=model_version,
            extracted_features=extracted_features,
            top_attributes=top_attributes
        )

    def _rule_based_classify(self, text: str, extracted_features: Dict[str, Any],
                             category: Optional[str]) -> ClassificationResult:
        
        category_keywords = {
            "手机": ["手机", "phone", "智能手机", "5G手机", "iphone", "安卓手机"],
            "笔记本电脑": ["笔记本", "笔记本电脑", "laptop", "游戏本", "轻薄本", "macbook"],
            "平板电脑": ["平板", "平板电脑", "ipad", "pad"],
            "电视": ["电视", "电视机", "智能电视", "4K电视", "oled电视"],
            "冰箱": ["冰箱", "电冰箱", "对开门冰箱", "三门冰箱", "冰柜"],
            "洗衣机": ["洗衣机", "滚筒洗衣机", "波轮洗衣机", "洗烘一体"],
            "空调": ["空调", "挂机空调", "柜机空调", "中央空调", "变频空调"],
            "耳机": ["耳机", "蓝牙耳机", "无线耳机", "降噪耳机", "入耳式耳机"],
            "智能手表": ["智能手表", "手表", "watch", "手环", "运动手表"],
            "相机": ["相机", "数码相机", "单反相机", "微单", "摄像机"],
            "运动鞋": ["运动鞋", "跑鞋", "篮球鞋", "休闲鞋", "板鞋"],
            "T恤": ["t恤", "T恤", "短袖", "圆领T恤", "POLO衫"],
            "手机壳": ["手机壳", "手机保护套", "手机套"],
        }
        
        scores = {}
        text_lower = text.lower()
        
        for cat, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[cat] = score
        
        if scores:
            predicted = max(scores, key=scores.get)
            max_score = scores[predicted]
            total_score = sum(scores.values())
            confidence = max_score / max(total_score, 1)
        else:
            predicted = category or "其他"
            confidence = 0.3
        
        top_attributes = [
            {"category": cat, "probability": score / max(total_score, 1)}
            for cat, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        all_probs = {
            cat: score / max(total_score, 1)
            for cat, score in scores.items()
        }
        
        return ClassificationResult(
            predicted_category=predicted,
            confidence=confidence,
            all_probabilities=all_probs,
            used_model="rule_based",
            model_version="1.0.0",
            extracted_features=extracted_features,
            top_attributes=top_attributes
        )

    def train_model(self, category: str, training_data: Optional[List[MLTrainingData]] = None,
                   model_type: str = "logistic_regression",
                   test_size: float = 0.2) -> Optional[ModelTrainingResult]:
        
        if not SKLEARN_AVAILABLE:
            print("scikit-learn未安装，无法训练模型")
            return None
        
        if not self.db and training_data is None:
            print("需要数据库连接或提供训练数据")
            return None
        
        if training_data is None and self.db:
            training_data = self.db.query(MLTrainingData).filter(
                MLTrainingData.category == category,
                MLTrainingData.quality_score >= 0.7
            ).all()
        
        if not training_data:
            print(f"类别 {category} 没有足够的训练数据")
            return None
        
        start_time = datetime.now()
        
        texts = []
        labels = []
        
        for data in training_data:
            tokens = self.text_processor.tokenize(data.input_text)
            texts.append(" ".join(tokens))
            labels.append(json.dumps(data.output_spec) if isinstance(data.output_spec, dict) else str(data.output_spec))
        
        unique_labels = list(set(labels))
        if len(unique_labels) < 2:
            print("标签种类不足，无法训练分类模型")
            return None
        
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(labels)
        
        vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=2
        )
        X = vectorizer.fit_transform(texts)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        if model_type == "random_forest":
            classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=None,
                min_samples_split=2,
                random_state=42,
                n_jobs=-1
            )
        else:
            classifier = LogisticRegression(
                max_iter=1000,
                C=1.0,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            )
        
        classifier.fit(X_train, y_train)
        
        y_pred = classifier.predict(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"{category}_{model_type}"
        model_version = f"v1.{len(unique_labels)}.{len(training_data)}"
        model_filename = f"{model_name}_{timestamp}.pkl"
        model_path = self.model_dir / model_filename
        
        model_data = {
            "classifier": classifier,
            "vectorizer": vectorizer,
            "label_encoder": label_encoder,
            "training_data_count": len(training_data),
            "label_classes": unique_labels,
            "training_time": (datetime.now() - start_time).total_seconds(),
            "metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            }
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        model_record = SpecClassificationModel(
            model_name=model_name,
            model_version=model_version,
            category=category,
            model_type=model_type,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            training_samples=len(training_data),
            last_trained_at=datetime.now(),
            is_active=True,
            model_path=str(model_path)
        )
        
        if self.db:
            old_models = self.db.query(SpecClassificationModel).filter(
                SpecClassificationModel.category == category
            ).all()
            for old in old_models:
                old.is_active = False
            
            self.db.add(model_record)
            self.db.commit()
            
            for data in training_data:
                data.used_for_training = True
                data.last_trained_at = datetime.now()
            self.db.commit()
        
        self.models[category] = (classifier, model_version)
        self.vectorizers[category] = vectorizer
        self.label_encoders[category] = label_encoder
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        return ModelTrainingResult(
            model_name=model_name,
            model_version=model_version,
            category=category,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            training_samples=len(training_data),
            test_samples=len(y_test),
            training_time=training_time
        )

    def add_training_data(self, category: str, input_text: str, 
                         output_spec: Dict[str, Any], source: str = "manual",
                         quality_score: float = 1.0) -> Optional[MLTrainingData]:
        
        if not self.db:
            print("需要数据库连接")
            return None
        
        training_data = MLTrainingData(
            category=category,
            input_text=input_text,
            output_spec=output_spec,
            source=source,
            quality_score=quality_score
        )
        
        self.db.add(training_data)
        self.db.commit()
        self.db.refresh(training_data)
        
        return training_data

    def classify_batch(self, items: List[Dict[str, Any]]) -> List[ClassificationResult]:
        results = []
        for item in items:
            result = self.classify(
                product_name=item.get("name", ""),
                description=item.get("description", ""),
                raw_specs=item.get("specs"),
                category=item.get("category")
            )
            results.append(result)
        return results

    def get_model_stats(self, category: Optional[str] = None) -> Dict[str, Any]:
        if not self.db:
            return {"error": "需要数据库连接"}
        
        query = self.db.query(SpecClassificationModel)
        if category:
            query = query.filter(SpecClassificationModel.category == category)
        
        models = query.all()
        
        stats = {
            "total_models": len(models),
            "active_models": sum(1 for m in models if m.is_active),
            "sklearn_available": SKLEARN_AVAILABLE,
            "jieba_available": JIEBA_AVAILABLE,
            "models": []
        }
        
        for model in models:
            stats["models"].append({
                "name": model.model_name,
                "version": model.model_version,
                "category": model.category,
                "type": model.model_type,
                "accuracy": model.accuracy,
                "precision": model.precision,
                "recall": model.recall,
                "f1_score": model.f1_score,
                "training_samples": model.training_samples,
                "is_active": model.is_active,
                "last_trained_at": model.last_trained_at.isoformat() if model.last_trained_at else None
            })
        
        return stats


class SpecMatcher:
    def __init__(self, classifier: SpecClassifier):
        self.classifier = classifier

    def match_products_by_specs(self, target_product: Dict[str, Any], 
                                candidates: List[Dict[str, Any]],
                                threshold: float = 0.7) -> List[Dict[str, Any]]:
        
        target_result = self.classifier.classify(
            target_product.get("name", ""),
            target_product.get("description", ""),
            target_product.get("specs")
        )
        
        matches = []
        for candidate in candidates:
            candidate_result = self.classifier.classify(
                candidate.get("name", ""),
                candidate.get("description", ""),
                candidate.get("specs")
            )
            
            similarity = self._calculate_spec_similarity(
                target_result, candidate_result,
                target_product, candidate
            )
            
            if similarity >= threshold:
                matches.append({
                    "candidate": candidate,
                    "similarity": similarity,
                    "target_category": target_result.predicted_category,
                    "candidate_category": candidate_result.predicted_category
                })
        
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches

    def _calculate_spec_similarity(self, target_result: ClassificationResult,
                                    candidate_result: ClassificationResult,
                                    target_product: Dict[str, Any],
                                    candidate_product: Dict[str, Any]) -> float:
        
        score = 0.0
        weights = 0.0
        
        if target_result.predicted_category == candidate_result.predicted_category:
            score += 0.3 * min(target_result.confidence, candidate_result.confidence)
        weights += 0.3
        
        target_tokens = set(target_result.extracted_features.get("tokens", []))
        candidate_tokens = set(candidate_result.extracted_features.get("tokens", []))
        
        if target_tokens and candidate_tokens:
            intersection = target_tokens & candidate_tokens
            union = target_tokens | candidate_tokens
            jaccard = len(intersection) / len(union) if union else 0
            score += 0.25 * jaccard
        weights += 0.25
        
        target_numeric = target_result.extracted_features.get("numeric_attributes", [])
        candidate_numeric = candidate_result.extracted_features.get("numeric_attributes", [])
        
        if target_numeric and candidate_numeric:
            numeric_match_score = self._compare_numeric_attributes(
                target_numeric, candidate_numeric
            )
            score += 0.25 * numeric_match_score
        weights += 0.25
        
        target_colors = set(target_result.extracted_features.get("color_matches", []))
        candidate_colors = set(candidate_result.extracted_features.get("color_matches", []))
        
        if target_colors and candidate_colors:
            if target_colors & candidate_colors:
                score += 0.2
        weights += 0.2
        
        return score / max(weights, 0.01)

    def _compare_numeric_attributes(self, target_attrs: List[Dict], 
                                    candidate_attrs: List[Dict]) -> float:
        matches = 0
        comparisons = 0
        
        for target in target_attrs:
            target_val = target.get("value")
            target_unit = target.get("unit", "").lower()
            
            for candidate in candidate_attrs:
                cand_val = candidate.get("value")
                cand_unit = candidate.get("unit", "").lower()
                
                if target_unit and cand_unit and target_unit == cand_unit:
                    comparisons += 1
                    if target_val and cand_val:
                        ratio = min(target_val, cand_val) / max(target_val, cand_val)
                        if ratio >= 0.95:
                            matches += 1
                        elif ratio >= 0.8:
                            matches += 0.5
        
        return matches / max(comparisons, 1)
