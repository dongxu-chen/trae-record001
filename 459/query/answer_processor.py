from typing import List, Dict, Any
from kg.schema import RELATION_TYPES


class AnswerProcessor:
    def __init__(self):
        self.relation_labels = RELATION_TYPES

    def format_answer(
        self,
        question: str,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any],
        entities: List[Dict[str, Any]],
        intent: str
    ) -> Dict[str, Any]:
        if not query_result:
            return {
                "question": question,
                "answer": "抱歉，我没有找到相关的答案。",
                "has_answer": False,
                "source": None
            }

        query_type = query_info.get("query_type", "single_hop")

        if query_type == "single_hop":
            return self._format_single_hop(question, query_result, query_info, entities, intent)
        elif query_type == "multi_hop":
            return self._format_multi_hop(question, query_result, query_info, entities)
        elif query_type == "path_between":
            return self._format_path_between(question, query_result, query_info)
        elif query_type == "fuzzy_match":
            return self._format_fuzzy_match(question, query_result, query_info)
        elif query_type == "entity_details":
            return self._format_entity_details(question, query_result, query_info)
        else:
            return self._format_generic(question, query_result, query_info)

    def _format_single_hop(
        self,
        question: str,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any],
        entities: List[Dict[str, Any]],
        intent: str
    ) -> Dict[str, Any]:
        results = [r.get("result") for r in query_result if r.get("result")]
        entity_name = entities[0]["canonical_name"] if entities else query_info.get("entity", "")

        answer_parts = []
        if intent == "disease_symptom":
            answer_parts.append(f"{entity_name}的常见症状包括：")
            answer_parts.append("、".join(results))
        elif intent == "disease_drug":
            answer_parts.append(f"治疗{entity_name}常用的药物有：")
            answer_parts.append("、".join(results))
        elif intent == "disease_department":
            answer_parts.append(f"{entity_name}应该挂：")
            answer_parts.append("、".join(results))
        elif intent == "disease_treatment":
            answer_parts.append(f"{entity_name}的治疗方法包括：")
            answer_parts.append("、".join(results))
        elif intent == "disease_examination":
            answer_parts.append(f"{entity_name}需要做的检查有：")
            answer_parts.append("、".join(results))
        elif intent == "drug_disease":
            answer_parts.append(f"{entity_name}可以治疗：")
            answer_parts.append("、".join(results))
        elif intent == "symptom_disease":
            answer_parts.append(f"有{entity_name}症状的疾病可能有：")
            answer_parts.append("、".join(results))
        elif intent == "department_disease":
            answer_parts.append(f"{entity_name}可以治疗：")
            answer_parts.append("、".join(results))
        elif intent == "doctor_disease":
            answer_parts.append(f"{entity_name}擅长治疗：")
            answer_parts.append("、".join(results))
        else:
            answer_parts.append(f"关于{entity_name}的查询结果：")
            answer_parts.append("、".join(results))

        answer = "".join(answer_parts)

        source = self._build_evidence_single_hop(query_result, query_info, entity_name)

        return {
            "question": question,
            "answer": answer,
            "has_answer": True,
            "results": results,
            "source": source
        }

    def _format_multi_hop(
        self,
        question: str,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        formatted_paths = []
        for result in query_result:
            path_nodes = result.get("path_nodes", [])
            path_relations = result.get("path_relations", [])

            readable_path = self._path_to_readable(path_nodes, path_relations)
            formatted_paths.append({
                "final_result": result.get("final_result"),
                "path": readable_path,
                "path_nodes": path_nodes,
                "path_relations": path_relations
            })

        start_entity = query_info.get("start_entity", "")
        relations = query_info.get("relations", [])

        answer = f"从{start_entity}经过{len(relations)}跳查询后，找到的结果有：\n"
        for i, path_info in enumerate(formatted_paths, 1):
            answer += f"{i}. {path_info['final_result']}\n"
            answer += f"   推理路径：{path_info['path']}\n"

        return {
            "question": question,
            "answer": answer,
            "has_answer": True,
            "results": formatted_paths,
            "source": {
                "type": "multi_hop",
                "start_entity": start_entity,
                "relations": relations,
                "paths": formatted_paths
            }
        }

    def _format_path_between(
        self,
        question: str,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        paths = []
        for result in query_result:
            path_nodes = result.get("path_nodes", [])
            path_relations = result.get("path_relations", [])
            hop_count = result.get("hop_count", 0)

            readable_path = self._path_to_readable(path_nodes, path_relations)
            paths.append({
                "path": readable_path,
                "path_nodes": path_nodes,
                "path_relations": path_relations,
                "hop_count": hop_count
            })

        entity1 = query_info.get("parameters", {}).get("entity1", "")
        entity2 = query_info.get("parameters", {}).get("entity2", "")

        answer = f"{entity1}和{entity2}之间的关联路径：\n"
        for i, path_info in enumerate(paths, 1):
            answer += f"{i}. {path_info['path']}（共{path_info['hop_count']}跳）\n"

        return {
            "question": question,
            "answer": answer,
            "has_answer": True,
            "results": paths,
            "source": {
                "type": "path_between",
                "entity1": entity1,
                "entity2": entity2,
                "paths": paths
            }
        }

    def _format_fuzzy_match(
        self,
        question: str,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        matches = []
        for result in query_result:
            matches.append({
                "name": result.get("result"),
                "types": result.get("entity_types", [])
            })

        search_term = query_info.get("parameters", {}).get("search_term", "")

        answer = f"与'{search_term}'相关的实体有：\n"
        for i, match in enumerate(matches, 1):
            types_str = "、".join(match["types"])
            answer += f"{i}. {match['name']}（{types_str}）\n"

        return {
            "question": question,
            "answer": answer,
            "has_answer": True,
            "results": matches,
            "source": {
                "type": "fuzzy_match",
                "search_term": search_term,
                "matches": matches
            }
        }

    def _format_entity_details(
        self,
        question: str,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not query_result:
            return {"question": question, "answer": "未找到相关信息", "has_answer": False}

        result = query_result[0]
        node = result.get("n", {})
        outgoing = result.get("outgoing_relations", [])
        incoming = result.get("incoming_relations", [])

        entity_name = node.get("name", "")

        answer = f"【{entity_name}】的详细信息：\n"

        if node.get("description"):
            answer += f"描述：{node['description']}\n"

        if outgoing:
            answer += "\n关联关系：\n"
            for rel in outgoing:
                rel_label = self.relation_labels.get(rel["relation"], rel["relation"])
                answer += f"- {rel_label} -> {rel['target']}\n"

        if incoming:
            answer += "\n被关联：\n"
            for rel in incoming:
                rel_label = self.relation_labels.get(rel["relation"], rel["relation"])
                answer += f"- {rel['source']} {rel_label}\n"

        return {
            "question": question,
            "answer": answer,
            "has_answer": True,
            "node_info": node,
            "source": {
                "type": "entity_details",
                "entity": entity_name,
                "properties": node,
                "outgoing_relations": outgoing,
                "incoming_relations": incoming
            }
        }

    def _format_generic(
        self,
        question: str,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        results = []
        for r in query_result:
            if isinstance(r, dict):
                results.extend([v for v in r.values() if isinstance(v, str)])

        answer = "查询结果：" + "、".join(results[:10])

        return {
            "question": question,
            "answer": answer,
            "has_answer": True,
            "results": results,
            "source": query_info
        }

    def _path_to_readable(self, nodes: List[str], relations: List[str]) -> str:
        if len(nodes) < 2:
            return " -> ".join(nodes)

        path_parts = [nodes[0]]
        for i, rel in enumerate(relations):
            rel_label = self.relation_labels.get(rel, rel)
            path_parts.append(f"--[{rel_label}]-->")
            if i + 1 < len(nodes):
                path_parts.append(nodes[i + 1])

        return " ".join(path_parts)

    def _build_evidence_single_hop(
        self,
        query_result: List[Dict[str, Any]],
        query_info: Dict[str, Any],
        entity_name: str
    ) -> Dict[str, Any]:
        relation = query_info.get("relation", "")
        relation_label = self.relation_labels.get(relation, relation)
        target_type = query_info.get("target_type", "")

        evidence = {
            "type": "single_hop",
            "query_entity": entity_name,
            "query_relation": relation,
            "query_relation_label": relation_label,
            "target_type": target_type,
            "cypher": query_info.get("cypher", ""),
            "parameters": query_info.get("parameters", {}),
            "evidence_tuples": []
        }

        for result in query_result:
            evidence["evidence_tuples"].append({
                "source": entity_name,
                "relation": relation,
                "relation_label": relation_label,
                "target": result.get("result", "")
            })

        return evidence
