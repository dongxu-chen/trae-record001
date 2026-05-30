import numpy as np
from typing import Dict, List, Tuple
from data_store import DataStore
from collections import defaultdict
from datetime import datetime, timedelta


class ColdStartHandler:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    def _compute_popularity_score(self, book_id: int) -> float:
        book = self.data_store.get_book(book_id)
        if not book or book.total_ratings == 0:
            return 0.0
        return book.avg_rating * np.log1p(book.total_ratings)

    def handle_new_user(self, user_id: int, top_n: int = 10) -> List[Tuple[int, float, str]]:
        user = self.data_store.get_user(user_id)
        user_genres = set(user.favorite_genres) if user and user.favorite_genres else None

        popularity_books = self.data_store.get_books_by_popularity(top_n * 3)
        hot_genres = self.data_store.get_hot_genres(top_n=5)
        hot_genre_names = {g for g, _ in hot_genres}

        scored = []
        for book_id, pop_score in popularity_books:
            book = self.data_store.get_book(book_id)
            if not book:
                continue

            boosted_score = pop_score
            reason_parts = []

            if user_genres and set(book.genres) & user_genres:
                overlap = len(set(book.genres) & user_genres)
                boosted_score *= (1.0 + 0.3 * overlap)
                reason_parts.append("偏好类型")

            if set(book.genres) & hot_genre_names:
                boosted_score *= 1.2
                reason_parts.append("热门类型")

            reason = " + ".join(reason_parts) if reason_parts else "流行度推荐"
            scored.append((book_id, boosted_score, reason))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def handle_new_book(self, book_id: int, top_n: int = 10) -> List[int]:
        book = self.data_store.get_book(book_id)
        if not book:
            return []

        similar_books = []
        for other_book_id in self.data_store.get_all_books():
            if other_book_id != book_id:
                other_book = self.data_store.get_book(other_book_id)
                if other_book:
                    genre_overlap = len(set(book.genres) & set(other_book.genres))
                    if genre_overlap > 0:
                        similar_books.append((other_book_id, genre_overlap, other_book.avg_rating))

        similar_books.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return [b[0] for b in similar_books[:top_n]]


class DiversityController:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    def _genre_vector(self, book_id: int) -> np.ndarray:
        all_genres = sorted({g for b in self.data_store.books.values() for g in b.genres})
        genre_idx = {g: i for i, g in enumerate(all_genres)}
        vec = np.zeros(len(all_genres))
        book = self.data_store.get_book(book_id)
        if book:
            for g in book.genres:
                if g in genre_idx:
                    vec[genre_idx[g]] = 1.0
        return vec

    def compute_genre_diversity(self, book_ids: List[int]) -> float:
        genre_counts = defaultdict(int)
        total_books = len(book_ids)
        if total_books == 0:
            return 0.0

        for book_id in book_ids:
            book = self.data_store.get_book(book_id)
            if book:
                for genre in book.genres:
                    genre_counts[genre] += 1

        if not genre_counts:
            return 0.0

        distribution = np.array(list(genre_counts.values())) / (total_books * 1.0)
        entropy = -np.sum(distribution * np.log2(distribution + 1e-10))
        max_entropy = np.log2(len(genre_counts)) if len(genre_counts) > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        dot = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def mmr_rerank(self, recommendations: List[Tuple[int, float, str]],
                    top_n: int = 10,
                    lambda_param: float = 0.5) -> List[Tuple[int, float, str]]:
        if not recommendations:
            return []

        rec_dict = {book_id: (score, reason) for book_id, score, reason in recommendations}
        all_ids = [r[0] for r in recommendations]

        genre_vectors = {}
        for book_id in all_ids:
            genre_vectors[book_id] = self._genre_vector(book_id)

        max_score = max(s for _, s, _ in recommendations) if recommendations else 1.0
        if max_score == 0:
            max_score = 1.0
        relevance = {}
        for book_id, score, _ in recommendations:
            relevance[book_id] = score / max_score

        selected: List[int] = []
        selected_vectors: List[np.ndarray] = []
        remaining = set(all_ids)

        first_id = max(remaining, key=lambda bid: relevance[bid])
        selected.append(first_id)
        selected_vectors.append(genre_vectors[first_id])
        remaining.remove(first_id)

        while len(selected) < top_n and remaining:
            best_id = None
            best_mmr = -float('inf')

            for candidate_id in remaining:
                rel = relevance[candidate_id]

                if selected_vectors:
                    max_sim = max(
                        self._similarity(genre_vectors[candidate_id], sv)
                        for sv in selected_vectors
                    )
                else:
                    max_sim = 0.0

                mmr = lambda_param * rel - (1 - lambda_param) * max_sim
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_id = candidate_id

            if best_id is not None:
                selected.append(best_id)
                selected_vectors.append(genre_vectors[best_id])
                remaining.remove(best_id)

        result = []
        for book_id in selected:
            score, reason = rec_dict[book_id]
            result.append((book_id, score, reason))

        return result

    def rerank_for_diversity(self, recommendations: List[Tuple[int, float, str]],
                               top_n: int = 10,
                               diversity_weight: float = 0.3) -> List[Tuple[int, float, str]]:
        lambda_param = 1.0 - diversity_weight
        return self.mmr_rerank(recommendations, top_n, lambda_param)

    def ensure_genre_coverage(self, recommendations: List[Tuple[int, float, str]],
                               min_genres: int = 3, top_n: int = 10) -> List[Tuple[int, float, str]]:
        if len(recommendations) <= top_n:
            return recommendations

        selected_genres = set()
        selected = []
        remaining = recommendations.copy()

        for book_id, score, reason in recommendations:
            book = self.data_store.get_book(book_id)
            if book and len(selected_genres) < min_genres:
                new_genres = set(book.genres) - selected_genres
                if new_genres:
                    selected.append((book_id, score, reason))
                    selected_genres.update(book.genres)
                    remaining = [r for r in remaining if r[0] != book_id]

        for book_id, score, reason in remaining:
            if len(selected) >= top_n:
                break
            selected.append((book_id, score, reason))

        return selected[:top_n]


