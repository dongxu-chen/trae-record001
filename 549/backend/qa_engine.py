import sys
import os
import re
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from neo4j_db import Neo4jDatabase
from intent_recognition import IntentRecognizer

class QAEngine:
    def __init__(self, db: Neo4jDatabase, intent_recognizer: IntentRecognizer):
        self.db = db
        self.intent_recognizer = intent_recognizer

    def answer(self, question: str) -> Dict[str, Any]:
        analysis = self.intent_recognizer.analyze_question(question)
        
        intent = analysis["intent"]
        entities = analysis["entities"]
        intent_confidence = analysis["intent_confidence"]
        
        answer, evidence = self._generate_answer(intent, entities, question)
        
        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "answer": answer,
            "evidence": evidence,
            "entities": entities
        }

    def _highlight_text(self, text: str, keywords: List[str]) -> str:
        highlighted = text
        for keyword in sorted(keywords, key=len, reverse=True):
            if keyword in highlighted:
                highlighted = highlighted.replace(
                    keyword,
                    f"<<{keyword}>>"
                )
        return highlighted

    def _find_paragraph_location(self, disease_name: str, keywords: List[str]) -> List[Dict]:
        locations = []
        try:
            paragraphs = self.db.get_paragraphs_for_disease(disease_name)
            for idx, para in enumerate(paragraphs):
                para_text = para if isinstance(para, str) else para.get("text", "")
                section = para.get("section", "") if isinstance(para, dict) else ""
                for keyword in keywords:
                    if keyword in para_text:
                        highlighted = self._highlight_text(para_text, keywords)
                        locations.append({
                            "paragraph_index": idx,
                            "section": section,
                            "original_text": para_text,
                            "highlighted_text": highlighted,
                            "keyword": keyword
                        })
                        break
        except Exception:
            pass
        return locations

    def _generate_answer(self, intent: str, entities: List[Dict], question: str) -> tuple:
        disease_entities = [e.get("canonical", e["text"]) for e in entities if e["type"] == "disease"]
        symptom_entities = [e.get("canonical", e["text"]) for e in entities if e["type"] == "symptom"]
        medicine_entities = [e.get("canonical", e["text"]) for e in entities if e["type"] == "medicine"]
        
        disease_raw = [e["text"] for e in entities if e["type"] == "disease"]
        
        evidence = []
        
        if intent == "symptom_query" and disease_entities:
            answer, evidence = self._answer_symptom_query(disease_entities[0], disease_raw[0] if disease_raw else disease_entities[0])
        elif intent == "disease_query" and symptom_entities:
            answer, evidence = self._answer_disease_by_symptom(symptom_entities[0])
        elif intent == "medicine_query" and disease_entities:
            answer, evidence = self._answer_medicine_query(disease_entities[0])
        elif intent == "treatment_query" and disease_entities:
            answer, evidence = self._answer_treatment_query(disease_entities[0])
        elif disease_entities:
            answer, evidence = self._answer_general_disease_query(disease_entities[0])
        elif symptom_entities:
            answer, evidence = self._answer_disease_by_symptom(symptom_entities[0])
        else:
            answer, evidence = self._answer_general_query(question)
        
        return answer, evidence

    def _build_evidence_with_location(self, source: str, content: str, 
                                       confidence: float, node_type: str,
                                       disease_name: str = "", 
                                       keywords: List[str] = None,
                                       is_rare: bool = False) -> Dict:
        evidence = {
            "source": source,
            "content": content,
            "confidence": confidence,
            "node_type": node_type,
            "is_rare": is_rare,
            "paragraph_location": None,
            "highlighted_text": None
        }
        
        if disease_name and keywords:
            locations = self._find_paragraph_location(disease_name, keywords)
            if locations:
                loc = locations[0]
                evidence["paragraph_location"] = {
                    "paragraph_index": loc["paragraph_index"],
                    "section": loc["section"]
                }
                evidence["highlighted_text"] = loc["highlighted_text"]
                evidence["original_text"] = loc["original_text"]
        
        return evidence

    def _answer_symptom_query(self, disease: str, disease_display: str = None) -> tuple:
        display = disease_display or disease
        try:
            disease_info = self.db.get_disease_and_relations(disease)
            
            if not disease_info.get("disease"):
                return f"抱歉，我暂时没有关于【{display}】的详细信息。", []
            
            dis = disease_info["disease"]
            symptoms = disease_info.get("symptoms", [])
            symptom_names = [s["name"] for s in symptoms]
            is_rare = dis.get("is_rare", False)
            source = dis.get("source", "医疗知识图谱")
            
            answer = f"根据医疗知识图谱，【{display}】的常见症状包括："
            answer += "、".join(symptom_names) + "。\n\n"
            answer += f"疾病简介：{dis.get('description', '')}"
            if is_rare:
                answer += "\n\n⚠️ 这是一种罕见病，建议前往专科医院就诊。"
            
            evidence = [self._build_evidence_with_location(
                source=source,
                content=f"{display}的症状信息",
                confidence=0.9,
                node_type="Disease",
                disease_name=disease,
                keywords=symptom_names + ["症状"],
                is_rare=is_rare
            )]
            
            for symptom in symptoms:
                evidence.append(self._build_evidence_with_location(
                    source=source,
                    content=f"症状：{symptom['name']} - {symptom.get('description', '')}",
                    confidence=0.85,
                    node_type="Symptom",
                    disease_name=disease,
                    keywords=[symptom["name"]],
                    is_rare=symptom.get("is_rare", False)
                ))
            
            return answer, evidence
        except Exception as e:
            return f"查询症状信息时出错：{str(e)}", []

    def _answer_disease_by_symptom(self, symptom: str) -> tuple:
        try:
            diseases = self.db.search_disease_by_symptom(symptom)
            
            if not diseases:
                return f"根据症状【{symptom}】，暂时未匹配到相关疾病。", []
            
            answer = f"根据症状【{symptom}】，可能的疾病包括：\n\n"
            
            evidence = []
            for i, disease in enumerate(diseases, 1):
                is_rare = disease.get("is_rare", False)
                source = disease.get("source", "医疗知识图谱") if isinstance(disease, dict) else "医疗知识图谱"
                
                answer += f"{i}. {disease['disease']}"
                if is_rare:
                    answer += " [罕见病]"
                answer += "\n"
                answer += f"   简介：{disease['description']}\n\n"
                
                ev = self._build_evidence_with_location(
                    source=source,
                    content=f"疾病{disease['disease']}与症状{symptom}相关联",
                    confidence=0.8,
                    node_type="Disease",
                    disease_name=disease["disease"],
                    keywords=[symptom],
                    is_rare=is_rare
                )
                evidence.append(ev)
            
            answer += "注意：以上仅为参考，具体诊断请咨询专业医生。"
            
            return answer, evidence
        except Exception as e:
            return f"查询疾病信息时出错：{str(e)}", []

    def _answer_medicine_query(self, disease: str) -> tuple:
        try:
            medicines = self.db.search_medicine_by_disease(disease)
            
            if not medicines:
                return f"抱歉，我暂时没有关于【{disease}】的用药信息。", []
            
            answer = f"针对【{disease}】，常用的治疗药物包括：\n\n"
            
            evidence = []
            for i, med in enumerate(medicines, 1):
                is_rare = med.get("is_rare", False)
                answer += f"{i}. {med['medicine']} ({med['category']})"
                if is_rare:
                    answer += " [罕见病用药]"
                answer += "\n"
                answer += f"   用法：{med['usage']}\n\n"
                
                evidence.append(self._build_evidence_with_location(
                    source="医疗知识图谱",
                    content=f"药物{med['medicine']}用于治疗{disease}",
                    confidence=0.85,
                    node_type="Medicine",
                    disease_name=disease,
                    keywords=[med["medicine"], "治疗"],
                    is_rare=is_rare
                ))
            
            answer += "【重要提示】用药请遵医嘱，切勿自行用药。"
            
            return answer, evidence
        except Exception as e:
            return f"查询药物信息时出错：{str(e)}", []

    def _answer_treatment_query(self, disease: str) -> tuple:
        try:
            disease_info = self.db.get_disease_and_relations(disease)
            
            if not disease_info.get("disease"):
                return f"抱歉，我暂时没有关于【{disease}】的治疗信息。", []
            
            dis = disease_info["disease"]
            medicines = disease_info.get("medicines", [])
            departments = disease_info.get("departments", [])
            is_rare = dis.get("is_rare", False)
            source = dis.get("source", "医疗知识图谱")
            
            answer = f"关于【{disease}】的治疗建议：\n\n"
            if is_rare:
                answer += "⚠️ 这是一种罕见病，强烈建议前往具有相关诊疗经验的专科医院就诊。\n\n"
            
            if departments:
                dept_names = [d["name"] for d in departments]
                answer += f"1. 就诊科室：{', '.join(dept_names)}\n\n"
            
            if medicines:
                answer += "2. 常用药物：\n"
                for med in medicines:
                    answer += f"   - {med.get('name', '')}"
                    if med.get("is_rare"):
                        answer += " [罕见病用药]"
                    answer += "\n"
                answer += "\n"
            
            answer += "3. 建议：\n"
            answer += "   - 及时就医，听从专业医生的诊断和治疗建议\n"
            answer += "   - 遵医嘱用药，不要自行增减药量\n"
            answer += "   - 注意休息，保持良好的生活习惯\n"
            
            med_keywords = [m.get("name", "") for m in medicines] + ["治疗"]
            evidence = [self._build_evidence_with_location(
                source=source,
                content=f"{disease}的治疗方案信息",
                confidence=0.85,
                node_type="Disease",
                disease_name=disease,
                keywords=med_keywords,
                is_rare=is_rare
            )]
            
            return answer, evidence
        except Exception as e:
            return f"查询治疗信息时出错：{str(e)}", []

    def _answer_general_disease_query(self, disease: str) -> tuple:
        try:
            disease_info = self.db.get_disease_and_relations(disease)
            
            if not disease_info.get("disease"):
                return f"抱歉，我暂时没有关于【{disease}】的信息。", []
            
            dis = disease_info["disease"]
            symptoms = disease_info.get("symptoms", [])
            medicines = disease_info.get("medicines", [])
            departments = disease_info.get("departments", [])
            is_rare = dis.get("is_rare", False)
            source = dis.get("source", "医疗知识图谱")
            
            answer = f"【{disease}】相关信息：\n\n"
            if is_rare:
                answer += "⚠️ 这是一种罕见病\n\n"
            answer += f"疾病简介：{dis.get('description', '')}\n\n"
            answer += f"文献来源：{source}\n\n"
            
            if symptoms:
                symptom_names = [s["name"] for s in symptoms]
                answer += f"常见症状：{', '.join(symptom_names)}\n\n"
            
            if departments:
                dept_names = [d["name"] for d in departments]
                answer += f"就诊科室：{', '.join(dept_names)}\n\n"
            
            if medicines:
                med_names = [m["name"] for m in medicines]
                answer += f"常用药物：{', '.join(med_names)}\n"
            
            all_keywords = [s["name"] for s in symptoms] + [disease]
            evidence = [self._build_evidence_with_location(
                source=source,
                content=f"{disease}的完整信息",
                confidence=0.9,
                node_type="Disease",
                disease_name=disease,
                keywords=all_keywords,
                is_rare=is_rare
            )]
            
            return answer, evidence
        except Exception as e:
            return f"查询疾病信息时出错：{str(e)}", []

    def _answer_general_query(self, question: str) -> tuple:
        answer = """
感谢您的提问。我是一个医疗知识问答系统，可以为您提供以下方面的信息：

1. 疾病症状查询 - 例如："感冒有什么症状？"
2. 疾病诊断 - 例如："发烧可能是什么病？"
3. 用药咨询 - 例如："感冒吃什么药？"
4. 治疗建议 - 例如："高血压怎么治疗？"
5. 罕见病查询 - 例如："渐冻症有什么症状？"

目前知识库包含以下常见疾病：感冒、高血压、糖尿病、胃炎、肺炎。
罕见病知识库包含：渐冻症(ALS)、系统性红斑狼疮(SLE)、血友病、帕金森病、多发性硬化症。

请问您有什么具体的健康问题吗？
        """.strip()
        
        evidence = [{
            "source": "系统引导",
            "content": "通用问答引导",
            "confidence": 0.7,
            "node_type": "System",
            "is_rare": False,
            "paragraph_location": None,
            "highlighted_text": None
        }]
        
        return answer, evidence
