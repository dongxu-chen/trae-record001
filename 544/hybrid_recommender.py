import numpy as np
from typing import Dict, List, Tuple
from data_store import DataStore
from collaborative_filtering import CollaborativeFiltering
from matrix_factorization import MatrixFactorization
from social_recommender import SocialRecommender
from cold_start_and_diversity import ColdStartHandler, DiversityController, ExplorationExploitation
from series_recommender import SeriesRecommender
from reading_predictor import ReadingPredictor
from review_summarizer import ReviewSummarizer


class HybridRecommender:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.collaborative_filtering = CollaborativeFiltering(data_store)
        self.matrix_factorization = MatrixFactorization(data_store)
        self.social_recommender = SocialRecommender(data_store)
        self.cold_start_handler = ColdStartHandler(data_store)
        self.diversity_controller = DiversityController(data_store)
        self.exploration_exploitation = ExplorationExploitation(data_store)
        self.series_recommender = SeriesRecommender(data_store)
        self.reading_predictor = ReadingPredictor(data_store)
        self.review_summarizer = ReviewSummarizer(data_store)

    def train(self):
        self.matrix_factorization.train()

    def recommend(self, user_id: int, top_n: int = 10,
                  diversity_weight: float = 0.3,
                  exploration_rate: float = 0.2) -> List[Tuple[int, float, str]]:
        
        if self.data_store.is_new_user(user_id):
            recommendations = self.cold_start_handler.handle_new_user(user_id, top_n * 2)
            recommendations = self.diversity_controller.rerank_for_diversity(
                recommendations, top_n, diversity_weight
            )
            return recommendations[:top_n]

        cf_recs = self.collaborative_filtering.recommend(user_id, top_n * 2)
        mf_recs = self.matrix_factorization.recommend(user_id, top_n * 2)
        social_recs = self.social_recommender.recommend(user_id, top_n * 2)
        series_recs = self.series_recommender.recommend_next_in_series(user_id, top_n * 2)

        combined_scores = {}
        combined_reasons = {}

        for book_id, score, reason in cf_recs:
            if book_id not in combined_scores:
                combined_scores[book_id] = 0
                combined_reasons[book_id] = []
            combined_scores[book_id] += score * 0.30
            combined_reasons[book_id].append(reason)

        for book_id, score, reason in mf_recs:
            if book_id not in combined_scores:
                combined_scores[book_id] = 0
                combined_reasons[book_id] = []
            combined_scores[book_id] += score * 0.35
            combined_reasons[book_id].append(reason)

        for book_id, score, reason in social_recs:
            if book_id not in combined_scores:
                combined_scores[book_id] = 0
                combined_reasons[book_id] = []
            combined_scores[book_id] += score * 0.20
            combined_reasons[book_id].append(reason)

        for book_id, score, reason in series_recs:
            if book_id not in combined_scores:
                combined_scores[book_id] = 0
                combined_reasons[book_id] = []
            combined_scores[book_id] += score * 0.15
            combined_reasons[book_id].append(reason)

        recommendations = []
        for book_id in combined_scores:
            reasons = list(set(combined_reasons[book_id]))
            final_reason = " + ".join(reasons)[:60]
            recommendations.append((book_id, combined_scores[book_id], final_reason))

        recommendations.sort(key=lambda x: x[1], reverse=True)

        actual_exploration_rate = self.exploration_exploitation.get_exploration_rate(
            user_id, exploration_rate
        )
        recommendations = self.exploration_exploitation.add_exploration_items(
            recommendations, user_id, actual_exploration_rate
        )

        recommendations = self.diversity_controller.rerank_for_diversity(
            recommendations, top_n, diversity_weight
        )

        return recommendations[:top_n]

    def explain_recommendation(self, user_id: int, book_id: int) -> Dict:
        explanation = {
            'book_id': book_id,
            'user_id': user_id,
            'factors': []
        }

        user_ratings = self.data_store.get_user_ratings(user_id)
        book = self.data_store.get_book(book_id)

        if book_id in user_ratings:
            explanation['already_read'] = True
            explanation['user_rating'] = user_ratings[book_id]
        else:
            explanation['already_read'] = False

        if book:
            explanation['book_info'] = {
                'title': book.title,
                'author': book.author,
                'genres': book.genres,
                'avg_rating': book.avg_rating
            }

            if not user_ratings:
                explanation['cold_start'] = True
                explanation['reason'] = '新用户推荐，基于热门或用户偏好类型'
            else:
                explanation['cold_start'] = False

                favorite_genres = []
                for rated_book_id, rating in user_ratings.items():
                    if rating >= 4.0:
                        rated_book = self.data_store.get_book(rated_book_id)
                        if rated_book:
                            favorite_genres.extend(rated_book.genres)
                
                genre_overlap = len(set(book.genres) & set(favorite_genres)) if favorite_genres else 0
                if genre_overlap > 0:
                    explanation['factors'].append({
                        'type': 'genre_match',
                        'description': f'与您喜欢的类型有{genre_overlap}个重叠',
                        'strength': genre_overlap / len(book.genres) if book.genres else 0
                    })

        friends = self.data_store.get_user_friends(user_id)
        friend_ratings = []
        for friend_id in friends:
            friend_rated = self.data_store.get_user_ratings(friend_id)
            if book_id in friend_rated and friend_rated[book_id] >= 4.0:
                friend_user = self.data_store.get_user(friend_id)
                friend_name = friend_user.username if friend_user else str(friend_id)
                friend_ratings.append(friend_name)
        
        if friend_ratings:
            explanation['factors'].append({
                'type': 'social',
                'description': f'好友{friend_ratings[0]}等{len(friend_ratings)}人喜欢这本书',
                'strength': len(friend_ratings) / len(friends) if friends else 0
            })

        return explanation

    def get_recommendation_stats(self, user_id: int) -> Dict:
        user_ratings = self.data_store.get_user_ratings(user_id)
        recommendations = self.recommend(user_id, top_n=20)

        stats = {
            'user_id': user_id,
            'is_new_user': self.data_store.is_new_user(user_id),
            'num_ratings': len(user_ratings),
            'num_recommendations': len(recommendations),
            'genre_coverage': self.diversity_controller.compute_genre_diversity([r[0] for r in recommendations]),
            'exploration_rate': self.exploration_exploitation.get_exploration_rate(user_id)
        }

        return stats
