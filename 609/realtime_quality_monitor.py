from typing import List, Dict, Any
from datetime import datetime
from bert_analyzer import ServiceEmotionAttributionAnalyzer


class RealtimeQualityMonitor:
    def __init__(self):
        self.emotion_analyzer = ServiceEmotionAttributionAnalyzer()
        self.warning_thresholds = {
            "response_time": 60,
            "negative_emotion": 0.6,
            "impoliteness": 0.3,
            "silence_duration": 120
        }

    def analyze_realtime_message(self, conversation_history: List[Dict[str, Any]], 
                                  new_message: Dict[str, Any]) -> Dict[str, Any]:
        all_messages = conversation_history + [new_message]
        warnings = []
        
        if new_message.get("role") == "service":
            response_time_warning = self._check_response_time(all_messages)
            if response_time_warning:
                warnings.append(response_time_warning)
            
            emotion_warning = self._check_service_emotion(new_message)
            if emotion_warning:
                warnings.append(emotion_warning)
            
            politeness_warning = self._check_politeness(new_message)
            if politeness_warning:
                warnings.append(politeness_warning)
        
        silence_warning = self._check_silence(all_messages)
        if silence_warning:
            warnings.append(silence_warning)
        
        current_score = self._calculate_current_quality_score(all_messages)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "current_quality_score": current_score,
            "warning_count": len(warnings),
            "warnings": warnings,
            "suggestions": self._generate_suggestions(warnings)
        }

    def _check_response_time(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(messages) < 2:
            return None
        
        last_customer_msg = None
        last_service_msg = None
        
        for msg in reversed(messages[:-1]):
            if msg.get("role") == "customer" and not last_customer_msg:
                last_customer_msg = msg
            if msg.get("role") == "service" and not last_service_msg:
                last_service_msg = msg
            if last_customer_msg and last_service_msg:
                break
        
        if not last_customer_msg:
            return None
        
        new_service_msg = messages[-1]
        
        try:
            customer_time = datetime.fromisoformat(last_customer_msg.get("timestamp", "").replace('Z', '+00:00'))
            service_time = datetime.fromisoformat(new_service_msg.get("timestamp", "").replace('Z', '+00:00'))
            response_time = (service_time - customer_time).total_seconds()
            
            if response_time > self.warning_thresholds["response_time"]:
                return {
                    "type": "response_time",
                    "severity": "medium" if response_time < 120 else "high",
                    "message": f"响应时间过长: {int(response_time)}秒",
                    "suggestion": "请加快回复速度，建议在60秒内响应"
                }
        except:
            pass
        
        return None

    def _check_service_emotion(self, message: Dict[str, Any]) -> Dict[str, Any]:
        text = message.get("content", "")
        sentiment = self.emotion_analyzer.sentiment_analyzer.analyze_sentiment(text)
        
        if sentiment["negative"] > self.warning_thresholds["negative_emotion"]:
            return {
                "type": "negative_emotion",
                "severity": "high",
                "message": f"检测到负面情绪倾向 (消极度: {sentiment['negative']:.2f})",
                "suggestion": "请保持专业和耐心，避免负面情绪表达"
            }
        
        return None

    def _check_politeness(self, message: Dict[str, Any]) -> Dict[str, Any]:
        text = message.get("content", "")
        politeness = self.emotion_analyzer._analyze_politeness(text)
        
        if politeness["negative_score"] > self.warning_thresholds["impoliteness"]:
            return {
                "type": "impoliteness",
                "severity": "high",
                "message": "检测到不礼貌用语",
                "suggestion": "请使用礼貌用语，保持专业形象"
            }
        
        return None

    def _check_silence(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(messages) < 1:
            return None
        
        last_msg = messages[-1]
        if last_msg.get("role") != "customer":
            return None
        
        try:
            last_time = datetime.fromisoformat(last_msg.get("timestamp", "").replace('Z', '+00:00'))
            current_time = datetime.now()
            silence_duration = (current_time - last_time).total_seconds()
            
            if silence_duration > self.warning_thresholds["silence_duration"]:
                return {
                    "type": "long_silence",
                    "severity": "medium",
                    "message": f"客户等待时间过长: {int(silence_duration)}秒",
                    "suggestion": "请尽快回复客户，或告知客户需要稍等"
                }
        except:
            pass
        
        return None

    def _calculate_current_quality_score(self, messages: List[Dict[str, Any]]) -> float:
        service_messages = [m for m in messages if m.get("role") == "service"]
        
        if not service_messages:
            return 80.0
        
        total_score = 0
        for msg in service_messages:
            text = msg.get("content", "")
            sentiment = self.emotion_analyzer.sentiment_analyzer.analyze_sentiment(text)
            politeness = self.emotion_analyzer._analyze_politeness(text)
            
            sentiment_score = (sentiment["positive"] - sentiment["negative"] + 1) * 50
            politeness_score = 60 + politeness["overall"] * 40
            
            msg_score = (sentiment_score + politeness_score) / 2
            total_score += msg_score
        
        avg_score = total_score / len(service_messages)
        return round(avg_score, 2)

    def _generate_suggestions(self, warnings: List[Dict[str, Any]]) -> List[str]:
        suggestions = []
        for warning in warnings:
            suggestions.append(warning.get("suggestion", ""))
        
        if not warnings:
            suggestions.append("当前对话质量良好，请继续保持！")
        
        return suggestions

    def get_warning_summary(self, all_warnings: List[Dict[str, Any]]) -> Dict[str, Any]:
        warning_types = {}
        high_severity_count = 0
        
        for warning in all_warnings:
            w_type = warning.get("type", "unknown")
            warning_types[w_type] = warning_types.get(w_type, 0) + 1
            if warning.get("severity") == "high":
                high_severity_count += 1
        
        return {
            "total_warnings": len(all_warnings),
            "warning_types": warning_types,
            "high_severity_count": high_severity_count,
            "risk_level": "high" if high_severity_count >= 3 else "medium" if high_severity_count >= 1 else "low"
        }
