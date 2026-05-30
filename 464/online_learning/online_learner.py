import os
import sys
import time
import json
import threading
import numpy as np
from collections import deque, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lightgbm_model import LambdaMARTRanker
from config.config import FEATURE_COLUMNS, MODEL_DIR


class ClickFeedback:
    def __init__(self, query, product, position, clicked, dwell_time=0, timestamp=None):
        self.query = query
        self.product = product
        self.position = position
        self.clicked = clicked
        self.dwell_time = dwell_time
        self.timestamp = timestamp or time.time()
        self.features = None

    def to_dict(self):
        return {
            "query": self.query,
            "product_id": self.product.get("product_id"),
            "position": self.position,
            "clicked": self.clicked,
            "dwell_time": self.dwell_time,
            "timestamp": self.timestamp,
        }


class OnlineLearner:
    def __init__(self, base_model_path=None, feature_columns=None):
        self.ranker = LambdaMARTRanker(feature_columns=feature_columns)
        self.feedback_buffer = deque(maxlen=10000)
        self.training_queue = deque()
        self.lock = threading.Lock()
        self.update_count = 0
        self.last_update_time = None
        self.min_feedback_for_update = 50
        self.update_interval = 300

        if base_model_path and os.path.exists(base_model_path):
            model_name = os.path.basename(base_model_path)
            self.ranker.load_model(model_name)

        self.feedback_stats = {
            "total_feedback": 0,
            "clicks": 0,
            "skips": 0,
            "model_updates": 0,
        }

    def record_feedback(self, query, product, position, clicked, dwell_time=0, features=None):
        feedback = ClickFeedback(
            query=query,
            product=product,
            position=position,
            clicked=clicked,
            dwell_time=dwell_time,
        )
        feedback.features = features

        with self.lock:
            self.feedback_buffer.append(feedback)
            self.feedback_stats["total_feedback"] += 1
            if clicked:
                self.feedback_stats["clicks"] += 1
            else:
                self.feedback_stats["skips"] += 1

        return feedback

    def record_search_session(self, query, products, clicked_positions, dwell_times=None):
        if dwell_times is None:
            dwell_times = [0] * len(products)

        for i, product in enumerate(products):
            clicked = i in clicked_positions
            dwell_time = dwell_times[i] if i < len(dwell_times) else 0
            self.record_feedback(query, product, i, clicked, dwell_time)

    def _compute_click_based_label(self, feedback, query_results):
        position = feedback.position
        clicked = feedback.clicked

        label = 0
        if clicked:
            if feedback.dwell_time > 30:
                label = 4
            elif feedback.dwell_time > 10:
                label = 3
            else:
                label = 2
        else:
            label = 1

        return label

    def _prepare_training_data_from_feedback(self, feedback_list, feature_extractor_fn):
        query_groups = defaultdict(list)
        for fb in feedback_list:
            query_groups[fb.query].append(fb)

        X_list = []
        y_list = []
        groups = []

        for query, feedbacks in query_groups.items():
            group_labels = []
            for fb in feedbacks:
                if fb.features is not None:
                    features = fb.features
                else:
                    features = feature_extractor_fn(query, fb.product)

                X_list.append([features.get(col, 0.0) for col in FEATURE_COLUMNS])
                label = self._compute_click_based_label(fb, feedbacks)
                group_labels.append(label)
                y_list.append(label)

            groups.append(len(feedbacks))

        return np.array(X_list), np.array(y_list, dtype=np.float32), groups

    def should_update(self):
        with self.lock:
            if len(self.feedback_buffer) < self.min_feedback_for_update:
                return False

            if self.last_update_time is None:
                return True

            time_since_update = time.time() - self.last_update_time
            return time_since_update >= self.update_interval

    def update_model(self, feature_extractor_fn):
        if not self.should_update():
            return False

        with self.lock:
            feedback_list = list(self.feedback_buffer)
            self.feedback_buffer.clear()

        X_new, y_new, groups_new = self._prepare_training_data_from_feedback(
            feedback_list, feature_extractor_fn
        )

        if len(X_new) < 10:
            return False

        try:
            if self.ranker.is_loaded():
                self.ranker.params["learning_rate"] = 0.01
                self.ranker.params["num_leaves"] = 31

                model = self.ranker.train(
                    X_new, y_new, groups_new,
                    num_boost_round=50,
                    early_stopping_rounds=10,
                )
            else:
                model = self.ranker.train(
                    X_new, y_new, groups_new,
                    num_boost_round=100,
                    early_stopping_rounds=20,
                )

            self.update_count += 1
            self.last_update_time = time.time()
            self.feedback_stats["model_updates"] += 1

            timestamp = int(time.time())
            backup_path = f"lambdamart_online_{timestamp}.txt"
            self.ranker.save_model(backup_path)

            return True

        except Exception as e:
            print(f"Online update failed: {e}")
            return False

    def predict(self, X):
        return self.ranker.predict(X)

    def get_stats(self):
        with self.lock:
            stats = self.feedback_stats.copy()
            stats["buffer_size"] = len(self.feedback_buffer)
            stats["update_count"] = self.update_count
            stats["click_rate"] = stats["clicks"] / max(stats["total_feedback"], 1)
        return stats

    def save_state(self, filepath):
        state = {
            "feedback_stats": self.feedback_stats,
            "update_count": self.update_count,
            "last_update_time": self.last_update_time,
        }
        with open(filepath, "w") as f:
            json.dump(state, f)

    def load_state(self, filepath):
        with open(filepath, "r") as f:
            state = json.load(f)
        self.feedback_stats = state.get("feedback_stats", self.feedback_stats)
        self.update_count = state.get("update_count", 0)
        self.last_update_time = state.get("last_update_time")


class FeedbackSimulator:
    def __init__(self, click_prob_model=None):
        self.click_prob_model = click_prob_model or self._default_click_model

    def _default_click_model(self, position, relevance_score):
        position_bias = 1.0 / (position + 2)
        click_prob = position_bias * (0.1 + 0.8 * relevance_score)
        return min(click_prob, 1.0)

    def simulate_click(self, position, relevance_score):
        prob = self.click_prob_model(position, relevance_score)
        clicked = np.random.random() < prob
        dwell_time = np.random.randint(5, 60) if clicked else 0
        return clicked, dwell_time

    def simulate_search_session(self, query, products, relevance_scores):
        clicked_positions = []
        dwell_times = []

        for pos, (product, score) in enumerate(zip(products, relevance_scores)):
            clicked, dwell_time = self.simulate_click(pos, score)
            dwell_times.append(dwell_time)
            if clicked:
                clicked_positions.append(pos)

        return clicked_positions, dwell_times
