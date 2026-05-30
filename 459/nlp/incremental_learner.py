import json
import os
import time
from typing import List, Dict, Any, Optional
from collections import Counter
import logging

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedbackStore:
    def __init__(self, store_path: str = None):
        self.store_path = store_path or os.path.join(
            os.path.dirname(__file__), "..", "data", "feedback_store.json"
        )
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        self.feedback_list = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(self.feedback_list, f, ensure_ascii=False, indent=2)

    def add_feedback(self, feedback: Dict[str, Any]) -> str:
        feedback_id = f"fb_{int(time.time() * 1000)}"
        feedback["id"] = feedback_id
        feedback["timestamp"] = time.time()
        feedback["processed"] = False
        self.feedback_list.append(feedback)
        self._save()
        logger.info(f"反馈已保存: {feedback_id}")
        return feedback_id

    def get_unprocessed(self) -> List[Dict[str, Any]]:
        return [fb for fb in self.feedback_list if not fb.get("processed", False)]

    def mark_processed(self, feedback_ids: List[str]):
        for fb in self.feedback_list:
            if fb["id"] in feedback_ids:
                fb["processed"] = True
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.feedback_list)
        if total == 0:
            return {"total": 0, "positive": 0, "negative": 0, "unprocessed": 0, "rate": 0}

        positive = sum(1 for fb in self.feedback_list if fb.get("rating", 0) >= 4)
        negative = sum(1 for fb in self.feedback_list if fb.get("rating", 0) <= 2)
        unprocessed = sum(1 for fb in self.feedback_list if not fb.get("processed", False))

        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "unprocessed": unprocessed,
            "satisfaction_rate": positive / total if total > 0 else 0
        }

    def get_negative_feedback(self) -> List[Dict[str, Any]]:
        return [fb for fb in self.feedback_list if fb.get("rating", 0) <= 2]


