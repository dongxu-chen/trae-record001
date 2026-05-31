import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from bert_analyzer import ServiceEmotionAttributionAnalyzer


class ResponseSpeedScorer:
    def __init__(self):
        self.ideal_response_time = 30
        self.max_penalty_time = 300

    def calculate_score(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(messages) < 2:
            return {"score": 100, "avg_response_time": 0, "details": {}}

        response_times = []
        customer_times = []

        for i in range(1, len(messages)):
            prev_msg = messages[i - 1]
            curr_msg = messages[i]

            if prev_msg.get("role") == "customer" and curr_msg.get("role") == "service":
                prev_time = prev_msg.get("timestamp")
                curr_time = curr_msg.get("timestamp")

                if prev_time and curr_time:
                    if isinstance(prev_time, str):
                        prev_time = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
                    if isinstance(curr_time, str):
                        curr_time = datetime.fromisoformat(curr_time.replace('Z', '+00:00'))

                    time_diff = (curr_time - prev_time).total_seconds()
                    response_times.append(time_diff)
                    customer_times.append(prev_time)

        if not response_times:
            return {"score": 100, "avg_response_time": 0, "details": {}}

        avg_time = np.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)

        score = self._time_to_score(avg_time)

        slow_responses = [t for t in response_times if t > 60]
        slow_count = len(slow_responses)

        return {
            "score": round(score, 2),
            "avg_response_time": round(avg_time, 2),
            "max_response_time": round(max_time, 2),
            "min_response_time": round(min_time, 2),
            "response_count": len(response_times),
            "slow_response_count": slow_count,
            "response_times": [round(t, 2) for t in response_times],
            "details": {
                "avg_time_seconds": round(avg_time, 2),
                "slow_responses": slow_count,
                "very_slow_responses": len([t for t in response_times if t > 120])
            }
        }

    def _time_to_score(self, avg_time: float) -> float:
        if avg_time <= self.ideal_response_time:
            return 100
        elif avg_time >= self.max_penalty_time:
            return 40
        else:
            penalty_ratio = (avg_time - self.ideal_response_time) / (self.max_penalty_time - self.ideal_response_time)
            return 100 - penalty_ratio * 60


