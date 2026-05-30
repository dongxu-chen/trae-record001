import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizer,
    EncoderDecoderModel,
    BertConfig,
    BertLMHeadModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    AutoTokenizer,
)
from typing import List, Dict, Any, Optional
import os
import logging
import re

from config.settings import settings
from kg.schema import RELATION_TYPES, ENTITY_TYPES, RELATION_INTENT_MAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CYPHER_SPECIAL_TOKENS = ["<ent>", "</ent>", "<type>", "</type>", "<intent>", "</intent>"]

TRAINING_PAIRS = [
    ("感冒有什么症状", "MATCH (n:Disease {name: $entity_name})-[r:HAS_SYMPTOM]->(m:Symptom) RETURN m.name as result"),
    ("肺炎会发烧吗", "MATCH (n:Disease {name: $entity_name})-[r:HAS_SYMPTOM]->(m:Symptom) RETURN m.name as result"),
    ("糖尿病的表现是什么", "MATCH (n:Disease {name: $entity_name})-[r:HAS_SYMPTOM]->(m:Symptom) RETURN m.name as result"),
    ("高血压会引起头痛吗", "MATCH (n:Disease {name: $entity_name})-[r:HAS_SYMPTOM]->(m:Symptom) RETURN m.name as result"),
    ("感冒吃什么药", "MATCH (n:Disease {name: $entity_name})-[r:USES_DRUG]->(m:Drug) RETURN m.name as result"),
    ("肺炎用什么药治疗", "MATCH (n:Disease {name: $entity_name})-[r:USES_DRUG]->(m:Drug) RETURN m.name as result"),
    ("糖尿病需要吃什么药", "MATCH (n:Disease {name: $entity_name})-[r:USES_DRUG]->(m:Drug) RETURN m.name as result"),
    ("高血压吃什么药", "MATCH (n:Disease {name: $entity_name})-[r:USES_DRUG]->(m:Drug) RETURN m.name as result"),
    ("感冒挂什么科", "MATCH (n:Disease {name: $entity_name})-[r:BELONGS_TO_DEPARTMENT]->(m:Department) RETURN m.name as result"),
    ("肺炎去哪个科室", "MATCH (n:Disease {name: $entity_name})-[r:BELONGS_TO_DEPARTMENT]->(m:Department) RETURN m.name as result"),
    ("糖尿病属于哪个科", "MATCH (n:Disease {name: $entity_name})-[r:BELONGS_TO_DEPARTMENT]->(m:Department) RETURN m.name as result"),
    ("感冒怎么治疗", "MATCH (n:Disease {name: $entity_name})-[r:HAS_TREATMENT]->(m:Treatment) RETURN m.name as result"),
    ("肺炎怎么治", "MATCH (n:Disease {name: $entity_name})-[r:HAS_TREATMENT]->(m:Treatment) RETURN m.name as result"),
    ("糖尿病的治疗方法", "MATCH (n:Disease {name: $entity_name})-[r:HAS_TREATMENT]->(m:Treatment) RETURN m.name as result"),
    ("感冒需要做什么检查", "MATCH (n:Disease {name: $entity_name})-[r:NEEDS_EXAMINATION]->(m:Examination) RETURN m.name as result"),
    ("肺炎需要检查什么", "MATCH (n:Disease {name: $entity_name})-[r:NEEDS_EXAMINATION]->(m:Examination) RETURN m.name as result"),
    ("阿莫西林治什么病", "MATCH (n:Disease)-[r:USES_DRUG]->(m:Drug {name: $entity_name}) RETURN n.name as result"),
    ("布洛芬能治什么", "MATCH (n:Disease)-[r:USES_DRUG]->(m:Drug {name: $entity_name}) RETURN n.name as result"),
    ("二甲双胍治什么病", "MATCH (n:Disease)-[r:USES_DRUG]->(m:Drug {name: $entity_name}) RETURN n.name as result"),
    ("发烧咳嗽是什么病", "MATCH (n:Disease)-[r:HAS_SYMPTOM]->(m:Symptom {name: $entity_name}) RETURN n.name as result"),
    ("头痛头晕可能是什么病", "MATCH (n:Disease)-[r:HAS_SYMPTOM]->(m:Symptom {name: $entity_name}) RETURN n.name as result"),
    ("腹痛恶心是什么病", "MATCH (n:Disease)-[r:HAS_SYMPTOM]->(m:Symptom {name: $entity_name}) RETURN n.name as result"),
    ("呼吸内科看什么病", "MATCH (n:Disease)-[r:BELONGS_TO_DEPARTMENT]->(m:Department {name: $entity_name}) RETURN n.name as result"),
    ("消化内科看什么病", "MATCH (n:Disease)-[r:BELONGS_TO_DEPARTMENT]->(m:Department {name: $entity_name}) RETURN n.name as result"),
    ("张医生治什么病", "MATCH (n:Doctor {name: $entity_name})-[r:TREATS_DISEASE]->(m:Disease) RETURN m.name as result"),
    ("李医生擅长什么", "MATCH (n:Doctor {name: $entity_name})-[r:TREATS_DISEASE]->(m:Disease) RETURN m.name as result"),
    ("感冒有什么症状然后用什么药", "MATCH (n:Disease {name: $entity_name})-[r1:HAS_SYMPTOM]->(m1:Symptom) RETURN m1.name as result UNION MATCH (n:Disease {name: $entity_name})-[r2:USES_DRUG]->(m2:Drug) RETURN m2.name as result"),
    ("肺炎应该挂什么科以及怎么治疗", "MATCH (n:Disease {name: $entity_name})-[r1:BELONGS_TO_DEPARTMENT]->(m1:Department) RETURN m1.name as result UNION MATCH (n:Disease {name: $entity_name})-[r2:HAS_TREATMENT]->(m2:Treatment) RETURN m2.name as result"),
    ("查找感冒的信息", "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($search_term) RETURN n.name as result, labels(n) as entity_types"),
    ("和肺相关的病", "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($search_term) RETURN n.name as result, labels(n) as entity_types"),
    ("感冒和呼吸内科的关系", "MATCH path = shortestPath((n1 {name: $entity1})-[*1..4]-(n2 {name: $entity2})) RETURN [node IN nodes(path) | node.name] as path_nodes, [rel IN relationships(path) | type(rel)] as path_relations"),
    ("感冒到阿莫西林的路径", "MATCH path = shortestPath((n1 {name: $entity1})-[*1..4]-(n2 {name: $entity2})) RETURN [node IN nodes(path) | node.name] as path_nodes, [rel IN relationships(path) | type(rel)] as path_relations"),
    ("胃溃疡的详细信息", "MATCH (n {name: $entity_name}) OPTIONAL MATCH (n)-[r_out]->(out) OPTIONAL MATCH (in_n)-[r_in]->(n) RETURN n, collect(DISTINCT {relation: type(r_out), target: out.name}) as outgoing_relations, collect(DISTINCT {relation: type(r_in), source: in_n.name}) as incoming_relations"),
    ("高血压有什么并发症", "MATCH (n:Disease {name: $entity_name})-[r:HAS_COMPLICATION]->(m:Disease) RETURN m.name as result"),
    ("感冒的症状对应的药物治疗", "MATCH (d:Disease {name: $entity_name})-[r1:HAS_SYMPTOM]->(s:Symptom) WITH d, collect(s) as symptoms MATCH (d)-[r2:USES_DRUG]->(dr:Drug) RETURN symptoms, collect(dr.name) as drugs"),
]


