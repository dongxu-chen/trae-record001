import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import random
import hashlib
from datetime import datetime
import json
import os


class ABTester:
    def __init__(self, test_name: str = "thumbnail_ab_test"):
        self.test_name = test_name
        self.test_variants = {}
        self.impressions = {}
        self.clicks = {}
        self.conversions = {}
        self.results = []

    def add_variant(self, 
                    variant_id: str, 
                    variant_data: Dict,
                    is_control: bool = False) -> None:
        self.test_variants[variant_id] = {
            "data": variant_data,
            "is_control": is_control,
            "created_at": datetime.now().isoformat()
        }
        self.impressions[variant_id] = 0
        self.clicks[variant_id] = 0
        self.conversions[variant_id] = 0

    def record_impression(self, variant_id: str) -> None:
        if variant_id in self.impressions:
            self.impressions[variant_id] += 1

    def record_click(self, variant_id: str) -> None:
        if variant_id in self.clicks:
            self.clicks[variant_id] += 1

    def record_conversion(self, variant_id: str) -> None:
        if variant_id in self.conversions:
            self.conversions[variant_id] += 1

    def get_ctr(self, variant_id: str) -> float:
        impressions = self.impressions.get(variant_id, 0)
        clicks = self.clicks.get(variant_id, 0)
        return clicks / impressions if impressions > 0 else 0.0

    def get_conversion_rate(self, variant_id: str) -> float:
        clicks = self.clicks.get(variant_id, 0)
        conversions = self.conversions.get(variant_id, 0)
        return conversions / clicks if clicks > 0 else 0.0

    def get_stats(self) -> Dict:
        stats = {}
        for variant_id in self.test_variants:
            impressions = self.impressions.get(variant_id, 0)
            clicks = self.clicks.get(variant_id, 0)
            conversions = self.conversions.get(variant_id, 0)
            
            stats[variant_id] = {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "ctr": self.get_ctr(variant_id),
                "conversion_rate": self.get_conversion_rate(variant_id),
                "is_control": self.test_variants[variant_id]["is_control"]
            }
        return stats

    def calculate_statistical_significance(self, 
                                           control_id: str, 
                                           variant_id: str,
                                           metric: str = "ctr") -> Dict:
        control_impressions = self.impressions.get(control_id, 0)
        variant_impressions = self.impressions.get(variant_id, 0)
        
        if metric == "ctr":
            control_success = self.clicks.get(control_id, 0)
            variant_success = self.clicks.get(variant_id, 0)
        else:
            control_success = self.conversions.get(control_id, 0)
            variant_success = self.conversions.get(variant_id, 0)
        
        if control_impressions == 0 or variant_impressions == 0:
            return {"significant": False, "p_value": 1.0, "uplift": 0.0}
        
        control_rate = control_success / control_impressions
        variant_rate = variant_success / variant_impressions
        
        pooled_prob = (control_success + variant_success) / (control_impressions + variant_impressions)
        pooled_se = np.sqrt(pooled_prob * (1 - pooled_prob) * (1/control_impressions + 1/variant_impressions))
        
        if pooled_se == 0:
            z_score = 0
        else:
            z_score = (variant_rate - control_rate) / pooled_se
        
        p_value = 2 * (1 - self._norm_cdf(abs(z_score)))
        
        uplift = ((variant_rate - control_rate) / control_rate * 100) if control_rate > 0 else 0
        
        return {
            "significant": p_value < 0.05,
            "p_value": p_value,
            "z_score": z_score,
            "uplift_percent": uplift,
            "control_rate": control_rate,
            "variant_rate": variant_rate
        }

    def _norm_cdf(self, x: float) -> float:
        return (1.0 + np.math.erf(x / np.sqrt(2.0))) / 2.0

    def get_winner(self, metric: str = "ctr") -> Tuple[Optional[str], Dict]:
        stats = self.get_stats()
        if not stats:
            return None, {}
        
        control_id = None
        for vid, data in stats.items():
            if data["is_control"]:
                control_id = vid
                break
        
        if not control_id:
            control_id = list(stats.keys())[0]
        
        best_variant = control_id
        best_rate = stats[control_id][metric]
        
        for variant_id, data in stats.items():
            if data[metric] > best_rate:
                best_variant = variant_id
                best_rate = data[metric]
        
        significance = self.calculate_statistical_significance(control_id, best_variant, metric)
        
        return best_variant, {
            "stats": stats[best_variant],
            "significance": significance
        }

    def generate_results_dataframe(self) -> pd.DataFrame:
        stats = self.get_stats()
        rows = []
        
        for variant_id, data in stats.items():
            rows.append({
                "variant_id": variant_id,
                "is_control": data["is_control"],
                "impressions": data["impressions"],
                "clicks": data["clicks"],
                "conversions": data["conversions"],
                "ctr": data["ctr"],
                "conversion_rate": data["conversion_rate"]
            })
        
        return pd.DataFrame(rows)

    def save_results(self, filepath: str) -> None:
        results = {
            "test_name": self.test_name,
            "variants": self.test_variants,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "timestamp": datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    def load_results(self, filepath: str) -> None:
        with open(filepath, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        self.test_name = results.get("test_name", self.test_name)
        self.test_variants = results.get("variants", {})
        self.impressions = results.get("impressions", {})
        self.clicks = results.get("clicks", {})
        self.conversions = results.get("conversions", {})

    def hash_user_id(self, user_id: str, salt: str = "") -> int:
        combined = f"{user_id}{salt}{self.test_name}"
        hash_obj = hashlib.md5(combined.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest(), 16)
        return hash_int

    def get_variant_for_user(self, user_id: str, salt: str = "") -> Optional[str]:
        if not self.test_variants:
            return None
        
        variant_ids = sorted(self.test_variants.keys())
        num_variants = len(variant_ids)
        
        hash_int = self.hash_user_id(user_id, salt)
        variant_index = hash_int % num_variants
        
        return variant_ids[variant_index]

    def get_weighted_variant_for_user(self, 
                                       user_id: str, 
                                       weights: Optional[Dict[str, float]] = None,
                                       salt: str = "") -> Optional[str]:
        if not self.test_variants:
            return None
        
        variant_ids = sorted(self.test_variants.keys())
        
        if weights is None:
            weights = {vid: 1.0 for vid in variant_ids}
        
        total_weight = sum(weights.get(vid, 1.0) for vid in variant_ids)
        
        hash_int = self.hash_user_id(user_id, salt)
        hash_normalized = (hash_int % 10000) / 10000.0
        
        cumulative = 0.0
        target = hash_normalized * total_weight
        
        for vid in variant_ids:
            cumulative += weights.get(vid, 1.0)
            if cumulative >= target:
                return vid
        
        return variant_ids[-1]

    def record_user_impression(self, user_id: str, salt: str = "") -> Optional[str]:
        variant_id = self.get_variant_for_user(user_id, salt)
        if variant_id:
            self.record_impression(variant_id)
        return variant_id

    def record_user_click(self, user_id: str, salt: str = "") -> Optional[str]:
        variant_id = self.get_variant_for_user(user_id, salt)
        if variant_id:
            self.record_click(variant_id)
        return variant_id

    def record_user_conversion(self, user_id: str, salt: str = "") -> Optional[str]:
        variant_id = self.get_variant_for_user(user_id, salt)
        if variant_id:
            self.record_conversion(variant_id)
        return variant_id

    def get_user_assignment(self, user_id: str, salt: str = "") -> Optional[Dict]:
        variant_id = self.get_variant_for_user(user_id, salt)
        if variant_id and variant_id in self.test_variants:
            return {
                "user_id": user_id,
                "variant_id": variant_id,
                "variant_data": self.test_variants[variant_id]["data"],
                "is_control": self.test_variants[variant_id]["is_control"],
                "hash_value": self.hash_user_id(user_id, salt)
            }
        return None


class ThumbnailABTester:
    def __init__(self):
        self.testers = {}

    def create_test(self, 
                    test_id: str, 
                    frames: List[Tuple[int, np.ndarray]],
                    titles: List[str],
                    styles: List[str] = ["modern", "bold", "clean"]) -> None:
        tester = ABTester(test_id)
        
        variant_index = 0
        for frame_idx, (frame_num, frame) in enumerate(frames):
            for title_idx, title in enumerate(titles):
                for style in styles:
                    variant_id = f"frame{frame_idx}_title{title_idx}_{style}"
                    tester.add_variant(
                        variant_id,
                        {
                            "frame_index": frame_idx,
                            "frame_number": frame_num,
                            "title": title,
                            "style": style
                        },
                        is_control=(variant_index == 0)
                    )
                    variant_index += 1
        
        self.testers[test_id] = tester

    def get_tester(self, test_id: str) -> Optional[ABTester]:
        return self.testers.get(test_id)

    def simulate_test(self, 
                      test_id: str, 
                      num_impressions: int = 1000,
                      use_user_hash: bool = False) -> Dict:
        tester = self.get_tester(test_id)
        if not tester:
            return {}
        
        variant_ids = list(tester.test_variants.keys())
        
        base_ctr = 0.05
        
        if use_user_hash:
            for i in range(num_impressions):
                user_id = f"user_{i}"
                variant_id = tester.record_user_impression(user_id)
                
                if variant_id:
                    variant_performance = hash(variant_id) % 100 / 100
                    effective_ctr = base_ctr * (0.5 + variant_performance)
                    
                    if random.random() < effective_ctr:
                        tester.record_user_click(user_id)
                        
                        if random.random() < 0.3:
                            tester.record_user_conversion(user_id)
        else:
            for i in range(num_impressions):
                variant_id = random.choice(variant_ids)
                tester.record_impression(variant_id)
                
                variant_performance = hash(variant_id) % 100 / 100
                effective_ctr = base_ctr * (0.5 + variant_performance)
                
                if random.random() < effective_ctr:
                    tester.record_click(variant_id)
                    
                    if random.random() < 0.3:
                        tester.record_conversion(variant_id)
        
        winner, winner_data = tester.get_winner("ctr")
        return {
            "test_id": test_id,
            "total_impressions": num_impressions,
            "use_user_hash": use_user_hash,
            "winner": winner,
            "winner_data": winner_data,
            "all_stats": tester.get_stats()
        }

    def simulate_test_with_user_hash(self,
                                     test_id: str,
                                     num_users: int = 1000,
                                     salt: str = "") -> Dict:
        tester = self.get_tester(test_id)
        if not tester:
            return {}
        
        user_assignments = {}
        for i in range(num_users):
            user_id = f"user_{i}"
            assignment = tester.get_user_assignment(user_id, salt)
            if assignment:
                user_assignments[user_id] = assignment
                tester.record_impression(assignment["variant_id"])
        
        variant_distribution = {}
        for assignment in user_assignments.values():
            vid = assignment["variant_id"]
            variant_distribution[vid] = variant_distribution.get(vid, 0) + 1
        
        base_ctr = 0.05
        for user_id, assignment in user_assignments.items():
            variant_id = assignment["variant_id"]
            variant_performance = hash(variant_id) % 100 / 100
            effective_ctr = base_ctr * (0.5 + variant_performance)
            
            if random.random() < effective_ctr:
                tester.record_click(variant_id)
                
                if random.random() < 0.3:
                    tester.record_conversion(variant_id)
        
        winner, winner_data = tester.get_winner("ctr")
        return {
            "test_id": test_id,
            "num_users": num_users,
            "variant_distribution": variant_distribution,
            "user_assignments": user_assignments,
            "winner": winner,
            "winner_data": winner_data,
            "all_stats": tester.get_stats()
        }

    def get_user_variant(self, test_id: str, user_id: str, salt: str = "") -> Optional[Dict]:
        tester = self.get_tester(test_id)
        if not tester:
            return None
        return tester.get_user_assignment(user_id, salt)

    def verify_user_consistency(self, test_id: str, num_checks: int = 100) -> Dict:
        tester = self.get_tester(test_id)
        if not tester:
            return {"consistent": False, "message": "Test not found"}
        
        consistent = True
        inconsistent_users = []
        
        for i in range(num_checks):
            user_id = f"user_{i}"
            first = tester.get_variant_for_user(user_id)
            second = tester.get_variant_for_user(user_id)
            
            if first != second:
                consistent = False
                inconsistent_users.append(user_id)
        
        return {
            "consistent": consistent,
            "num_checks": num_checks,
            "inconsistent_count": len(inconsistent_users),
            "inconsistent_users": inconsistent_users[:10]
        }

    def get_test_summary(self, test_id: str) -> Dict:
        tester = self.get_tester(test_id)
        if not tester:
            return {}
        
        winner_ctr, data_ctr = tester.get_winner("ctr")
        winner_conv, data_conv = tester.get_winner("conversion_rate")
        
        return {
            "test_id": test_id,
            "num_variants": len(tester.test_variants),
            "total_impressions": sum(tester.impressions.values()),
            "total_clicks": sum(tester.clicks.values()),
            "total_conversions": sum(tester.conversions.values()),
            "winner_ctr": winner_ctr,
            "winner_ctr_data": data_ctr,
            "winner_conversion": winner_conv,
            "winner_conversion_data": data_conv,
            "all_results": tester.generate_results_dataframe().to_dict('records')
        }