class CustomerSatisfactionScorer:
    def __init__(self):
        self.survey_keywords = {
            "very_satisfied": ["非常满意", "很满意", "太好了", "很棒", "优秀", "专业", "感谢", "谢谢", "五星", "好评"],
            "satisfied": ["满意", "可以", "还行", "不错", "好的", "了解了", "清楚了"],
            "neutral": ["一般", "普通", "还行吧", "凑活", "还好"],
            "dissatisfied": ["不满意", "不好", "不行", "差劲", "失望", "恼火"],
            "very_dissatisfied": ["非常不满意", "太差了", "垃圾", "投诉", "举报", "再也不", "退款", "赔偿"]
        }

    def calculate_score(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        messages = conversation.get("messages", [])
        post_survey = conversation.get("post_survey", {})

        if post_survey:
            return self._calculate_from_survey(post_survey)
        else:
            return self._calculate_from_conversation(messages)

    def _calculate_from_survey(self, post_survey: Dict[str, Any]) -> Dict[str, Any]:
        satisfaction_score = post_survey.get("satisfaction_score", 3)
        resolution_rating = post_survey.get("resolution_rating", 3)
        attitude_rating = post_survey.get("attitude_rating", 3)
        would_recommend = post_survey.get("would_recommend", False)
        comment = post_survey.get("comment", "")

        base_score = (satisfaction_score / 5) * 100
        resolution_bonus = (resolution_rating - 3) * 5
        attitude_bonus = (attitude_rating - 3) * 5
        recommend_bonus = 10 if would_recommend else 0

        comment_sentiment = self._analyze_comment_sentiment(comment)
        comment_bonus = comment_sentiment * 8

        final_score = base_score + resolution_bonus + attitude_bonus + recommend_bonus + comment_bonus
        final_score = max(0, min(100, final_score))

        satisfaction_level = self._get_satisfaction_level(satisfaction_score)

        return {
            "score": round(final_score, 2),
            "satisfaction_score": satisfaction_score,
            "satisfaction_level": satisfaction_level,
            "resolution_rating": resolution_rating,
            "attitude_rating": attitude_rating,
            "would_recommend": would_recommend,
            "comment": comment,
            "source": "post_survey",
            "details": {
                "base_score": round(base_score, 2),
                "resolution_bonus": resolution_bonus,
                "attitude_bonus": attitude_bonus,
                "recommend_bonus": recommend_bonus,
                "comment_bonus": round(comment_bonus, 2)
            }
        }

    def _calculate_from_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        customer_messages = [m for m in messages if m.get("role") == "customer"]

        if not customer_messages:
            return {
                "score": 60,
                "satisfaction_score": 3,
                "satisfaction_level": "neutral",
                "source": "conversation_estimated",
                "details": {}
            }

        last_customer_msg = customer_messages[-1].get("content", "")
        all_customer_text = " ".join([m.get("content", "") for m in customer_messages])

        very_satisfied_count = self._count_keywords(all_customer_text, self.survey_keywords["very_satisfied"])
        satisfied_count = self._count_keywords(all_customer_text, self.survey_keywords["satisfied"])
        dissatisfied_count = self._count_keywords(all_customer_text, self.survey_keywords["dissatisfied"])
        very_dissatisfied_count = self._count_keywords(all_customer_text, self.survey_keywords["very_dissatisfied"])

        last_very_satisfied = self._count_keywords(last_customer_msg, self.survey_keywords["very_satisfied"])
        last_satisfied = self._count_keywords(last_customer_msg, self.survey_keywords["satisfied"])
        last_dissatisfied = self._count_keywords(last_customer_msg, self.survey_keywords["dissatisfied"])
        last_very_dissatisfied = self._count_keywords(last_customer_msg, self.survey_keywords["very_dissatisfied"])

        positive_score = (very_satisfied_count * 2 + satisfied_count) * 8
        negative_score = (very_dissatisfied_count * 2 + dissatisfied_count) * 8

        last_positive = (last_very_satisfied * 2 + last_satisfied) * 5
        last_negative = (last_very_dissatisfied * 2 + last_dissatisfied) * 5

        estimated_score = 60 + positive_score - negative_score + last_positive - last_negative
        estimated_score = max(0, min(100, estimated_score))

        satisfaction_score = round(estimated_score / 20)
        satisfaction_score = max(1, min(5, satisfaction_score))

        satisfaction_level = self._get_satisfaction_level(satisfaction_score)

        return {
            "score": round(estimated_score, 2),
            "satisfaction_score": satisfaction_score,
            "satisfaction_level": satisfaction_level,
            "source": "conversation_estimated",
            "details": {
                "positive_indicators": very_satisfied_count + satisfied_count,
                "negative_indicators": very_dissatisfied_count + dissatisfied_count,
                "last_message_sentiment": "positive" if last_positive > last_negative else "negative" if last_negative > last_positive else "neutral"
            }
        }

    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        text_lower = text.lower()
        return sum(1 for kw in keywords if kw in text_lower)

    def _analyze_comment_sentiment(self, comment: str) -> float:
        if not comment:
            return 0

        positive_count = self._count_keywords(comment, self.survey_keywords["very_satisfied"] + self.survey_keywords["satisfied"])
        negative_count = self._count_keywords(comment, self.survey_keywords["very_dissatisfied"] + self.survey_keywords["dissatisfied"])

        total = positive_count + negative_count + 1
        return (positive_count - negative_count) / total

    def _get_satisfaction_level(self, score: int) -> str:
        if score >= 5:
            return "very_satisfied"
        elif score >= 4:
            return "satisfied"
        elif score >= 3:
            return "neutral"
        elif score >= 2:
            return "dissatisfied"
        else:
            return "very_dissatisfied"


class ComprehensiveScorer:
    def __init__(self):
        self.response_speed_scorer = ResponseSpeedScorer()
        self.customer_satisfaction_scorer = CustomerSatisfactionScorer()
        self.service_emotion_analyzer = ServiceEmotionAttributionAnalyzer()

        self.weights = {
            "response_speed": 0.25,
            "customer_satisfaction": 0.40,
            "service_emotion": 0.35
        }

    def score_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        messages = conversation.get("messages", [])

        speed_result = self.response_speed_scorer.calculate_score(messages)
        satisfaction_result = self.customer_satisfaction_scorer.calculate_score(conversation)
        emotion_result = self.service_emotion_analyzer.analyze_service_emotion(messages)

        speed_score = speed_result.get("score", 0)
        satisfaction_score = satisfaction_result.get("score", 0)
        emotion_score = emotion_result.get("score", 0)

        comprehensive_score = (
            speed_score * self.weights["response_speed"] +
            satisfaction_score * self.weights["customer_satisfaction"] +
            emotion_score * self.weights["service_emotion"]
        )

        deductions = self._identify_deductions(
            speed_result, satisfaction_result, emotion_result
        )

        grade = self._get_grade(comprehensive_score)

        return {
            "conversation_id": conversation.get("id", "unknown"),
            "agent_id": conversation.get("agent_id", "unknown"),
            "customer_id": conversation.get("customer_id", "unknown"),
            "timestamp": conversation.get("timestamp", ""),
            "comprehensive_score": round(comprehensive_score, 2),
            "grade": grade,
            "dimension_scores": {
                "response_speed": {
                    "score": speed_score,
                    "weight": self.weights["response_speed"],
                    "details": speed_result
                },
                "customer_satisfaction": {
                    "score": satisfaction_score,
                    "weight": self.weights["customer_satisfaction"],
                    "details": satisfaction_result
                },
                "service_emotion": {
                    "score": emotion_score,
                    "weight": self.weights["service_emotion"],
                    "details": emotion_result
                }
            },
            "deductions": deductions,
            "summary": {
                "total_messages": len(messages),
                "service_messages": len([m for m in messages if m.get("role") == "service"]),
                "customer_messages": len([m for m in messages if m.get("role") == "customer"]),
                "satisfaction_level": satisfaction_result.get("satisfaction_level", "unknown"),
                "emotion_stability": emotion_result.get("emotion_stability", "unknown")
            }
        }

    def _identify_deductions(self, speed_result: Dict, satisfaction_result: Dict, emotion_result: Dict) -> List[Dict]:
        deductions = []

        speed_score = speed_result.get("score", 100)
        if speed_score < 90:
            deductions.append({
                "category": "响应速度",
                "score_loss": round(100 - speed_score, 2),
                "severity": "high" if speed_score < 70 else "medium",
                "description": f"平均响应时间 {speed_result.get('avg_response_time', 0)}秒，超过理想值30秒",
                "suggestion": "加强响应速度培训，设置消息提醒，避免让客户等待"
            })

        satisfaction_score = satisfaction_result.get("score", 100)
        if satisfaction_score < 80:
            level = satisfaction_result.get("satisfaction_level", "unknown")
            source = satisfaction_result.get("source", "unknown")
            deductions.append({
                "category": "用户满意度",
                "score_loss": round(100 - satisfaction_score, 2),
                "severity": "high" if satisfaction_score < 60 else "medium",
                "description": f"用户满意度评价: {level} (数据源: {source})",
                "suggestion": "提升服务质量，关注用户体验，积极解决用户问题"
            })

        emotion_score = emotion_result.get("score", 100)
        if emotion_score < 85:
            emotion_issues = emotion_result.get("emotion_issues", [])
            issue_desc = "; ".join([f"{i['type']}" for i in emotion_issues]) if emotion_issues else "客服情绪稳定性不足"
            customer_provocation = emotion_result.get("customer_provocation_count", 0)
            if customer_provocation > 0:
                issue_desc += f" (已剔除客户激怒因素: {customer_provocation}次)"
            deductions.append({
                "category": "客服情绪归因",
                "score_loss": round(100 - emotion_score, 2),
                "severity": "high" if emotion_score < 70 else "medium",
                "description": issue_desc,
                "suggestion": "加强情绪管理培训，保持专业态度，不受客户情绪影响"
            })

        return deductions

    def _get_grade(self, score: float) -> str:
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
