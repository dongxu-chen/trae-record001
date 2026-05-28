import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder, StandardScaler
from scipy.sparse import csr_matrix
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist
import warnings
warnings.filterwarnings('ignore')

GENRE_LIST = ['动作', '喜剧', '剧情', '科幻', '恐怖', '爱情', '动画', '悬疑', '冒险', '战争']


class CollaborativeFilteringRecommender:
    def __init__(self, n_neighbors=20, n_clusters=None, exploration_ratio=0.2):
        self.n_neighbors = n_neighbors
        self.n_clusters = n_clusters
        self.exploration_ratio = exploration_ratio
        self.user_similarity_matrix = None
        self.item_similarity_matrix = None
        self.user_item_matrix = None
        self.user_id_to_idx = {}
        self.movie_id_to_idx = {}
        self.idx_to_user_id = {}
        self.idx_to_movie_id = {}
        self.users_df = None
        self.movies_df = None
        self.ratings_df = None
        self.user_clusters = None
        self.cluster_labels = None
        self.optimal_n_clusters = None
        self.demographic_model = None
        self._demo_encoder_age = LabelEncoder()
        self._demo_encoder_gender = LabelEncoder()
        self._demo_encoder_occupation = LabelEncoder()
        self._demo_encoder_city = LabelEncoder()
        self._demo_encoder_freq = LabelEncoder()
        self._demo_scaler = StandardScaler()
        self._movie_popularity = {}
        self.user_watch_sequences = {}
        self.sequence_model = {}
        self.user_time_patterns = {}

    def fit(self, ratings_df, users_df=None, movies_df=None):
        self.ratings_df = ratings_df
        self.users_df = users_df
        self.movies_df = movies_df

        user_ids = sorted(ratings_df['user_id'].unique())
        movie_ids = sorted(movies_df['movie_id'].unique()) if movies_df is not None else sorted(ratings_df['movie_id'].unique())

        self.user_id_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
        self.movie_id_to_idx = {mid: idx for idx, mid in enumerate(movie_ids)}
        self.idx_to_user_id = {idx: uid for uid, idx in self.user_id_to_idx.items()}
        self.idx_to_movie_id = {idx: mid for mid, idx in self.movie_id_to_idx.items()}

        n_users = len(user_ids)
        n_movies = len(movie_ids)

        valid_ratings = ratings_df[ratings_df['movie_id'].isin(self.movie_id_to_idx)]
        rows = valid_ratings['user_id'].map(self.user_id_to_idx).values
        cols = valid_ratings['movie_id'].map(self.movie_id_to_idx).values
        values = valid_ratings['rating'].values

        self.user_item_matrix = csr_matrix((values, (rows, cols)), shape=(n_users, n_movies))

        self._compute_user_similarity()
        self._compute_item_similarity()
        self._compute_movie_popularity()
        self._build_demographic_model()
        self._build_hierarchical_clusters()
        self._build_user_watch_sequences()
        self._analyze_user_time_patterns()
        self._train_sequence_model()

        return self

    def _compute_user_similarity(self):
        user_item_dense = self.user_item_matrix.toarray()
        user_mean = np.mean(user_item_dense, axis=1, keepdims=True)
        user_centered = user_item_dense - user_mean
        user_centered[user_item_dense == 0] = 0
        self.user_similarity_matrix = cosine_similarity(user_centered)

    def _compute_item_similarity(self):
        user_item_dense = self.user_item_matrix.toarray()
        item_mean = np.mean(user_item_dense, axis=0, keepdims=True)
        item_centered = user_item_dense - item_mean
        item_centered[user_item_dense == 0] = 0
        self.item_similarity_matrix = cosine_similarity(item_centered.T)

    def _compute_movie_popularity(self):
        if self.ratings_df is None:
            return
        movie_stats = self.ratings_df.groupby('movie_id').agg(
            rating_count=('rating', 'count'),
            rating_mean=('rating', 'mean')
        ).reset_index()
        max_count = movie_stats['rating_count'].max() if len(movie_stats) > 0 else 1
        for _, row in movie_stats.iterrows():
            popularity = 0.6 * (row['rating_count'] / max_count) + 0.4 * (row['rating_mean'] / 5.0)
            self._movie_popularity[row['movie_id']] = round(popularity, 4)

    def _build_demographic_model(self):
        if self.users_df is None or self.ratings_df is None:
            return

        user_ratings = self.ratings_df.groupby('user_id').agg(
            avg_rating=('rating', 'mean'),
            rating_count=('rating', 'count')
        ).reset_index()

        merged = pd.merge(self.users_df, user_ratings, on='user_id', how='left')
        merged['avg_rating'] = merged['avg_rating'].fillna(3.0)
        merged['rating_count'] = merged['rating_count'].fillna(0)

        self._demo_encoder_age.fit(merged['age_group'].astype(str))
        self._demo_encoder_gender.fit(merged['gender'].astype(str))
        self._demo_encoder_occupation.fit(merged['occupation'].astype(str))
        self._demo_encoder_city.fit(merged['city'].astype(str))
        self._demo_encoder_freq.fit(merged['watch_frequency'].astype(str))

        genre_pref_cols = [c for c in merged.columns if c.startswith('pref_')]
        feature_matrix = np.column_stack([
            self._demo_encoder_age.transform(merged['age_group'].astype(str)),
            self._demo_encoder_gender.transform(merged['gender'].astype(str)),
            self._demo_encoder_occupation.transform(merged['occupation'].astype(str)),
            self._demo_encoder_city.transform(merged['city'].astype(str)),
            self._demo_encoder_freq.transform(merged['watch_frequency'].astype(str)),
        ] + [merged[c].fillna(0.5).values for c in genre_pref_cols])

        self._demo_scaler.fit(feature_matrix)
        self.demographic_model = {
            'features': self._demo_scaler.transform(feature_matrix),
            'user_ids': merged['user_id'].values,
            'avg_ratings': merged['avg_rating'].values,
            'genre_preferences': {row['user_id']: {c: row[c] for c in genre_pref_cols} for _, row in merged.iterrows()}
        }

    def _encode_new_user_demographics(self, user_row):
        def safe_transform(encoder, val):
            val = str(val)
            if val in encoder.classes_:
                return encoder.transform([val])[0]
            return len(encoder.classes_) // 2

        genre_pref_cols = [c for c in user_row.index if c.startswith('pref_')]
        feature_vec = np.array([[
            safe_transform(self._demo_encoder_age, user_row['age_group']),
            safe_transform(self._demo_encoder_gender, user_row['gender']),
            safe_transform(self._demo_encoder_occupation, user_row['occupation']),
            safe_transform(self._demo_encoder_city, user_row['city']),
            safe_transform(self._demo_encoder_freq, user_row['watch_frequency']),
        ] + [user_row.get(c, 0.5) for c in genre_pref_cols]])

        return self._demo_scaler.transform(feature_vec)[0]

    def _build_hierarchical_clusters(self):
        if self.demographic_model is None:
            return

        features = self.demographic_model['features']
        n_samples = features.shape[0]

        if n_samples < 4:
            self.optimal_n_clusters = 1
            self.cluster_labels = np.zeros(n_samples, dtype=int)
            self.user_clusters = {self.demographic_model['user_ids'][i]: 0 for i in range(n_samples)}
            return

        distance_matrix = pdist(features, metric='euclidean')
        Z = linkage(distance_matrix, method='ward')

        if self.n_clusters is not None:
            self.optimal_n_clusters = min(self.n_clusters, n_samples)
        else:
            self.optimal_n_clusters = self._find_optimal_clusters(Z, n_samples)

        self.cluster_labels = fcluster(Z, t=self.optimal_n_clusters, criterion='maxclust') - 1
        self.user_clusters = {
            self.demographic_model['user_ids'][i]: int(self.cluster_labels[i])
            for i in range(n_samples)
        }

        print(f"层次聚类完成: {self.optimal_n_clusters} 个聚类")

    def _find_optimal_clusters(self, Z, n_samples):
        max_k = min(15, n_samples // 3)
        max_k = max(max_k, 2)

        best_k = 2
        best_score = -1

        for k in range(2, max_k + 1):
            labels = fcluster(Z, t=k, criterion='maxclust') - 1

            cluster_sizes = np.bincount(labels)
            size_balance = 1.0 - np.std(cluster_sizes) / (np.mean(cluster_sizes) + 1e-8)
            size_balance = max(0, size_balance)

            total_inertia = 0.0
            features = self.demographic_model['features']
            for c in range(k):
                mask = labels == c
                if np.sum(mask) > 0:
                    centroid = features[mask].mean(axis=0)
                    total_inertia += np.sum((features[mask] - centroid) ** 2)

            total_inertia = max(total_inertia, 1e-8)
            score = size_balance * 0.4 + (1.0 / (1.0 + total_inertia / features.shape[0])) * 0.6

            if score > best_score:
                best_score = score
                best_k = k

        return best_k

    def _predict_user_based(self, user_idx, item_idx):
        user_similarities = self.user_similarity_matrix[user_idx]
        user_item_dense = self.user_item_matrix.toarray()
        item_ratings = user_item_dense[:, item_idx]
        rated_users = item_ratings > 0

        if not np.any(rated_users):
            return 3.0

        similar_users = user_similarities[rated_users]
        similar_ratings = item_ratings[rated_users]

        top_k_indices = np.argsort(similar_users)[-self.n_neighbors:]
        top_k_similarities = similar_users[top_k_indices]
        top_k_ratings = similar_ratings[top_k_indices]

        if np.sum(top_k_similarities) == 0:
            return np.mean(top_k_ratings)

        return np.sum(top_k_similarities * top_k_ratings) / np.sum(top_k_similarities)

    def _predict_item_based(self, user_idx, item_idx):
        item_similarities = self.item_similarity_matrix[item_idx]
        user_item_dense = self.user_item_matrix.toarray()
        user_ratings = user_item_dense[user_idx, :]
        rated_items = user_ratings > 0

        if not np.any(rated_items):
            return 3.0

        similar_items = item_similarities[rated_items]
        similar_ratings = user_ratings[rated_items]

        top_k_indices = np.argsort(similar_items)[-self.n_neighbors:]
        top_k_similarities = similar_items[top_k_indices]
        top_k_ratings = similar_ratings[top_k_indices]

        if np.sum(top_k_similarities) == 0:
            return np.mean(top_k_ratings)

        return np.sum(top_k_similarities * top_k_ratings) / np.sum(top_k_similarities)

    def _incorporate_context_features(self, user_id, movie_id, base_score):
        if self.users_df is None or self.movies_df is None:
            return base_score

        user_data = self.users_df[self.users_df['user_id'] == user_id]
        movie_data = self.movies_df[self.movies_df['movie_id'] == movie_id]

        if len(user_data) == 0 or len(movie_data) == 0:
            return base_score

        user_row = user_data.iloc[0]
        movie_row = movie_data.iloc[0]

        context_boost = 0.0

        movie_genres = movie_row['genres'].split('|')
        for genre in movie_genres:
            pref_score = user_row.get(f'pref_{genre}', 0.5)
            context_boost += (pref_score - 0.5) * 0.3

        if user_row['age_group'] in ['18-25', '26-35']:
            if '科幻' in movie_genres or '动作' in movie_genres:
                context_boost += 0.2

        if user_row['age_group'] in ['46-55', '55+']:
            if '剧情' in movie_genres or '爱情' in movie_genres:
                context_boost += 0.2

        if user_row['watch_frequency'] == '高频':
            context_boost += 0.1

        return base_score + context_boost

    def _is_cold_start(self, user_id):
        if user_id not in self.user_id_to_idx:
            return True
        user_idx = self.user_id_to_idx[user_id]
        user_ratings = self.user_item_matrix.getrow(user_idx).toarray().flatten()
        return np.sum(user_ratings > 0) < 3

    def _recommend_cold_start_demographic(self, user_id, top_n=10, explore_ratio=None):
        if explore_ratio is None:
            explore_ratio = self.exploration_ratio

        if self.users_df is None or self.demographic_model is None:
            return self._recommend_popular(top_n)

        user_data = self.users_df[self.users_df['user_id'] == user_id]
        if len(user_data) == 0:
            return self._recommend_popular(top_n)

        user_row = user_data.iloc[0]
        user_features = self._encode_new_user_demographics(user_row)

        all_features = self.demographic_model['features']
        similarities = cosine_similarity([user_features], all_features)[0]

        n_exploit = max(1, int(top_n * (1 - explore_ratio)))
        n_explore = top_n - n_exploit

        top_similar_idx = np.argsort(similarities)[::-1][:10]
        similar_user_ids = self.demographic_model['user_ids'][top_similar_idx]

        cluster_id = self._assign_cluster_for_user(user_features)

        movie_scores = {}
        for similar_uid in similar_user_ids:
            if similar_uid in self.user_id_to_idx:
                user_idx = self.user_id_to_idx[similar_uid]
                user_ratings = self.user_item_matrix.getrow(user_idx).toarray().flatten()
                sim = similarities[self.user_id_to_idx[similar_uid]]
                for movie_idx in range(len(user_ratings)):
                    if user_ratings[movie_idx] > 0:
                        mid = self.idx_to_movie_id[movie_idx]
                        if mid not in movie_scores:
                            movie_scores[mid] = {'weighted_sum': 0, 'weight_sum': 0}
                        movie_scores[mid]['weighted_sum'] += sim * user_ratings[movie_idx]
                        movie_scores[mid]['weight_sum'] += sim

        genre_pref = {}
        for genre in GENRE_LIST:
            genre_pref[genre] = user_row.get(f'pref_{genre}', 0.5)

        scored_movies = []
        for mid, scores in movie_scores.items():
            if scores['weight_sum'] > 0:
                base_score = scores['weighted_sum'] / scores['weight_sum']
            else:
                base_score = 3.0

            movie_row = self.movies_df[self.movies_df['movie_id'] == mid] if self.movies_df is not None else pd.DataFrame()
            genre_boost = 0.0
            if len(movie_row) > 0:
                for g in movie_row.iloc[0]['genres'].split('|'):
                    genre_boost += (genre_pref.get(g, 0.5) - 0.5) * 0.3

            final_score = base_score + genre_boost
            scored_movies.append((mid, final_score, 'exploit'))

        scored_movies.sort(key=lambda x: x[1], reverse=True)

        exploit_movies = scored_movies[:n_exploit]

        explore_movies = self._generate_exploration_movies(
            user_row, cluster_id, n_explore,
            exclude_mids={m[0] for m in exploit_movies}
        )

        results = []
        for mid, score, source in exploit_movies + explore_movies:
            movie_info = self._build_movie_info(mid, round(score, 2))
            movie_info['recommendation_source'] = source
            results.append(movie_info)

        return results

    def _recommend_popular(self, top_n):
        if not self._movie_popularity:
            return []
        sorted_movies = sorted(self._movie_popularity.items(), key=lambda x: x[1], reverse=True)
        results = []
        for mid, pop in sorted_movies[:top_n]:
            movie_info = self._build_movie_info(mid, round(pop * 5, 2))
            movie_info['recommendation_source'] = 'popular'
            results.append(movie_info)
        return results

    def _assign_cluster_for_user(self, user_features):
        if self.demographic_model is None or self.optimal_n_clusters is None:
            return 0
        all_features = self.demographic_model['features']
        similarities = cosine_similarity([user_features], all_features)[0]
        best_idx = np.argmax(similarities)
        return int(self.cluster_labels[best_idx])

    def _generate_exploration_movies(self, user_row, cluster_id, n_explore, exclude_mids=None):
        if exclude_mids is None:
            exclude_mids = set()

        if self.ratings_df is None or self.movies_df is None:
            return []

        user_genre_prefs = {}
        for genre in GENRE_LIST:
            user_genre_prefs[genre] = user_row.get(f'pref_{genre}', 0.5)

        explore_genres = sorted(user_genre_prefs, key=user_genre_prefs.get)[:3]

        candidate_movies = []
        for _, movie_row in self.movies_df.iterrows():
            mid = movie_row['movie_id']
            if mid in exclude_mids:
                continue
            movie_genres = movie_row['genres'].split('|')
            has_explore_genre = any(g in explore_genres for g in movie_genres)
            popularity = self._movie_popularity.get(mid, 0.3)
            diversity_score = 0.4 * (1.0 - popularity) + 0.6 * (1.0 if has_explore_genre else 0.0)
            candidate_movies.append((mid, diversity_score))

        candidate_movies.sort(key=lambda x: x[1], reverse=True)
        return [(mid, score, 'explore') for mid, score in candidate_movies[:n_explore]]

    def _build_movie_info(self, movie_id, predicted_rating):
        movie_info = {'movie_id': movie_id, 'predicted_rating': predicted_rating}
        if self.movies_df is not None:
            movie_row = self.movies_df[self.movies_df['movie_id'] == movie_id]
            if len(movie_row) > 0:
                r = movie_row.iloc[0]
                movie_info.update({
                    'title': r['title'],
                    'genres': r['genres'],
                    'director': r['director'],
                    'release_year': int(r['release_year']),
                })
        return movie_info

    def predict(self, user_id, movie_id, method='hybrid'):
        if self._is_cold_start(user_id):
            return self._predict_cold_start(user_id, movie_id)

        if user_id not in self.user_id_to_idx or movie_id not in self.movie_id_to_idx:
            return 3.0

        user_idx = self.user_id_to_idx[user_id]
        item_idx = self.movie_id_to_idx[movie_id]

        if method == 'user_based':
            score = self._predict_user_based(user_idx, item_idx)
        elif method == 'item_based':
            score = self._predict_item_based(user_idx, item_idx)
        elif method == 'hybrid':
            user_score = self._predict_user_based(user_idx, item_idx)
            item_score = self._predict_item_based(user_idx, item_idx)
            score = 0.5 * user_score + 0.5 * item_score
        else:
            raise ValueError("Method must be 'user_based', 'item_based', or 'hybrid'")

        score = self._incorporate_context_features(user_id, movie_id, score)

        return max(1.0, min(5.0, score))

    def _predict_cold_start(self, user_id, movie_id):
        if self.users_df is None or self.demographic_model is None:
            return 3.0

        user_data = self.users_df[self.users_df['user_id'] == user_id]
        if len(user_data) == 0:
            return 3.0

        user_row = user_data.iloc[0]
        user_features = self._encode_new_user_demographics(user_row)

        all_features = self.demographic_model['features']
        similarities = cosine_similarity([user_features], all_features)[0]
        top_similar_idx = np.argsort(similarities)[::-1][:5]

        if movie_id in self.movie_id_to_idx:
            movie_idx = self.movie_id_to_idx[movie_id]
            weighted_sum = 0.0
            weight_total = 0.0
            for idx in top_similar_idx:
                sim = similarities[idx]
                rating = self.user_item_matrix.getrow(idx).toarray().flatten()[movie_idx]
                if rating > 0:
                    weighted_sum += sim * rating
                    weight_total += sim

            if weight_total > 0:
                score = weighted_sum / weight_total
            else:
                score = 3.0
        else:
            score = 3.0

        score = self._incorporate_context_features(user_id, movie_id, score)
        return max(1.0, min(5.0, score))

    def recommend(self, user_id, top_n=10, exclude_rated=True, method='hybrid', explore_ratio=None):
        if self._is_cold_start(user_id):
            return self._recommend_cold_start_demographic(user_id, top_n, explore_ratio)

        user_idx = self.user_id_to_idx[user_id]
        user_item_dense = self.user_item_matrix.toarray()

        predictions = []
        for movie_id, movie_idx in self.movie_id_to_idx.items():
            if exclude_rated and user_item_dense[user_idx, movie_idx] > 0:
                continue
            pred_score = self.predict(user_id, movie_id, method)
            predictions.append((movie_id, pred_score))

        predictions.sort(key=lambda x: x[1], reverse=True)

        if explore_ratio is None:
            explore_ratio = self.exploration_ratio

        n_exploit = max(1, int(top_n * (1 - explore_ratio)))
        n_explore = top_n - n_exploit

        cluster_id = self.user_clusters.get(user_id, 0)
        user_row = self.users_df[self.users_df['user_id'] == user_id].iloc[0] if self.users_df is not None else None

        exploit_movies = predictions[:n_exploit]
        exclude_mids = {m[0] for m in exploit_movies}

        explore_movies = []
        if n_explore > 0 and user_row is not None:
            explore_movies = self._generate_exploration_movies(
                user_row, cluster_id, n_explore, exclude_mids
            )

        results = []
        for movie_id, score in exploit_movies:
            movie_info = self._build_movie_info(movie_id, round(score, 2))
            movie_info['recommendation_source'] = 'exploit'
            results.append(movie_info)

        for mid, score, source in explore_movies:
            movie_info = self._build_movie_info(mid, round(score, 2))
            movie_info['recommendation_source'] = source
            results.append(movie_info)

        return results

    def get_similar_users(self, user_id, top_n=5):
        if user_id not in self.user_id_to_idx:
            if self.users_df is not None and user_id in self.users_df['user_id'].values:
                return self._get_similar_users_demographic(user_id, top_n)
            return []

        user_idx = self.user_id_to_idx[user_id]
        similarities = self.user_similarity_matrix[user_idx]
        similar_indices = np.argsort(similarities)[::-1][1:top_n + 1]

        results = []
        for idx in similar_indices:
            similar_user_id = self.idx_to_user_id[idx]
            results.append({
                'user_id': similar_user_id,
                'similarity': round(similarities[idx], 4)
            })
        return results

    def _get_similar_users_demographic(self, user_id, top_n=5):
        if self.demographic_model is None:
            return []

        user_data = self.users_df[self.users_df['user_id'] == user_id]
        if len(user_data) == 0:
            return []

        user_features = self._encode_new_user_demographics(user_data.iloc[0])
        all_features = self.demographic_model['features']
        similarities = cosine_similarity([user_features], all_features)[0]

        top_indices = np.argsort(similarities)[::-1][:top_n + 1]
        results = []
        for idx in top_indices:
            uid = self.demographic_model['user_ids'][idx]
            if uid != user_id:
                results.append({
                    'user_id': uid,
                    'similarity': round(similarities[idx], 4),
                    'match_type': 'demographic'
                })
        return results[:top_n]

    def get_similar_movies(self, movie_id, top_n=5):
        if movie_id not in self.movie_id_to_idx:
            return []

        movie_idx = self.movie_id_to_idx[movie_id]
        similarities = self.item_similarity_matrix[movie_idx]
        similar_indices = np.argsort(similarities)[::-1][1:top_n + 1]

        results = []
        for idx in similar_indices:
            similar_movie_id = self.idx_to_movie_id[idx]
            movie_info = {'movie_id': similar_movie_id, 'similarity': round(similarities[idx], 4)}
            if self.movies_df is not None:
                movie_row = self.movies_df[self.movies_df['movie_id'] == similar_movie_id]
                if len(movie_row) > 0:
                    movie_info['title'] = movie_row.iloc[0]['title']
                    movie_info['genres'] = movie_row.iloc[0]['genres']
            results.append(movie_info)

        return results

    def get_cluster_info(self, user_id=None):
        if self.cluster_labels is None:
            return {}

        info = {
            'optimal_n_clusters': self.optimal_n_clusters,
            'cluster_sizes': {}
        }

        unique, counts = np.unique(self.cluster_labels, return_counts=True)
        for c, size in zip(unique, counts):
            info['cluster_sizes'][int(c)] = int(size)

        if user_id is not None:
            cluster_id = self.user_clusters.get(user_id, None)
            info['user_cluster'] = cluster_id
            if cluster_id is not None:
                cluster_user_ids = [uid for uid, cid in self.user_clusters.items() if cid == cluster_id]
                info['cluster_members_count'] = len(cluster_user_ids)

                if self.users_df is not None:
                    cluster_users = self.users_df[self.users_df['user_id'].isin(cluster_user_ids)]
                    if len(cluster_users) > 0:
                        info['cluster_demographics'] = {
                            'age_distribution': cluster_users['age_group'].value_counts().to_dict(),
                            'gender_distribution': cluster_users['gender'].value_counts().to_dict(),
                            'top_occupations': cluster_users['occupation'].value_counts().head(3).to_dict()
                        }

        return info

    def get_cluster_members(self, cluster_id, limit=20):
        if self.cluster_labels is None:
            return []
        member_ids = [uid for uid, cid in self.user_clusters.items() if cid == cluster_id]
        return member_ids[:limit]

    def _build_user_watch_sequences(self):
        if self.ratings_df is None or 'rating_date' not in self.ratings_df.columns:
            return

        for user_id in self.ratings_df['user_id'].unique():
            user_ratings = self.ratings_df[self.ratings_df['user_id'] == user_id].copy()
            user_ratings['rating_date'] = pd.to_datetime(user_ratings['rating_date'])
            user_ratings = user_ratings.sort_values('rating_date')

            sequence = []
            for _, row in user_ratings.iterrows():
                sequence.append({
                    'movie_id': row['movie_id'],
                    'rating': row['rating'],
                    'date': row['rating_date'],
                    'timestamp': row['rating_date'].timestamp()
                })

            self.user_watch_sequences[user_id] = sequence

    def _analyze_user_time_patterns(self):
        if self.ratings_df is None or 'rating_date' not in self.ratings_df.columns:
            return

        for user_id in self.ratings_df['user_id'].unique():
            user_ratings = self.ratings_df[self.ratings_df['user_id'] == user_id].copy()
            user_ratings['rating_date'] = pd.to_datetime(user_ratings['rating_date'])
            user_ratings['dayofweek'] = user_ratings['rating_date'].dt.dayofweek
            user_ratings['month'] = user_ratings['rating_date'].dt.month

            day_counts = user_ratings['dayofweek'].value_counts().sort_index()
            day_distribution = {str(d): int(day_counts.get(d, 0)) for d in range(7)}

            month_counts = user_ratings['month'].value_counts().sort_index()
            month_distribution = {str(m): int(month_counts.get(m, 0)) for m in range(1, 13)}

            total_watches = len(user_ratings)
            weekend_ratio = (day_distribution.get('5', 0) + day_distribution.get('6', 0)) / max(total_watches, 1)

            if self.movies_df is not None:
                user_watched = self.movies_df[self.movies_df['movie_id'].isin(user_ratings['movie_id'])]
                if len(user_watched) > 0:
                    avg_runtime = user_watched['runtime'].mean()
                    preferred_runtime_range = self._get_preferred_runtime_range(user_watched['runtime'])
                else:
                    avg_runtime = 120
                    preferred_runtime_range = (90, 150)
            else:
                avg_runtime = 120
                preferred_runtime_range = (90, 150)

            self.user_time_patterns[user_id] = {
                'day_distribution': day_distribution,
                'month_distribution': month_distribution,
                'weekend_ratio': round(weekend_ratio, 3),
                'total_watches': total_watches,
                'avg_runtime_watched': round(avg_runtime, 1),
                'preferred_runtime_range': preferred_runtime_range,
                'preferred_days': sorted(day_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
                'is_weekend_watcher': weekend_ratio > 0.5
            }

    def _get_preferred_runtime_range(self, runtimes, percentile=0.7):
        if len(runtimes) == 0:
            return (90, 150)
        sorted_runtimes = sorted(runtimes)
        lower_idx = int(len(sorted_runtimes) * (1 - percentile) / 2)
        upper_idx = int(len(sorted_runtimes) * (1 - (1 - percentile) / 2)) - 1
        lower_idx = max(0, lower_idx)
        upper_idx = min(len(sorted_runtimes) - 1, upper_idx)
        return (int(sorted_runtimes[lower_idx]), int(sorted_runtimes[upper_idx]))

    def _train_sequence_model(self):
        if not self.user_watch_sequences:
            return

        self.sequence_model = {
            'genre_transitions': {},
            'recent_weight': 0.7,
            'decay_factor': 0.9
        }

        for user_id, sequence in self.user_watch_sequences.items():
            if len(sequence) < 3:
                continue

            user_genre_transitions = {}

            for i in range(len(sequence) - 1):
                current_mid = sequence[i]['movie_id']
                next_mid = sequence[i + 1]['movie_id']

                if self.movies_df is not None:
                    current_row = self.movies_df[self.movies_df['movie_id'] == current_mid]
                    next_row = self.movies_df[self.movies_df['movie_id'] == next_mid]
                    if len(current_row) > 0 and len(next_row) > 0:
                        current_genres = current_row.iloc[0]['genres'].split('|')
                        next_genres = next_row.iloc[0]['genres'].split('|')

                        for cg in current_genres:
                            for ng in next_genres:
                                key = f"{cg}->{ng}"
                                if key not in user_genre_transitions:
                                    user_genre_transitions[key] = 0
                                time_weight = self.sequence_model['decay_factor'] ** (len(sequence) - i - 1)
                                user_genre_transitions[key] += time_weight

            self.sequence_model['genre_transitions'][user_id] = user_genre_transitions

    def get_user_sequence_analysis(self, user_id):
        if user_id not in self.user_watch_sequences:
            return {'error': '用户无观影序列数据'}

        sequence = self.user_watch_sequences[user_id]

        genre_evolution = []
        if self.movies_df is not None and len(sequence) >= 3:
            for i, item in enumerate(sequence):
                movie_row = self.movies_df[self.movies_df['movie_id'] == item['movie_id']]
                if len(movie_row) > 0:
                    genre_evolution.append({
                        'position': i + 1,
                        'movie_id': item['movie_id'],
                        'genres': movie_row.iloc[0]['genres'],
                        'rating': item['rating'],
                        'date': item['date'].strftime('%Y-%m-%d')
                    })

        transition_analysis = {}
        if user_id in self.sequence_model.get('genre_transitions', {}):
            transitions = self.sequence_model['genre_transitions'][user_id]
            sorted_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:10]
            transition_analysis = {t[0]: round(t[1], 3) for t in sorted_transitions}

        time_pattern = self.user_time_patterns.get(user_id, {})

        return {
            'user_id': user_id,
            'total_watched': len(sequence),
            'genre_evolution': genre_evolution[:10],
            'top_genre_transitions': transition_analysis,
            'time_pattern': time_pattern,
            'recent_trend': self._get_recent_genre_trend(user_id, n=5)
        }

    def _get_recent_genre_trend(self, user_id, n=5):
        if user_id not in self.user_watch_sequences or self.movies_df is None:
            return []

        sequence = self.user_watch_sequences[user_id]
        recent = sequence[-n:] if len(sequence) >= n else sequence

        genre_counts = {}
        for item in recent:
            movie_row = self.movies_df[self.movies_df['movie_id'] == item['movie_id']]
            if len(movie_row) > 0:
                for genre in movie_row.iloc[0]['genres'].split('|'):
                    if genre not in genre_counts:
                        genre_counts[genre] = 0
                    genre_counts[genre] += item['rating'] / 5.0

        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return [{'genre': g, 'trend_score': round(s, 3)} for g, s in sorted_genres]

    def _calculate_sequence_score(self, user_id, movie_id):
        if user_id not in self.sequence_model.get('genre_transitions', {}) or self.movies_df is None:
            return 0.0

        movie_row = self.movies_df[self.movies_df['movie_id'] == movie_id]
        if len(movie_row) == 0:
            return 0.0

        target_genres = movie_row.iloc[0]['genres'].split('|')
        transitions = self.sequence_model['genre_transitions'].get(user_id, {})

        if user_id not in self.user_watch_sequences or len(self.user_watch_sequences[user_id]) < 1:
            return 0.0

        last_watched = self.user_watch_sequences[user_id][-1]
        last_movie_row = self.movies_df[self.movies_df['movie_id'] == last_watched['movie_id']]
        if len(last_movie_row) == 0:
            return 0.0

        last_genres = last_movie_row.iloc[0]['genres'].split('|')

        total_score = 0.0
        for lg in last_genres:
            for tg in target_genres:
                key = f"{lg}->{tg}"
                total_score += transitions.get(key, 0.0)

        max_transition = max(transitions.values()) if transitions else 1.0
        normalized_score = total_score / (max_transition * len(last_genres) + 1e-8)

        return min(normalized_score, 1.0)

    def recommend_sequence(self, user_id, top_n=10, exclude_rated=True, sequence_weight=0.3):
        if user_id not in self.user_watch_sequences:
            return self.recommend(user_id, top_n, exclude_rated)

        base_recommendations = self.recommend(user_id, top_n=top_n * 2, exclude_rated=exclude_rated)

        for rec in base_recommendations:
            seq_score = self._calculate_sequence_score(user_id, rec['movie_id'])
            rec['sequence_score'] = round(seq_score, 4)
            rec['final_score'] = round(
                (1 - sequence_weight) * (rec['predicted_rating'] / 5.0) + sequence_weight * seq_score,
                4
            )

        base_recommendations.sort(key=lambda x: x.get('final_score', x['predicted_rating'] / 5.0), reverse=True)

        results = []
        for rec in base_recommendations[:top_n]:
            results.append({
                **rec,
                'recommendation_type': 'sequence_aware'
            })

        return results

    def _calculate_diversity_penalty(self, genres, selected_genres, diversity_threshold=0.3):
        genre_set = set(genres.split('|'))
        selected_set = set()
        for sg in selected_genres:
            selected_set.update(sg.split('|'))

        overlap = len(genre_set & selected_set) / max(len(genre_set), 1)

        if overlap > diversity_threshold:
            return 1.0 - overlap
        return 0.0

    def recommend_with_diversity(self, user_id, top_n=10, exclude_rated=True, diversity_weight=0.25, diversity_method='greedy'):
        base_recommendations = self.recommend(user_id, top_n=top_n * 3, exclude_rated=exclude_rated)

        if diversity_method == 'greedy':
            return self._diversify_greedy(base_recommendations, top_n, diversity_weight)
        elif diversity_method == 'mmr':
            return self._diversify_mmr(base_recommendations, top_n, diversity_weight)
        else:
            return base_recommendations[:top_n]

    def _diversify_greedy(self, candidates, top_n, diversity_weight):
        selected = []
        selected_genres = []
        remaining = candidates.copy()

        while len(selected) < top_n and remaining:
            best_idx = 0
            best_score = -1

            for i, candidate in enumerate(remaining):
                relevance = candidate['predicted_rating'] / 5.0

                if selected_genres:
                    penalty = self._calculate_diversity_penalty(candidate['genres'], selected_genres)
                    adjusted_score = (1 - diversity_weight) * relevance + diversity_weight * (1 - penalty)
                else:
                    adjusted_score = relevance

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_idx = i

            selected_item = remaining.pop(best_idx)
            selected_item['diversity_adjusted_score'] = round(best_score, 4)
            selected.append(selected_item)
            selected_genres.append(selected_item['genres'])

        for item in selected:
            item['recommendation_type'] = 'diversified'

        return selected

    def _diversify_mmr(self, candidates, top_n, diversity_weight):
        selected = []
        selected_genres = []
        remaining = candidates.copy()

        for _ in range(min(top_n, len(candidates))):
            mmr_scores = []
            for candidate in remaining:
                relevance = candidate['predicted_rating'] / 5.0

                max_similarity = 0.0
                if selected_genres:
                    candidate_genres = set(candidate['genres'].split('|'))
                    for sg in selected_genres:
                        sg_set = set(sg.split('|'))
                        sim = len(candidate_genres & sg_set) / max(len(candidate_genres | sg_set), 1)
                        max_similarity = max(max_similarity, sim)

                mmr = (1 - diversity_weight) * relevance - diversity_weight * max_similarity
                mmr_scores.append(mmr)

            best_idx = mmr_scores.index(max(mmr_scores))
            selected_item = remaining.pop(best_idx)
            selected_item['mmr_score'] = round(mmr_scores[best_idx], 4)
            selected.append(selected_item)
            selected_genres.append(selected_item['genres'])

        for item in selected:
            item['recommendation_type'] = 'mmr_diversified'

        return selected

    def recommend_by_runtime(self, user_id, available_minutes, top_n=10, exclude_rated=True, tolerance=15):
        time_pattern = self.user_time_patterns.get(user_id, {})
        preferred_range = time_pattern.get('preferred_runtime_range', (90, 150))

        min_runtime = max(available_minutes - tolerance, 30)
        max_runtime = available_minutes + tolerance

        base_recommendations = self.recommend(user_id, top_n=top_n * 3, exclude_rated=exclude_rated)

        filtered = []
        for rec in base_recommendations:
            movie_row = self.movies_df[self.movies_df['movie_id'] == rec['movie_id']] if self.movies_df is not None else None
            if movie_row is not None and len(movie_row) > 0:
                runtime = movie_row.iloc[0]['runtime']
                rec['runtime'] = int(runtime)
                if min_runtime <= runtime <= max_runtime:
                    fit_score = 1.0 - abs(runtime - available_minutes) / max(available_minutes, 1)
                    rec['runtime_fit_score'] = round(fit_score, 4)
                    rec['is_preferred_range'] = preferred_range[0] <= runtime <= preferred_range[1]
                    filtered.append(rec)

        filtered.sort(key=lambda x: (x['runtime_fit_score'], x['predicted_rating']), reverse=True)

        return {
            'user_id': user_id,
            'available_minutes': available_minutes,
            'tolerance_minutes': tolerance,
            'preferred_runtime_range': preferred_range,
            'recommendation_count': len(filtered[:top_n]),
            'recommendations': filtered[:top_n]
        }

    def get_user_watch_time_analysis(self, user_id):
        if user_id not in self.user_time_patterns:
            return {'error': '用户无观影时间数据'}

        pattern = self.user_time_patterns[user_id]

        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        day_distribution_named = {}
        for d, count in pattern['day_distribution'].items():
            day_distribution_named[day_names[int(d)]] = count

        best_time_suggestion = self._suggest_best_watch_time(user_id)

        return {
            'user_id': user_id,
            'total_watches': pattern['total_watches'],
            'day_distribution': day_distribution_named,
            'weekend_ratio': pattern['weekend_ratio'],
            'is_weekend_watcher': pattern['is_weekend_watcher'],
            'preferred_days': [(day_names[int(d[0])], d[1]) for d in pattern['preferred_days']],
            'avg_runtime_watched': pattern['avg_runtime_watched'],
            'preferred_runtime_range': pattern['preferred_runtime_range'],
            'best_time_suggestion': best_time_suggestion
        }

    def _suggest_best_watch_time(self, user_id):
        if user_id not in self.user_time_patterns:
            return {'suggestion': '数据不足', 'best_day': None, 'suggested_duration': 120}

        pattern = self.user_time_patterns[user_id]

        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        best_day_idx = int(pattern['preferred_days'][0][0])
        best_day = day_names[best_day_idx]

        preferred_range = pattern['preferred_runtime_range']
        suggested_duration = (preferred_range[0] + preferred_range[1]) // 2

        is_weekend = pattern['is_weekend_watcher']
        if is_weekend:
            suggestion = f"建议在周末观看，时长约{suggested_duration}分钟"
        else:
            suggestion = f"建议在{best_day}观看，时长约{suggested_duration}分钟"

        return {
            'suggestion': suggestion,
            'best_day': best_day,
            'is_weekend_preferred': is_weekend,
            'suggested_duration_minutes': suggested_duration,
            'runtime_range_minutes': preferred_range
        }
