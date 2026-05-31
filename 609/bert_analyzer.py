import numpy as np
from typing import List, Dict, Tuple, Any

try:
    import torch
    from transformers import BertTokenizer, BertForSequenceClassification
    BERT_AVAILABLE = True
except Exception as e:
    print(f"Warning: PyTorch/Transformers not available: {e}")
    print("Using rule-based sentiment analysis only.")
    BERT_AVAILABLE = False


class SentimentAnalyzer:
    def __init__(self, model_name: str = "bert-base-chinese"):
        self.model_name = model_name
        self.device = None
        self.tokenizer = None
        self.model = None
        if BERT_AVAILABLE:
            self._load_model()

    def _load_model(self):
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
            self.model = BertForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=3
            ).to(self.device)
            self.model.eval()
        except Exception as e:
            print(f"Warning: Could not load BERT model: {e}")
            print("Using rule-based sentiment analysis as fallback.")
            self.model = None

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        if not BERT_AVAILABLE or self.model is None:
            return self._rule_based_sentiment(text)

        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]

            return {
                "negative": float(probabilities[0]),
                "neutral": float(probabilities[1]),
                "positive": float(probabilities[2])
            }
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return self._rule_based_sentiment(text)

    def _rule_based_sentiment(self, text: str) -> Dict[str, float]:
        positive_words = [
            "您好", "请", "谢谢", "感谢", "不客气", "抱歉", "对不起",
            "很高兴", "满意", "帮到您", "为您服务", "祝您", "欢迎",
            "好的", "没问题", "可以", "是的", "对的", "理解",
            "请稍等", "马上", "立刻", "尽快", "专业", "耐心", "细致"
        ]
        negative_words = [
            "不知道", "不清楚", "没办法", "不行", "不能", "不可以",
            "等等", "等一下", "自己", "你自己", "应该", "必须",
            "烦", "恼火", "生气", "投诉", "不满意", "差", "糟糕",
            "为什么不", "怎么不", "你不懂", "不会吧", "不可能"
        ]

        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        total = pos_count + neg_count + 1
        positive = pos_count / total
        negative = neg_count / total
        neutral = 1 - positive - negative

        return {
            "negative": max(0.0, negative),
            "neutral": max(0.0, neutral),
            "positive": max(0.0, positive)
        }


