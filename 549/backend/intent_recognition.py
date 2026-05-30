import sys
import os
import json
import re
from typing import Tuple, List, Dict
from difflib import SequenceMatcher

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

class MedicalDictionary:
    def __init__(self):
        self.diseases = {"common": [], "rare": []}
        self.symptoms = {"common": [], "rare": []}
        self.medicines = {"common": [], "rare": []}
        self.body_parts = []
        self.aliases = {}
        self.all_diseases = []
        self.all_symptoms = []
        self.all_medicines = []
        self._loaded = False

    def load(self, dict_path: str = None):
        if dict_path is None:
            dict_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "medical_dictionary.json"
            )
        
        if not os.path.exists(dict_path):
            print(f"医学词典文件不存在: {dict_path}，使用内置词典")
            self._load_builtin()
            self._loaded = True
            return

        try:
            with open(dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            disease_data = data.get("disease", {})
            self.diseases["common"] = disease_data.get("common", [])
            self.diseases["rare"] = disease_data.get("rare", [])
            self.aliases = disease_data.get("aliases", {})

            symptom_data = data.get("symptom", {})
            self.symptoms["common"] = symptom_data.get("common", [])
            self.symptoms["rare"] = symptom_data.get("rare", [])

            medicine_data = data.get("medicine", {})
            self.medicines["common"] = medicine_data.get("common", [])
            self.medicines["rare"] = medicine_data.get("rare", [])

            self.body_parts = data.get("body_part", [])

            self.all_diseases = self.diseases["common"] + self.diseases["rare"]
            self.all_symptoms = self.symptoms["common"] + self.symptoms["rare"]
            self.all_medicines = self.medicines["common"] + self.medicines["rare"]
            self._loaded = True
            print(f"医学词典加载成功: {len(self.all_diseases)}种疾病, "
                  f"{len(self.all_symptoms)}种症状, {len(self.all_medicines)}种药物, "
                  f"{len(self.aliases)}个别名")
        except Exception as e:
            print(f"医学词典加载失败: {e}，使用内置词典")
            self._load_builtin()
            self._loaded = True

    def _load_builtin(self):
        self.diseases["common"] = ["感冒", "高血压", "糖尿病", "胃炎", "肺炎"]
        self.diseases["rare"] = ["渐冻症", "系统性红斑狼疮", "血友病",
                                 "多发性硬化症", "重症肌无力", "帕金森病"]
        self.symptoms["common"] = ["发热", "咳嗽", "头痛", "头晕", "恶心"]
        self.symptoms["rare"] = ["肌束颤动", "吞咽困难", "雷诺现象"]
        self.medicines["common"] = ["阿莫西林", "布洛芬", "二甲双胍"]
        self.medicines["rare"] = ["利鲁唑", "依库珠单抗"]
        self.aliases = {"渐冻症": "肌萎缩侧索硬化症", "老年痴呆": "阿尔茨海默病"}
        self.all_diseases = self.diseases["common"] + self.diseases["rare"]
        self.all_symptoms = self.symptoms["common"] + self.symptoms["rare"]
        self.all_medicines = self.medicines["common"] + self.medicines["rare"]

    def resolve_alias(self, name: str) -> str:
        return self.aliases.get(name, name)

    def fuzzy_match(self, text: str, candidates: List[str], threshold: float = 0.7) -> List[Dict]:
        matches = []
        for candidate in candidates:
            ratio = SequenceMatcher(None, text, candidate).ratio()
            if ratio >= threshold:
                matches.append({
                    "text": candidate,
                    "score": ratio,
                    "is_rare": candidate in (self.diseases.get("rare", []) +
                                             self.symptoms.get("rare", []) +
                                             self.medicines.get("rare", []))
                })
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches

    def is_rare_disease(self, name: str) -> bool:
        return name in self.diseases.get("rare", [])

    def is_rare_symptom(self, name: str) -> bool:
        return name in self.symptoms.get("rare", [])

    def is_rare_medicine(self, name: str) -> bool:
        return name in self.medicines.get("rare", [])


class IntentRecognizer:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.medical_dict = MedicalDictionary()
        
        self.intent_labels = [
            "symptom_query",
            "disease_query",
            "medicine_query",
            "treatment_query",
            "diagnosis_query",
            "general_query"
        ]
        
        self.intent_keywords = {
            "symptom_query": ["症状", "表现", "征兆", "特征", "有什么症状", "会怎么样"],
            "disease_query": ["什么病", "疾病", "病情", "这是什么病", "得了什么病"],
            "medicine_query": ["药", "药物", "吃什么药", "用什么药", "药品"],
            "treatment_query": ["治疗", "怎么治", "如何治疗", "治疗方法", "怎么办"],
            "diagnosis_query": ["诊断", "检查", "怎么检查", "需要做什么检查"],
            "general_query": []
        }

    def load_model(self):
        self.medical_dict.load()
        
        try:
            from transformers import BertTokenizer, BertForSequenceClassification
            import torch
            
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"使用设备: {self.device}")
            
            self.tokenizer = BertTokenizer.from_pretrained(settings.BERT_MODEL_NAME)
            self.model = BertForSequenceClassification.from_pretrained(
                settings.BERT_MODEL_NAME,
                num_labels=len(self.intent_labels)
            )
            self.model.to(self.device)
            self.model.eval()
            
            print("BERT模型加载成功")
        except Exception as e:
            print(f"BERT模型加载失败，使用关键词匹配: {e}")
            self.model = None
            self.tokenizer = None

    def recognize_intent(self, question: str) -> Tuple[str, float]:
        if self.model and self.tokenizer:
            return self._recognize_with_bert(question)
        else:
            return self._recognize_with_keywords(question)

    def _recognize_with_bert(self, question: str) -> Tuple[str, float]:
        try:
            import torch
            
            inputs = self.tokenizer(
                question,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=128
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)
                
                predicted_idx = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][predicted_idx].item()
                
                return self.intent_labels[predicted_idx], confidence
        except Exception as e:
            print(f"BERT识别失败，使用关键词匹配: {e}")
            return self._recognize_with_keywords(question)

    def _recognize_with_keywords(self, question: str) -> Tuple[str, float]:
        scores = {}
        
        for intent, keywords in self.intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in question:
                    score += 1
            scores[intent] = score
        
        max_intent = max(scores, key=scores.get)
        
        if scores[max_intent] > 0:
            total = sum(scores.values()) or 1
            confidence = scores[max_intent] / total
            confidence = min(0.95, 0.5 + confidence * 0.45)
        else:
            max_intent = "general_query"
            confidence = 0.5
        
        return max_intent, confidence

    def extract_entities(self, question: str) -> List[Dict]:
        entities = []
        seen = set()

        for name in self.medical_dict.all_diseases:
            if name in question and name not in seen:
                resolved = self.medical_dict.resolve_alias(name)
                is_rare = self.medical_dict.is_rare_disease(name) or self.medical_dict.is_rare_disease(resolved)
                entities.append({
                    "text": name,
                    "canonical": resolved,
                    "type": "disease",
                    "is_rare": is_rare,
                    "match_method": "exact"
                })
                seen.add(name)

        for name in self.medical_dict.all_symptoms:
            if name in question and name not in seen:
                is_rare = self.medical_dict.is_rare_symptom(name)
                entities.append({
                    "text": name,
                    "canonical": name,
                    "type": "symptom",
                    "is_rare": is_rare,
                    "match_method": "exact"
                })
                seen.add(name)

        for name in self.medical_dict.all_medicines:
            if name in question and name not in seen:
                is_rare = self.medical_dict.is_rare_medicine(name)
                entities.append({
                    "text": name,
                    "canonical": name,
                    "type": "medicine",
                    "is_rare": is_rare,
                    "match_method": "exact"
                })
                seen.add(name)

        for alias, canonical in self.medical_dict.aliases.items():
            if alias in question and alias not in seen and canonical not in seen:
                is_rare = self.medical_dict.is_rare_disease(canonical)
                entities.append({
                    "text": alias,
                    "canonical": canonical,
                    "type": "disease",
                    "is_rare": is_rare,
                    "match_method": "alias"
                })
                seen.add(alias)

        if not any(e["type"] == "disease" for e in entities):
            disease_matches = self.medical_dict.fuzzy_match(question, self.medical_dict.all_diseases, 0.6)
            for match in disease_matches[:1]:
                if match["text"] not in seen:
                    resolved = self.medical_dict.resolve_alias(match["text"])
                    entities.append({
                        "text": match["text"],
                        "canonical": resolved,
                        "type": "disease",
                        "is_rare": match.get("is_rare", False),
                        "match_method": "fuzzy",
                        "fuzzy_score": round(match["score"], 3)
                    })
                    seen.add(match["text"])

        if not any(e["type"] == "symptom" for e in entities):
            symptom_matches = self.medical_dict.fuzzy_match(question, self.medical_dict.all_symptoms, 0.6)
            for match in symptom_matches[:1]:
                if match["text"] not in seen:
                    entities.append({
                        "text": match["text"],
                        "canonical": match["text"],
                        "type": "symptom",
                        "is_rare": match.get("is_rare", False),
                        "match_method": "fuzzy",
                        "fuzzy_score": round(match["score"], 3)
                    })
                    seen.add(match["text"])

        return entities

    def analyze_question(self, question: str) -> Dict:
        intent, confidence = self.recognize_intent(question)
        entities = self.extract_entities(question)
        
        return {
            "intent": intent,
            "intent_confidence": confidence,
            "entities": entities
        }
