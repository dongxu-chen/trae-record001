import os
import sys
import json
import numpy as np
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class UserProfile:
    def __init__(self, user_id):
        self.user_id = user_id
        self.category_preference = defaultdict(float)
        self.brand_preference = defaultdict(float)
        self.price_range = {"min": None, "max": None, "mean": None, "median": None}
        self.click_history = []
        self.purchase_history = []
        self.browse_history = []
        self.last_active = None

    def update_from_click(self, product, timestamp=None, weight=1.0):
        category = product.get("category", "")
        brand = product.get("brand", "")
        price = product.get("price", 0)

        self.category_preference[category] += weight
        self.brand_preference[brand] += weight

        self.click_history.append({
            "product_id": product.get("product_id"),
            "timestamp": timestamp,
            "category": category,
            "brand": brand,
            "price": price,
        })

        self._update_price_stats(price)

    def update_from_purchase(self, product, timestamp=None, weight=3.0):
        category = product.get("category", "")
        brand = product.get("brand", "")
        price = product.get("price", 0)

        self.category_preference[category] += weight
        self.brand_preference[brand] += weight

        self.purchase_history.append({
            "product_id": product.get("product_id"),
            "timestamp": timestamp,
            "category": category,
            "brand": brand,
            "price": price,
        })

        self._update_price_stats(price)

    def update_from_browse(self, product, timestamp=None, weight=0.5):
        category = product.get("category", "")
        brand = product.get("brand", "")
        price = product.get("price", 0)

        self.category_preference[category] += weight
        self.brand_preference[brand] += weight

        self.browse_history.append({
            "product_id": product.get("product_id"),
            "timestamp": timestamp,
            "category": category,
            "brand": brand,
            "price": price,
        })

        self._update_price_stats(price)

    def _update_price_stats(self, price):
        all_prices = [
            item["price"] for item in
            self.click_history + self.purchase_history + self.browse_history
        ]
        if all_prices:
            self.price_range["min"] = min(all_prices)
            self.price_range["max"] = max(all_prices)
            self.price_range["mean"] = np.mean(all_prices)
            self.price_range["median"] = np.median(all_prices)

    def get_top_categories(self, n=5):
        sorted_cats = sorted(self.category_preference.items(), key=lambda x: -x[1])
        return sorted_cats[:n]

    def get_top_brands(self, n=5):
        sorted_brands = sorted(self.brand_preference.items(), key=lambda x: -x[1])
        return sorted_brands[:n]

    def normalize_preferences(self):
        cat_sum = sum(self.category_preference.values())
        brand_sum = sum(self.brand_preference.values())

        if cat_sum > 0:
            for cat in self.category_preference:
                self.category_preference[cat] /= cat_sum

        if brand_sum > 0:
            for brand in self.brand_preference:
                self.brand_preference[brand] /= brand_sum

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "category_preference": dict(self.category_preference),
            "brand_preference": dict(self.brand_preference),
            "price_range": self.price_range,
            "click_count": len(self.click_history),
            "purchase_count": len(self.purchase_history),
            "browse_count": len(self.browse_history),
        }


class PersonalizationEngine:
    def __init__(self):
        self.user_profiles = {}

    def get_or_create_user(self, user_id):
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id)
        return self.user_profiles[user_id]

    def record_click(self, user_id, product, timestamp=None):
        user = self.get_or_create_user(user_id)
        user.update_from_click(product, timestamp)
        return user

    def record_purchase(self, user_id, product, timestamp=None):
        user = self.get_or_create_user(user_id)
        user.update_from_purchase(product, timestamp)
        return user

    def record_browse(self, user_id, product, timestamp=None):
        user = self.get_or_create_user(user_id)
        user.update_from_browse(product, timestamp)
        return user

    def compute_personalization_features(self, user_id, product):
        user = self.get_or_create_user(user_id)
        features = {}

        category = product.get("category", "")
        brand = product.get("brand", "")
        price = product.get("price", 0)

        features["user_category_match"] = user.category_preference.get(category, 0.0)
        features["user_brand_match"] = user.brand_preference.get(brand, 0.0)

        if user.price_range["mean"] is not None and user.price_range["mean"] > 0:
            features["user_price_similarity"] = 1.0 - abs(price - user.price_range["mean"]) / max(user.price_range["mean"], 1)
            features["user_price_similarity"] = max(0, features["user_price_similarity"])
        else:
            features["user_price_similarity"] = 0.5

        features["user_total_clicks"] = min(len(user.click_history) / 100.0, 1.0)
        features["user_total_purchases"] = min(len(user.purchase_history) / 50.0, 1.0)

        features["user_has_purchase_history"] = 1.0 if len(user.purchase_history) > 0 else 0.0
        features["user_activity_level"] = min(
            (len(user.click_history) + len(user.purchase_history) * 2 + len(user.browse_history) * 0.5) / 200.0,
            1.0
        )

        top_categories = user.get_top_categories(3)
        features["user_top_category_match"] = 1.0 if top_categories and category == top_categories[0][0] else 0.0

        top_brands = user.get_top_brands(3)
        features["user_top_brand_match"] = 1.0 if top_brands and brand == top_brands[0][0] else 0.0

        return features

    def rerank_with_personalization(self, user_id, products, base_scores, personalization_weight=0.3):
        if user_id not in self.user_profiles:
            return products, base_scores

        personalized_scores = []
        for i, product in enumerate(products):
            pers_feats = self.compute_personalization_features(user_id, product)
            pers_score = (
                pers_feats["user_category_match"] * 0.4 +
                pers_feats["user_brand_match"] * 0.3 +
                pers_feats["user_price_similarity"] * 0.3
            )
            combined_score = base_scores[i] * (1 - personalization_weight) + pers_score * personalization_weight
            personalized_scores.append(combined_score)

        sorted_indices = np.argsort(-np.array(personalized_scores))
        reranked_products = [products[i] for i in sorted_indices]
        reranked_scores = [personalized_scores[i] for i in sorted_indices]

        return reranked_products, reranked_scores

    def save_profiles(self, filepath):
        data = {uid: profile.to_dict() for uid, profile in self.user_profiles.items()}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_profiles(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for uid, profile_data in data.items():
            profile = UserProfile(uid)
            profile.category_preference = defaultdict(float, profile_data.get("category_preference", {}))
            profile.brand_preference = defaultdict(float, profile_data.get("brand_preference", {}))
            profile.price_range = profile_data.get("price_range", {"min": None, "max": None, "mean": None, "median": None})
            self.user_profiles[uid] = profile
