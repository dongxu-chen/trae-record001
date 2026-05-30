import math
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

from config import settings
from schemas import (
    ReviewItem, VoteRecord, GangDetectionResult
)


class GangDetector:
    def __init__(self):
        self._user_vote_graph: Dict[str, Set[str]] = defaultdict(set)
        self._user_reviews: Dict[str, List[str]] = defaultdict(list)
        self._review_data: Dict[str, ReviewItem] = {}
        self._vote_count: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def _build_vote_graph(self, vote_records: List[VoteRecord]):
        self._user_vote_graph.clear()
        self._vote_count.clear()
        for record in vote_records:
            self._user_vote_graph[record.voter_id].add(record.target_user_id)
            self._vote_count[record.voter_id][record.target_user_id] += 1

    def _build_review_index(self, reviews: List[ReviewItem]):
        self._user_reviews.clear()
        self._review_data.clear()
        for review in reviews:
            self._user_reviews[review.user_id].append(review.review_id)
            self._review_data[review.review_id] = review

    def _find_mutual_vote_pairs(self) -> List[Tuple[str, str, int]]:
        mutual_pairs = []
        all_users = set(self._user_vote_graph.keys())

        for user_a in all_users:
            for user_b in self._user_vote_graph.get(user_a, set()):
                if user_b in all_users and user_a in self._user_vote_graph.get(user_b, set()):
                    if user_a < user_b:
                        a_votes_b = self._vote_count.get(user_a, {}).get(user_b, 0)
                        b_votes_a = self._vote_count.get(user_b, {}).get(user_a, 0)
                        mutual_strength = min(a_votes_b, b_votes_a)
                        mutual_pairs.append((user_a, user_b, mutual_strength))

        return mutual_pairs

    def _find_gang_clusters(self, mutual_pairs: List[Tuple[str, str, int]]) -> List[Set[str]]:
        if not mutual_pairs:
            return []

        adjacency = defaultdict(set)
        for user_a, user_b, strength in mutual_pairs:
            if strength >= settings.GANG_MUTUAL_VOTE_THRESHOLD:
                adjacency[user_a].add(user_b)
                adjacency[user_b].add(user_a)

        visited = set()
        clusters = []

        for user in adjacency:
            if user in visited:
                continue

            cluster = set()
            queue = [user]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                cluster.add(current)
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            if len(cluster) >= settings.GANG_MIN_MEMBERS:
                clusters.append(cluster)

        return clusters

    def _calculate_rating_similarity(self, members: Set[str]) -> float:
        member_ratings = defaultdict(list)
        for uid in members:
            for rid in self._user_reviews.get(uid, []):
                review = self._review_data.get(rid)
                if review:
                    member_ratings[uid].append(review.rating)

        if not member_ratings:
            return 0.0

        avg_ratings = {}
        for uid, ratings in member_ratings.items():
            avg_ratings[uid] = sum(ratings) / len(ratings)

        rating_values = list(avg_ratings.values())
        if len(rating_values) < 2:
            return 0.0

        rating_range = 4.0
        diffs = []
        for i in range(len(rating_values)):
            for j in range(i + 1, len(rating_values)):
                diffs.append(abs(rating_values[i] - rating_values[j]))

        avg_diff = sum(diffs) / len(diffs)
        similarity = max(0, 1.0 - avg_diff / rating_range)

        return similarity

    def _calculate_content_similarity(self, members: Set[str]) -> float:
        member_contents = defaultdict(list)
        for uid in members:
            for rid in self._user_reviews.get(uid, []):
                review = self._review_data.get(rid)
                if review:
                    member_contents[uid].append(review.content)

        all_texts = []
        for uid in members:
            combined = " ".join(member_contents.get(uid, []))
            if combined:
                all_texts.append(combined)

        if len(all_texts) < 2:
            return 0.0

        char_sets = [set(text) for text in all_texts]
        similarities = []
        for i in range(len(char_sets)):
            for j in range(i + 1, len(char_sets)):
                if not char_sets[i] or not char_sets[j]:
                    continue
                intersection = char_sets[i] & char_sets[j]
                union = char_sets[i] | char_sets[j]
                jaccard = len(intersection) / len(union) if union else 0
                similarities.append(jaccard)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _check_same_product_concentration(self, members: Set[str]) -> float:
        product_counts = defaultdict(int)
        total_reviews = 0

        for uid in members:
            for rid in self._user_reviews.get(uid, []):
                review = self._review_data.get(rid)
                if review:
                    product_counts[review.product_id] += 1
                    total_reviews += 1

        if total_reviews == 0 or not product_counts:
            return 0.0

        max_concentration = max(product_counts.values()) / total_reviews

        same_product_count = sum(
            1 for pid, cnt in product_counts.items()
            if cnt >= settings.GANG_MIN_MEMBERS
        )

        concentration_score = max_concentration * settings.GANG_SAME_PRODUCT_WEIGHT
        if same_product_count > 0:
            concentration_score *= 1.5

        return min(concentration_score, 1.0)

    def _check_temporal_clustering(self, members: Set[str]) -> float:
        review_times = []
        for uid in members:
            for rid in self._user_reviews.get(uid, []):
                review = self._review_data.get(rid)
                if review:
                    review_times.append(review.create_time)

        if len(review_times) < 2:
            return 0.0

        review_times.sort()
        window = timedelta(hours=settings.GANG_TIME_WINDOW_HOURS)

        max_cluster = 1
        current_cluster = 1
        for i in range(1, len(review_times)):
            if review_times[i] - review_times[i - 1] <= window:
                current_cluster += 1
                max_cluster = max(max_cluster, current_cluster)
            else:
                current_cluster = 1

        temporal_score = max_cluster / len(review_times)
        return min(temporal_score, 1.0)

    def _check_account_characteristics(self, members: Set[str]) -> float:
        new_account_count = 0
        low_review_count = 0
        total = 0

        for uid in members:
            for rid in self._user_reviews.get(uid, []):
                review = self._review_data.get(rid)
                if review and review.user_profile:
                    total += 1
                    if review.user_profile.account_age_days < settings.GANG_ACCOUNT_AGE_NEW_DAYS:
                        new_account_count += 1
                    if review.user_profile.total_reviews <= 3:
                        low_review_count += 1

        if total == 0:
            return 0.0

        new_ratio = new_account_count / total
        low_ratio = low_review_count / total

        return (new_ratio + low_ratio) / 2.0

    def _calculate_suspicious_score(
        self,
        members: Set[str],
        mutual_vote_count: int,
        mutual_votes: List[Dict]
    ) -> Tuple[float, List[str]]:
        warnings = []

        rating_sim = self._calculate_rating_similarity(members)
        content_sim = self._calculate_content_similarity(members)
        product_conc = self._check_same_product_concentration(members)
        temporal = self._check_temporal_clustering(members)
        account_chars = self._check_account_characteristics(members)

        mutual_density = min(mutual_vote_count / max(len(members), 1), 1.0)

        if rating_sim > settings.GANG_RATING_SIMILARITY_THRESHOLD:
            warnings.append(f"群组成员评分高度相似 ({rating_sim:.2f})")

        if content_sim > settings.GANG_CONTENT_SIMILARITY_THRESHOLD:
            warnings.append(f"群组评论内容高度相似 ({content_sim:.2f})")

        if product_conc > 0.7:
            warnings.append(f"评论高度集中于同一商品 ({product_conc:.2f})")

        if temporal > 0.6:
            warnings.append(f"评论时间高度集中 ({temporal:.2f})")

        if account_chars > 0.5:
            warnings.append(f"群组成员多为新/低活跃账号 ({account_chars:.2f})")

        if mutual_density > 0.5:
            warnings.append(f"相互点赞密度异常 ({mutual_density:.2f})")

        suspicious_score = (
            mutual_density * 0.30 +
            rating_sim * 0.20 +
            content_sim * 0.15 +
            product_conc * 0.15 +
            temporal * 0.10 +
            account_chars * 0.10
        ) * 100.0

        return round(min(100.0, max(0.0, suspicious_score)), 2), warnings

    def detect_gangs(
        self,
        reviews: List[ReviewItem],
        vote_records: List[VoteRecord]
    ) -> List[GangDetectionResult]:
        self._build_vote_graph(vote_records)
        self._build_review_index(reviews)

        mutual_pairs = self._find_mutual_vote_pairs()
        clusters = self._find_gang_clusters(mutual_pairs)

        results = []
        for idx, cluster in enumerate(clusters, 1):
            cluster_mutual_votes = []
            total_mutual_count = 0

            for user_a, user_b, strength in mutual_pairs:
                if user_a in cluster and user_b in cluster:
                    total_mutual_count += strength
                    cluster_mutual_votes.append({
                        "user_a": user_a,
                        "user_b": user_b,
                        "mutual_vote_strength": strength
                    })

            suspicious_score, warnings = self._calculate_suspicious_score(
                cluster, total_mutual_count, cluster_mutual_votes
            )

            is_suspicious = suspicious_score >= settings.GANG_SUSPICIOUS_SCORE_THRESHOLD

            gang_id = f"gang_{uuid.uuid4().hex[:8]}"

            results.append(GangDetectionResult(
                gang_id=gang_id,
                member_count=len(cluster),
                mutual_vote_count=total_mutual_count,
                suspicious_score=suspicious_score,
                members=sorted(list(cluster)),
                mutual_votes=cluster_mutual_votes,
                is_suspicious=is_suspicious,
                warnings=warnings
            ))

        results.sort(key=lambda x: x.suspicious_score, reverse=True)
        return results

    def check_user_in_gangs(
        self,
        user_id: str,
        gang_results: List[GangDetectionResult]
    ) -> List[GangDetectionResult]:
        user_gangs = []
        for gang in gang_results:
            if user_id in gang.members:
                user_gangs.append(gang)
        return user_gangs

    def calculate_gang_penalty(
        self,
        user_id: str,
        gang_results: List[GangDetectionResult]
    ) -> Tuple[float, List[str]]:
        user_gangs = self.check_user_in_gangs(user_id, gang_results)
        if not user_gangs:
            return 0.0, []

        max_suspicious = max(g.suspicious_score for g in user_gangs)
        penalty = min(
            max_suspicious / 100.0 * settings.GANG_DETECTION_AUTHENTICITY_PENALTY,
            settings.GANG_DETECTION_AUTHENTICITY_PENALTY
        )

        warnings = []
        for gang in user_gangs:
            warnings.append(
                f"用户属于可疑评论团伙 {gang.gang_id} "
                f"(可疑度:{gang.suspicious_score:.1f}, 成员:{gang.member_count}人)"
            )

        return penalty, warnings