class ExplorationExploitation:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.user_click_history: Dict[int, List[Tuple[int, datetime]]] = defaultdict(list)
        self.user_session_start: Dict[int, datetime] = {}
        self.epsilon_0 = 0.8
        self.decay_rate = 0.05
        self.min_epsilon = 0.05

    def _ensure_session(self, user_id: int):
        if user_id not in self.user_session_start:
            self.user_session_start[user_id] = datetime.now()

    def record_click(self, user_id: int, book_id: int):
        self._ensure_session(user_id)
        self.user_click_history[user_id].append((book_id, datetime.now()))

    def get_exploration_rate(self, user_id: int, base_rate: float = 0.2) -> float:
        self._ensure_session(user_id)
        session_start = self.user_session_start[user_id]
        elapsed_hours = (datetime.now() - session_start).total_seconds() / 3600.0

        n_ratings = len(self.data_store.get_user_ratings(user_id))
        n_clicks = len(self.user_click_history.get(user_id, []))

        interaction_factor = n_ratings + n_clicks

        epsilon = self.epsilon_0 * np.exp(-self.decay_rate * interaction_factor)

        time_boost = max(0.0, 1.0 - 0.02 * elapsed_hours)
        epsilon *= time_boost

        epsilon = max(epsilon, self.min_epsilon)

        if interaction_factor < 3:
            epsilon = max(epsilon, 0.6)
        elif interaction_factor < 5:
            epsilon = max(epsilon, 0.4)

        return min(epsilon, 1.0)

    def add_exploration_items(self, recommendations: List[Tuple[int, float, str]],
                               user_id: int,
                               exploration_rate: float = 0.2) -> List[Tuple[int, float, str]]:
        epsilon = self.get_exploration_rate(user_id, exploration_rate)
        n_explore = max(1, int(len(recommendations) * epsilon))

        user_ratings = self.data_store.get_user_ratings(user_id)
        user_genres = set()
        for book_id in user_ratings:
            book = self.data_store.get_book(book_id)
            if book:
                user_genres.update(book.genres)

        rec_book_ids = {r[0] for r in recommendations}

        explore_candidates = []
        for book_id in self.data_store.get_all_books():
            if book_id not in user_ratings and book_id not in rec_book_ids:
                book = self.data_store.get_book(book_id)
                if book:
                    genre_overlap = len(set(book.genres) & user_genres) if user_genres else 0
                    if genre_overlap == 0 or genre_overlap < len(book.genres) // 2:
                        explore_score = book.avg_rating * np.log1p(book.total_ratings) * 0.5
                        explore_candidates.append((book_id, explore_score, "探索新类型"))

        explore_candidates.sort(key=lambda x: x[1], reverse=True)
        explore_items = explore_candidates[:n_explore]

        result = recommendations.copy()
        for item in explore_items:
            insert_pos = np.random.randint(0, len(result) + 1)
            result.insert(insert_pos, item)

        return result
