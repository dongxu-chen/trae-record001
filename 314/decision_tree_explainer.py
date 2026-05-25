import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class DecisionNodeType(Enum):
    ROOT = 'root'
    MODULE = 'module'
    SUBMODULE = 'submodule'
    FEATURE = 'feature'
    EVIDENCE = 'evidence'
    THRESHOLD = 'threshold'


@dataclass
class DecisionNode:
    node_id: str
    node_type: DecisionNodeType
    name: str
    description: str
    value: float
    weight: float
    contribution: float
    threshold: Optional[float] = None
    condition: Optional[str] = None
    children: List['DecisionNode'] = field(default_factory=list)
    parent_id: Optional[str] = None
    evidence: List[str] = field(default_factory=list)


@dataclass
class DecisionPath:
    path_id: str
    nodes: List[DecisionNode]
    final_score: float
    total_contribution: float
    description: str


@dataclass
class TreeExplanationResult:
    root_node: DecisionNode
    all_paths: List[DecisionPath]
    feature_contributions: Dict[str, float]
    decision_rules: List[str]
    visualization_data: Dict
    summary: Dict


class DecisionTreeExplainer:
    def __init__(self):
        self._init_thresholds()
        self._init_node_descriptions()
    
    def _init_thresholds(self):
        self.thresholds = {
            'excellent': 0.8,
            'good': 0.7,
            'above_average': 0.6,
            'average': 0.5,
            'below_average': 0.4,
            'poor': 0.3,
            'critical': 0.2
        }
        
        self.grade_thresholds = [
            (0.9, 'S', '优秀'),
            (0.8, 'A', '良好'),
            (0.7, 'B', '较好'),
            (0.6, 'C', '一般'),
            (0.5, 'D', '较差'),
            (0.0, 'F', '差')
        ]
    
    def _init_node_descriptions(self):
        self.module_descriptions = {
            'text_quality': {
                'name': '文本质量',
                'description': '评估评论文本的内在质量',
                'submodules': {
                    'usefulness': {
                        'name': '有用性',
                        'description': '评论的信息含量和实用价值',
                        'features': ['text_length', 'detail_keywords', 'numeric_descriptions', 'sentence_count']
                    },
                    'authenticity': {
                        'name': '真实性',
                        'description': '评论的真实可信度',
                        'features': ['template_detection', 'character_repetition', 'emotional_intensity', 'exclamation_count']
                    },
                    'completeness': {
                        'name': '完整性',
                        'description': '评论覆盖的评价维度',
                        'features': ['aspect_coverage', 'aspect_depth', 'product_quality', 'appearance', 'functionality', 'service', 'logistics', 'price']
                    }
                }
            },
            'knowledge_graph': {
                'name': '知识图谱',
                'description': '基于语义结构的事实性评估',
                'submodules': {
                    'fact_verification': {
                        'name': '事实验证',
                        'description': '与事实库的一致性',
                        'features': ['negation_detection', 'intensifier_detection', 'measurement_entities', 'known_products', 'known_brands']
                    },
                    'entity_diversity': {
                        'name': '实体多样性',
                        'description': '提取实体的丰富程度',
                        'features': ['entity_count', 'entity_type_count', 'entropy', 'quantity_score']
                    },
                    'relation_quality': {
                        'name': '关系质量',
                        'description': '语义关系的数量和质量',
                        'features': ['relation_count', 'predicate_diversity', 'avg_confidence']
                    }
                }
            },
            'user_reputation': {
                'name': '用户信誉',
                'description': '发布用户的历史信用评估',
                'submodules': {
                    'trustworthiness': {
                        'name': '可信度',
                        'description': '用户的可信程度',
                        'features': ['report_rate', 'verified_status', 'account_age', 'user_level', 'historical_quality']
                    },
                    'influence': {
                        'name': '影响力',
                        'description': '用户在社区的影响力',
                        'features': ['total_likes', 'avg_likes_per_comment', 'total_comments']
                    },
                    'consistency': {
                        'name': '一致性',
                        'description': '用户评价的稳定性',
                        'features': ['rating_consistency', 'length_consistency', 'quality_consistency']
                    },
                    'risk': {
                        'name': '风险',
                        'description': '用户的风险程度(越低越好)',
                        'features': ['report_risk', 'age_risk', 'report_count_risk', 'burst_risk']
                    }
                }
            }
        }
    
    def explain(
        self,
        scoring_result: Any,
        scoring_weights: Dict,
        show_path: bool = True
    ) -> TreeExplanationResult:
        root_node = self._build_decision_tree(scoring_result, scoring_weights)
        all_paths = self._extract_decision_paths(root_node)
        feature_contributions = self._calculate_feature_contributions(root_node)
        decision_rules = self._generate_decision_rules(root_node, scoring_result.final_score)
        visualization_data = self._prepare_visualization_data(root_node, all_paths, feature_contributions)
        summary = self._generate_summary(scoring_result, root_node, feature_contributions)
        
        return TreeExplanationResult(
            root_node=root_node,
            all_paths=all_paths,
            feature_contributions=feature_contributions,
            decision_rules=decision_rules,
            visualization_data=visualization_data,
            summary=summary
        )
    
    def _build_decision_tree(self, scoring_result: Any, scoring_weights: Dict) -> DecisionNode:
        final_score = scoring_result.final_score
        
        root_node = DecisionNode(
            node_id='root',
            node_type=DecisionNodeType.ROOT,
            name='最终评分',
            description=f'综合评分为 {final_score:.4f}，等级为 {scoring_result.score_grade}',
            value=final_score,
            weight=1.0,
            contribution=final_score,
            threshold=None,
            condition=None
        )
        
        text_quality_node = self._build_module_node(
            'text_quality',
            scoring_result.text_quality,
            scoring_weights.get('text_quality', 0.45),
            parent_id='root'
        )
        
        kg_node = self._build_module_node(
            'knowledge_graph',
            scoring_result.knowledge_graph,
            scoring_weights.get('knowledge_graph', 0.25),
            parent_id='root'
        )
        
        rep_node = self._build_module_node(
            'user_reputation',
            scoring_result.user_reputation,
            scoring_weights.get('user_reputation', 0.30),
            parent_id='root'
        )
        
        root_node.children = [text_quality_node, kg_node, rep_node]
        
        return root_node
    
    def _build_module_node(
        self,
        module_key: str,
        module_result: Any,
        module_weight: float,
        parent_id: str
    ) -> DecisionNode:
        module_info = self.module_descriptions.get(module_key, {})
        module_name = module_info.get('name', module_key)
        
        if module_key == 'text_quality':
            module_value = module_result.overall_text_score
            submodules_data = {
                'usefulness': {
                    'score': module_result.usefulness_score,
                    'evidence': module_result.usefulness_evidence
                },
                'authenticity': {
                    'score': module_result.authenticity_score,
                    'evidence': module_result.authenticity_evidence
                },
                'completeness': {
                    'score': module_result.completeness_score,
                    'evidence': module_result.completeness_evidence
                }
            }
        elif module_key == 'knowledge_graph':
            module_value = module_result.overall_kg_score
            submodules_data = {
                'fact_verification': {
                    'score': module_result.fact_verification_score,
                    'evidence': module_result.evidence[:5]
                },
                'entity_diversity': {
                    'score': module_result.entity_diversity_score,
                    'evidence': [f'提取到{len(module_result.entities)}个实体，涵盖{len(set(e.type for e in module_result.entities))}种类型']
                },
                'relation_quality': {
                    'score': module_result.relation_quality_score,
                    'evidence': [f'提取到{len(module_result.relations)}个语义关系']
                }
            }
        else:
            module_value = module_result.overall_reputation_score
            submodules_data = {
                'trustworthiness': {
                    'score': module_result.trustworthiness_score,
                    'evidence': list(module_result.detailed_metrics.get('trustworthiness', {}).get('components', {}).keys())
                },
                'influence': {
                    'score': module_result.influence_score,
                    'evidence': list(module_result.detailed_metrics.get('influence', {}).get('components', {}).keys())
                },
                'consistency': {
                    'score': module_result.consistency_score,
                    'evidence': list(module_result.detailed_metrics.get('consistency', {}).get('components', {}).keys())
                },
                'risk': {
                    'score': module_result.risk_score,
                    'evidence': list(module_result.detailed_metrics.get('risk', {}).get('components', {}).keys())
                }
            }
        
        contribution = module_value * module_weight
        
        module_node = DecisionNode(
            node_id=f'module_{module_key}',
            node_type=DecisionNodeType.MODULE,
            name=module_name,
            description=module_info.get('description', ''),
            value=module_value,
            weight=module_weight,
            contribution=contribution,
            condition=f'权重: {module_weight:.2%}',
            parent_id=parent_id
        )
        
        submodule_config = module_info.get('submodules', {})
        submodule_weights = self._get_submodule_weights(module_key)
        
        for submodule_key, submodule_data in submodules_data.items():
            submodule_info = submodule_config.get(submodule_key, {})
            submodule_weight = submodule_weights.get(submodule_key, 0.25)
            submodule_node = self._build_submodule_node(
                submodule_key,
                submodule_data['score'],
                submodule_weight,
                submodule_info,
                submodule_data.get('evidence', []),
                parent_id=f'module_{module_key}'
            )
            module_node.children.append(submodule_node)
        
        return module_node
    
    def _get_submodule_weights(self, module_key: str) -> Dict[str, float]:
        weights_map = {
            'text_quality': {
                'usefulness': 0.35,
                'authenticity': 0.35,
                'completeness': 0.30
            },
            'knowledge_graph': {
                'fact_verification': 0.40,
                'entity_diversity': 0.30,
                'relation_quality': 0.30
            },
            'user_reputation': {
                'trustworthiness': 0.40,
                'influence': 0.30,
                'consistency': 0.20,
                'risk': 0.10
            }
        }
        return weights_map.get(module_key, {})
    
    def _build_submodule_node(
        self,
        submodule_key: str,
        submodule_value: float,
        submodule_weight: float,
        submodule_info: Dict,
        evidence: List[str],
        parent_id: str
    ) -> DecisionNode:
        submodule_name = submodule_info.get('name', submodule_key)
        submodule_description = submodule_info.get('description', '')
        
        contribution = submodule_value * submodule_weight
        
        condition = self._get_condition_description(submodule_value)
        threshold = self._get_relevant_threshold(submodule_value)
        
        submodule_node = DecisionNode(
            node_id=f'submodule_{submodule_key}',
            node_type=DecisionNodeType.SUBMODULE,
            name=submodule_name,
            description=submodule_description,
            value=submodule_value,
            weight=submodule_weight,
            contribution=contribution,
            threshold=threshold,
            condition=condition,
            evidence=[str(e) for e in evidence[:3]],
            parent_id=parent_id
        )
        
        features = submodule_info.get('features', [])
        for idx, feature in enumerate(features):
            feature_node = self._build_feature_node(
                feature,
                submodule_value,
                submodule_weight / max(len(features), 1),
                parent_id=f'submodule_{submodule_key}'
            )
            submodule_node.children.append(feature_node)
        
        return submodule_node
    
    def _build_feature_node(
        self,
        feature_key: str,
        feature_value: float,
        feature_weight: float,
        parent_id: str
    ) -> DecisionNode:
        feature_names = {
            'text_length': '文本长度',
            'detail_keywords': '细节关键词',
            'numeric_descriptions': '数字描述',
            'sentence_count': '句子数量',
            'template_detection': '模板检测',
            'character_repetition': '字符重复',
            'emotional_intensity': '情感强度',
            'exclamation_count': '感叹号数量',
            'aspect_coverage': '维度覆盖',
            'aspect_depth': '维度深度',
            'product_quality': '产品质量',
            'appearance': '外观设计',
            'functionality': '功能体验',
            'service': '客户服务',
            'logistics': '物流配送',
            'price': '价格性价比',
            'negation_detection': '否定检测',
            'intensifier_detection': '程度词检测',
            'measurement_entities': '度量实体',
            'known_products': '已知产品',
            'known_brands': '已知品牌',
            'entity_count': '实体数量',
            'entity_type_count': '实体类型数',
            'entropy': '信息熵',
            'quantity_score': '数量得分',
            'relation_count': '关系数量',
            'predicate_diversity': '谓语多样性',
            'avg_confidence': '平均置信度',
            'report_rate': '举报率',
            'verified_status': '认证状态',
            'account_age': '账号年龄',
            'user_level': '用户等级',
            'historical_quality': '历史质量',
            'total_likes': '总点赞数',
            'avg_likes_per_comment': '平均点赞',
            'total_comments': '总评论数',
            'rating_consistency': '评分一致性',
            'length_consistency': '长度一致性',
            'quality_consistency': '质量一致性',
            'report_risk': '举报风险',
            'age_risk': '年龄风险',
            'report_count_risk': '举报次数风险',
            'burst_risk': '爆发发布风险'
        }
        
        feature_name = feature_names.get(feature_key, feature_key)
        
        contribution = feature_value * feature_weight
        condition = self._get_condition_description(feature_value)
        
        return DecisionNode(
            node_id=f'feature_{feature_key}',
            node_type=DecisionNodeType.FEATURE,
            name=feature_name,
            description=f'{feature_name}对评分的贡献',
            value=feature_value,
            weight=feature_weight,
            contribution=contribution,
            condition=condition,
            parent_id=parent_id
        )
    
    def _get_condition_description(self, value: float) -> str:
        if value >= self.thresholds['excellent']:
            return f'优秀 (≥{self.thresholds["excellent"]})'
        elif value >= self.thresholds['good']:
            return f'良好 (≥{self.thresholds["good"]})'
        elif value >= self.thresholds['above_average']:
            return f'较好 (≥{self.thresholds["above_average"]})'
        elif value >= self.thresholds['average']:
            return f'中等 (≥{self.thresholds["average"]})'
        elif value >= self.thresholds['below_average']:
            return f'一般 (≥{self.thresholds["below_average"]})'
        elif value >= self.thresholds['poor']:
            return f'较差 (≥{self.thresholds["poor"]})'
        else:
            return f'差 (<{self.thresholds["poor"]})'
    
    def _get_relevant_threshold(self, value: float) -> float:
        for threshold, _, _ in self.grade_thresholds:
            if value >= threshold:
                return threshold
        return 0.0
    
    def _extract_decision_paths(self, root_node: DecisionNode) -> List[DecisionPath]:
        paths = []
        
        def traverse(node: DecisionNode, current_path: List[DecisionNode]):
            current_path.append(node)
            
            if not node.children:
                path_id = f'path_{len(paths)}'
                total_contribution = sum(n.contribution for n in current_path[1:])
                description = ' → '.join(f'{n.name}({n.value:.3f})' for n in current_path)
                
                paths.append(DecisionPath(
                    path_id=path_id,
                    nodes=current_path.copy(),
                    final_score=root_node.value,
                    total_contribution=total_contribution,
                    description=description
                ))
            else:
                for child in node.children:
                    traverse(child, current_path)
            
            current_path.pop()
        
        traverse(root_node, [])
        return paths
    
    def _calculate_feature_contributions(self, root_node: DecisionNode) -> Dict[str, float]:
        contributions = defaultdict(float)
        
        def collect_contributions(node: DecisionNode):
            if node.node_type in [DecisionNodeType.FEATURE, DecisionNodeType.SUBMODULE, DecisionNodeType.MODULE]:
                contributions[node.name] = node.contribution
            
            for child in node.children:
                collect_contributions(child)
        
        collect_contributions(root_node)
        return dict(sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True))
    
    def _generate_decision_rules(self, root_node: DecisionNode, final_score: float) -> List[str]:
        rules = []
        
        for threshold, grade, grade_cn in self.grade_thresholds:
            if final_score >= threshold:
                rules.append(f"IF 最终评分 >= {threshold:.2f} THEN 等级 = {grade} ({grade_cn})")
                break
        
        for child in root_node.children:
            condition = self._get_condition_description(child.value)
            impact = '正面影响' if child.contribution > 0.2 else '负面影响' if child.contribution < 0.1 else '中等影响'
            rules.append(f"IF {child.name} = {condition} THEN {impact} (+{child.contribution:.4f})")
        
        def collect_rules(node: DecisionNode, depth: int = 0):
            if depth >= 2:
                return
            
            for child in node.children:
                condition = self._get_condition_description(child.value)
                rules.append(f"    IF {child.name} = {condition} THEN 贡献 = {child.contribution:.4f}")
                collect_rules(child, depth + 1)
        
        collect_rules(root_node, 0)
        
        return rules
    
    def _prepare_visualization_data(
        self,
        root_node: DecisionNode,
        paths: List[DecisionPath],
        contributions: Dict[str, float]
    ) -> Dict:
        nodes = []
        links = []
        
        def build_vis_data(node: DecisionNode):
            color = self._get_node_color(node.value, node.node_type)
            size = 20 + node.contribution * 80
            
            nodes.append({
                'id': node.node_id,
                'name': node.name,
                'value': node.value,
                'weight': node.weight,
                'contribution': node.contribution,
                'type': node.node_type.value,
                'color': color,
                'size': size,
                'condition': node.condition
            })
            
            for child in node.children:
                links.append({
                    'source': node.node_id,
                    'target': child.node_id,
                    'value': child.contribution,
                    'weight': child.weight
                })
                build_vis_data(child)
        
        build_vis_data(root_node)
        
        top_contributors = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
        
        sankey_data = self._prepare_sankey_data(root_node)
        
        return {
            'tree_nodes': nodes,
            'tree_links': links,
            'top_contributors': [
                {'name': name, 'contribution': value}
                for name, value in top_contributors
            ],
            'sankey_data': sankey_data,
            'grade_boundaries': self.grade_thresholds
        }
    
    def _get_node_color(self, value: float, node_type: DecisionNodeType) -> str:
        if node_type == DecisionNodeType.ROOT:
            return '#1f77b4'
        elif node_type == DecisionNodeType.MODULE:
            return '#2ca02c' if value >= 0.6 else '#ff7f0e' if value >= 0.4 else '#d62728'
        elif node_type == DecisionNodeType.SUBMODULE:
            return '#9467bd' if value >= 0.6 else '#ffbb78' if value >= 0.4 else '#ff9896'
        else:
            return '#8c564b' if value >= 0.6 else '#c5b0d5' if value >= 0.4 else '#c49c94'
    
    def _prepare_sankey_data(self, root_node: DecisionNode) -> Dict:
        sankey_nodes = []
        sankey_links = []
        node_map = {}
        
        def add_sankey_node(node: DecisionNode, level: int) -> int:
            if node.node_id in node_map:
                return node_map[node.node_id]
            
            idx = len(sankey_nodes)
            sankey_nodes.append({
                'name': node.name,
                'level': level,
                'value': node.contribution
            })
            node_map[node.node_id] = idx
            
            return idx
        
        def add_sankey_links(node: DecisionNode, level: int = 0):
            source_idx = add_sankey_node(node, level)
            
            for child in node.children:
                target_idx = add_sankey_node(child, level + 1)
                sankey_links.append({
                    'source': source_idx,
                    'target': target_idx,
                    'value': child.contribution
                })
                add_sankey_links(child, level + 1)
        
        add_sankey_links(root_node)
        
        return {
            'nodes': sankey_nodes,
            'links': sankey_links
        }
    
    def _generate_summary(
        self,
        scoring_result: Any,
        root_node: DecisionNode,
        contributions: Dict[str, float]
    ) -> Dict:
        positive_contributors = [k for k, v in contributions.items() if v >= 0.05]
        negative_contributors = [k for k, v in contributions.items() if v < 0.03]
        
        sorted_contributions = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        top_3_positive = sorted_contributions[:3]
        bottom_3_negative = sorted_contributions[-3:]
        
        return {
            'final_score': scoring_result.final_score,
            'grade': scoring_result.score_grade,
            'percentile': scoring_result.score_percentile,
            'total_modules': 3,
            'total_submodules': len([c for c in root_node.children for cc in c.children]),
            'total_features': sum(len(cc.children) for c in root_node.children for cc in c.children),
            'top_positive_contributors': [
                {'name': name, 'contribution': value}
                for name, value in top_3_positive
            ],
            'top_negative_contributors': [
                {'name': name, 'contribution': value}
                for name, value in bottom_3_negative
            ],
            'strengths': positive_contributors[:5],
            'weaknesses': negative_contributors[:5],
            'interpretation': scoring_result.interpretation
        }
    
    def print_decision_tree(self, result: TreeExplanationResult, max_depth: int = 3, show_contributions: bool = True):
        print("=" * 80)
        print("                    评分决策树")
        print("=" * 80)
        print()
        
        def print_node(node: DecisionNode, level: int = 0, is_last: bool = True):
            if level > max_depth:
                return
            
            prefix = "    " * level
            branch = "└── " if is_last else "├── "
            
            value_str = f"{node.value:.4f}"
            contrib_str = f" (+{node.contribution:.4f})" if show_contributions else ""
            condition_str = f" [{node.condition}]" if node.condition else ""
            
            color_code = self._get_color_code(node.value)
            reset_code = "\033[0m"
            
            print(f"{prefix}{branch}{color_code}{node.name}: {value_str}{contrib_str}{condition_str}{reset_code}")
            
            if node.evidence and level >= 1:
                for ev in node.evidence[:2]:
                    ev_prefix = "    " * (level + 1)
                    print(f"{ev_prefix}  • {str(ev)[:60]}...")
            
            for i, child in enumerate(node.children):
                is_last_child = i == len(node.children) - 1
                print_node(child, level + 1, is_last_child)
        
        print_node(result.root_node)
        print()
    
    def _get_color_code(self, value: float) -> str:
        if value >= 0.7:
            return "\033[92m"
        elif value >= 0.5:
            return "\033[93m"
        else:
            return "\033[91m"
    
    def print_decision_paths(self, result: TreeExplanationResult, top_n: int = 5):
        print("=" * 80)
        print("                    主要决策路径")
        print("=" * 80)
        print()
        
        sorted_paths = sorted(result.all_paths, key=lambda p: abs(p.total_contribution), reverse=True)
        
        for idx, path in enumerate(sorted_paths[:top_n], 1):
            print(f"路径 {idx}: {path.description}")
            print(f"  总贡献: {path.total_contribution:.4f}")
            print()
    
    def print_feature_contributions(self, result: TreeExplanationResult, top_n: int = 15):
        print("=" * 80)
        print("                    特征贡献度排行")
        print("=" * 80)
        print()
        print(f"{'排名':<6} {'特征名称':<20} {'贡献度':<12} {'占比':<10} {'柱状图'}")
        print("-" * 80)
        
        total = sum(abs(v) for v in result.feature_contributions.values())
        
        sorted_items = sorted(result.feature_contributions.items(), key=lambda x: x[1], reverse=True)
        
        for idx, (name, value) in enumerate(sorted_items[:top_n], 1):
            percentage = (value / total * 100) if total > 0 else 0
            bar_length = int(abs(value) * 50)
            bar = '█' * bar_length
            color = '\033[92m' if value >= 0.05 else '\033[91m' if value < 0.03 else '\033[93m'
            reset = '\033[0m'
            
            print(f"{idx:<6} {name[:18]:<20} {value:<12.4f} {percentage:<9.1f}% {color}{bar}{reset}")
        
        print()
    
    def print_decision_rules(self, result: TreeExplanationResult):
        print("=" * 80)
        print("                    决策规则")
        print("=" * 80)
        print()
        
        for idx, rule in enumerate(result.decision_rules[:15], 1):
            print(f"  {idx:2d}. {rule}")
        
        print()
    
    def export_to_json(self, result: TreeExplanationResult, file_path: str):
        def node_to_dict(node: DecisionNode) -> Dict:
            return {
                'node_id': node.node_id,
                'node_type': node.node_type.value,
                'name': node.name,
                'description': node.description,
                'value': node.value,
                'weight': node.weight,
                'contribution': node.contribution,
                'threshold': node.threshold,
                'condition': node.condition,
                'evidence': node.evidence,
                'children': [node_to_dict(child) for child in node.children]
            }
        
        paths_dict = [
            {
                'path_id': p.path_id,
                'description': p.description,
                'final_score': p.final_score,
                'total_contribution': p.total_contribution,
                'nodes': [
                    {
                        'node_id': n.node_id,
                        'name': n.name,
                        'value': n.value,
                        'contribution': n.contribution
                    }
                    for n in p.nodes
                ]
            }
            for p in result.all_paths
        ]
        
        export_data = {
            'decision_tree': node_to_dict(result.root_node),
            'decision_paths': paths_dict,
            'feature_contributions': result.feature_contributions,
            'decision_rules': result.decision_rules,
            'visualization_data': result.visualization_data,
            'summary': result.summary
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return file_path
