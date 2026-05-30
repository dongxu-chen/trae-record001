from typing import List, Dict, Any, Optional
import logging

from kg.neo4j_client import Neo4jClient
from kg.schema import ENTITY_TYPES
from nlp.entity_extractor import EntityExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClarificationEngine:
    def __init__(self, neo4j_client: Neo4jClient, entity_extractor: EntityExtractor):
        self.neo4j_client = neo4j_client
        self.entity_extractor = entity_extractor

    def check_ambiguity(
        self,
        question: str,
        intent_result: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        ambiguities = []

        intent_confidence = intent_result.get("confidence", 1.0)
        if intent_confidence < 0.5:
            top_intents = intent_result.get("all_predictions", [])[:3]
            ambiguities.append({
                "type": "intent_ambiguity",
                "confidence": intent_confidence,
                "details": {
                    "message": "您的问题可以有多种理解",
                    "possible_intents": [
                        {"intent": p["intent"], "confidence": p["confidence"]}
                        for p in top_intents
                    ]
                }
            })

        entity_ambiguity = self._check_entity_ambiguity(entities)
        if entity_ambiguity:
            ambiguities.append(entity_ambiguity)

        referential_ambiguity = self._check_referential_ambiguity(question, entities)
        if referential_ambiguity:
            ambiguities.append(referential_ambiguity)

        scope_ambiguity = self._check_scope_ambiguity(question, intent_result, entities)
        if scope_ambiguity:
            ambiguities.append(scope_ambiguity)

        if not ambiguities:
            return None

        return {
            "has_ambiguity": True,
            "ambiguities": ambiguities,
            "clarification": self._generate_clarification(ambiguities)
        }

    def _check_entity_ambiguity(self, entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for entity in entities:
            if entity.get("fuzzy", False):
                confidence = entity.get("confidence", 0)
                if confidence < 0.8:
                    return {
                        "type": "entity_ambiguity",
                        "entity": entity.get("text", ""),
                        "matched": entity.get("canonical_name", ""),
                        "confidence": confidence,
                        "details": {
                            "message": f'您提到的"{entity.get("text", "")}"可能有多种匹配',
                            "matched_entity": entity.get("canonical_name", ""),
                            "match_confidence": confidence
                        }
                    }

        return None

    def _check_referential_ambiguity(
        self,
        question: str,
        entities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        pronouns = ["这个", "那个", "它", "其", "这种", "那种", "该"]
        has_pronoun = any(p in question for p in pronouns)

        if has_pronoun and len(entities) == 0:
            return {
                "type": "referential_ambiguity",
                "details": {
                    "message": "您的问题中包含代词指代，但未找到明确的指代对象",
                    "pronouns_found": [p for p in pronouns if p in question]
                }
            }

        if has_pronoun and len(entities) > 1:
            return {
                "type": "referential_ambiguity",
                "details": {
                    "message": "您的问题中包含代词，但存在多个可能的指代对象",
                    "possible_references": [e["canonical_name"] for e in entities],
                    "pronouns_found": [p for p in pronouns if p in question]
                }
            }

        return None

    def _check_scope_ambiguity(
        self,
        question: str,
        intent_result: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        intent = intent_result.get("predicted_intent", "")
        multi_intent_keywords = ["和", "与", "及", "以及", "还有", "同时", "并且"]

        has_multi = any(kw in question for kw in multi_intent_keywords)
        if has_multi and intent != "multi_hop":
            return {
                "type": "scope_ambiguity",
                "details": {
                    "message": "您的问题似乎涉及多个方面，需要确认查询范围",
                    "detected_intent": intent,
                    "multi_aspect": True
                }
            }

        if intent == "fuzzy_query" and entities:
            entity_name = entities[0].get("canonical_name", "")
            query = """
            MATCH (n {name: $name})-[r]-(m)
            RETURN DISTINCT labels(m) as neighbor_types, count(m) as count
            ORDER BY count DESC
            LIMIT 5
            """
            try:
                results = self.neo4j_client.execute_query(query, {"name": entity_name})
                if results and len(results) >= 3:
                    return {
                        "type": "scope_ambiguity",
                        "details": {
                            "message": f'"{entity_name}"关联的信息较多，可以缩小查询范围',
                            "available_types": [
                                {
                                    "type": r["neighbor_types"][0] if r["neighbor_types"] else "Unknown",
                                    "count": r["count"]
                                }
                                for r in results
                                if r["neighbor_types"]
                            ]
                        }
                    }
            except Exception:
                pass

        return None

    def _generate_clarification(self, ambiguities: List[Dict[str, Any]]) -> Dict[str, Any]:
        questions = []
        options = []

        for amb in ambiguities:
            amb_type = amb["type"]
            details = amb.get("details", {})

            if amb_type == "intent_ambiguity":
                possible = details.get("possible_intents", [])
                intent_labels = {
                    "disease_symptom": "查询症状",
                    "disease_drug": "查询用药",
                    "disease_department": "查询科室",
                    "disease_treatment": "查询治疗方法",
                    "disease_examination": "查询检查项目",
                    "drug_disease": "查询药物治疗的疾病",
                    "symptom_disease": "根据症状查疾病",
                    "department_disease": "查询科室治疗的疾病",
                    "doctor_disease": "查询医生擅长的疾病",
                    "multi_hop": "综合查询",
                    "fuzzy_query": "模糊搜索"
                }
                q = details.get("message", "您的问题有多种理解")
                questions.append(q)
                for p in possible[:4]:
                    intent_name = p["intent"]
                    options.append({
                        "label": intent_labels.get(intent_name, intent_name),
                        "intent": intent_name,
                        "confidence": p["confidence"]
                    })

            elif amb_type == "entity_ambiguity":
                entity_text = amb.get("entity", "")
                q = f'您说的"{entity_text}"是指"{amb.get("matched", "")}"吗？'
                questions.append(q)
                options.append({
                    "label": f'是的，指"{amb.get("matched", "")}"',
                    "entity": amb.get("matched", ""),
                    "confirm": True
                })
                options.append({
                    "label": "不是，我重新描述",
                    "confirm": False
                })

            elif amb_type == "referential_ambiguity":
                refs = details.get("possible_references", [])
                q = details.get("message", "请明确您指的是哪个")
                questions.append(q)
                for ref in refs[:4]:
                    options.append({
                        "label": f'指的是"{ref}"',
                        "entity": ref
                    })

            elif amb_type == "scope_ambiguity":
                avail = details.get("available_types", [])
                q = details.get("message", "请缩小查询范围")
                questions.append(q)
                type_labels = {
                    "Symptom": "相关症状",
                    "Drug": "相关药物",
                    "Department": "相关科室",
                    "Treatment": "治疗方法",
                    "Examination": "检查项目",
                    "Disease": "相关疾病",
                    "Doctor": "相关医生"
                }
                for a in avail[:4]:
                    t = a.get("type", "")
                    options.append({
                        "label": type_labels.get(t, t),
                        "filter_type": t
                    })
                options.append({
                    "label": "全部信息",
                    "filter_type": None
                })

        clarification_text = "；".join(questions) + " 请选择："

        return {
            "clarification_question": clarification_text,
            "options": options,
            "ambiguity_count": len(ambiguities)
        }
