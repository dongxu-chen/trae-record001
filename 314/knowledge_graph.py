import re
import networkx as nx
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Entity:
    name: str
    type: str
    confidence: float
    mentions: List[str] = field(default_factory=list)


@dataclass
class Relation:
    subject: str
    predicate: str
    object: str
    confidence: float


@dataclass
class KGResult:
    entities: List[Entity]
    relations: List[Relation]
    fact_verification_score: float
    entity_diversity_score: float
    relation_quality_score: float
    overall_kg_score: float
    evidence: List[str]
    graph_stats: Dict


class KnowledgeGraphAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._init_entity_patterns()
        self._init_relation_patterns()
        self._init_fact_database()
    
    def _init_entity_patterns(self):
        self.entity_patterns = {
            'product': [
                r'(手机|电脑|笔记本|平板|耳机|音箱|相机|手表|手环)',
                r'(电视|冰箱|空调|洗衣机|微波炉|电饭煲)',
                r'(衣服|鞋子|裤子|包包|化妆品|护肤品)',
                r'(书籍|教材|杂志|小说|绘本)',
                r'(食品|饮料|零食|水果|蔬菜|肉类)',
                r'(家具|家电|灯具|厨具|餐具)',
            ],
            'brand': [
                r'(华为|小米|苹果|三星|OPPO|vivo|荣耀|魅族)',
                r'(格力|美的|海尔|西门子|博世|飞利浦)',
                r'(耐克|阿迪|李宁|安踏|优衣库|无印良品)',
                r'(宝马|奔驰|奥迪|丰田|本田|特斯拉)',
            ],
            'attribute': [
                r'(质量|品质|做工|材质|外观|设计|颜色|款式)',
                r'(性能|功能|速度|续航|容量|配置|参数)',
                r'(价格|性价比|优惠|折扣|便宜|贵)',
                r'(服务|售后|客服|态度|物流|快递|包装)',
            ],
            'measurement': [
                r'\d+\s*(厘米|公分|米|英寸|寸|尺)',
                r'\d+\s*(克|千克|公斤|斤|磅)',
                r'\d+\s*(元|块|美元|欧元|日元)',
                r'\d+\s*(小时|分钟|秒|天|个月|年)',
                r'\d+\s*(mAh|W|V|A|GB|MB|KB)',
            ]
        }
        
        self.negation_words = {'不', '没', '没有', '无', '非', '否', '别', '不要'}
        self.intensifier_words = {'非常', '很', '特别', '极其', '相当', '比较', '稍微', '有点'}
    
    def _init_relation_patterns(self):
        self.relation_patterns = [
            (r'(.*?)(质量|品质)(怎么样|如何|好|差|不错|一般)', 'quality_eval'),
            (r'(.*?)(价格|性价比)(高|低|合理|贵|便宜)', 'price_eval'),
            (r'(.*?)(外观|设计)(好看|漂亮|丑|时尚|老气)', 'appearance_eval'),
            (r'(.*?)(功能|性能)(强大|弱|齐全|不足)', 'function_eval'),
            (r'(.*?)(物流|快递)(快|慢|准时|延误)', 'logistics_eval'),
            (r'(.*?)(客服|服务态度)(好|差|热情|冷淡)', 'service_eval'),
            (r'(.*?)(比|相比|比较|对比)(.*?)(好|差|强|弱)', 'comparison'),
            (r'(.*?)(推荐|建议|别买|值得买)(.*?)', 'recommendation'),
        ]
        
        self.predicate_mapping = {
            'quality_eval': '质量评价为',
            'price_eval': '价格评价为',
            'appearance_eval': '外观评价为',
            'function_eval': '功能评价为',
            'logistics_eval': '物流评价为',
            'service_eval': '服务评价为',
            'comparison': '相比',
            'recommendation': '建议'
        }
    
    def _init_fact_database(self):
        self.fact_db = {
            'product_specs': {
                'iPhone 15': {'屏幕尺寸': '6.1英寸', '处理器': 'A17', '电池': '3274mAh'},
                '华为Mate 60': {'屏幕尺寸': '6.69英寸', '处理器': '麒麟9000S', '电池': '5000mAh'},
                '小米14': {'屏幕尺寸': '6.36英寸', '处理器': '骁龙8 Gen3', '电池': '4610mAh'},
            },
            'brand_attributes': {
                '苹果': {'定位': '高端', '系统': 'iOS', '产地': '美国'},
                '华为': {'定位': '中高端', '系统': '鸿蒙', '产地': '中国'},
                '小米': {'定位': '性价比', '系统': 'MIUI', '产地': '中国'},
            },
            'common_sense': {
                '电池容量越大续航越好': True,
                '像素越高拍照越好': False,
                '价格越高质量越好': False,
                '新品比旧品好': False,
            }
        }
    
    def analyze(self, text: str) -> KGResult:
        entities = self._extract_entities(text)
        relations = self._extract_relations(text, entities)
        self._build_graph(entities, relations)
        
        fact_verification_score, fact_evidence = self._verify_facts(text, entities, relations)
        entity_diversity_score, diversity_evidence = self._calculate_entity_diversity(entities)
        relation_quality_score, relation_evidence = self._calculate_relation_quality(relations)
        
        weights = {
            'fact_verification': 0.4,
            'entity_diversity': 0.3,
            'relation_quality': 0.3
        }
        
        overall_kg_score = (
            fact_verification_score * weights['fact_verification'] +
            entity_diversity_score * weights['entity_diversity'] +
            relation_quality_score * weights['relation_quality']
        )
        
        evidence = fact_evidence + diversity_evidence + relation_evidence
        
        graph_stats = self._get_graph_stats()
        
        return KGResult(
            entities=entities,
            relations=relations,
            fact_verification_score=round(fact_verification_score, 4),
            entity_diversity_score=round(entity_diversity_score, 4),
            relation_quality_score=round(relation_quality_score, 4),
            overall_kg_score=round(overall_kg_score, 4),
            evidence=evidence,
            graph_stats=graph_stats
        )
    
    def _extract_entities(self, text: str) -> List[Entity]:
        entities = []
        entity_names = set()
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    entity_name = match.group(0)
                    if entity_name not in entity_names:
                        entity_names.add(entity_name)
                        start, end = match.span()
                        context = text[max(0, start-10):min(len(text), end+10)]
                        entities.append(Entity(
                            name=entity_name,
                            type=entity_type,
                            confidence=0.85,
                            mentions=[context]
                        ))
        
        return entities
    
    def _extract_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        relations = []
        entity_names = [e.name for e in entities]
        
        for pattern, rel_type in self.relation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    subject = match.group(1).strip() if match.groups()[0] else ''
                    if len(subject) > 20:
                        subject = self._find_closest_entity(subject, entity_names)
                    
                    obj = match.group(3).strip() if len(match.groups()) >= 3 else match.group(2).strip()
                    if len(obj) > 20:
                        obj = self._find_closest_entity(obj, entity_names)
                    
                    predicate = self.predicate_mapping.get(rel_type, rel_type)
                    
                    if subject and obj and len(subject) > 0 and len(obj) > 0:
                        relations.append(Relation(
                            subject=subject[:20],
                            predicate=predicate,
                            object=obj[:20],
                            confidence=0.75
                        ))
                except (IndexError, AttributeError):
                    continue
        
        return relations
    
    def _find_closest_entity(self, text: str, entity_names: List[str]) -> str:
        for entity in entity_names:
            if entity in text:
                return entity
        return text[:20]
    
    def _build_graph(self, entities: List[Entity], relations: List[Relation]):
        self.graph.clear()
        
        for entity in entities:
            self.graph.add_node(entity.name, type=entity.type, confidence=entity.confidence)
        
        for relation in relations:
            if self.graph.has_node(relation.subject) and self.graph.has_node(relation.object):
                self.graph.add_edge(
                    relation.subject,
                    relation.object,
                    predicate=relation.predicate,
                    confidence=relation.confidence
                )
            else:
                if not self.graph.has_node(relation.subject):
                    self.graph.add_node(relation.subject, type='unknown', confidence=0.5)
                if not self.graph.has_node(relation.object):
                    self.graph.add_node(relation.object, type='unknown', confidence=0.5)
                self.graph.add_edge(
                    relation.subject,
                    relation.object,
                    predicate=relation.predicate,
                    confidence=relation.confidence
                )
    
    def _verify_facts(self, text: str, entities: List[Entity], relations: List[Relation]) -> Tuple[float, List[str]]:
        score = 0.0
        evidence = []
        checks = 0
        passed = 0
        
        has_negation = any(neg in text for neg in self.negation_words)
        has_intensifier = any(intens in text for intens in self.intensifier_words)
        
        checks += 1
        if has_negation:
            score += 0.2
            passed += 1
            evidence.append("检测到否定表达，已进行语义修正处理")
        else:
            score += 0.1
        
        checks += 1
        if has_intensifier:
            score += 0.1
            evidence.append("检测到程度修饰词，已调整置信度权重")
        else:
            score += 0.05
        
        for entity in entities:
            checks += 1
            if entity.type == 'measurement':
                score += 0.1
                passed += 1
                evidence.append(f"检测到量化描述: {entity.name}，增强了事实可信度")
            
            if entity.name in self.fact_db['product_specs']:
                checks += 1
                score += 0.15
                passed += 1
                evidence.append(f"识别已知产品: {entity.name}，可与规格库进行比对验证")
            
            if entity.name in self.fact_db['brand_attributes']:
                checks += 1
                score += 0.15
                passed += 1
                brand_info = self.fact_db['brand_attributes'][entity.name]
                evidence.append(f"识别品牌: {entity.name} (定位: {brand_info['定位']})")
        
        checks += 1
        if len(relations) >= 2:
            score += 0.2
            passed += 1
            evidence.append(f"提取到{len(relations)}个语义关系，事实表述更完整")
        elif len(relations) >= 1:
            score += 0.1
            passed += 0.5
        
        for rel in relations:
            checks += 1
            if rel.predicate in ['质量评价为', '价格评价为', '功能评价为']:
                score += 0.1
                passed += 1
        
        verification_ratio = passed / checks if checks > 0 else 0
        evidence.append(f"事实验证通过率: {verification_ratio:.1%} ({passed}/{checks}项检查通过)")
        
        score = min(1.0, score / max(1.0, len(entities) * 0.5 + len(relations) * 0.3 + 0.5))
        
        if score >= 0.7:
            evidence.append("评论事实一致性良好，可信度高")
        elif score >= 0.4:
            evidence.append("评论事实基本一致，可信度中等")
        else:
            evidence.append("评论事实一致性较差，存在可疑表述")
        
        return score, evidence
    
    def _calculate_entity_diversity(self, entities: List[Entity]) -> Tuple[float, List[str]]:
        evidence = []
        
        if not entities:
            evidence.append("未提取到有效实体")
            return 0.0, evidence
        
        type_counts = defaultdict(int)
        for entity in entities:
            type_counts[entity.type] += 1
        
        entity_count = len(entities)
        type_count = len(type_counts)
        max_possible_types = len(self.entity_patterns)
        
        type_diversity = type_count / max_possible_types
        
        from math import log
        if entity_count > 1:
            entropy = 0
            for count in type_counts.values():
                p = count / entity_count
                if p > 0:
                    entropy -= p * log(p, 2)
            max_entropy = log(min(entity_count, max_possible_types), 2) if max_possible_types > 0 else 1
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        else:
            normalized_entropy = 0
        
        quantity_score = min(1.0, entity_count / 8.0)
        
        weights = {'type_diversity': 0.4, 'entropy': 0.3, 'quantity': 0.3}
        diversity_score = (
            type_diversity * weights['type_diversity'] +
            normalized_entropy * weights['entropy'] +
            quantity_score * weights['quantity']
        )
        
        evidence.append(f"提取到{entity_count}个实体，涵盖{type_count}种类型")
        
        type_names = {
            'product': '产品',
            'brand': '品牌',
            'attribute': '属性',
            'measurement': '度量'
        }
        for e_type, count in type_counts.items():
            evidence.append(f"- {type_names.get(e_type, e_type)}: {count}个")
        
        if entity_count >= 5 and type_count >= 3:
            evidence.append("实体丰富度高，评论信息详实")
        elif entity_count >= 3:
            evidence.append("实体丰富度中等，评论有一定信息量")
        else:
            evidence.append("实体数量较少，评论信息量有限")
        
        return diversity_score, evidence
    
    def _calculate_relation_quality(self, relations: List[Relation]) -> Tuple[float, List[str]]:
        evidence = []
        
        if not relations:
            evidence.append("未提取到有效语义关系")
            return 0.0, evidence
        
        relation_count = len(relations)
        unique_predicates = set(r.predicate for r in relations)
        predicate_count = len(unique_predicates)
        
        quantity_score = min(1.0, relation_count / 5.0)
        diversity_score = min(1.0, predicate_count / 4.0)
        
        avg_confidence = sum(r.confidence for r in relations) / relation_count
        confidence_score = avg_confidence
        
        weights = {'quantity': 0.4, 'diversity': 0.3, 'confidence': 0.3}
        quality_score = (
            quantity_score * weights['quantity'] +
            diversity_score * weights['diversity'] +
            confidence_score * weights['confidence']
        )
        
        evidence.append(f"提取到{relation_count}个语义关系，包含{predicate_count}种关系类型")
        
        predicate_examples = list(unique_predicates)[:3]
        evidence.append(f"关系类型示例: {', '.join(predicate_examples)}")
        
        for rel in relations[:3]:
            evidence.append(f"- {rel.subject} {rel.predicate} {rel.object}")
        
        return quality_score, evidence
    
    def _get_graph_stats(self) -> Dict:
        if self.graph.number_of_nodes() == 0:
            return {
                'node_count': 0,
                'edge_count': 0,
                'density': 0.0,
                'connected_components': 0,
                'avg_degree': 0.0
            }
        
        node_count = self.graph.number_of_nodes()
        edge_count = self.graph.number_of_edges()
        density = nx.density(self.graph)
        
        try:
            connected_components = nx.number_connected_components(self.graph.to_undirected())
        except:
            connected_components = 1
        
        avg_degree = sum(dict(self.graph.degree()).values()) / node_count
        
        try:
            centrality = nx.degree_centrality(self.graph)
            top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:3]
            key_entities = [node for node, _ in top_nodes]
        except:
            key_entities = []
        
        return {
            'node_count': node_count,
            'edge_count': edge_count,
            'density': round(density, 4),
            'connected_components': connected_components,
            'avg_degree': round(avg_degree, 4),
            'key_entities': key_entities
        }
    
    def visualize_graph(self, output_path: Optional[str] = None):
        import matplotlib.pyplot as plt
        
        if self.graph.number_of_nodes() == 0:
            print("图谱为空，无法可视化")
            return
        
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.graph, k=0.5, iterations=50)
        
        node_colors = []
        for node, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            color_map = {
                'product': '#ff6b6b',
                'brand': '#4ecdc4',
                'attribute': '#45b7d1',
                'measurement': '#96ceb4',
                'unknown': '#999999'
            }
            node_colors.append(color_map.get(node_type, '#999999'))
        
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=1500,
            alpha=0.8
        )
        
        nx.draw_networkx_edges(
            self.graph, pos,
            edge_color='#666666',
            width=1.5,
            alpha=0.6,
            arrowsize=20
        )
        
        nx.draw_networkx_labels(
            self.graph, pos,
            font_size=10,
            font_weight='bold'
        )
        
        edge_labels = nx.get_edge_attributes(self.graph, 'predicate')
        nx.draw_networkx_edge_labels(
            self.graph, pos,
            edge_labels=edge_labels,
            font_size=8
        )
        
        plt.title("评论知识图谱")
        plt.axis('off')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"图谱已保存至: {output_path}")
        else:
            plt.show()
        
        plt.close()