class CypherDataset(Dataset):
    def __init__(self, pairs: List[tuple], tokenizer: BertTokenizer, max_src_len: int = 64, max_tgt_len: int = 256):
        self.pairs = pairs
        self.tokenizer = tokenizer
        self.max_src_len = max_src_len
        self.max_tgt_len = max_tgt_len

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        src_text, tgt_text = self.pairs[idx]

        src_enc = self.tokenizer(
            src_text,
            max_length=self.max_src_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        tgt_enc = self.tokenizer(
            tgt_text,
            max_length=self.max_tgt_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        labels = tgt_enc["input_ids"].squeeze()
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": src_enc["input_ids"].squeeze(),
            "attention_mask": src_enc["attention_mask"].squeeze(),
            "labels": labels,
            "decoder_attention_mask": tgt_enc["attention_mask"].squeeze(),
        }


class Seq2SeqCypherGenerator:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = BertTokenizer.from_pretrained(settings.BERT_MODEL)

        special_tokens_dict = {"additional_special_tokens": CYPHER_SPECIAL_TOKENS}
        self.tokenizer.add_special_tokens(special_tokens_dict)

        if model_path and os.path.isdir(model_path):
            logger.info(f"从 {model_path} 加载Seq2Seq模型")
            self.model = EncoderDecoderModel.from_pretrained(model_path)
        else:
            logger.info("初始化新的Seq2Seq模型")
            encoder_config = BertConfig.from_pretrained(settings.BERT_MODEL)
            decoder_config = BertConfig.from_pretrained(settings.BERT_MODEL)
            decoder_config.is_decoder = True
            decoder_config.add_cross_attention = True

            self.model = EncoderDecoderModel.from_encoder_decoder_pretrained(
                settings.BERT_MODEL, settings.BERT_MODEL
            )

        self.model.config.decoder_start_token_id = self.tokenizer.cls_token_id
        self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.config.eos_token_id = self.tokenizer.sep_token_id
        self.model.config.vocab_size = self.model.config.encoder.vocab_size
        self.model.config.max_length = 256
        self.model.config.min_length = 10
        self.model.config.no_repeat_ngram_size = 3
        self.model.config.length_penalty = 1.0
        self.model.config.early_stopping = True
        self.model.config.num_beams = 4

        self.model.resize_token_embeddings(len(self.tokenizer))
        self.model = self.model.to(self.device)
        self.trained = False

    def train(self, epochs: int = 30, batch_size: int = 4, learning_rate: float = 5e-5):
        dataset = CypherDataset(TRAINING_PAIRS, self.tokenizer)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)
        self.model.train()

        for epoch in range(epochs):
            total_loss = 0.0
            for batch in dataloader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)
                decoder_attention_mask = batch["decoder_attention_mask"].to(self.device)

                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                    decoder_attention_mask=decoder_attention_mask,
                )

                loss = outputs.loss
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()

                total_loss += loss.item()

            avg_loss = total_loss / len(dataloader)
            logger.info(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

        self.trained = True
        logger.info("Seq2Seq模型训练完成")

    def generate(self, question: str, intent: str = None, entities: List[Dict] = None) -> Dict[str, Any]:
        prompt = self._build_prompt(question, intent, entities)

        self.model.eval()
        src_enc = self.tokenizer(
            prompt,
            max_length=64,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = src_enc["input_ids"].to(self.device)
        attention_mask = src_enc["attention_mask"].to(self.device)

        with torch.no_grad():
            generated = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=256,
                min_length=10,
                num_beams=4,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )

        cypher_text = self.tokenizer.decode(generated[0], skip_special_tokens=True)
        cypher_text = self._postprocess_cypher(cypher_text, entities)

        query_type = self._infer_query_type(cypher_text)

        return {
            "cypher": cypher_text,
            "parameters": self._extract_parameters(cypher_text, entities, intent),
            "query_type": query_type,
            "generation_method": "seq2seq",
        }

    def _build_prompt(self, question: str, intent: str = None, entities: List[Dict] = None) -> str:
        parts = [question]

        if intent:
            parts.append(f"<intent>{intent}</intent>")

        if entities:
            ent_strs = []
            for e in entities:
                name = e.get("canonical_name", e.get("text", ""))
                etype = e.get("type", "")
                ent_strs.append(f"<ent>{name}</ent><type>{etype}</type>")
            parts.append(" ".join(ent_strs))

        return " ".join(parts)

    def _postprocess_cypher(self, cypher: str, entities: List[Dict] = None) -> str:
        cypher = re.sub(r'\s+', ' ', cypher).strip()

        if "$entity_name" not in cypher and entities and len(entities) > 0:
            name = entities[0].get("canonical_name", entities[0].get("text", ""))
            cypher = cypher.replace("感冒", f'"${{entity_name}}"')
            cypher = cypher.replace('"$entity_name"', "$entity_name")

        if not cypher.upper().startswith("MATCH"):
            if "MATCH" in cypher.upper():
                idx = cypher.upper().index("MATCH")
                cypher = cypher[idx:]

        if "RETURN" not in cypher.upper():
            cypher += " RETURN m.name as result"

        return cypher

    def _extract_parameters(self, cypher: str, entities: List[Dict] = None, intent: str = None) -> Dict[str, Any]:
        params = {}
        if entities and len(entities) > 0:
            params["entity_name"] = entities[0].get("canonical_name", entities[0].get("text", ""))

        if "$entity1" in cypher and entities and len(entities) >= 2:
            params["entity1"] = entities[0].get("canonical_name", "")
            params["entity2"] = entities[1].get("canonical_name", "")

        if "$search_term" in cypher and entities and len(entities) > 0:
            params["search_term"] = entities[0].get("canonical_name", "")

        return params

    def _infer_query_type(self, cypher: str) -> str:
        upper = cypher.upper()
        if "UNION" in upper:
            return "multi_hop"
        if "shortestPath" in upper:
            return "path_between"
        if "CONTAINS" in upper:
            return "fuzzy_match"
        if "OPTIONAL MATCH" in upper:
            return "entity_details"
        if "[*" in cypher:
            return "variable_hop"
        return "single_hop"

    def save_model(self, path: str):
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        logger.info(f"Seq2Seq模型已保存到 {path}")


class HybridCypherGenerator:
    def __init__(self, use_seq2seq: bool = True):
        self.template_generator = CypherTemplateGenerator()
        self.seq2seq_generator = None
        self.use_seq2seq = use_seq2seq

        if use_seq2seq:
            try:
                model_dir = os.path.join(os.path.dirname(__file__), "..", "models", "seq2seq_cypher")
                if os.path.isdir(model_dir):
                    self.seq2seq_generator = Seq2SeqCypherGenerator(model_path=model_dir)
                else:
                    self.seq2seq_generator = Seq2SeqCypherGenerator()
                logger.info("Seq2Seq Cypher生成器初始化成功")
            except Exception as e:
                logger.warning(f"Seq2Seq初始化失败，回退到模板生成: {e}")
                self.seq2seq_generator = None

    def generate(
        self,
        question: str,
        intent: str,
        entities: List[Dict[str, Any]],
        use_seq2seq: bool = None
    ) -> Dict[str, Any]:
        should_use_seq2seq = use_seq2seq if use_seq2seq is not None else self.use_seq2seq

        if should_use_seq2seq and self.seq2seq_generator and self.seq2seq_generator.trained:
            try:
                result = self.seq2seq_generator.generate(question, intent, entities)
                if self._validate_cypher(result.get("cypher", "")):
                    return result
                logger.info("Seq2Seq生成的Cypher无效，回退到模板生成")
            except Exception as e:
                logger.warning(f"Seq2Seq生成失败: {e}")

        return self.template_generator.generate(intent, entities)

    def _validate_cypher(self, cypher: str) -> bool:
        if not cypher:
            return False
        upper = cypher.upper().strip()
        if not upper.startswith("MATCH") and not upper.startswith("CYPHER"):
            return False
        if "RETURN" not in upper:
            return False
        open_parens = cypher.count("(") - cypher.count(")")
        open_brackets = cypher.count("[") - cypher.count("]")
        open_braces = cypher.count("{") - cypher.count("}")
        if open_parens != 0 or open_brackets != 0 or open_braces != 0:
            return False
        return True

    def train_seq2seq(self, epochs: int = 30, batch_size: int = 4):
        if self.seq2seq_generator:
            self.seq2seq_generator.train(epochs=epochs, batch_size=batch_size)


class CypherTemplateGenerator:
    def __init__(self):
        self.relation_map = RELATION_INTENT_MAP

    def generate(self, intent: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not entities:
            return {"cypher": None, "error": "没有识别到实体"}

        entity_name = entities[0].get("canonical_name", entities[0].get("text", ""))

        if intent == "multi_hop":
            return self._generate_multi_hop(intent, entities)
        elif intent == "fuzzy_query":
            return self._generate_fuzzy_match(entity_name)
        elif intent in self.relation_map:
            return self._generate_single_hop(intent, entity_name)
        else:
            return self._generate_entity_details(entity_name)

    def _generate_single_hop(self, intent: str, entity_name: str) -> Dict[str, Any]:
        relation_info = self.relation_map[intent]
        relation = relation_info["relation"]
        target_type = relation_info["target"]
        direction = relation_info["direction"]

        if direction == "out":
            cypher = f"MATCH (n {{name: $entity_name}})-[r:{relation}]->(m:{target_type}) RETURN m.name as result, m as node, type(r) as relation_type"
        else:
            cypher = f"MATCH (n:{target_type})-[r:{relation}]->(m {{name: $entity_name}}) RETURN n.name as result, n as node, type(r) as relation_type"

        return {
            "cypher": cypher,
            "parameters": {"entity_name": entity_name},
            "query_type": "single_hop",
            "entity": entity_name,
            "relation": relation,
            "target_type": target_type,
            "generation_method": "template",
        }

    def _generate_multi_hop(self, intent: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        entity_name = entities[0].get("canonical_name", "")
        relations = ["HAS_SYMPTOM", "USES_DRUG"]

        relation_pattern = "->".join([f"[r{i}:{r}]" for i, r in enumerate(relations)])
        relation_pattern = "-" + relation_pattern + "->"

        cypher = f"MATCH path = (n {{name: $start_entity}}){relation_pattern}(m) RETURN m.name as final_result, [node IN nodes(path) | node.name] as path_nodes, [rel IN relationships(path) | type(rel)] as path_relations, path LIMIT 20"

        return {
            "cypher": cypher,
            "parameters": {"start_entity": entity_name},
            "query_type": "multi_hop",
            "start_entity": entity_name,
            "relations": relations,
            "generation_method": "template",
        }

    def _generate_fuzzy_match(self, search_term: str) -> Dict[str, Any]:
        cypher = "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($search_term) RETURN n.name as result, labels(n) as entity_types, n as node ORDER BY size(n.name) ASC LIMIT 10"

        return {
            "cypher": cypher,
            "parameters": {"search_term": search_term},
            "query_type": "fuzzy_match",
            "generation_method": "template",
        }

    def _generate_entity_details(self, entity_name: str) -> Dict[str, Any]:
        cypher = "MATCH (n {name: $entity_name}) OPTIONAL MATCH (n)-[r_out]->(out) OPTIONAL MATCH (in_n)-[r_in]->(n) RETURN n, collect(DISTINCT {relation: type(r_out), target: out.name}) as outgoing_relations, collect(DISTINCT {relation: type(r_in), source: in_n.name}) as incoming_relations"

        return {
            "cypher": cypher,
            "parameters": {"entity_name": entity_name},
            "query_type": "entity_details",
            "generation_method": "template",
        }
