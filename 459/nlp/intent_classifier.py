import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification, AdamW
from transformers import get_linear_schedule_with_warmup
import numpy as np
from typing import List, Dict, Tuple
import os

from config.settings import settings
from kg.schema import INTENT_TYPES


class IntentDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenizer: BertTokenizer, max_len: int):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = str(self.texts[item])
        label = self.labels[item]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding="max_length",
            truncation=True,
            return_attention_mask=True,
            return_tensors="pt"
        )

        return {
            "text": text,
            "input_ids": encoding["input_ids"].flatten(),
            "attention_mask": encoding["attention_mask"].flatten(),
            "label": torch.tensor(label, dtype=torch.long)
        }


class BERTIntentClassifier:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = BertTokenizer.from_pretrained(settings.BERT_MODEL)
        self.max_len = settings.MAX_SEQ_LENGTH
        self.num_classes = len(INTENT_TYPES)
        self.intent_to_idx = {intent: idx for idx, intent in enumerate(INTENT_TYPES)}
        self.idx_to_intent = {idx: intent for idx, intent in enumerate(INTENT_TYPES)}

        if model_path and os.path.exists(model_path):
            self.model = BertForSequenceClassification.from_pretrained(model_path)
        else:
            self.model = BertForSequenceClassification.from_pretrained(
                settings.BERT_MODEL,
                num_labels=self.num_classes
            )

        self.model = self.model.to(self.device)
        self.trained = False

    def prepare_training_data(self) -> Tuple[List[str], List[int]]:
        training_data = {
            "disease_symptom": [
                "感冒有什么症状",
                "肺炎会发烧吗",
                "糖尿病的表现是什么",
                "高血压会引起头痛吗",
                "胃炎有哪些症状",
                "这个病有什么表现",
                "这种病会有什么症状",
                "症状有哪些"
            ],
            "disease_drug": [
                "感冒吃什么药",
                "肺炎用什么药治疗",
                "糖尿病需要吃什么药",
                "高血压吃什么药",
                "胃炎用什么药",
                "治疗这个病用什么药",
                "用什么药物治疗"
            ],
            "disease_department": [
                "感冒挂什么科",
                "肺炎去哪个科室",
                "糖尿病属于哪个科",
                "高血压应该看什么科",
                "胃炎去哪个科室看",
                "这个病属于哪个科室",
                "应该挂什么科"
            ],
            "disease_treatment": [
                "感冒怎么治疗",
                "肺炎怎么治",
                "糖尿病的治疗方法",
                "高血压怎么治疗",
                "胃炎如何治疗",
                "这个病怎么治",
                "有什么治疗方法"
            ],
            "disease_examination": [
                "感冒需要做什么检查",
                "肺炎需要检查什么",
                "糖尿病要做什么检查",
                "高血压需要做哪些检查",
                "胃炎需要检查什么",
                "这个病需要做什么检查"
            ],
            "drug_disease": [
                "阿莫西林治什么病",
                "布洛芬能治什么",
                "奥美拉唑治疗什么",
                "二甲双胍治什么病",
                "这个药治什么",
                "这种药能治什么病"
            ],
            "symptom_disease": [
                "发烧咳嗽是什么病",
                "头痛头晕可能是什么病",
                "腹痛恶心是什么病",
                "多饮多尿是什么病",
                "这些症状是什么病",
                "有这些症状可能得什么病"
            ],
            "department_disease": [
                "呼吸内科看什么病",
                "心内科治疗哪些疾病",
                "消化内科看什么病",
                "内分泌科看什么病",
                "这个科室看什么病",
                "神经内科治什么病"
            ],
            "doctor_disease": [
                "张医生治什么病",
                "李医生擅长什么",
                "王医生看什么病",
                "赵医生的专业是什么",
                "这个医生擅长什么病"
            ],
            "multi_hop": [
                "治疗感冒的医生在哪个科室",
                "肺炎的治疗药物有哪些副作用",
                "高血压患者需要做哪些检查然后吃什么药",
                "糖尿病的医生推荐什么治疗方法",
                "胃炎的症状有哪些应该吃什么药"
            ],
            "fuzzy_query": [
                "和感冒相关的信息",
                "关于肺的病有哪些",
                "降压相关的东西",
                "胃相关的问题",
                "找一下关于心脏的病"
            ]
        }

        texts = []
        labels = []

        for intent, questions in training_data.items():
            for q in questions:
                texts.append(q)
                labels.append(self.intent_to_idx[intent])

        return texts, labels

    def train(self, epochs: int = 20, batch_size: int = 8, learning_rate: float = 2e-5):
        texts, labels = self.prepare_training_data()

        dataset = IntentDataset(texts, labels, self.tokenizer, self.max_len)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        total_steps = len(dataloader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=0, num_training_steps=total_steps
        )

        self.model.train()

        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["label"].to(self.device)

                self.model.zero_grad()

                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )

                loss = outputs.loss
                total_loss += loss.item()

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()

            avg_loss = total_loss / len(dataloader)
            print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

        self.trained = True
        print("训练完成！")

    def predict(self, text: str) -> Dict[str, any]:
        self.model.eval()

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding="max_length",
            truncation=True,
            return_attention_mask=True,
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]

        predictions = []
        for idx, prob in enumerate(probabilities):
            predictions.append({
                "intent": self.idx_to_intent[idx],
                "confidence": float(prob)
            })

        predictions.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "text": text,
            "predicted_intent": predictions[0]["intent"],
            "confidence": predictions[0]["confidence"],
            "all_predictions": predictions
        }

    def save_model(self, save_path: str):
        self.model.save_pretrained(save_path)
        print(f"模型已保存到: {save_path}")


class SimpleIntentClassifier:
    def __init__(self):
        self.keyword_maps = {
            "disease_symptom": ["症状", "表现", "征兆", "特征"],
            "disease_drug": ["药", "药物", "吃什么药", "用什么药"],
            "disease_department": ["科室", "科", "挂什么科", "哪个科"],
            "disease_treatment": ["治疗", "治", "怎么治", "疗法"],
            "disease_examination": ["检查", "化验", "做什么检查"],
            "drug_disease": ["治什么", "什么病", "治疗什么"],
            "symptom_disease": ["什么病", "是什么病", "可能是什么"],
            "department_disease": ["什么病", "哪些病", "看什么病"],
            "doctor_disease": ["医生", "治什么", "擅长"]
        }

    def predict(self, text: str) -> Dict[str, any]:
        scores = {intent: 0 for intent in INTENT_TYPES}

        for intent, keywords in self.keyword_maps.items():
            for keyword in keywords:
                if keyword in text:
                    scores[intent] += 1

        if sum(scores.values()) == 0:
            return {
                "text": text,
                "predicted_intent": "fuzzy_query",
                "confidence": 0.5,
                "all_predictions": [{"intent": "fuzzy_query", "confidence": 0.5}]
            }

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        total = sum(scores.values())

        predictions = [
            {"intent": intent, "confidence": score / total if total > 0 else 0}
            for intent, score in sorted_intents
            if score > 0
        ]

        return {
            "text": text,
            "predicted_intent": predictions[0]["intent"],
            "confidence": predictions[0]["confidence"],
            "all_predictions": predictions
        }
