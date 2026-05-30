import numpy as np
from typing import Dict, List, Tuple
from data_store import DataStore
from sklearn.metrics.pairwise import cosine_similarity


class CollaborativeFiltering:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    def compute_user_similarity(self, user1_id: int, user2_id: int) -> float:
        user1_ratings = self.data_store.get_user_ratings(user1_id)
        user2_ratings = self.data_store.get_user_ratings(user2_id)

        common_books = set(user1_ratings.keys()) & set(user2_ratings.keys())
        if len(common_books) < 2:
            return 0.0

        u1_ratings = np.array([user1_ratings[b] for b in common_books])
        u2_ratings = np.array([user2_ratings[b] for b in common_books])

        u1_mean = np.mean(u1_ratings)
        u2_mean = np.mean(u2_ratings)

        u1_centered = u1_ratings - u1_mean
        u2_centered = u2_ratings - u2_mean

        numerator = np.sum(u1_centered * u2_centered)
        denominator = np.sqrt(np.sum(u1_centered ** 2)) * np.sqrt(np.sum(u2_centered ** 2))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def compute_book_similarity(self, book1_id: int, book2_id: int) -> float:
        book1_ratings = self.data_store.get_book_ratings(book1_id)
        book2_ratings = self.data_store.get_book_ratings(book2_id)

        common_users = set(book1_ratings.keys()) & set(book2_ratings.keys())
        if len(common_users) < 2:
            return 0.0

        b1_ratings = np.array([book1_ratings[u] for u in common_users])
        b2_ratings = np.array([book2_ratings[u] for u in common_users])

        b1_mean = np.mean(b1_ratings)
        b2_mean = np.mean(b2_ratings)

        b1_centered = b1_ratings - b1_mean
        b2_centered = b2_ratings - b2_mean

        numerator = np.sum(b1_centered * b2_centered)
        denominator = np.sqrt(np.sum(b1_centered ** 2)) * np.sqrt(np.sum(b2_centered ** 2))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def user_based_recommend(self, user_id: int, top_n: int = 10) -> List[Tuple[int, float, str]]:
        user_ratings = self.data_store.get_user_ratings(user_id)
        if not user_ratings:
            return []

        all_users = self.data_store.get_all_users()
        similarities = []

        for other_user in all_users:
            if other_user != user_id:
                sim = self.compute_user_similarity(user_id, other_user)
                if sim > 0:
                    similarities.append((other_user, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similar_users = similarities[:50]

        predictions = {}
        similarity_sums = {}

        for sim_user, sim in top_similar_users:
            sim_user_ratings = self.data_store.get_user_ratings(sim_user)
            for book_id, rating in sim_user_ratings.items():
                if book_id not in user_ratings:
                    if book_id not in predictions:
                        predictions[book_id] = 0
                        similarity_sums[book_id] = 0
                    predictions[book_id] += sim * rating
                    similarity_sums[book_id] += sim

        recommendations = []
        for book_id in predictions:
            if similarity_sums[book_id] > 0:
                score = predictions[book_id] / similarity_sums[book_id]
                recommendations.append((book_id, score, "基于相似用户推荐"))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]

    def item_based_recommend(self, user_id: int, top_n: int = 10) -> List[Tuple[int, float, str]]:
        user_ratings = self.data_store.get_user_ratings(user_id)
        if not user_ratings:
            return []

        predictions = {}
        similarity_sums = {}

        for rated_book, user_rating in user_ratings.items():
            all_books = self.data_store.get_all_books()
            for book_id in all_books:
                if book_id not in user_ratings:
                    sim = self.compute_book_similarity(rated_book, book_id)
                    if sim > 0:
                        if book_id not in predictions:
                            predictions[book_id] = 0
                            similarity_sums[book_id] = 0
                        predictions[book_id] += sim * user_rating
                        similarity_sums[book_id] += sim

        recommendations = []
        for book_id in predictions:
            if similarity_sums[book_id] > 0:
                score = predictions[book_id] / similarity_sums[book_id]
                recommendations.append((book_id, score, "基于相似书籍推荐"))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]

    def recommend(self, user_id: int, top_n: int = 10) -> List[Tuple[int, float, str]]:
        user_based_recs = self.user_based_recommend(user_id, top_n * 2)
        item_based_recs = self.item_based_recommend(user_id, top_n * 2)

        combined = {}
        for book_id, score, reason in user_based_recs:
            if book_id not in combined:
                combined[book_id] = {'score': 0, 'count': 0, 'reasons': []}
            combined[book_id]['score'] += score * 0.5
            combined[book_id]['count'] += 1
            combined[book_id]['reasons'].append(reason)

        for book_id, score, reason in item_based_recs:
            if book_id not in combined:
                combined[book_id] = {'score': 0, 'count': 0, 'reasons': []}
            combined[book_id]['score'] += score * 0.5
            combined[book_id]['count'] += 1
            combined[book_id]['reasons'].append(reason)

        recommendations = []
        for book_id, data in combined.items():
            avg_score = data['score'] / data['count'] if data['count'] > 0 else 0
            final_reason = " + ".join(set(data['reasons']))
            recommendations.append((book_id, avg_score, final_reason))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]