class IncrementalLearner:
    def __init__(self, feedback_store: FeedbackStore = None):
        self.feedback_store = feedback_store or FeedbackStore()
        self.intent_correction_rules = {}
        self.entity_correction_rules = {}
        self.answer_correction_rules = {}
        self.custom_qa_pairs = []

        self._correction_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "correction_rules.json"
        )
        os.makedirs(os.path.dirname(self._correction_path), exist_ok=True)
        self._load_rules()

    def _load_rules(self):
        if os.path.exists(self._correction_path):
            try:
                with open(self._correction_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.intent_correction_rules = data.get("intent_rules", {})
                self.entity_correction_rules = data.get("entity_rules", {})
                self.answer_correction_rules = data.get("answer_rules", {})
                self.custom_qa_pairs = data.get("qa_pairs", [])
            except Exception:
                pass

    def _save_rules(self):
        data = {
            "intent_rules": self.intent_correction_rules,
            "entity_rules": self.entity_correction_rules,
            "answer_rules": self.answer_correction_rules,
            "qa_pairs": self.custom_qa_pairs
        }
        with open(self._correction_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def process_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        feedback_id = self.feedback_store.add_feedback(feedback)

        result = {
            "feedback_id": feedback_id,
            "processed": False,
            "actions": []
        }

        rating = feedback.get("rating", 0)
        question = feedback.get("question", "")
        correction = feedback.get("correction", {})
        correct_intent = feedback.get("correct_intent")
        correct_answer = feedback.get("correct_answer")
        correct_entity = feedback.get("correct_entity")

        if correct_intent and question:
            self.intent_correction_rules[question] = correct_intent
            result["actions"].append(f"意图修正: {question} -> {correct_intent}")

        if correct_entity and question:
            original_entity = feedback.get("original_entity", "")
            if original_entity:
                self.entity_correction_rules[original_entity] = correct_entity
                result["actions"].append(f"实体修正: {original_entity} -> {correct_entity}")

        if correct_answer and question:
            self.answer_correction_rules[question] = correct_answer
            result["actions"].append(f"答案修正: {question} -> {correct_answer}")

        if rating <= 2 and correction:
            self.custom_qa_pairs.append({
                "question": question,
                "answer": correction.get("answer", correct_answer or ""),
                "intent": correction.get("intent", correct_intent or ""),
                "source": "user_feedback",
                "timestamp": time.time()
            })
            result["actions"].append("新增自定义问答对")

        if rating >= 4:
            self.custom_qa_pairs.append({
                "question": question,
                "answer": feedback.get("given_answer", ""),
                "intent": feedback.get("given_intent", ""),
                "source": "positive_reinforcement",
                "timestamp": time.time()
            })
            result["actions"].append("正向强化记录")

        if result["actions"]:
            self._save_rules()
            result["processed"] = True

        return result

    def apply_intent_correction(self, question: str, predicted_intent: str) -> str:
        if question in self.intent_correction_rules:
            corrected = self.intent_correction_rules[question]
            logger.info(f"意图修正: {predicted_intent} -> {corrected} (基于用户反馈)")
            return corrected

        for rule_q, rule_intent in self.intent_correction_rules.items():
            if self._similar_question(question, rule_q):
                logger.info(f"意图修正(相似匹配): {predicted_intent} -> {rule_intent}")
                return rule_intent

        return predicted_intent

    def apply_entity_correction(self, entity_text: str) -> Optional[str]:
        if entity_text in self.entity_correction_rules:
            return self.entity_correction_rules[entity_text]
        return None

    def apply_answer_correction(self, question: str) -> Optional[str]:
        if question in self.answer_correction_rules:
            return self.answer_correction_rules[question]

        for rule_q, rule_a in self.answer_correction_rules.items():
            if self._similar_question(question, rule_q):
                return rule_a

        return None

    def get_training_samples(self) -> List[Dict[str, Any]]:
        samples = []
        for pair in self.custom_qa_pairs:
            samples.append({
                "question": pair["question"],
                "intent": pair.get("intent", ""),
                "answer": pair.get("answer", ""),
                "source": pair.get("source", "unknown")
            })

        for rule_q, rule_intent in self.intent_correction_rules.items():
            samples.append({
                "question": rule_q,
                "intent": rule_intent,
                "source": "intent_correction"
            })

        return samples

    def batch_process_unprocessed(self) -> Dict[str, Any]:
        unprocessed = self.feedback_store.get_unprocessed()
        processed_count = 0
        actions = []

        for fb in unprocessed:
            result = self.process_feedback(fb)
            if result["processed"]:
                processed_count += 1
                actions.extend(result["actions"])

        if processed_count > 0:
            self.feedback_store.mark_processed(
                [fb["id"] for fb in unprocessed]
            )

        return {
            "processed_count": processed_count,
            "total_unprocessed": len(unprocessed),
            "actions": actions
        }

    def _similar_question(self, q1: str, q2: str) -> bool:
        if not q1 or not q2:
            return False

        set1 = set(q1)
        set2 = set(q2)
        if not set1 or not set2:
            return False

        intersection = set1 & set2
        union = set1 | set2
        jaccard = len(intersection) / len(union) if union else 0

        if jaccard > 0.6:
            return True

        if q1 in q2 or q2 in q1:
            return True

        common_chars = sum(1 for c in q1 if c in q2)
        if common_chars / max(len(q1), len(q2)) > 0.7:
            return True

        return False

    def get_learning_stats(self) -> Dict[str, Any]:
        feedback_stats = self.feedback_store.get_stats()
        return {
            "feedback_stats": feedback_stats,
            "intent_corrections": len(self.intent_correction_rules),
            "entity_corrections": len(self.entity_correction_rules),
            "answer_corrections": len(self.answer_correction_rules),
            "custom_qa_pairs": len(self.custom_qa_pairs),
            "training_samples_available": len(self.get_training_samples())
        }
