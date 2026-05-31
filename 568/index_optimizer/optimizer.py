from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import json
from pathlib import Path

from sql_analyzer import SQLParser
from rewriter import SQLRewriter, RewriteResult
from .recommender import IndexRecommender, IndexRecommendationResult, IndexRecommendation


@dataclass
class CombinedOptimizationResult:
    sql_before: str
    sql_after: str
    rewrite_result: RewriteResult
    index_recommendations: IndexRecommendationResult
    combined_benefit_score: float = 0.0
    is_rewritten: bool = False
    has_index_recommendations: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql_before": self.sql_before,
            "sql_after": self.sql_after,
            "rewrite_result": self.rewrite_result.to_dict() if self.rewrite_result else None,
            "index_recommendations": self.index_recommendations.to_dict() if self.index_recommendations else None,
            "combined_benefit_score": self.combined_benefit_score,
            "is_rewritten": self.is_rewritten,
            "has_index_recommendations": self.has_index_recommendations,
        }


class IndexRewriteCoordinator:
    def __init__(
        self,
        rewriter: SQLRewriter,
        index_recommender: IndexRecommender,
        dialect: str = "mysql",
    ):
        self.rewriter = rewriter
        self.index_recommender = index_recommender
        self.dialect = dialect
        self.sql_parser = SQLParser(dialect)

    def optimize(self, sql: str, plan_analysis=None) -> CombinedOptimizationResult:
        rewrite_result = self.rewriter.rewrite(sql)

        if rewrite_result.is_rewritten and rewrite_result.rewritten_sql:
            optimized_sql = rewrite_result.rewritten_sql
        else:
            optimized_sql = sql

        index_result = self.index_recommender.recommend_for_query(
            optimized_sql, plan_analysis
        )

        benefit_score = self._calculate_combined_benefit(rewrite_result, index_result)

        return CombinedOptimizationResult(
            sql_before=sql,
            sql_after=optimized_sql,
            rewrite_result=rewrite_result,
            index_recommendations=index_result,
            combined_benefit_score=benefit_score,
            is_rewritten=rewrite_result.is_rewritten,
            has_index_recommendations=len(index_result.recommendations) > 0,
        )

    def optimize_batch(
        self,
        sql_list: List[str],
    ) -> List[CombinedOptimizationResult]:
        results = []
        for sql in sql_list:
            result = self.optimize(sql)
            results.append(result)
        return results

    def generate_optimization_summary(
        self,
        results: List[CombinedOptimizationResult],
    ) -> Dict[str, Any]:
        total_optimized = len(results)
        rewritten_count = sum(1 for r in results if r.is_rewritten)
        with_index = sum(1 for r in results if r.has_index_recommendations)

        total_index_recs = sum(
            len(r.index_recommendations.recommendations)
            for r in results
            if r.index_recommendations
        )

        table_index_recs: Dict[str, List[IndexRecommendation]] = {}
        for r in results:
            if r.index_recommendations:
                for rec in r.index_recommendations.recommendations:
                    if rec.table_name not in table_index_recs:
                        table_index_recs[rec.table_name] = []
                    table_index_recs[rec.table_name].append(rec)

        aggregated_indexes = self._aggregate_indexes(table_index_recs)

        return {
            "total_queries": total_optimized,
            "rewritten_count": rewritten_count,
            "with_index_recommendations": with_index,
            "total_index_recommendations": total_index_recs,
            "rewrite_rate": rewritten_count / total_optimized if total_optimized > 0 else 0,
            "aggregated_indexes": [r.to_dict() for r in aggregated_indexes],
        }

    def _calculate_combined_benefit(
        self,
        rewrite_result: RewriteResult,
        index_result: IndexRecommendationResult,
    ) -> float:
        rewrite_benefit = 0.0
        if rewrite_result.is_rewritten:
            rewrite_benefit = rewrite_result.rules_applied * 10.0

        index_benefit = sum(
            rec.estimated_benefit * rec.confidence
            for rec in index_result.recommendations
        )

        return rewrite_benefit + index_benefit

    def _aggregate_indexes(
        self,
        table_index_recs: Dict[str, List[IndexRecommendation]],
    ) -> List[IndexRecommendation]:
        aggregated = []

        for table, recs in table_index_recs.items():
            rec_groups: Dict[str, List[IndexRecommendation]] = {}

            for rec in recs:
                key = f"{table}:{','.join(sorted(rec.columns))}"
                if key not in rec_groups:
                    rec_groups[key] = []
                rec_groups[key].append(rec)

            for key, group in rec_groups.items():
                best = max(group, key=lambda x: x.estimated_benefit * x.confidence)
                best.estimated_benefit = sum(r.estimated_benefit for r in group)
                best.confidence = min(1.0, max(r.confidence for r in group))
                aggregated.append(best)

        return sorted(aggregated, key=lambda x: x.estimated_benefit, reverse=True)
