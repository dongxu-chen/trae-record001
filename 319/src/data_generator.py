import random
import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np


class DataGenerator:
    def __init__(self):
        self.genders = ["M", "F", "U"]
        self.age_groups = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
        self.educations = ["high_school", "college", "bachelor", "master", "phd"]
        self.occupations = ["student", "engineer", "teacher", "doctor", "manager", "worker", "freelancer", "retired"]
        self.marital_statuses = ["single", "married", "divorced", "widowed"]
        self.cities = [
            "beijing", "shanghai", "guangzhou", "shenzhen", "hangzhou",
            "chengdu", "wuhan", "xian", "nanjing", "chongqing",
            "tianjin", "suzhou", "zhengzhou", "changsha", "qingdao",
        ]
        self.provinces = [
            "beijing", "shanghai", "guangdong", "zhejiang", "sichuan",
            "hubei", "shaanxi", "jiangsu", "chongqing", "shandong",
        ]
        self.city_tiers = ["tier1", "tier2", "tier3", "tier4"]
        self.interests = [
            "tech", "fashion", "sports", "travel", "food",
            "finance", "education", "health", "entertainment", "gaming",
            "reading", "music", "movies", "photography", "cooking",
        ]
        self.user_intents = ["browsing", "comparison", "purchase", "research", "entertainment"]
        self.purchase_intents = ["low", "medium", "high", "very_high"]
        self.brand_preferences = ["none", "casual", "loyal", "exclusive"]
        self.ad_categories = [
            "electronics", "clothing", "beauty", "automotive", "food_beverage",
            "travel", "education", "finance", "healthcare", "entertainment",
            "home_goods", "sports", "baby_products", "pet_supplies", "books",
        ]
        self.ad_placements = ["feed", "banner", "splash", "native", "rewarded", "interstitial"]
        self.ad_positions = ["top", "middle", "bottom", "sidebar", "fullscreen"]
        self.ad_creative_types = ["image", "video", "text", "carousel", "animated"]
        self.device_types = ["mobile", "desktop", "tablet", "smart_tv", "wearable"]
        self.os_types = ["ios", "android", "windows", "macos", "linux", "harmonyos"]
        self.os_versions = ["14.0", "15.0", "16.0", "11.0", "12.0", "13.0", "10.0"]
        self.time_slots = [
            "morning_peak", "morning", "noon", "afternoon", "evening_peak", "night", "late_night"
        ]
        self.network_types = ["4G", "5G", "WIFI", "3G", "ethernet"]
        self.carriers = ["china_mobile", "china_unicom", "china_telecom", "other"]
        self.app_categories = ["social", "ecommerce", "news", "entertainment", "tools", "games", "education"]
        self.content_categories = ["news", "entertainment", "sports", "finance", "tech", "lifestyle", "education"]
        self.weather_conditions = ["sunny", "cloudy", "rainy", "snowy", "foggy", "windy"]
        self.temperature_levels = ["cold", "cool", "mild", "warm", "hot"]
        self.holidays = ["yes", "no"]
        self.user_ids = [f"user_{i}" for i in range(1000)]
        self.ad_ids = [f"ad_{i}" for i in range(100)]

    def _get_time_slot(self) -> str:
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "noon"
        elif 14 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        elif 22 <= hour < 24:
            return "night"
        else:
            return "late_night"

    def generate_user_profile(self, user_id: str = None) -> Dict[str, Any]:
        if user_id is None:
            user_id = random.choice(self.user_ids)
        
        city = random.choice(self.cities)
        city_tier_mapping = {
            "beijing": "tier1", "shanghai": "tier1", "guangzhou": "tier1", "shenzhen": "tier1",
            "hangzhou": "tier2", "chengdu": "tier2", "wuhan": "tier2", "xian": "tier2", 
            "nanjing": "tier2", "chongqing": "tier2", "tianjin": "tier2", "suzhou": "tier2",
        }
        province_mapping = {
            "beijing": "beijing", "shanghai": "shanghai", "guangzhou": "guangdong", 
            "shenzhen": "guangdong", "hangzhou": "zhejiang", "chengdu": "sichuan",
            "wuhan": "hubei", "xian": "shaanxi", "nanjing": "jiangsu", "chongqing": "chongqing",
            "tianjin": "tianjin", "suzhou": "jiangsu", "zhengzhou": "henan", 
            "changsha": "hunan", "qingdao": "shandong",
        }
        
        profile = {
            "user_id": user_id,
            "user_gender": random.choice(self.genders),
            "user_age_group": random.choice(self.age_groups),
            "user_city": city,
            "province": province_mapping.get(city, random.choice(self.provinces)),
            "city_tier": city_tier_mapping.get(city, random.choice(self.city_tiers)),
            "user_interest": random.choice(self.interests),
            "user_education": random.choice(self.educations),
            "user_occupation": random.choice(self.occupations),
            "user_marital_status": random.choice(self.marital_statuses),
            "user_intent": random.choice(self.user_intents),
            "purchase_intent": random.choice(self.purchase_intents),
            "brand_preference": random.choice(self.brand_preferences),
            "user_income": round(random.uniform(3000, 50000), 2),
            "user_active_days": random.randint(1, 365),
            "user_click_count": random.randint(0, 100),
            "user_conversion_count": random.randint(0, 20),
            "user_avg_session_duration": round(random.uniform(1, 120), 2),
            "user_pages_per_session": random.randint(1, 50),
            "user_last_visit_days": random.randint(0, 30),
            "user_cart_count": random.randint(0, 20),
            "user_wishlist_count": random.randint(0, 50),
            "user_order_count": random.randint(0, 30),
            "user_total_spend": round(random.uniform(0, 50000), 2),
            "days_since_purchase": random.randint(0, 180),
            "price_sensitivity": round(random.uniform(0, 1), 4),
            "brand_loyalty_score": round(random.uniform(0, 1), 4),
            "context_relevance_score": round(random.uniform(0, 1), 4),
            "user_ad_match_score": round(random.uniform(0, 1), 4),
            "time_decay_factor": round(random.uniform(0.5, 1), 4),
        }
        return profile

    def generate_context(self) -> Dict[str, Any]:
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()
        
        return {
            "device_type": random.choice(self.device_types),
            "os_type": random.choice(self.os_types),
            "os_version": random.choice(self.os_versions),
            "time_slot": self._get_time_slot(),
            "hour_of_day": f"h{hour}",
            "day_of_week": f"d{weekday}",
            "is_weekend": "yes" if weekday >= 5 else "no",
            "is_holiday": random.choice(self.holidays),
            "ip": f"192.168.{random.randint(0, 255)}.{random.randint(1, 255)}",
            "app_version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "network_type": random.choice(self.network_types),
            "carrier": random.choice(self.carriers),
            "app_category": random.choice(self.app_categories),
            "content_category": random.choice(self.content_categories),
            "weather": random.choice(self.weather_conditions),
            "temperature_level": random.choice(self.temperature_levels),
            "timestamp": int(now.timestamp() * 1000),
            "hour": hour,
            "minute": now.minute,
            "day_of_month": now.day,
            "week_of_year": now.isocalendar()[1],
        }

    def generate_ad_info(self, ad_id: str = None) -> Dict[str, Any]:
        if ad_id is None:
            ad_id = random.choice(self.ad_ids)
        
        ad_position = random.choice(self.ad_positions)
        position_score_mapping = {
            "top": 1.0, "fullscreen": 0.95, "middle": 0.7, 
            "sidebar": 0.5, "bottom": 0.4,
        }
        
        return {
            "ad_id": ad_id,
            "ad_category": random.choice(self.ad_categories),
            "ad_placement": random.choice(self.ad_placements),
            "ad_position": ad_position,
            "ad_position_score": position_score_mapping.get(ad_position, 0.5),
            "ad_ctr_history": round(random.uniform(0.001, 0.1), 4),
            "ad_cvr_history": round(random.uniform(0.001, 0.05), 4),
            "ad_creative_type": random.choice(self.ad_creative_types),
            "ad_impression_count": random.randint(100, 10000),
            "ad_click_count": random.randint(0, 500),
            "ad_conversion_count": random.randint(0, 50),
        }

    def generate_bid_request(
        self,
        user_id: str = None,
        ad_id: str = None,
        campaign_id: str = "default",
        floor_price: float = None,
        cpa_goal: float = None,
    ) -> Dict[str, Any]:
        if floor_price is None:
            floor_price = round(random.uniform(0.01, 0.5), 2)
        if cpa_goal is None:
            cpa_goal = round(random.uniform(5.0, 50.0), 2)
        request_id = str(uuid.uuid4())
        user_profile = self.generate_user_profile(user_id)
        context = self.generate_context()
        ad_info = self.generate_ad_info(ad_id)
        return {
            "request_id": request_id,
            "user_id": user_profile["user_id"],
            "ad_id": ad_info["ad_id"],
            "campaign_id": campaign_id,
            "user_profile": user_profile,
            "context": context,
            "ad_info": ad_info,
            "floor_price": floor_price,
            "cpa_goal": cpa_goal,
            "timestamp": int(time.time() * 1000),
        }

    def generate_bid_request_batch(self, count: int, campaign_id: str = "default") -> List[Dict[str, Any]]:
        return [self.generate_bid_request(campaign_id=campaign_id) for _ in range(count)]

    def generate_impression(self, bid_id: str, request_id: str) -> Dict[str, Any]:
        return {
            "bid_id": bid_id,
            "request_id": request_id,
            "event_type": "impression",
            "timestamp": int(time.time() * 1000),
        }

    def generate_click(self, bid_id: str, request_id: str) -> Dict[str, Any]:
        return {
            "bid_id": bid_id,
            "request_id": request_id,
            "event_type": "click",
            "click_position": random.choice(["top", "middle", "bottom"]),
            "time_on_page": random.randint(1, 300),
            "timestamp": int(time.time() * 1000),
        }

    def generate_conversion(self, bid_id: str, request_id: str) -> Dict[str, Any]:
        return {
            "bid_id": bid_id,
            "request_id": request_id,
            "event_type": "conversion",
            "conversion_type": random.choice(["signup", "purchase", "download", "lead"]),
            "conversion_value": round(random.uniform(1.0, 100.0), 2),
            "timestamp": int(time.time() * 1000),
        }

    def generate_training_data(
        self,
        sample_count: int = 10000,
        feature_dim: int = 50,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        X = np.random.randn(sample_count, feature_dim).astype(np.float32)
        ctr_y = np.zeros(sample_count, dtype=np.int32)
        cvr_y = np.zeros(sample_count, dtype=np.int32)
        for i in range(sample_count):
            base_score = np.sum(X[i, :10]) * 0.1 + np.random.normal(0, 0.5)
            ctr_prob = 1 / (1 + np.exp(-base_score))
            ctr_y[i] = 1 if random.random() < ctr_prob else 0
            if ctr_y[i] == 1:
                cvr_prob = 1 / (1 + np.exp(-(base_score + np.random.normal(0, 0.3))))
                cvr_y[i] = 1 if random.random() < cvr_prob * 0.3 else 0
        return X, ctr_y, cvr_y

    def generate_simulation_stream(
        self,
        requests_per_second: int = 10,
        duration_seconds: int = 60,
        click_rate: float = 0.05,
        conversion_rate: float = 0.1,
    ):
        total_requests = requests_per_second * duration_seconds
        for i in range(total_requests):
            bid_request = self.generate_bid_request()
            yield ("bid_request", bid_request)
            if random.random() < click_rate:
                bid_id = str(uuid.uuid4())
                yield ("click", self.generate_click(bid_id, bid_request["request_id"]))
                if random.random() < conversion_rate:
                    yield ("conversion", self.generate_conversion(bid_id, bid_request["request_id"]))
            time.sleep(1.0 / requests_per_second)

    def save_user_profiles_to_redis(self, count: int = 100):
        from src.redis_client import RedisClient
        redis_client = RedisClient()
        profiles = {}
        for _ in range(count):
            profile = self.generate_user_profile()
            user_id = profile["user_id"]
            profiles[user_id] = profile
            redis_client.set_user_profile(user_id, profile)
        print(f"Saved {len(profiles)} user profiles to Redis")
        return profiles

    def create_mock_models(self, ctr_save_path: str = "models/ctr_xgboost.model", cvr_save_path: str = "models/cvr_xgboost.model"):
        from src.prediction_model import PredictionModel
        import os
        os.makedirs(os.path.dirname(ctr_save_path), exist_ok=True)
        os.makedirs(os.path.dirname(cvr_save_path), exist_ok=True)
        print("Generating training data...")
        X, ctr_y, cvr_y = self.generate_training_data(sample_count=5000)
        print(f"Training data shape: X={X.shape}, CTR_y={ctr_y.shape}, CVR_y={cvr_y.shape}")
        print(f"CTR positive rate: {ctr_y.mean():.4f}")
        print(f"CVR positive rate (among clicks): {cvr_y[ctr_y == 1].mean() if ctr_y.sum() > 0 else 0:.4f}")
        predictor = PredictionModel()
        print("\nTraining CTR model...")
        predictor.train_ctr_model(X, ctr_y, ctr_save_path)
        print("CTR model trained and saved")
        print("\nTraining CVR model...")
        cvr_mask = ctr_y == 1
        predictor.train_cvr_model(X[cvr_mask], cvr_y[cvr_mask], cvr_save_path)
        print("CVR model trained and saved")
        return predictor