class CustomerProvocationDetector:
    def __init__(self):
        self.provocation_patterns = [
            "你什么态度", "什么态度", "你们怎么回事", "怎么搞的",
            "你们是垃圾", "垃圾", "废物", "没用", "差劲",
            "投诉你", "我要投诉", "举报", "曝光",
            "你们是不是傻", "脑子有病", "有病", "神经病",
            "会不会说话", "听不懂人话", "你聋了", "你瞎吗",
            "去死", "滚蛋", "滚", "闭嘴",
            "什么玩意儿", "什么东西", "什么服务",
            "差评", "给差评", "再也不买", "再也不来"
        ]
        self.negative_emotion_words = [
            "愤怒", "生气", "恼火", "气愤", "不满", "失望",
            "太差了", "太烂了", "糟糕透了", "什么玩意"
        ]

    def detect_provocation(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()

        provocation_count = 0
        matched_patterns = []

        for pattern in self.provocation_patterns:
            if pattern in text_lower:
                provocation_count += 1
                matched_patterns.append(pattern)

        emotion_intensity = 0
        for word in self.negative_emotion_words:
            if word in text_lower:
                emotion_intensity += 0.2

        exclamation_count = text.count("!")
        if exclamation_count >= 3:
            emotion_intensity += 0.3

        question_count = text.count("?")
        if question_count >= 3:
            emotion_intensity += 0.2

        is_provocation = provocation_count > 0 or emotion_intensity >= 0.5
        provocation_level = min(1.0, provocation_count * 0.25 + emotion_intensity)

        return {
            "is_provocation": is_provocation,
            "provocation_level": provocation_level,
            "provocation_count": provocation_count,
            "matched_patterns": matched_patterns,
            "emotion_intensity": emotion_intensity
        }


class ServiceEmotionAttributionAnalyzer:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.provocation_detector = CustomerProvocationDetector()

        self.polite_patterns = [
            "您好", "你好", "请问", "请您", "麻烦您", "劳驾",
            "谢谢", "感谢", "不客气", "不好意思", "抱歉", "对不起",
            "请稍等", "请耐心", "请理解", "请谅解",
            "很高兴为您服务", "祝您", "欢迎您", "感谢您的"
        ]
        self.negative_service_patterns = [
            "你自己", "自己看", "不知道", "不清楚", "我怎么知道",
            "随便", "无所谓", "等着", "急什么", "吵什么",
            "不是告诉你了吗", "听不懂吗", "你傻啊", "有病",
            "凭什么", "管不着", "你到底", "你能不能",
            "那没办法", "解决不了", "不可能", "不行就是不行"
        ]

    def analyze_service_emotion(self, messages: List[Dict[str, str]]) -> Dict:
        if not messages:
            return {"score": 50, "details": {}, "emotion_issues": []}

        service_messages = [m for m in messages if m.get("role") == "service"]

        if not service_messages:
            return {"score": 50, "details": {}, "emotion_issues": []}

        customer_provocations = self._detect_customer_provocations(messages)
        customer_provocation_count = sum(1 for p in customer_provocations if p["is_provocation"])

        emotion_scores = []
        emotion_issues = []
        emotion_trend = []

        for i, msg in enumerate(service_messages):
            text = msg.get("content", "")
            msg_index = messages.index(msg)

            was_provoked = self._was_provoked_before(messages, msg_index)

            sentiment = self.sentiment_analyzer.analyze_sentiment(text)
            politeness = self._analyze_politeness(text)

            adjusted_score = self._calculate_adjusted_emotion_score(
                sentiment, politeness, was_provoked
            )
            emotion_scores.append(adjusted_score)
            emotion_trend.append(adjusted_score)

            issue = self._identify_emotion_issue(text, sentiment, politeness, was_provoked)
            if issue:
                emotion_issues.append(issue)

        avg_emotion_score = np.mean(emotion_scores) if emotion_scores else 50
        emotion_stability = np.std(emotion_trend) if len(emotion_trend) > 1 else 0
        stability_level = self._get_stability_level(emotion_stability)

        final_score = 50 + avg_emotion_score * 25
        final_score = max(0, min(100, final_score))

        positive_ratio = np.mean([s["positive"] for s in [
            self.sentiment_analyzer.analyze_sentiment(m.get("content", ""))
            for m in service_messages
        ]])
        negative_ratio = np.mean([s["negative"] for s in [
            self.sentiment_analyzer.analyze_sentiment(m.get("content", ""))
            for m in service_messages
        ]])

        issues_unique = self._deduplicate_issues(emotion_issues)

        return {
            "score": round(final_score, 2),
            "emotion_stability": stability_level,
            "customer_provocation_count": customer_provocation_count,
            "details": {
                "avg_emotion_score": round(avg_emotion_score, 3),
                "positive_ratio": round(positive_ratio, 3),
                "negative_ratio": round(negative_ratio, 3),
                "emotion_stability_score": round(1 - min(1, emotion_stability / 0.5), 3),
                "message_count": len(service_messages),
                "emotion_trend": [round(s, 2) for s in emotion_trend]
            },
            "emotion_issues": issues_unique
        }

    def _detect_customer_provocations(self, messages: List[Dict[str, str]]) -> List[Dict]:
        provocations = []
        for msg in messages:
            if msg.get("role") == "customer":
                result = self.provocation_detector.detect_provocation(msg.get("content", ""))
                provocations.append(result)
        return provocations

    def _was_provoked_before(self, messages: List[Dict[str, str]], service_msg_index: int) -> bool:
        for i in range(service_msg_index):
            if messages[i].get("role") == "customer":
                provocation = self.provocation_detector.detect_provocation(messages[i].get("content", ""))
                if provocation["is_provocation"] and provocation["provocation_level"] >= 0.5:
                    return True
        return False

    def _analyze_politeness(self, text: str) -> Dict[str, float]:
        text_lower = text.lower()
        polite_count = sum(1 for p in self.polite_patterns if p in text_lower)
        negative_count = sum(1 for p in self.negative_service_patterns if p in text_lower)

        polite_score = min(1.0, polite_count * 0.15)
        negative_score = min(1.0, negative_count * 0.25)

        return {
            "polite_score": polite_score,
            "negative_score": negative_score,
            "overall": 0.5 + polite_score - negative_score
        }

    def _calculate_adjusted_emotion_score(self, sentiment: Dict, politeness: Dict, was_provoked: bool) -> float:
        sentiment_score = sentiment["positive"] - sentiment["negative"]
        politeness_score = politeness["overall"] - 0.5

        base_score = sentiment_score * 0.6 + politeness_score * 0.8

        if was_provoked and base_score >= -0.3:
            base_score = min(0.5, base_score + 0.3)
        elif was_provoked and base_score < -0.3:
            base_score = base_score * 0.5

        return base_score

    def _identify_emotion_issue(self, text: str, sentiment: Dict, politeness: Dict, was_provoked: bool) -> Dict:
        issues = []

        if politeness["negative_score"] >= 0.25:
            if was_provoked:
                issues.append({
                    "type": "不礼貌用语（客户激怒后）",
                    "severity": "low",
                    "note": "考虑到客户先有激怒行为，此项扣分已减轻"
                })
            else:
                issues.append({
                    "type": "不礼貌用语",
                    "severity": "high",
                    "note": "在无客户激怒情况下使用不礼貌用语"
                })

        if sentiment["negative"] >= 0.5:
            if was_provoked:
                issues.append({
                    "type": "负面情绪表达（客户激怒后）",
                    "severity": "low",
                    "note": "考虑到客户先有激怒行为，此项扣分已减轻"
                })
            else:
                issues.append({
                    "type": "负面情绪表达",
                    "severity": "medium",
                    "note": "在无客户激怒情况下表达负面情绪"
                })

        if len(text) < 5 and sentiment["neutral"] > 0.7:
            issues.append({
                "type": "回应过于简短",
                "severity": "low",
                "note": "建议提供更详细的回复"
            })

        return issues[0] if issues else None

    def _deduplicate_issues(self, issues: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for issue in issues:
            if issue and issue.get("type") not in seen:
                seen.add(issue.get("type"))
                unique.append(issue)
        return unique

    def _get_stability_level(self, std_dev: float) -> str:
        if std_dev < 0.1:
            return "very_stable"
        elif std_dev < 0.2:
            return "stable"
        elif std_dev < 0.35:
            return "moderate"
        elif std_dev < 0.5:
            return "unstable"
        else:
            return "very_unstable"
