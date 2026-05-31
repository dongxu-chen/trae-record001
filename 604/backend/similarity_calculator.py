from typing import List, Dict, Any
import numpy as np
from collections import Counter


class SimilarityCalculator:
    def __init__(self):
        pass
    
    def rank_cases(
        self,
        query_text: str,
        query_analysis: Dict[str, Any],
        candidate_cases: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        ranked_cases = []
        
        for case in candidate_cases:
            total_score = self._calculate_comprehensive_score(
                query_text,
                query_analysis,
                case
            )
            case["similarity_score"] = total_score
            ranked_cases.append(case)
        
        ranked_cases.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        return ranked_cases
    
    def _calculate_comprehensive_score(
        self,
        query_text: str,
        query_analysis: Dict[str, Any],
        case: Dict[str, Any]
    ) -> float:
        weights = {
            "semantic": 0.4,
            "case_type": 0.15,
            "key_points": 0.25,
            "entities": 0.2
        }
        
        semantic_score = case.get("similarity_score", 0.5)
        case_type_score = self._calculate_case_type_similarity(query_analysis, case)
        key_points_score = self._calculate_key_points_similarity(query_analysis, case)
        entities_score = self._calculate_entities_similarity(query_analysis, case)
        
        total_score = (
            weights["semantic"] * semantic_score +
            weights["case_type"] * case_type_score +
            weights["key_points"] * key_points_score +
            weights["entities"] * entities_score
        )
        
        return total_score
    
    def _calculate_case_type_similarity(
        self,
        query_analysis: Dict[str, Any],
        case: Dict[str, Any]
    ) -> float:
        query_type = query_analysis.get("case_type", "")
        case_type = case.get("case_type", "")
        
        if query_type == case_type:
            return 1.0
        
        type_hierarchy = {
            "民间借贷纠纷": ["合同纠纷"],
            "买卖合同纠纷": ["合同纠纷"],
            "租赁合同纠纷": ["合同纠纷"]
        }
        
        query_parent = type_hierarchy.get(query_type, [])
        case_parent = type_hierarchy.get(case_type, [])
        
        if query_type in case_parent or case_type in query_parent:
            return 0.6
        
        if set(query_parent) & set(case_parent):
            return 0.3
        
        return 0.0
    
    def _calculate_key_points_similarity(
        self,
        query_analysis: Dict[str, Any],
        case: Dict[str, Any]
    ) -> float:
        query_points = set(query_analysis.get("key_points", []))
        case_points = set(case.get("key_points", []))
        
        if not query_points or not case_points:
            return 0.3
        
        intersection = query_points & case_points
        union = query_points | case_points
        
        jaccard = len(intersection) / len(union) if union else 0
        
        return jaccard
    
    def _calculate_entities_similarity(
        self,
        query_analysis: Dict[str, Any],
        case: Dict[str, Any]
    ) -> float:
        query_entities = query_analysis.get("legal_entities", {})
        case_entities = case.get("legal_entities", {})
        
        if not query_entities or not case_entities:
            return 0.2
        
        entity_types = ["金额", "证据", "法条"]
        type_scores = []
        
        for entity_type in entity_types:
            query_set = set(query_entities.get(entity_type, []))
            case_set = set(case_entities.get(entity_type, []))
            
            if query_set or case_set:
                intersection = query_set & case_set
                union = query_set | case_set
                type_scores.append(len(intersection) / len(union) if union else 0)
        
        if type_scores:
            return sum(type_scores) / len(type_scores)
        
        return 0.2
    
    def analyze_differences(
        self,
        query_analysis: Dict[str, Any],
        case: Dict[str, Any]
    ) -> Dict[str, Any]:
        differences = {
            "case_type": {
                "query": query_analysis.get("case_type", ""),
                "case": case.get("case_type", ""),
                "same": query_analysis.get("case_type") == case.get("case_type")
            },
            "key_points": {
                "common": [],
                "query_only": [],
                "case_only": []
            },
            "entities": {},
            "similarity_level": ""
        }
        
        query_points = set(query_analysis.get("key_points", []))
        case_points = set(case.get("key_points", []))
        
        differences["key_points"]["common"] = list(query_points & case_points)
        differences["key_points"]["query_only"] = list(query_points - case_points)
        differences["key_points"]["case_only"] = list(case_points - query_points)
        
        query_entities = query_analysis.get("legal_entities", {})
        case_entities = case.get("legal_entities", {})
        
        for entity_type in ["原告", "被告", "金额", "证据", "法条"]:
            query_set = set(query_entities.get(entity_type, []))
            case_set = set(case_entities.get(entity_type, []))
            differences["entities"][entity_type] = {
                "query": list(query_set),
                "case": list(case_set),
                "overlap": list(query_set & case_set)
            }
        
        score = case.get("similarity_score", 0)
        if score >= 0.8:
            differences["similarity_level"] = "高度相似"
        elif score >= 0.6:
            differences["similarity_level"] = "较为相似"
        elif score >= 0.4:
            differences["similarity_level"] = "部分相似"
        else:
            differences["similarity_level"] = "差异较大"
        
        return differences
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.replace("，", " ").replace("。", " ").split())
        words2 = set(text2.replace("，", " ").replace("。", " ").split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def get_difference_summary(
        self,
        differences: Dict[str, Any]
    ) -> List[str]:
        summary = []
        
        if not differences["case_type"]["same"]:
            summary.append(f"案件类型不同：本案为{differences['case_type']['query']}，案例为{differences['case_type']['case']}")
        
        query_only = differences["key_points"]["query_only"]
        if query_only:
            summary.append(f"本案独有情节：{', '.join(query_only[:3])}")
        
        case_only = differences["key_points"]["case_only"]
        if case_only:
            summary.append(f"案例独有情节：{', '.join(case_only[:3])}")
        
        evidence_diff = differences["entities"]["证据"]
        if evidence_diff["query"] and not evidence_diff["overlap"]:
            summary.append("证据类型存在差异")
        
        return summary
