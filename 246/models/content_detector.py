import os
import numpy as np
import tensorflow as tf
from PIL import Image
from typing import Dict, Tuple, List
from config import config

class RiskLevel:
    NO_RISK = "no_risk"
    LOW_RISK = "low_risk"
    HIGH_RISK = "high_risk"

class ContentType:
    NORMAL = "normal"
    PORN = "porn"
    SWIMWEAR = "swimwear"
    VIOLENCE = "violence"
    ADVERTISEMENT = "advertisement"

class RiskThreshold:
    PORN_HIGH = 0.85
    PORN_LOW = 0.5
    SWIMWEAR_HIGH = 0.95
    SWIMWEAR_LOW = 0.7
    VIOLENCE_HIGH = 0.8
    VIOLENCE_LOW = 0.4
    AD_HIGH = 0.75
    AD_LOW = 0.35

class ContentDetector:
    def __init__(self):
        self.model = None
        self.class_names = [
            ContentType.NORMAL,
            ContentType.PORN,
            ContentType.SWIMWEAR,
            ContentType.VIOLENCE,
            ContentType.ADVERTISEMENT
        ]
        self._load_model()
    
    def _load_model(self):
        if os.path.exists(config.MODEL_PATH):
            self.model = tf.keras.models.load_model(config.MODEL_PATH)
        else:
            self.model = self._create_mock_model()
    
    def _create_mock_model(self):
        base_model = tf.keras.applications.MobileNetV2(
            input_shape=(*config.IMAGE_SIZE, 3),
            include_top=False,
            weights='imagenet'
        )
        base_model.trainable = False
        
        model = tf.keras.Sequential([
            base_model,
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dense(512, activation='relu'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(len(self.class_names), activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        image = image.resize(config.IMAGE_SIZE)
        img_array = np.array(image, dtype=np.float32)
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        return np.expand_dims(img_array, axis=0)
    
    def _get_thresholds(self, content_type: str) -> Tuple[float, float]:
        thresholds = {
            ContentType.PORN: (RiskThreshold.PORN_HIGH, RiskThreshold.PORN_LOW),
            ContentType.SWIMWEAR: (RiskThreshold.SWIMWEAR_HIGH, RiskThreshold.SWIMWEAR_LOW),
            ContentType.VIOLENCE: (RiskThreshold.VIOLENCE_HIGH, RiskThreshold.VIOLENCE_LOW),
            ContentType.ADVERTISEMENT: (RiskThreshold.AD_HIGH, RiskThreshold.AD_LOW),
        }
        return thresholds.get(content_type, (config.HIGH_RISK_THRESHOLD, config.LOW_RISK_THRESHOLD))
    
    def _classify_risk(self, predictions: Dict[str, float]) -> Dict:
        sorted_items = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        top_content, top_score = sorted_items[0]
        second_content, second_score = sorted_items[1]
        
        if top_content == ContentType.NORMAL:
            return {
                "risk_level": RiskLevel.NO_RISK,
                "primary_content": top_content,
                "secondary_content": second_content,
                "risk_details": {"reason": "normal_content"}
            }
        
        if top_content == ContentType.SWIMWEAR and second_content == ContentType.PORN:
            if second_score > 0.3:
                combined_risk = self._evaluate_combined_risk(
                    ContentType.PORN, second_score,
                    ContentType.SWIMWEAR, top_score
                )
                return combined_risk
        
        high_thresh, low_thresh = self._get_thresholds(top_content)
        
        if top_content == ContentType.SWIMWEAR:
            if top_score >= high_thresh:
                risk_level = RiskLevel.LOW_RISK
            else:
                risk_level = RiskLevel.NO_RISK
            reason = "swimwear_scene"
        else:
            if top_score >= high_thresh:
                risk_level = RiskLevel.HIGH_RISK
                reason = f"high_confidence_{top_content}"
            elif top_score >= low_thresh:
                risk_level = RiskLevel.LOW_RISK
                reason = f"medium_confidence_{top_content}"
            else:
                risk_level = RiskLevel.NO_RISK
                reason = "low_confidence"
        
        return {
            "risk_level": risk_level,
            "primary_content": top_content,
            "secondary_content": second_content,
            "risk_details": {
                "reason": reason,
                "primary_score": top_score,
                "secondary_score": second_score
            }
        }
    
    def _evaluate_combined_risk(self, content1: str, score1: float, 
                                 content2: str, score2: float) -> Dict:
        if content1 == ContentType.PORN:
            adjusted_score = score1 * 0.7 + score2 * 0.3
            if adjusted_score >= RiskThreshold.PORN_HIGH * 0.8:
                risk_level = RiskLevel.HIGH_RISK
            elif adjusted_score >= RiskThreshold.PORN_LOW * 0.8:
                risk_level = RiskLevel.LOW_RISK
            else:
                risk_level = RiskLevel.NO_RISK
        else:
            risk_level = RiskLevel.LOW_RISK
        
        return {
            "risk_level": risk_level,
            "primary_content": content1,
            "secondary_content": content2,
            "risk_details": {
                "reason": "combined_evaluation",
                "combined_score": adjusted_score if content1 == ContentType.PORN else score1,
                "is_swimwear_context": True
            }
        }
    
    def detect(self, image: Image.Image) -> Dict:
        processed_image = self._preprocess_image(image)
        
        predictions = self.model.predict(processed_image, verbose=0)[0]
        
        result = {}
        for idx, class_name in enumerate(self.class_names):
            result[class_name] = float(predictions[idx])
        
        risk_analysis = self._classify_risk(result)
        confidence = float(max(result.values()))
        
        return {
            "predictions": result,
            "risk_level": risk_analysis["risk_level"],
            "main_content": risk_analysis["primary_content"],
            "secondary_content": risk_analysis["secondary_content"],
            "confidence": confidence,
            "risk_details": risk_analysis["risk_details"],
            "is_swimwear_context": risk_analysis["risk_details"].get("is_swimwear_context", False)
        }
    
    def detect_batch(self, images: list) -> list:
        results = []
        for image in images:
            results.append(self.detect(image))
        return results

detector = ContentDetector()
