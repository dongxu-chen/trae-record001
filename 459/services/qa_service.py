from typing import Dict, Any, Optional
import logging

from kg.neo4j_client import Neo4jClient
from kg.graph_visualizer import GraphVisualizer
from nlp.intent_classifier import SimpleIntentClassifier
from nlp.entity_extractor import EntityExtractor
from nlp.clarification import ClarificationEngine
from nlp.incremental_learner import IncrementalLearner, FeedbackStore
from query.seq2seq_cypher import HybridCypherGenerator
from query.path_reasoner import PathReasoner
from query.answer_processor import AnswerProcessor
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAService:
    def __init__(self, use_bert: bool = False, use_seq2seq: bool = True):
        self.neo4j_client = Neo4jClient()
        self.entity_extractor = EntityExtractor(self.neo4j_client)
        self.cypher_generator = HybridCypherGenerator(use_seq2seq=use_seq2seq)
        self.path_reasoner = PathReasoner(self.neo4j_client)
        self.answer_processor = AnswerProcessor()
        self.graph_visualizer = GraphVisualizer(self.neo4j_client)
        self.clarification_engine = ClarificationEngine(self.neo4j_client, self.entity_extractor)
        self.incremental_learner = IncrementalLearner()

        if use_bert:
            try:
                from nlp.intent_classifier import BERTIntentClassifier
                self.intent_classifier = BERTIntentClassifier()
                logger.info("使用BERT意图分类器")
            except Exception as e:
                logger.warning(f"BERT初始化失败，使用简单规则分类器: {e}")
                self.intent_classifier = SimpleIntentClassifier()
        else:
            self.intent_classifier = SimpleIntentClassifier()
            logger.info("使用简单规则意图分类器")

    def answer(self, question: str, skip_clarification: bool = False) -> Dict[str, Any]:
        logger.info(f"收到问题: {question}")

        intent_result = self.intent_classifier.predict(question)
        intent = intent_result["predicted_intent"]

        intent = self.incremental_learner.apply_intent_correction(question, intent)

        corrected_answer = self.incremental_learner.apply_answer_correction(question)
        if corrected_answer:
            logger.info("增量学习命中答案修正")
            return {
                "question": question,
                "answer": corrected_answer,
                "has_answer": True,
                "intent": {"predicted": intent, "confidence": 1.0, "source": "incremental_learning"},
                "entities": [],
                "source": {"type": "user_correction"}
            }

        intent_confidence = intent_result.get("confidence", 1.0)

        entities = self.entity_extractor.extract_entities(question)

        for e in entities:
            if e.get("text"):
                corrected = self.incremental_learner.apply_entity_correction(e["text"])
                if corrected:
                    e["canonical_name"] = corrected
                    logger.info(f"实体修正: {e['text']} -> {corrected}")

        logger.info(f"识别意图: {intent} (置信度: {intent_confidence:.2f})")
        logger.info(f"识别实体: {[e['canonical_name'] for e in entities]}")

        if not skip_clarification:
            ambiguity = self.clarification_engine.check_ambiguity(
                question, intent_result, entities
            )
            if ambiguity:
                logger.info("检测到歧义，返回澄清请求")
                return {
                    "question": question,
                    "answer": ambiguity["clarification"]["clarification_question"],
                    "has_answer": False,
                    "needs_clarification": True,
                    "clarification": ambiguity["clarification"],
                    "ambiguity_details": ambiguity["ambiguities"],
                    "intent": {"predicted": intent, "confidence": intent_confidence},
                    "entities": entities
                }

        if not entities:
            logger.info("未识别到实体，尝试模糊匹配")
            return self._handle_fuzzy_query(question)

        if intent == "multi_hop" or self._is_multi_hop_question(question):
            logger.info("检测到多跳查询")
            return self._handle_multi_hop_query(question, intent, entities)
        elif intent == "fuzzy_query":
            logger.info("处理模糊查询")
            return self._handle_fuzzy_query(question, entities)
        else:
            return self._handle_single_hop_query(question, intent, entities, intent_confidence)

    def _handle_single_hop_query(
        self,
        question: str,
        intent: str,
        entities: list,
        intent_confidence: float = 0.8
    ) -> Dict[str, Any]:
        entity = entities[0]
        entity_name = entity["canonical_name"]

        logger.info(f"单跳查询: {intent} - {entity_name}")

        query_info = self.cypher_generator.generate(
            question=question,
            intent=intent,
            entities=entities,
        )

        if not query_info or not query_info.get("cypher"):
            logger.warning("Hybrid生成失败，回退到模板")
            from query.seq2seq_cypher import CypherTemplateGenerator
            fallback = CypherTemplateGenerator()
            query_info = fallback.generate(intent, entities)

        cypher = query_info.get("cypher")
        parameters = query_info.get("parameters", {})

        logger.info(f"执行Cypher查询 [method={query_info.get('generation_method', 'unknown')}]")

        query_result = []
        try:
            query_result = self.neo4j_client.execute_query(cypher, parameters)
        except Exception as e:
            logger.warning(f"Cypher执行出错: {e}，尝试路径补全")
            return self._handle_with_path_completion(question, intent, entities)

        if not query_result:
            logger.info("查询无结果，尝试路径推理补全")
            return self._handle_with_path_completion(question, intent, entities)

        formatted_answer = self.answer_processor.format_answer(
            question=question,
            query_result=query_result,
            query_info=query_info,
            entities=entities,
            intent=intent
        )

        return {
            **formatted_answer,
            "intent": {
                "predicted": intent,
                "confidence": intent_confidence,
                "all_predictions": []
            },
            "entities": entities,
            "query_info": query_info
        }

    def _handle_multi_hop_query(
        self,
        question: str,
        intent: str,
        entities: list
    ) -> Dict[str, Any]:
        entity = entities[0]
        entity_name = entity["canonical_name"]

        intents = self._extract_multiple_intents(question)
        relation_chain = []
        for i in intents:
            if i in self.cypher_generator.template_generator.relation_map:
                relation_chain.append(
                    self.cypher_generator.template_generator.relation_map[i]["relation"]
                )

        if len(relation_chain) < 2:
            relation_chain = ["HAS_SYMPTOM", "USES_DRUG"]

        logger.info(f"多跳推理(含补全): {entity_name}, relations={relation_chain}")

        path_result = self.path_reasoner.multi_hop_with_completion(
            start_entity=entity_name,
            relation_chain=relation_chain
        )

        if path_result["status"] == "strict_match":
            formatted = self.answer_processor.format_answer(
                question=question,
                query_result=path_result["results"],
                query_info={"query_type": "multi_hop", "start_entity": entity_name, "relations": relation_chain},
                entities=entities,
                intent="multi_hop"
            )
        elif path_result["status"] == "relaxed_match":
            formatted = self.answer_processor.format_answer(
                question=question,
                query_result=path_result["results"],
                query_info={
                    "query_type": "multi_hop",
                    "start_entity": entity_name,
                    "relations": relation_chain,
                    "completion_used": True,
                    "completion_type": "relation_skip"
                },
                entities=entities,
                intent="multi_hop"
            )
        else:
            query_info = self.cypher_generator.generate(
                question=question,
                intent=intent if intent else "multi_hop",
                entities=entities,
                use_seq2seq=False
            )

            cypher = query_info.get("cypher")
            parameters = query_info.get("parameters", {})

            query_result = self.neo4j_client.execute_query(cypher, parameters)

            formatted = self.answer_processor.format_answer(
                question=question,
                query_result=query_result,
                query_info=query_info,
                entities=entities,
                intent="multi_hop"
            )

        return {
            **formatted,
            "intent": {
                "predicted": "multi_hop",
                "confidence": 0.7,
                "relations": relation_chain
            },
            "entities": entities,
            "path_reasoning": path_result
        }

    def _handle_with_path_completion(
        self,
        question: str,
        intent: str,
        entities: list
    ) -> Dict[str, Any]:
        entity_name = entities[0]["canonical_name"]

        target_relation = None
        target_type = None
        if intent in self.cypher_generator.template_generator.relation_map:
            info = self.cypher_generator.template_generator.relation_map[intent]
            target_relation = info["relation"]
            target_type = info["target"]

        logger.info(f"缺失节点跳跃查询: {entity_name}, relation={target_relation}, type={target_type}")

        hop_result = self.path_reasoner.missing_node_hop_query(
            start_entity=entity_name,
            target_relation=target_relation,
            target_entity_type=target_type
        )

        if hop_result["status"] == "success" and hop_result["results"]:
            formatted = self.answer_processor.format_answer(
                question=question,
                query_result=hop_result["results"],
                query_info={
                    "query_type": "missing_node_hop",
                    "entity": entity_name,
                    "target_relation": target_relation,
                    "target_type": target_type,
                    "hop_distribution": hop_result.get("hop_distribution", {})
                },
                entities=entities,
                intent=intent
            )

            return {
                **formatted,
                "intent": {"predicted": intent, "confidence": 0.6},
                "entities": entities,
                "path_completion": hop_result
            }

        return {
            "question": question,
            "answer": "抱歉，通过路径补全也未找到相关答案。",
            "has_answer": False,
            "intent": {"predicted": intent, "confidence": 0.3},
            "entities": entities,
            "path_completion": hop_result
        }

    def _handle_fuzzy_query(
        self,
        question: str,
        entities: list = None
    ) -> Dict[str, Any]:
        if entities and len(entities) > 0:
            search_term = entities[0]["canonical_name"]
        else:
            search_term = question.replace("什么", "").replace("哪些", "").replace("？", "").replace("?", "")
            search_term = search_term.strip()[:10]

        logger.info(f"模糊查询: {search_term}")

        query_info = self.cypher_generator.generate(
            question=question,
            intent="fuzzy_query",
            entities=entities or [{"canonical_name": search_term, "text": search_term, "type": ""}],
            use_seq2seq=False,
        )

        cypher = query_info.get("cypher")
        parameters = query_info.get("parameters", {})

        query_result = self.neo4j_client.execute_query(cypher, parameters)

        formatted_answer = self.answer_processor.format_answer(
            question=question,
            query_result=query_result,
            query_info=query_info,
            entities=entities or [],
            intent="fuzzy_query"
        )

        return {
            **formatted_answer,
            "intent": {
                "predicted": "fuzzy_query",
                "confidence": 0.6
            },
            "entities": entities or [],
            "query_info": query_info
        }

    def submit_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"收到用户反馈: rating={feedback.get('rating')}")
        return self.incremental_learner.process_feedback(feedback)

    def get_visualization(
        self,
        center_entity: str,
        depth: int = 2,
        answer_result: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        logger.info(f"获取可视化: center={center_entity}")

        if answer_result:
            return self.graph_visualizer.get_visualization_with_answer(
                center_entity=center_entity,
                answer_result=answer_result,
                depth=depth
            )

        return self.graph_visualizer.get_subgraph(center_entity, depth)

    def get_full_graph_visualization(self, limit: int = 200) -> Dict[str, Any]:
        return self.graph_visualizer.get_full_graph(limit)

    def get_entity_neighborhood_vis(
        self,
        entity_name: str,
        relation_filter: str = None,
        direction: str = "both"
    ) -> Dict[str, Any]:
        return self.graph_visualizer.get_entity_neighborhood(
            entity_name, relation_filter, direction
        )

    def path_completion_query(
        self,
        entity1: str,
        entity2: str,
        known_intermediates: list = None,
        max_hops: int = 5
    ) -> Dict[str, Any]:
        return self.path_reasoner.path_completion(
            start_entity=entity1,
            end_entity=entity2,
            max_hops=max_hops,
            known_intermediates=known_intermediates
        )

    def missing_node_hop(
        self,
        start_entity: str,
        target_relation: str = None,
        target_entity_type: str = None,
        max_hops: int = 4
    ) -> Dict[str, Any]:
        return self.path_reasoner.missing_node_hop_query(
            start_entity=start_entity,
            target_relation=target_relation,
            target_entity_type=target_entity_type,
            max_hops=max_hops
        )

    def get_path_between_entities(
        self,
        entity1: str,
        entity2: str,
        max_hops: int = 5
    ) -> Dict[str, Any]:
        return self.path_reasoner.find_all_paths_between(
            entity1=entity1,
            entity2=entity2,
            max_hops=max_hops
        )

    def get_entity_details(self, entity_name: str) -> Dict[str, Any]:
        query_info = self.cypher_generator.generate(
            question=f"查询{entity_name}的详情",
            intent="entity_details",
            entities=[{"canonical_name": entity_name, "text": entity_name, "type": "Unknown"}],
            use_seq2seq=False,
        )

        cypher = query_info.get("cypher")
        parameters = query_info.get("parameters", {})

        query_result = self.neo4j_client.execute_query(cypher, parameters)

        return self.answer_processor.format_answer(
            question=f"查询{entity_name}的详情",
            query_result=query_result,
            query_info=query_info,
            entities=[{"canonical_name": entity_name, "type": "Unknown"}],
            intent="entity_details"
        )

    def fuzzy_match_detail(self, text: str) -> Dict[str, Any]:
        return self.entity_extractor.fuzzy_match_with_detail(text)

    def get_learning_stats(self) -> Dict[str, Any]:
        return self.incremental_learner.get_learning_stats()

    def batch_process_feedback(self) -> Dict[str, Any]:
        return self.incremental_learner.batch_process_unprocessed()

    def _is_multi_hop_question(self, question: str) -> bool:
        multi_hop_keywords = ["然后", "接着", "之后", "同时", "以及", "还有", "分别"]
        for keyword in multi_hop_keywords:
            if keyword in question:
                return True
        return False

    def _extract_multiple_intents(self, question: str) -> list:
        all_intents = []
        question_parts = self._split_question(question)

        for part in question_parts:
            result = self.intent_classifier.predict(part)
            all_intents.append(result["predicted_intent"])

        return list(set(all_intents))

    def _split_question(self, question: str) -> list:
        separators = ["然后", "接着", "之后", "同时", "以及", "还有", "，", "；", ";"]
        parts = [question]

        for sep in separators:
            new_parts = []
            for p in parts:
                new_parts.extend(p.split(sep))
            parts = new_parts

        return [p.strip() for p in parts if p.strip()]

    def close(self):
        self.neo4j_client.close()
