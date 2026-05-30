from typing import List, Set, Dict, Tuple
from collections import defaultdict


class TasteConflictDetector:
    def __init__(self):
        self.conflict_rules = self._build_conflict_rules()
    
    def _build_conflict_rules(self) -> Dict[Tuple[str, str], Dict]:
        rules = {}
        
        severe_conflicts = [
            ("辣", "清淡"),
            ("麻辣", "清淡"),
            ("甜", "辣"),
            ("甜", "麻辣"),
            ("酸", "甜"),
        ]
        
        for taste1, taste2 in severe_conflicts:
            rules[(taste1, taste2)] = {
                "severity": "severe",
                "description": f"{taste1}与{''.join(taste2)}口味强烈冲突，不建议同桌点"
            }
            rules[(taste2, taste1)] = {
                "severity": "severe",
                "description": f"{taste2}与{taste1}口味强烈冲突，不建议同桌点"
            }
        
        medium_conflicts = [
            ("酸辣", "甜"),
            ("重口味", "清淡"),
            ("蒜香", "清淡"),
            ("咸鲜", "甜"),
        ]
        
        for taste1, taste2 in medium_conflicts:
            rules[(taste1, taste2)] = {
                "severity": "medium",
                "description": f"{taste1}与{taste2}口味有一定冲突，建议谨慎搭配"
            }
            rules[(taste2, taste1)] = {
                "severity": "medium",
                "description": f"{taste2}与{taste1}口味有一定冲突，建议谨慎搭配"
            }
        
        mild_conflicts = [
            ("香", "清淡"),
            ("酥脆", "清淡"),
            ("茶香", "麻辣"),
        ]
        
        for taste1, taste2 in mild_conflicts:
            rules[(taste1, taste2)] = {
                "severity": "mild",
                "description": f"{taste1}与{taste2}口味略有差异，可搭配"
            }
            rules[(taste2, taste1)] = {
                "severity": "mild",
                "description": f"{taste2}与{taste1}口味略有差异，可搭配"
            }
        
        return rules
    
    def detect_conflicts(self, dish_tastes: Dict[str, List[str]]) -> List[Dict]:
        conflicts = []
        dish_ids = list(dish_tastes.keys())
        
        for i, dish1_id in enumerate(dish_ids):
            for dish2_id in dish_ids[i+1:]:
                tastes1 = set(dish_tastes[dish1_id])
                tastes2 = set(dish_tastes[dish2_id])
                
                for t1 in tastes1:
                    for t2 in tastes2:
                        conflict_key = (t1, t2)
                        if conflict_key in self.conflict_rules:
                            rule = self.conflict_rules[conflict_key]
                            conflicts.append({
                                "dish1_id": dish1_id,
                                "dish2_id": dish2_id,
                                "taste1": t1,
                                "taste2": t2,
                                "severity": rule["severity"],
                                "description": rule["description"]
                            })
        
        return conflicts
    
    def has_severe_conflict(self, dish_tastes: Dict[str, List[str]]) -> bool:
        conflicts = self.detect_conflicts(dish_tastes)
        return any(c["severity"] == "severe" for c in conflicts)
    
    def filter_conflict_dishes(
        self,
        candidate_dishes: List[Tuple[str, float]],
        current_dishes: List[str],
        dish_taste_map: Dict[str, List[str]],
        max_severity: str = "medium"
    ) -> List[Tuple[str, float]]:
        severity_order = {"mild": 1, "medium": 2, "severe": 3}
        max_level = severity_order.get(max_severity, 2)
        
        current_tastes = {}
        for dish_id in current_dishes:
            if dish_id in dish_taste_map:
                current_tastes[dish_id] = dish_taste_map[dish_id]
        
        filtered = []
        for dish_id, score in candidate_dishes:
            if dish_id not in dish_taste_map:
                filtered.append((dish_id, score))
                continue
            
            test_tastes = dict(current_tastes)
            test_tastes[dish_id] = dish_taste_map[dish_id]
            
            conflicts = self.detect_conflicts(test_tastes)
            has_conflict = any(
                severity_order.get(c["severity"], 1) > max_level
                for c in conflicts
            )
            
            if not has_conflict:
                filtered.append((dish_id, score))
            else:
                adjusted_score = score * 0.5
                filtered.append((dish_id, adjusted_score))
        
        filtered.sort(key=lambda x: x[1], reverse=True)
        return filtered
    
    def get_conflict_summary(self, conflicts: List[Dict]) -> Dict[str, List]:
        summary = {
            "severe": [],
            "medium": [],
            "mild": []
        }
        
        for conflict in conflicts:
            severity = conflict["severity"]
            summary[severity].append({
                "dishes": (conflict["dish1_id"], conflict["dish2_id"]),
                "tastes": (conflict["taste1"], conflict["taste2"]),
                "description": conflict["description"]
            })
        
        return summary
    
    def suggest_alternatives(
        self,
        conflicting_dish_id: str,
        available_dishes: List[str],
        dish_taste_map: Dict[str, List[str]],
        current_dishes: List[str],
        top_n: int = 3
    ) -> List[str]:
        conflict_tastes = set(dish_taste_map.get(conflicting_dish_id, []))
        
        alternatives = []
        for dish_id in available_dishes:
            if dish_id == conflicting_dish_id or dish_id in current_dishes:
                continue
            
            dish_tastes = set(dish_taste_map.get(dish_id, []))
            
            has_conflict = False
            for current_id in current_dishes:
                current_tastes = set(dish_taste_map.get(current_id, []))
                for t1 in dish_tastes:
                    for t2 in current_tastes:
                        if (t1, t2) in self.conflict_rules:
                            rule = self.conflict_rules[(t1, t2)]
                            if rule["severity"] == "severe":
                                has_conflict = True
                                break
                    if has_conflict:
                        break
                if has_conflict:
                    break
            
            if not has_conflict:
                alternatives.append(dish_id)
                
                if len(alternatives) >= top_n:
                    break
        
        return alternatives
