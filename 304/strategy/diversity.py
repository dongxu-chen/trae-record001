import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np
from dataclasses import dataclass, field

from config import config
from data.models import RecommendationResult

logger = logging.getLogger(__name__)


@dataclass
class RecommendationBlock:
    block_id: int
    category: str
    candidates: List[RecommendationResult] = field(default_factory=list)
    selected_count: int = 0
    capacity: int = 0
    priority: float = 1.0

    def add_candidate(self, rec: RecommendationResult):
        self.candidates.append(rec)

    def sort_candidates(self):
        self.candidates.sort(key=lambda x: x.score, reverse=True)

    def pop_next(self) -> Optional[RecommendationResult]:
        if self.candidates and self.selected_count < self.capacity:
            rec = self.candidates.pop(0)
            self.selected_count += 1
            return rec
        return None

    def has_available(self) -> bool:
        return len(self.candidates) > 0 and self.selected_count < self.capacity


@dataclass
class BlockConfig:
    block_size: int = 10
    min_blocks_per_category: int = 1
    max_blocks_per_category: int = 5
    intra_block_dedup: bool = True
    inter_block_dedup: bool = True
    round_robin: bool = True
    capacity_based_on_priority: bool = True


class BlockBasedDiversity:
    def __init__(
        self,
        category_list: List[str] = None,
        block_config: Optional[BlockConfig] = None,
        category_preferences: Optional[Dict[str, float]] = None
    ):
        self.category_list = category_list or config.CATEGORY_LIST
        self.block_config = block_config or BlockConfig()
        self.category_preferences = category_preferences or {}

    def _dedup_candidates(self, candidates: List[RecommendationResult]) -> List[RecommendationResult]:
        seen_ids = set()
        unique_recs = []

        for rec in candidates:
            if rec.news_id not in seen_ids:
                seen_ids.add(rec.news_id)
                unique_recs.append(rec)

        logger.debug(f"Dedup: {len(candidates)} -> {len(unique_recs)} candidates")
        return unique_recs

    def _calculate_block_priority(
        self,
        category: str,
        category_candidates: List[RecommendationResult],
        user_preferences: Optional[Dict[str, float]] = None
    ) -> float:
        base_score = np.mean([rec.score for rec in category_candidates]) if category_candidates else 0.0

        pref_score = user_preferences.get(category, 0.5) if user_preferences else 0.5
        config_pref = self.category_preferences.get(category, 0.5)

        priority = 0.5 * base_score + 0.3 * pref_score + 0.2 * config_pref

        return priority

    def _create_blocks(
        self,
        recommendations: List[RecommendationResult],
        user_preferences: Optional[Dict[str, float]] = None,
        target_total: int = 20
    ) -> List[RecommendationBlock]:
        category_groups: Dict[str, List[RecommendationResult]] = defaultdict(list)

        for rec in recommendations:
            category_groups[rec.category].append(rec)

        blocks: List[RecommendationBlock] = []
        block_id = 0

        total_candidates = len(recommendations)
        category_priorities = {}

        for category, candidates in category_groups.items():
            if self.block_config.intra_block_dedup:
                candidates = self._dedup_candidates(candidates)
                category_groups[category] = candidates

            priority = self._calculate_block_priority(category, candidates, user_preferences)
            category_priorities[category] = priority

            num_blocks = max(
                self.block_config.min_blocks_per_category,
                min(
                    self.block_config.max_blocks_per_category,
                    int(np.ceil(len(candidates) / self.block_config.block_size))
                )
            )

            for i in range(num_blocks):
                start_idx = i * self.block_config.block_size
                end_idx = min(start_idx + self.block_config.block_size, len(candidates))
                block_candidates = candidates[start_idx:end_idx]

                if block_candidates:
                    block = RecommendationBlock(
                        block_id=block_id,
                        category=category,
                        candidates=block_candidates.copy(),
                        priority=priority if i == 0 else priority * 0.8 ** i
                    )
                    block.sort_candidates()
                    blocks.append(block)
                    block_id += 1

        total_capacity_needed = target_total
        total_available = sum(len(b.candidates) for b in blocks)

        for block in blocks:
            if self.block_config.capacity_based_on_priority:
                category_share = block.priority / sum(category_priorities.values())
                block.capacity = max(1, int(total_capacity_needed * category_share))
            else:
                block.capacity = max(1, int(total_capacity_needed / len(blocks)))

            block.capacity = min(block.capacity, len(block.candidates))

        logger.info(f"Created {len(blocks)} blocks across {len(category_groups)} categories")
        return blocks

    def _inter_block_dedup(
        self,
        blocks: List[RecommendationBlock]
    ) -> List[RecommendationBlock]:
        seen_ids = set()

        for block in blocks:
            filtered_candidates = []
            for rec in block.candidates:
                if rec.news_id not in seen_ids:
                    filtered_candidates.append(rec)
                    seen_ids.add(rec.news_id)
            block.candidates = filtered_candidates

        return blocks

    def _round_robin_selection(
        self,
        blocks: List[RecommendationBlock],
        top_n: int
    ) -> List[RecommendationResult]:
        blocks = sorted(blocks, key=lambda b: b.priority, reverse=True)
        selected = []
        used_ids = set()

        round_num = 0
        max_rounds = top_n * 2

        while len(selected) < top_n and round_num < max_rounds:
            made_progress = False

            for block in blocks:
                if len(selected) >= top_n:
                    break

                if not block.has_available():
                    continue

                rec = block.pop_next()
                if rec is None:
                    continue

                if rec.news_id in used_ids:
                    continue

                used_ids.add(rec.news_id)
                selected.append(rec)
                made_progress = True

            if not made_progress:
                for block in blocks:
                    if len(selected) >= top_n:
                        break
                    rec = block.pop_next()
                    if rec is not None and rec.news_id not in used_ids:
                        used_ids.add(rec.news_id)
                        selected.append(rec)
                        made_progress = True

                if not made_progress:
                    break

            round_num += 1

        for i, rec in enumerate(selected):
            rec.rank = i + 1
            rec.reason = f"block_selection_round_{i // len(blocks)}"

        logger.debug(f"Round-robin selected {len(selected)} items in {round_num} rounds")
        return selected

    def _score_based_selection(
        self,
        blocks: List[RecommendationBlock],
        top_n: int
    ) -> List[RecommendationResult]:
        all_candidates = []
        category_counts = defaultdict(int)
        max_per_category = max(1, int(top_n * config.CATEGORY_MAX_RATIO))

        for block in blocks:
            for rec in block.candidates:
                all_candidates.append((rec, block.priority))

        all_candidates.sort(key=lambda x: x[0].score * x[1], reverse=True)

        selected = []
        used_ids = set()

        for rec, priority in all_candidates:
            if len(selected) >= top_n:
                break

            if rec.news_id in used_ids:
                continue

            category = rec.category
            if category_counts[category] >= max_per_category and len(selected) < top_n - len(self.category_list):
                continue

            used_ids.add(rec.news_id)
            category_counts[category] += 1
            rec.reason = "score_based_selection"
            selected.append(rec)

        for i, rec in enumerate(selected):
            rec.rank = i + 1

        logger.debug(f"Score-based selected {len(selected)} items")
        return selected

    def apply_block_diversity(
        self,
        recommendations: List[RecommendationResult],
        top_n: int = None,
        user_preferences: Optional[Dict[str, float]] = None,
        use_round_robin: bool = None
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N
        use_round_robin = use_round_robin if use_round_robin is not None else self.block_config.round_robin

        if len(recommendations) <= top_n:
            return self._simple_diversity_rerank(recommendations, top_n)

        blocks = self._create_blocks(recommendations, user_preferences, top_n)

        if self.block_config.inter_block_dedup:
            blocks = self._inter_block_dedup(blocks)

        if use_round_robin:
            selected = self._round_robin_selection(blocks, top_n)
        else:
            selected = self._score_based_selection(blocks, top_n)

        if len(selected) < top_n:
            remaining = [rec for rec in recommendations if rec.news_id not in {s.news_id for s in selected}]
            remaining.sort(key=lambda x: x.score, reverse=True)
            for rec in remaining:
                if len(selected) >= top_n:
                    break
                rec.rank = len(selected) + 1
                rec.reason = "fallback_fill"
                selected.append(rec)

        return selected[:top_n]

    def _simple_diversity_rerank(
        self,
        recommendations: List[RecommendationResult],
        top_n: int
    ) -> List[RecommendationResult]:
        category_counts = defaultdict(int)
        max_per_category = max(1, int(top_n * config.CATEGORY_MAX_RATIO))
        reranked = []
        used_ids = set()

        for rec in sorted(recommendations, key=lambda x: x.score, reverse=True):
            if len(reranked) >= top_n:
                break
            if rec.news_id in used_ids:
                continue

            category = rec.category
            if category_counts[category] >= max_per_category:
                continue

            used_ids.add(rec.news_id)
            category_counts[category] += 1
            reranked.append(rec)

        for i, rec in enumerate(reranked):
            rec.rank = i + 1
            rec.reason = "simple_diversity"

        return reranked

    def calculate_diversity_score(
        self,
        recommendations: List[RecommendationResult]
    ) -> Dict[str, float]:
        if not recommendations:
            return {
                'gini_index': 0.0,
                'category_coverage': 0.0,
                'shannon_index': 0.0,
                'unique_ratio': 0.0
            }

        category_counts = defaultdict(int)
        news_ids = set()
        for rec in recommendations:
            category_counts[rec.category] += 1
            news_ids.add(rec.news_id)

        total = len(recommendations)
        categories_present = len([c for c in category_counts.values() if c > 0])
        category_coverage = categories_present / len(self.category_list)
        unique_ratio = len(news_ids) / total if total > 0 else 1.0

        proportions = [count / total for count in category_counts.values()]
        gini_index = 1 - sum(p ** 2 for p in proportions)

        import math
        shannon_index = -sum(p * math.log(p) for p in proportions if p > 0)

        return {
            'gini_index': gini_index,
            'category_coverage': category_coverage,
            'shannon_index': shannon_index,
            'unique_ratio': unique_ratio
        }

    def get_block_statistics(
        self,
        recommendations: List[RecommendationResult],
        user_preferences: Optional[Dict[str, float]] = None
    ) -> Dict:
        blocks = self._create_blocks(recommendations, user_preferences)

        stats = {
            'total_blocks': len(blocks),
            'categories': defaultdict(dict),
            'total_capacity': sum(b.capacity for b in blocks),
            'total_candidates': sum(len(b.candidates) for b in blocks)
        }

        for block in blocks:
            cat = block.category
            if 'blocks' not in stats['categories'][cat]:
                stats['categories'][cat]['blocks'] = 0
                stats['categories'][cat]['total_candidates'] = 0
                stats['categories'][cat]['priority'] = block.priority
            stats['categories'][cat]['blocks'] += 1
            stats['categories'][cat]['total_candidates'] += len(block.candidates)

        return stats


class DiversityController:
    def __init__(
        self,
        category_list: List[str] = None,
        diversity_penalty: float = None,
        category_max_ratio: float = None,
        use_block_based: bool = True
    ):
        self.category_list = category_list or config.CATEGORY_LIST
        self.diversity_penalty = diversity_penalty or config.DIVERSITY_PENALTY
        self.category_max_ratio = category_max_ratio or config.CATEGORY_MAX_RATIO
        self.use_block_based = use_block_based

        if use_block_based:
            self.block_diversity = BlockBasedDiversity(
                category_list=self.category_list,
                block_config=BlockConfig()
            )

    def apply_diversity(
        self,
        recommendations: List[RecommendationResult],
        top_n: int = None,
        user_preferences: Optional[Dict[str, float]] = None
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N

        if self.use_block_based:
            return self.block_diversity.apply_block_diversity(
                recommendations, top_n, user_preferences
            )
        else:
            return self._legacy_apply_diversity(recommendations, top_n)

    def _legacy_apply_diversity(
        self,
        recommendations: List[RecommendationResult],
        top_n: int = None
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N

        if len(recommendations) <= top_n:
            return self._rerank_with_diversity(recommendations)

        selected = []
        category_counts = defaultdict(int)
        used_news_ids = set()

        candidates = recommendations.copy()

        max_per_category = max(1, int(top_n * self.category_max_ratio))

        while len(selected) < top_n and candidates:
            best_idx = -1
            best_score = -1.0

            for i, rec in enumerate(candidates):
                if rec.news_id in used_news_ids:
                    continue

                category = rec.category
                current_count = category_counts[category]

                if current_count >= max_per_category and len(selected) < top_n - len(self.category_list):
                    continue

                adjusted_score = self._calculate_diversity_adjusted_score(
                    score=rec.score,
                    category=category,
                    category_counts=category_counts,
                    total_selected=len(selected)
                )

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_idx = i

            if best_idx == -1:
                for i, rec in enumerate(candidates):
                    if rec.news_id not in used_news_ids:
                        best_idx = i
                        break

            if best_idx == -1:
                break

            selected_rec = candidates[best_idx]
            selected.append(selected_rec)
            used_news_ids.add(selected_rec.news_id)
            category_counts[selected_rec.category] += 1

            candidates.pop(best_idx)

        for i, rec in enumerate(selected):
            rec.rank = i + 1

        return selected

    def _calculate_diversity_adjusted_score(
        self,
        score: float,
        category: str,
        category_counts: Dict[str, int],
        total_selected: int
    ) -> float:
        if total_selected == 0:
            return score

        category_count = category_counts[category]
        category_ratio = category_count / total_selected if total_selected > 0 else 0

        penalty = self.diversity_penalty * category_ratio

        if category_ratio > self.category_max_ratio:
            extra_penalty = (category_ratio - self.category_max_ratio) * 2
            penalty += extra_penalty

        adjusted_score = score * (1 - penalty)

        return adjusted_score

    def _rerank_with_diversity(
        self,
        recommendations: List[RecommendationResult]
    ) -> List[RecommendationResult]:
        category_counts = defaultdict(int)
        reranked = []
        used_news_ids = set()

        for i, rec in enumerate(recommendations):
            if rec.news_id in used_news_ids:
                continue

            adjusted_score = self._calculate_diversity_adjusted_score(
                score=rec.score,
                category=rec.category,
                category_counts=category_counts,
                total_selected=i
            )

            rec.score = adjusted_score
            category_counts[rec.category] += 1
            used_news_ids.add(rec.news_id)
            reranked.append(rec)

        reranked.sort(key=lambda x: x.score, reverse=True)

        for i, rec in enumerate(reranked):
            rec.rank = i + 1

        return reranked

    def calculate_diversity_score(
        self,
        recommendations: List[RecommendationResult]
    ) -> Dict[str, float]:
        if self.use_block_based:
            return self.block_diversity.calculate_diversity_score(recommendations)
        else:
            if not recommendations:
                return {
                    'gini_index': 0.0,
                    'category_coverage': 0.0,
                    'shannon_index': 0.0
                }

            category_counts = defaultdict(int)
            for rec in recommendations:
                category_counts[rec.category] += 1

            total = len(recommendations)
            categories_present = len([c for c in category_counts.values() if c > 0])
            category_coverage = categories_present / len(self.category_list)

            proportions = [count / total for count in category_counts.values()]
            gini_index = 1 - sum(p ** 2 for p in proportions)

            import math
            shannon_index = -sum(p * math.log(p) for p in proportions if p > 0)

            return {
                'gini_index': gini_index,
                'category_coverage': category_coverage,
                'shannon_index': shannon_index
            }

    def apply_mmr(
        self,
        recommendations: List[RecommendationResult],
        news_embeddings: Dict[int, List[float]],
        lambda_param: float = 0.7,
        top_n: int = None
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N

        if len(recommendations) <= top_n:
            return recommendations

        candidate_recs = {rec.news_id: rec for rec in recommendations}
        candidate_ids = list(candidate_recs.keys())

        selected = []
        selected_embeddings = []
        remaining = candidate_ids.copy()

        if not remaining:
            return recommendations

        first_id = max(remaining, key=lambda x: candidate_recs[x].score)
        selected.append(first_id)
        if first_id in news_embeddings:
            selected_embeddings.append(np.array(news_embeddings[first_id]))
        remaining.remove(first_id)

        while len(selected) < top_n and remaining:
            best_id = None
            best_mmr = -1.0

            for news_id in remaining:
                rec = candidate_recs[news_id]
                relevance = rec.score

                if news_id in news_embeddings and selected_embeddings:
                    news_emb = np.array(news_embeddings[news_id])
                    similarities = []
                    for sel_emb in selected_embeddings:
                        sim = np.dot(news_emb, sel_emb) / (
                            np.linalg.norm(news_emb) * np.linalg.norm(sel_emb)
                        )
                        similarities.append(sim)
                    max_similarity = max(similarities) if similarities else 0.0
                else:
                    max_similarity = 0.0

                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_id = news_id

            if best_id is None:
                break

            selected.append(best_id)
            if best_id in news_embeddings:
                selected_embeddings.append(np.array(news_embeddings[best_id]))
            remaining.remove(best_id)

        results = []
        for i, news_id in enumerate(selected):
            rec = candidate_recs[news_id]
            rec.rank = i + 1
            results.append(rec)

        return results
