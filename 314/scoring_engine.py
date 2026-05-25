import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

from bert_analyzer import BERTTextAnalyzer, TextQualityResult
from knowledge_graph import KnowledgeGraphAnalyzer, KGResult
from user_reputation import UserReputationAnalyzer, UserHistory, ReputationResult
from decision_tree_explainer import DecisionTreeExplainer, TreeExplanationResult
from event_driven_reputation import EventDrivenReputationSystem, EventType, EventSeverity, ReputationEvent, EventProcessingResult
from fake_review_detector import FakeReviewDetector, ReviewForDetection, FakeReviewDetectionResult, GroupDetectionResult
from review_ranking import ReviewRanker, ReviewForRanking, RankingResult, SortStrategy
from trend_monitor import CommentTrendMonitor, TrendAlert, TrendAnalysisResult, AlertSeverity, AlertType


@dataclass
class CommentQualityResult:
    comment_id: str
    user_id: str
    final_score: float
    score_grade: str
    score_percentile: float
    text_quality: TextQualityResult
    knowledge_graph: KGResult
    user_reputation: ReputationResult
    scoring_weights: Dict
    score_breakdown: Dict
    interpretation: Dict
    recommendations: List[str]
    decision_tree_explanation: Optional[TreeExplanationResult] = None
    fake_review_detection: Optional[FakeReviewDetectionResult] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CommentQualityScoringEngine:
    def __init__(self, use_bert_pretrained: bool = False, enable_event_driven: bool = True, enable_fake_detection: bool = True):
        self.bert_analyzer = BERTTextAnalyzer(use_pretrained=use_bert_pretrained)
        self.kg_analyzer = KnowledgeGraphAnalyzer()
        self.reputation_analyzer = UserReputationAnalyzer()
        self.decision_tree_explainer = DecisionTreeExplainer()
        self.event_system = EventDrivenReputationSystem() if enable_event_driven else None
        self.fake_detector = FakeReviewDetector() if enable_fake_detection else None
        self.ranker = ReviewRanker()
        self.trend_monitor = CommentTrendMonitor()
        self.enable_event_driven = enable_event_driven
        self.enable_fake_detection = enable_fake_detection
        self._init_weight_config()
    
    def _init_weight_config(self):
        self.weights = {
            'text_quality': 0.45,
            'knowledge_graph': 0.25,
            'user_reputation': 0.30
        }
        
        self.text_quality_subweights = {
            'usefulness': 0.35,
            'authenticity': 0.35,
            'completeness': 0.30
        }
        
        self.kg_subweights = {
            'fact_verification': 0.40,
            'entity_diversity': 0.30,
            'relation_quality': 0.30
        }
        
        self.reputation_subweights = {
            'trustworthiness': 0.40,
            'influence': 0.30,
            'consistency': 0.20,
            'risk': 0.10
        }
    
    def update_weights(self, weights: Optional[Dict] = None):
        if weights:
            if 'text_quality' in weights:
                self.weights['text_quality'] = weights['text_quality']
            if 'knowledge_graph' in weights:
                self.weights['knowledge_graph'] = weights['knowledge_graph']
            if 'user_reputation' in weights:
                self.weights['user_reputation'] = weights['user_reputation']
        
        total = sum(self.weights.values())
        if total != 1.0:
            for k in self.weights:
                self.weights[k] = round(self.weights[k] / total, 4)
    
    def score_comment(
        self,
        comment_id: str,
        comment_text: str,
        user_history: UserHistory,
        historical_text_scores: Optional[List[float]] = None,
        custom_weights: Optional[Dict] = None,
        generate_decision_tree: bool = True
    ) -> CommentQualityResult:
        if custom_weights:
            original_weights = self.weights.copy()
            self.update_weights(custom_weights)
        
        text_result = self.bert_analyzer.analyze(comment_text)
        kg_result = self.kg_analyzer.analyze(comment_text)
        rep_result = self.reputation_analyzer.analyze(user_history, historical_text_scores)
        
        final_score, score_breakdown = self._calculate_final_score(text_result, kg_result, rep_result)
        
        score_grade = self._get_score_grade(final_score)
        score_percentile = self._calculate_percentile(final_score)
        interpretation = self._generate_interpretation(text_result, kg_result, rep_result, final_score)
        recommendations = self._generate_recommendations(text_result, kg_result, rep_result, final_score)
        
        decision_tree_explanation = None
        if generate_decision_tree:
            temp_result = CommentQualityResult(
                comment_id=comment_id,
                user_id=user_history.user_id,
                final_score=round(final_score, 4),
                score_grade=score_grade,
                score_percentile=round(score_percentile, 4),
                text_quality=text_result,
                knowledge_graph=kg_result,
                user_reputation=rep_result,
                scoring_weights=self.weights.copy(),
                score_breakdown=score_breakdown,
                interpretation=interpretation,
                recommendations=recommendations
            )
            decision_tree_explanation = self.decision_tree_explainer.explain(
                temp_result, self.weights
            )
        
        if self.enable_event_driven:
            event = self.event_system.create_event(
                event_type=EventType.COMMENT_POSTED,
                user_id=user_history.user_id,
                severity=EventSeverity.LOW,
                metadata={
                    'comment_id': comment_id,
                    'text_quality': text_result.overall_text_score,
                    'is_quality_review': final_score >= 0.7
                }
            )
            self.event_system.process_event(event, rep_result.overall_reputation_score)
        
        fake_review_detection = None
        if self.enable_fake_detection:
            metadata = getattr(user_history, 'metadata', {}) or {}
            review_for_detection = ReviewForDetection(
                review_id=comment_id,
                user_id=user_history.user_id,
                product_id=metadata.get('product_id', 'UNKNOWN'),
                content=comment_text,
                rating=metadata.get('rating', 5),
                timestamp=datetime.now(),
                ip_address=metadata.get('ip_address'),
                device_id=metadata.get('device_id'),
                user_account_age_days=user_history.account_age_days,
                user_total_reviews=user_history.total_comments,
                user_average_rating=metadata.get('user_average_rating')
            )
            fake_review_detection = self.fake_detector.detect(review_for_detection)

        if custom_weights:
            self.weights = original_weights
        
        return CommentQualityResult(
            comment_id=comment_id,
            user_id=user_history.user_id,
            final_score=round(final_score, 4),
            score_grade=score_grade,
            score_percentile=round(score_percentile, 4),
            text_quality=text_result,
            knowledge_graph=kg_result,
            user_reputation=rep_result,
            scoring_weights=self.weights.copy(),
            score_breakdown=score_breakdown,
            interpretation=interpretation,
            recommendations=recommendations,
            decision_tree_explanation=decision_tree_explanation,
            fake_review_detection=fake_review_detection
        )
    
    def handle_event(
        self,
        event_type: EventType,
        user_id: str,
        current_reputation: float,
        severity: EventSeverity = EventSeverity.MEDIUM,
        metadata: Optional[Dict] = None
    ) -> EventProcessingResult:
        if not self.enable_event_driven:
            raise RuntimeError("事件驱动系统未启用，请在初始化时设置 enable_event_driven=True")
        
        event = self.event_system.create_event(
            event_type=event_type,
            user_id=user_id,
            severity=severity,
            metadata=metadata
        )
        
        result = self.event_system.process_event(event, current_reputation)
        return result
    
    def get_user_audit_trail(self, user_id: str) -> List[Dict]:
        if not self.enable_event_driven:
            return []
        return self.event_system.get_audit_trail(user_id)
    
    def get_user_event_summary(self, user_id: str) -> Dict:
        if not self.enable_event_driven:
            return {}
        return self.event_system.get_user_event_summary(user_id)
    
    def print_decision_tree(self, result: CommentQualityResult, max_depth: int = 3):
        if not result.decision_tree_explanation:
            print("未生成决策树解释，请在评分时设置 generate_decision_tree=True")
            return
        
        self.decision_tree_explainer.print_decision_tree(
            result.decision_tree_explanation, 
            max_depth=max_depth
        )
    
    def print_feature_contributions(self, result: CommentQualityResult, top_n: int = 15):
        if not result.decision_tree_explanation:
            print("未生成决策树解释，请在评分时设置 generate_decision_tree=True")
            return
        
        self.decision_tree_explainer.print_feature_contributions(
            result.decision_tree_explanation,
            top_n=top_n
        )
    
    def print_decision_paths(self, result: CommentQualityResult, top_n: int = 5):
        if not result.decision_tree_explanation:
            print("未生成决策树解释，请在评分时设置 generate_decision_tree=True")
            return
        
        self.decision_tree_explainer.print_decision_paths(
            result.decision_tree_explanation,
            top_n=top_n
        )
    
    def print_decision_rules(self, result: CommentQualityResult):
        if not result.decision_tree_explanation:
            print("未生成决策树解释，请在评分时设置 generate_decision_tree=True")
            return
        
        self.decision_tree_explainer.print_decision_rules(
            result.decision_tree_explanation
        )
    
    def _calculate_final_score(
        self,
        text_result: TextQualityResult,
        kg_result: KGResult,
        rep_result: ReputationResult
    ) -> Tuple[float, Dict]:
        text_weighted = (
            text_result.usefulness_score * self.text_quality_subweights['usefulness'] +
            text_result.authenticity_score * self.text_quality_subweights['authenticity'] +
            text_result.completeness_score * self.text_quality_subweights['completeness']
        )
        
        kg_weighted = (
            kg_result.fact_verification_score * self.kg_subweights['fact_verification'] +
            kg_result.entity_diversity_score * self.kg_subweights['entity_diversity'] +
            kg_result.relation_quality_score * self.kg_subweights['relation_quality']
        )
        
        rep_weighted = (
            rep_result.trustworthiness_score * self.reputation_subweights['trustworthiness'] +
            rep_result.influence_score * self.reputation_subweights['influence'] +
            rep_result.consistency_score * self.reputation_subweights['consistency'] +
            (1 - rep_result.risk_score) * self.reputation_subweights['risk']
        )
        
        final_score = (
            text_weighted * self.weights['text_quality'] +
            kg_weighted * self.weights['knowledge_graph'] +
            rep_weighted * self.weights['user_reputation']
        )
        
        final_score = max(0.0, min(1.0, final_score))
        
        score_breakdown = {
            'module_scores': {
                'text_quality': {
                    'raw_score': round(text_result.overall_text_score, 4),
                    'weighted_score': round(text_weighted * self.weights['text_quality'], 4),
                    'weight': self.weights['text_quality'],
                    'subscores': {
                        'usefulness': {
                            'score': text_result.usefulness_score,
                            'weight': self.text_quality_subweights['usefulness']
                        },
                        'authenticity': {
                            'score': text_result.authenticity_score,
                            'weight': self.text_quality_subweights['authenticity']
                        },
                        'completeness': {
                            'score': text_result.completeness_score,
                            'weight': self.text_quality_subweights['completeness']
                        }
                    }
                },
                'knowledge_graph': {
                    'raw_score': round(kg_result.overall_kg_score, 4),
                    'weighted_score': round(kg_weighted * self.weights['knowledge_graph'], 4),
                    'weight': self.weights['knowledge_graph'],
                    'subscores': {
                        'fact_verification': {
                            'score': kg_result.fact_verification_score,
                            'weight': self.kg_subweights['fact_verification']
                        },
                        'entity_diversity': {
                            'score': kg_result.entity_diversity_score,
                            'weight': self.kg_subweights['entity_diversity']
                        },
                        'relation_quality': {
                            'score': kg_result.relation_quality_score,
                            'weight': self.kg_subweights['relation_quality']
                        }
                    }
                },
                'user_reputation': {
                    'raw_score': round(rep_result.overall_reputation_score, 4),
                    'weighted_score': round(rep_weighted * self.weights['user_reputation'], 4),
                    'weight': self.weights['user_reputation'],
                    'subscores': {
                        'trustworthiness': {
                            'score': rep_result.trustworthiness_score,
                            'weight': self.reputation_subweights['trustworthiness']
                        },
                        'influence': {
                            'score': rep_result.influence_score,
                            'weight': self.reputation_subweights['influence']
                        },
                        'consistency': {
                            'score': rep_result.consistency_score,
                            'weight': self.reputation_subweights['consistency']
                        },
                        'risk': {
                            'score': rep_result.risk_score,
                            'weight': self.reputation_subweights['risk'],
                            'note': '风险分数越低越好，计算时使用 (1 - risk_score)'
                        }
                    }
                }
            },
            'calculation_formula': f"最终分数 = 文本质量({self.weights['text_quality']}) + 知识图谱({self.weights['knowledge_graph']}) + 用户信誉({self.weights['user_reputation']})",
            'final_score': round(final_score, 4)
        }
        
        return final_score, score_breakdown
    
    def _get_score_grade(self, score: float) -> str:
        if score >= 0.9:
            return 'S (优秀)'
        elif score >= 0.8:
            return 'A (良好)'
        elif score >= 0.7:
            return 'B (较好)'
        elif score >= 0.6:
            return 'C (一般)'
        elif score >= 0.5:
            return 'D (较差)'
        else:
            return 'F (差)'
    
    def _calculate_percentile(self, score: float) -> float:
        import numpy as np
        percentile = score * 100
        return min(99.99, max(0.01, percentile))
    
    def _generate_interpretation(
        self,
        text_result: TextQualityResult,
        kg_result: KGResult,
        rep_result: ReputationResult,
        final_score: float
    ) -> Dict:
        strengths = []
        weaknesses = []
        overall_summary = []
        
        if text_result.usefulness_score >= 0.7:
            strengths.append("评论内容详实，信息含量高")
        elif text_result.usefulness_score <= 0.3:
            weaknesses.append("评论内容较简短，信息含量有限")
        
        if text_result.authenticity_score >= 0.8:
            strengths.append("评论表达自然，真实性高")
        elif text_result.authenticity_score <= 0.5:
            weaknesses.append("评论存在可疑特征，真实性有待验证")
        
        if text_result.completeness_score >= 0.7:
            strengths.append("评论维度覆盖全面，分析透彻")
        elif text_result.completeness_score <= 0.3:
            weaknesses.append("评论维度单一，分析不够全面")
        
        if kg_result.fact_verification_score >= 0.7:
            strengths.append("评论事实一致性良好")
        elif kg_result.fact_verification_score <= 0.4:
            weaknesses.append("评论存在事实一致性问题")
        
        if kg_result.entity_diversity_score >= 0.6:
            strengths.append("评论提及的实体丰富，信息量大")
        
        if rep_result.trustworthiness_score >= 0.8:
            strengths.append("发布用户信誉良好，可信度高")
        elif rep_result.risk_score >= 0.6:
            weaknesses.append("发布用户存在一定风险，需谨慎对待")
        
        if rep_result.influence_score >= 0.7:
            strengths.append("发布用户具有较强的社区影响力")
        
        if final_score >= 0.8:
            overall_summary.append("这是一条高质量评论，具有很高的参考价值")
            overall_summary.append("该评论内容详实、真实可信，发布用户信誉良好")
        elif final_score >= 0.6:
            overall_summary.append("这是一条质量较好的评论，具有一定的参考价值")
            overall_summary.append("评论整体质量可接受，但仍有提升空间")
        elif final_score >= 0.4:
            overall_summary.append("这是一条质量一般的评论，参考价值有限")
            overall_summary.append("建议结合其他评论和信息进行综合判断")
        else:
            overall_summary.append("这是一条质量较差的评论，参考价值较低")
            overall_summary.append("请谨慎参考，建议优先查看高质量评论")
        
        module_rankings = sorted([
            ('文本质量', text_result.overall_text_score),
            ('知识图谱', kg_result.overall_kg_score),
            ('用户信誉', rep_result.overall_reputation_score)
        ], key=lambda x: x[1], reverse=True)
        
        best_module = module_rankings[0]
        worst_module = module_rankings[-1]
        
        if best_module[1] - worst_module[1] >= 0.3:
            overall_summary.append(f"评论在'{best_module[0]}'方面表现最佳，但在'{worst_module[0]}'方面有待提升")
        
        return {
            'overall_summary': overall_summary,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'module_rankings': [
                {'module': name, 'score': round(score, 4)}
                for name, score in module_rankings
            ]
        }
    
    def _generate_recommendations(
        self,
        text_result: TextQualityResult,
        kg_result: KGResult,
        rep_result: ReputationResult,
        final_score: float
    ) -> List[str]:
        recommendations = []
        
        if text_result.usefulness_score <= 0.5:
            recommendations.append("建议：评论可以增加更多具体的使用细节和体验描述，提升信息量")
        
        if text_result.authenticity_score <= 0.6:
            recommendations.append("提示：评论存在一些模板化或情绪化特征，建议表达更加客观真实")
        
        if text_result.completeness_score <= 0.5:
            missing_aspects = [
                name for name, score in text_result.keyword_analysis['aspect_scores'].items()
                if score == 0
            ]
            if missing_aspects:
                recommendations.append(f"建议：可以补充对{', '.join(missing_aspects[:3])}等方面的评价，使评论更完整")
        
        if kg_result.entity_diversity_score <= 0.4:
            recommendations.append("建议：评论可以提及更多具体的产品特征、品牌或量化指标，增强说服力")
        
        if kg_result.relation_quality_score <= 0.4:
            recommendations.append("建议：可以增加更多对比、评价类的表述，建立更清晰的语义关系")
        
        if rep_result.risk_score >= 0.5:
            recommendations.append("注意：该用户存在一定风险标记，建议结合更多历史评价进行判断")
        
        if rep_result.consistency_score <= 0.5 and len(rep_result.detailed_metrics['user_statistics']) > 0:
            recommendations.append("提示：该用户历史评价波动较大，建议关注其评价的稳定性")
        
        if final_score >= 0.7:
            recommendations.append("推荐：该评论质量较高，可以优先展示给其他用户参考")
        elif final_score <= 0.3:
            recommendations.append("建议：该评论质量较低，建议降低展示权重或进行人工审核")
        else:
            recommendations.append("建议：该评论质量中等，可以正常展示")
        
        return recommendations
    
    def export_result_to_json(self, result: CommentQualityResult, file_path: str):
        result_dict = {
            'comment_id': result.comment_id,
            'user_id': result.user_id,
            'final_score': result.final_score,
            'score_grade': result.score_grade,
            'score_percentile': result.score_percentile,
            'timestamp': result.timestamp,
            'scoring_weights': result.scoring_weights,
            'score_breakdown': result.score_breakdown,
            'interpretation': result.interpretation,
            'recommendations': result.recommendations,
            'text_quality': {
                'overall_score': result.text_quality.overall_text_score,
                'usefulness_score': result.text_quality.usefulness_score,
                'authenticity_score': result.text_quality.authenticity_score,
                'completeness_score': result.text_quality.completeness_score,
                'usefulness_evidence': result.text_quality.usefulness_evidence,
                'authenticity_evidence': result.text_quality.authenticity_evidence,
                'completeness_evidence': result.text_quality.completeness_evidence,
                'keyword_analysis': result.text_quality.keyword_analysis
            },
            'knowledge_graph': {
                'overall_score': result.knowledge_graph.overall_kg_score,
                'fact_verification_score': result.knowledge_graph.fact_verification_score,
                'entity_diversity_score': result.knowledge_graph.entity_diversity_score,
                'relation_quality_score': result.knowledge_graph.relation_quality_score,
                'entities': [
                    {'name': e.name, 'type': e.type, 'confidence': e.confidence}
                    for e in result.knowledge_graph.entities
                ],
                'relations': [
                    {'subject': r.subject, 'predicate': r.predicate, 'object': r.object, 'confidence': r.confidence}
                    for r in result.knowledge_graph.relations
                ],
                'evidence': result.knowledge_graph.evidence,
                'graph_stats': result.knowledge_graph.graph_stats
            },
            'user_reputation': {
                'overall_score': result.user_reputation.overall_reputation_score,
                'trustworthiness_score': result.user_reputation.trustworthiness_score,
                'influence_score': result.user_reputation.influence_score,
                'consistency_score': result.user_reputation.consistency_score,
                'risk_score': result.user_reputation.risk_score,
                'evidence': result.user_reputation.evidence,
                'detailed_metrics': result.user_reputation.detailed_metrics
            }
        }
        
        if result.decision_tree_explanation:
            result_dict['decision_tree_explanation'] = {
                'feature_contributions': result.decision_tree_explanation.feature_contributions,
                'decision_rules': result.decision_tree_explanation.decision_rules,
                'summary': result.decision_tree_explanation.summary,
                'top_contributors': result.decision_tree_explanation.visualization_data.get('top_contributors', [])
            }
        
        if result.fake_review_detection:
            result_dict['fake_review_detection'] = result.fake_review_detection.to_dict()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def print_result_summary(self, result: CommentQualityResult, show_details: bool = False,
                            show_decision_tree: bool = False, show_feature_contributions: bool = False,
                            show_decision_paths: bool = False, show_decision_rules: bool = False):
        print("=" * 70)
        print("评论质量评分报告")
        print("=" * 70)
        print(f"评论ID: {result.comment_id}")
        print(f"用户ID: {result.user_id}")
        print(f"评分时间: {result.timestamp}")
        print("-" * 70)
        print(f"最终评分: {result.final_score:.4f} / 1.0000")
        print(f"等级评定: {result.score_grade}")
        print(f"百分位排名: 前 {result.score_percentile:.2f}%")
        print("-" * 70)
        
        print("\n📊 各模块得分:")
        for module_name, module_data in result.score_breakdown['module_scores'].items():
            module_display = {
                'text_quality': '文本质量',
                'knowledge_graph': '知识图谱',
                'user_reputation': '用户信誉'
            }.get(module_name, module_name)
            print(f"  {module_display}: {module_data['raw_score']:.4f} "
                  f"(权重: {module_data['weight']:.2%}, 加权贡献: {module_data['weighted_score']:.4f})")
        
        print("\n📝 评分总结:")
        for summary in result.interpretation['overall_summary']:
            print(f"  - {summary}")
        
        if result.interpretation['strengths']:
            print("\n✅ 主要优势:")
            for strength in result.interpretation['strengths']:
                print(f"  + {strength}")
        
        if result.interpretation['weaknesses']:
            print("\n⚠️  待改进点:")
            for weakness in result.interpretation['weaknesses']:
                print(f"  - {weakness}")
        
        print("\n💡 建议:")
        for recommendation in result.recommendations:
            print(f"  {recommendation}")
        
        if result.fake_review_detection:
            self._print_fake_detection_result(result.fake_review_detection)
        
        if show_decision_tree and result.decision_tree_explanation:
            self.print_decision_tree(result)
        
        if show_feature_contributions and result.decision_tree_explanation:
            self.print_feature_contributions(result)
        
        if show_decision_paths and result.decision_tree_explanation:
            self.print_decision_paths(result)
        
        if show_decision_rules and result.decision_tree_explanation:
            self.print_decision_rules(result)
        
        if show_details:
            self._print_detailed_evidence(result)
        
        print("\n" + "=" * 70)
    
    def _print_detailed_evidence(self, result: CommentQualityResult):
        print("\n" + "=" * 50)
        print("📄 详细评分依据")
        print("=" * 50)
        
        print("\n【文本质量分析依据】")
        print(f"  有用性分析 ({result.text_quality.usefulness_score:.4f}):")
        for ev in result.text_quality.usefulness_evidence:
            print(f"    - {ev}")
        
        print(f"\n  真实性分析 ({result.text_quality.authenticity_score:.4f}):")
        for ev in result.text_quality.authenticity_evidence:
            print(f"    - {ev}")
        
        print(f"\n  完整性分析 ({result.text_quality.completeness_score:.4f}):")
        for ev in result.text_quality.completeness_evidence:
            print(f"    - {ev}")
        
        print("\n【知识图谱分析依据】")
        for ev in result.knowledge_graph.evidence:
            print(f"  - {ev}")
        
        if result.knowledge_graph.entities:
            print(f"\n  提取的实体 ({len(result.knowledge_graph.entities)}个):")
            type_names = {'product': '产品', 'brand': '品牌', 'attribute': '属性', 'measurement': '度量'}
            for entity in result.knowledge_graph.entities[:10]:
                type_name = type_names.get(entity.type, entity.type)
                print(f"    - {entity.name} ({type_name}, 置信度: {entity.confidence:.2f})")
        
        if result.knowledge_graph.relations:
            print(f"\n  提取的关系 ({len(result.knowledge_graph.relations)}个):")
            for rel in result.knowledge_graph.relations[:5]:
                print(f"    - {rel.subject} → {rel.predicate} → {rel.object}")
        
        print("\n【用户信誉分析依据】")
        for ev in result.user_reputation.evidence[:15]:
            print(f"  - {ev}")
        
        print("\n【图谱统计信息】")
        stats = result.knowledge_graph.graph_stats
        print(f"  节点数: {stats['node_count']}, 边数: {stats['edge_count']}")
        print(f"  图谱密度: {stats['density']:.4f}, 平均度数: {stats['avg_degree']:.4f}")
        if stats['key_entities']:
            print(f"  关键实体: {', '.join(stats['key_entities'])}")
    
    def _print_fake_detection_result(self, detection: FakeReviewDetectionResult):
        print("\n🔍 虚假评论检测结果:")
        
        status_icon = "⚠️" if detection.is_fake else "✅"
        status_text = "虚假评论" if detection.is_fake else "正常评论"
        
        type_names = {
            'legitimate': '正常',
            'brushing': '刷单',
            'water_army': '水军',
            'competitor_malicious': '竞品恶意'
        }
        level_names = {
            'none': '无',
            'low': '低',
            'medium': '中',
            'high': '高',
            'critical': '极高'
        }
        
        print(f"  {status_icon} {status_text} | 类型: {type_names.get(detection.fake_type.value, detection.fake_type.value)}")
        print(f"  可疑程度: {level_names.get(detection.suspicion_level.value, detection.suspicion_level.value)} ({detection.suspicion_score:.2%})")
        print(f"  刷单嫌疑: {detection.brushing_score:.2%} | 水军嫌疑: {detection.water_army_score:.2%} | 竞品恶意: {detection.competitor_score:.2%}")
        
        if detection.evidence:
            print(f"  检测证据:")
            for ev in detection.evidence:
                impact_icon = "🔴" if ev.impact >= 0.2 else "🟡" if ev.impact >= 0.1 else "🟢"
                print(f"    {impact_icon} {ev.description} (影响: {ev.impact:.2%})")
    
    def rank_reviews(
        self,
        reviews: List[ReviewForRanking],
        strategy: SortStrategy = SortStrategy.BALANCED,
        custom_weights: Optional[Dict[str, float]] = None,
        enable_diversity: bool = True
    ) -> List[Tuple[ReviewForRanking, RankingResult]]:
        ranked = self.ranker.rank_reviews(reviews, strategy=strategy, custom_weights=custom_weights)
        if enable_diversity:
            ranked = self.ranker.rerank_with_diversity(ranked)
        return ranked
    
    def print_ranking_comparison(self, reviews: List[ReviewForRanking], top_n: int = 5):
        self.ranker.print_ranking_comparison(reviews, top_n)
    
    def print_ranking_details(self, ranked: List[Tuple[ReviewForRanking, RankingResult]], top_n: int = 10):
        self.ranker.print_ranking_details(ranked, top_n)
    
    def add_quality_data(
        self,
        product_id: str,
        quality_score: float,
        timestamp: Optional[datetime] = None,
        avg_rating: float = 0.0,
        fake_review_count: int = 0,
        fake_review_ratio: float = 0.0,
        avg_usefulness: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.trend_monitor.add_quality_data(
            product_id=product_id,
            quality_score=quality_score,
            timestamp=timestamp,
            avg_rating=avg_rating,
            fake_review_count=fake_review_count,
            fake_review_ratio=fake_review_ratio,
            avg_usefulness=avg_usefulness,
            metadata=metadata
        )
    
    def analyze_trends(
        self,
        product_id: str,
        time_window_hours: Optional[int] = None
    ) -> TrendAnalysisResult:
        return self.trend_monitor.analyze_trends(product_id, time_window_hours)
    
    def get_trend_summary(
        self,
        product_id: str,
        time_window_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        return self.trend_monitor.get_trend_summary(product_id, time_window_hours)
    
    def print_trend_report(
        self,
        product_id: str,
        time_window_hours: Optional[int] = None
    ):
        self.trend_monitor.print_trend_report(product_id, time_window_hours)
    
    def get_active_alerts(
        self,
        product_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        only_unhandled: bool = True
    ) -> List[TrendAlert]:
        return self.trend_monitor.get_active_alerts(product_id, severity, only_unhandled)
    
    def mark_alert_handled(self, alert_id: str) -> bool:
        return self.trend_monitor.mark_alert_handled(alert_id)
    
    def detect_fake_review(
        self,
        review: ReviewForDetection,
        all_reviews: Optional[List[ReviewForDetection]] = None,
        user_reviews: Optional[List[ReviewForDetection]] = None
    ) -> FakeReviewDetectionResult:
        if not self.fake_detector:
            self.fake_detector = FakeReviewDetector()
        return self.fake_detector.detect(review, all_reviews, user_reviews)
    
    def batch_detect_fake_reviews(
        self,
        reviews: List[ReviewForDetection]
    ) -> List[FakeReviewDetectionResult]:
        if not self.fake_detector:
            self.fake_detector = FakeReviewDetector()
        return self.fake_detector.batch_detect(reviews)
    
    def detect_fake_review_groups(
        self,
        reviews: List[ReviewForDetection]
    ) -> List[GroupDetectionResult]:
        if not self.fake_detector:
            self.fake_detector = FakeReviewDetector()
        return self.fake_detector.detect_group(reviews)
