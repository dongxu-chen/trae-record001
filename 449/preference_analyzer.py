import pandas as pd
import numpy as np
from collections import Counter


class PreferenceAnalyzer:
    def __init__(self):
        self.genre_list = ['动作', '喜剧', '剧情', '科幻', '恐怖', '爱情', '动画', '悬疑', '冒险', '战争']

    def analyze_user_preferences(self, user_id, ratings_df, movies_df, users_df):
        user_ratings = ratings_df[ratings_df['user_id'] == user_id]
        
        if len(user_ratings) == 0:
            return {'error': '该用户暂无评分数据'}
        
        user_ratings_with_movies = pd.merge(user_ratings, movies_df, on='movie_id', how='left')
        
        user_info = {}
        if users_df is not None:
            user_row = users_df[users_df['user_id'] == user_id]
            if len(user_row) > 0:
                user_row = user_row.iloc[0]
                user_info = {
                    'age_group': user_row['age_group'],
                    'gender': user_row['gender'],
                    'occupation': user_row['occupation'],
                    'city': user_row['city'],
                    'watch_frequency': user_row['watch_frequency']
                }
        
        analysis = {
            'user_id': user_id,
            'user_info': user_info,
            'basic_stats': self._get_basic_stats(user_ratings_with_movies),
            'genre_preferences': self._analyze_genre_preferences(user_ratings_with_movies),
            'director_preferences': self._analyze_director_preferences(user_ratings_with_movies),
            'actor_preferences': self._analyze_actor_preferences(user_ratings_with_movies),
            'year_preferences': self._analyze_year_preferences(user_ratings_with_movies),
            'rating_distribution': self._get_rating_distribution(user_ratings),
            'watch_patterns': self._analyze_watch_patterns(user_ratings),
            'preference_summary': self._generate_preference_summary(user_ratings_with_movies)
        }
        
        return analysis

    def _get_basic_stats(self, user_ratings_with_movies):
        total_ratings = len(user_ratings_with_movies)
        avg_rating = user_ratings_with_movies['rating'].mean()
        std_rating = user_ratings_with_movies['rating'].std()
        high_rated = len(user_ratings_with_movies[user_ratings_with_movies['rating'] >= 4.0])
        low_rated = len(user_ratings_with_movies[user_ratings_with_movies['rating'] <= 2.0])
        
        return {
            'total_ratings': total_ratings,
            'average_rating': round(avg_rating, 2),
            'rating_std': round(std_rating, 2) if not pd.isna(std_rating) else 0,
            'high_rated_count': high_rated,
            'high_rated_ratio': round(high_rated / total_ratings, 2),
            'low_rated_count': low_rated,
            'low_rated_ratio': round(low_rated / total_ratings, 2)
        }

    def _analyze_genre_preferences(self, user_ratings_with_movies):
        genre_ratings = {}
        
        for _, row in user_ratings_with_movies.iterrows():
            genres = str(row['genres']).split('|')
            rating = row['rating']
            
            for genre in genres:
                if genre not in genre_ratings:
                    genre_ratings[genre] = []
                genre_ratings[genre].append(rating)
        
        genre_stats = []
        for genre, ratings in genre_ratings.items():
            genre_stats.append({
                'genre': genre,
                'count': len(ratings),
                'avg_rating': round(np.mean(ratings), 2),
                'preference_score': round((np.mean(ratings) - 3) * len(ratings) / 10, 2)
            })
        
        genre_stats.sort(key=lambda x: x['preference_score'], reverse=True)
        
        return {
            'top_preferred': genre_stats[:5],
            'least_preferred': genre_stats[-3:],
            'all_genres': genre_stats
        }

    def _analyze_director_preferences(self, user_ratings_with_movies):
        director_ratings = {}
        
        for _, row in user_ratings_with_movies.iterrows():
            director = row['director']
            rating = row['rating']
            
            if director not in director_ratings:
                director_ratings[director] = []
            director_ratings[director].append(rating)
        
        director_stats = []
        for director, ratings in director_ratings.items():
            if len(ratings) >= 1:
                director_stats.append({
                    'director': director,
                    'count': len(ratings),
                    'avg_rating': round(np.mean(ratings), 2)
                })
        
        director_stats.sort(key=lambda x: x['avg_rating'], reverse=True)
        
        return {
            'top_directors': director_stats[:5]
        }

    def _analyze_actor_preferences(self, user_ratings_with_movies):
        actor_ratings = {}
        
        for _, row in user_ratings_with_movies.iterrows():
            actors = str(row['actors']).split('|')
            rating = row['rating']
            
            for actor in actors:
                if actor not in actor_ratings:
                    actor_ratings[actor] = []
                actor_ratings[actor].append(rating)
        
        actor_stats = []
        for actor, ratings in actor_ratings.items():
            if len(ratings) >= 2:
                actor_stats.append({
                    'actor': actor,
                    'count': len(ratings),
                    'avg_rating': round(np.mean(ratings), 2)
                })
        
        actor_stats.sort(key=lambda x: x['avg_rating'], reverse=True)
        
        return {
            'top_actors': actor_stats[:5]
        }

    def _analyze_year_preferences(self, user_ratings_with_movies):
        user_ratings_with_movies['release_decade'] = (user_ratings_with_movies['release_year'] // 10) * 10
        
        decade_stats = user_ratings_with_movies.groupby('release_decade').agg({
            'rating': ['count', 'mean']
        }).reset_index()
        
        decade_stats.columns = ['decade', 'count', 'avg_rating']
        decade_stats['avg_rating'] = decade_stats['avg_rating'].round(2)
        decade_stats = decade_stats.sort_values('avg_rating', ascending=False)
        
        return decade_stats.to_dict('records')

    def _get_rating_distribution(self, user_ratings):
        distribution = user_ratings['rating'].value_counts().sort_index()
        
        result = []
        for rating, count in distribution.items():
            result.append({
                'rating': float(rating),
                'count': int(count),
                'ratio': round(count / len(user_ratings), 2)
            })
        
        return result

    def _analyze_watch_patterns(self, user_ratings):
        user_ratings['rating_date'] = pd.to_datetime(user_ratings['rating_date'])
        user_ratings['month'] = user_ratings['rating_date'].dt.month
        user_ratings['dayofweek'] = user_ratings['rating_date'].dt.dayofweek
        
        month_activity = user_ratings.groupby('month').size().sort_values(ascending=False)
        weekday_activity = user_ratings.groupby('dayofweek').size().sort_values(ascending=False)
        
        return {
            'most_active_months': month_activity.head(3).index.tolist(),
            'most_active_weekdays': weekday_activity.head(3).index.tolist()
        }

    def _generate_preference_summary(self, user_ratings_with_movies):
        genre_prefs = self._analyze_genre_preferences(user_ratings_with_movies)
        
        top_genres = [g['genre'] for g in genre_prefs['top_preferred'][:3]]
        
        summary_parts = []
        
        if top_genres:
            summary_parts.append(f"偏好{', '.join(top_genres)}类型的电影")
        
        high_rated_ratio = len(user_ratings_with_movies[user_ratings_with_movies['rating'] >= 4.0]) / len(user_ratings_with_movies)
        if high_rated_ratio > 0.5:
            summary_parts.append("评分较为宽松")
        elif high_rated_ratio < 0.2:
            summary_parts.append("评分较为严格")
        
        avg_rating = user_ratings_with_movies['rating'].mean()
        if avg_rating >= 4.0:
            summary_parts.append("整体观影满意度较高")
        elif avg_rating <= 2.5:
            summary_parts.append("整体观影满意度较低")
        
        return '；'.join(summary_parts) if summary_parts else "暂无明显偏好特征"

    def compare_users(self, user_id1, user_id2, ratings_df, movies_df):
        user1_prefs = self.analyze_user_preferences(user_id1, ratings_df, movies_df, None)
        user2_prefs = self.analyze_user_preferences(user_id2, ratings_df, movies_df, None)
        
        if 'error' in user1_prefs or 'error' in user2_prefs:
            return {'error': '无法比较，部分用户数据缺失'}
        
        user1_genres = set(g['genre'] for g in user1_prefs['genre_preferences']['top_preferred'])
        user2_genres = set(g['genre'] for g in user2_prefs['genre_preferences']['top_preferred'])
        
        common_genres = user1_genres.intersection(user2_genres)
        
        user1_ratings = ratings_df[ratings_df['user_id'] == user_id1]
        user2_ratings = ratings_df[ratings_df['user_id'] == user_id2]
        
        common_movies = pd.merge(user1_ratings, user2_ratings, on='movie_id', suffixes=('_user1', '_user2'))
        
        comparison = {
            'user1_id': user_id1,
            'user2_id': user_id2,
            'common_preferred_genres': list(common_genres),
            'common_movies_count': len(common_movies),
            'user1_avg_rating': user1_prefs['basic_stats']['average_rating'],
            'user2_avg_rating': user2_prefs['basic_stats']['average_rating'],
            'rating_difference': abs(user1_prefs['basic_stats']['average_rating'] - user2_prefs['basic_stats']['average_rating'])
        }
        
        if len(common_movies) > 0:
            comparison['common_movies_agreement'] = round(
                1 - np.mean(np.abs(common_movies['rating_user1'] - common_movies['rating_user2'])) / 4, 2
            )
        
        return comparison
