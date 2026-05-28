import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import os


class BoxOfficePredictor:
    def __init__(self, model_dir='models'):
        self.model = None
        self.label_encoders = {}
        self.scaler = None
        self.feature_columns = []
        self.model_dir = model_dir
        self.genre_list = ['动作', '喜剧', '剧情', '科幻', '恐怖', '爱情', '动画', '悬疑', '冒险', '战争']
        self.marketing_stats = {}
        os.makedirs(model_dir, exist_ok=True)

    def _extract_genre_features(self, df):
        for genre in self.genre_list:
            df[f'genre_{genre}'] = df['genres'].apply(lambda x: 1 if genre in str(x).split('|') else 0)
        return df

    def _encode_categorical_features(self, df, fit=False):
        categorical_cols = ['director', 'production_company']

        for col in categorical_cols:
            if fit:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                le = self.label_encoders[col]
                df[col] = df[col].astype(str).map(lambda x: le.transform([x])[0] if x in le.classes_ else -1)

        return df

    def _estimate_marketing_spend(self, movie_features, boxoffice_row=None):
        if boxoffice_row is not None and 'marketing_spend' in boxoffice_row.columns:
            val = boxoffice_row['marketing_spend'].values[0] if len(boxoffice_row) > 0 else None
            if val is not None and not pd.isna(val) and val > 0:
                return float(val)

        budget = movie_features.get('budget', 50000000)
        estimated = self._compute_marketing_from_history(movie_features)
        return estimated

    def _compute_marketing_from_history(self, movie_features):
        budget = movie_features.get('budget', 50000000)
        base_ratio = self.marketing_stats.get('budget_ratio_mean', 0.3)

        popularity_score = self._compute_movie_heat_score(movie_features)

        adjusted_ratio = base_ratio * (0.7 + 0.3 * popularity_score)

        adjusted_ratio = max(0.15, min(0.50, adjusted_ratio))

        return budget * adjusted_ratio

    def _compute_movie_heat_score(self, movie_features):
        score = 0.5

        budget = movie_features.get('budget', 50000000)
        if budget >= 150000000:
            score += 0.2
        elif budget >= 80000000:
            score += 0.1

        genres = str(movie_features.get('genres', '')).split('|')
        hot_genres = {'动作', '科幻', '喜剧', '动画'}
        genre_match = len(set(genres) & hot_genres)
        score += min(genre_match * 0.05, 0.15)

        if movie_features.get('is_sequel', 0) == 1:
            score += 0.1

        director = str(movie_features.get('director', ''))
        if director in ['导演A', '导演B', '导演C']:
            score += 0.1

        return min(score, 1.0)

    def _build_marketing_stats(self, movies_df, boxoffice_df):
        merged = pd.merge(movies_df, boxoffice_df, on='movie_id', how='inner')

        if 'marketing_spend' in merged.columns and 'budget' in merged.columns:
            valid = merged[merged['marketing_spend'] > 0]
            if len(valid) > 0:
                ratios = valid['marketing_spend'] / valid['budget']
                self.marketing_stats['budget_ratio_mean'] = ratios.mean()
                self.marketing_stats['budget_ratio_std'] = ratios.std()
                self.marketing_stats['marketing_mean'] = valid['marketing_spend'].mean()
                self.marketing_stats['marketing_median'] = valid['marketing_spend'].median()

                for genre in self.genre_list:
                    genre_mask = valid['genres'].str.contains(genre)
                    if genre_mask.sum() > 0:
                        self.marketing_stats[f'ratio_{genre}'] = ratios[genre_mask].mean()

                for director in valid['director'].unique():
                    dir_mask = valid['director'] == director
                    if dir_mask.sum() >= 2:
                        self.marketing_stats[f'ratio_dir_{director}'] = ratios[dir_mask].mean()
            else:
                self.marketing_stats['budget_ratio_mean'] = 0.3
                self.marketing_stats['marketing_mean'] = 30000000
                self.marketing_stats['marketing_median'] = 25000000
                self.marketing_stats['budget_ratio_std'] = 0.1
        else:
            self.marketing_stats['budget_ratio_mean'] = 0.3
            self.marketing_stats['marketing_mean'] = 30000000
            self.marketing_stats['marketing_median'] = 25000000
            self.marketing_stats['budget_ratio_std'] = 0.1

    def _feature_engineering(self, movies_df, boxoffice_df, fit=False):
        merged_df = pd.merge(movies_df, boxoffice_df, on='movie_id', how='inner')

        merged_df = self._extract_genre_features(merged_df)
        merged_df = self._encode_categorical_features(merged_df, fit=fit)

        merged_df['budget_per_minute'] = merged_df['budget'] / merged_df['runtime']
        merged_df['year_since_release'] = 2024 - merged_df['release_year']
        merged_df['is_weekend_release'] = (merged_df['release_weekday'] >= 5).astype(int)
        merged_df['is_summer_release'] = merged_df['release_month'].isin([6, 7, 8]).astype(int)
        merged_df['is_holiday_release'] = merged_df['holiday_season']

        merged_df['marketing_spend_filled'] = merged_df.apply(
            lambda row: self._fill_marketing_for_row(row), axis=1
        )
        merged_df['marketing_is_imputed'] = (
            merged_df['marketing_spend'].isna() | (merged_df['marketing_spend'] <= 0)
        ).astype(int)

        feature_cols = [
            'budget', 'runtime', 'is_sequel', 'release_year',
            'director', 'production_company',
            'release_month', 'release_weekday', 'holiday_season',
            'marketing_spend_filled', 'num_screens',
            'budget_per_minute', 'year_since_release',
            'is_weekend_release', 'is_summer_release', 'is_holiday_release',
            'marketing_is_imputed'
        ] + [f'genre_{g}' for g in self.genre_list]

        if fit:
            self.feature_columns = feature_cols

        return merged_df[feature_cols]

    def _fill_marketing_for_row(self, row):
        if pd.notna(row.get('marketing_spend')) and row.get('marketing_spend', 0) > 0:
            return row['marketing_spend']

        movie_features = {
            'budget': row.get('budget', 50000000),
            'genres': row.get('genres', ''),
            'is_sequel': row.get('is_sequel', 0),
            'director': row.get('director', '')
        }
        return self._compute_marketing_from_history(movie_features)

    def train(self, movies_df, boxoffice_df, test_size=0.2, random_state=42):
        print("开始训练票房预测模型...")

        self._build_marketing_stats(movies_df, boxoffice_df)
        print(f"宣发费用统计: 预算占比均值={self.marketing_stats.get('budget_ratio_mean', 0.3):.2%}")

        X = self._feature_engineering(movies_df, boxoffice_df, fit=True)
        y = boxoffice_df['opening_weekend_revenue'].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': random_state
        }

        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=1000,
            valid_sets=[valid_data],
            callbacks=[lgb.early_stopping(stopping_rounds=50)]
        )

        y_pred = self.model.predict(X_test, num_iteration=self.model.best_iteration)

        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f"模型训练完成:")
        print(f"  RMSE: {rmse:,.0f}")
        print(f"  MAE: {mae:,.0f}")
        print(f"  R2: {r2:.4f}")

        self._save_model()

        return {'rmse': rmse, 'mae': mae, 'r2': r2}

    def _save_model(self):
        model_path = os.path.join(self.model_dir, 'boxoffice_model.txt')
        self.model.save_model(model_path)

        encoders_path = os.path.join(self.model_dir, 'label_encoders.pkl')
        joblib.dump(self.label_encoders, encoders_path)

        feature_path = os.path.join(self.model_dir, 'feature_columns.pkl')
        joblib.dump(self.feature_columns, feature_path)

        stats_path = os.path.join(self.model_dir, 'marketing_stats.pkl')
        joblib.dump(self.marketing_stats, stats_path)

        print(f"模型已保存到 {self.model_dir}/")

    def load_model(self):
        model_path = os.path.join(self.model_dir, 'boxoffice_model.txt')
        if os.path.exists(model_path):
            self.model = lgb.Booster(model_file=model_path)

            encoders_path = os.path.join(self.model_dir, 'label_encoders.pkl')
            self.label_encoders = joblib.load(encoders_path)

            feature_path = os.path.join(self.model_dir, 'feature_columns.pkl')
            self.feature_columns = joblib.load(feature_path)

            stats_path = os.path.join(self.model_dir, 'marketing_stats.pkl')
            if os.path.exists(stats_path):
                self.marketing_stats = joblib.load(stats_path)

            print("模型加载成功")
            return True
        return False

    def predict(self, movie_features, boxoffice_context=None):
        if self.model is None:
            if not self.load_model():
                raise ValueError("模型未训练，请先调用 train() 方法")

        if boxoffice_context is None:
            estimated_marketing = self._compute_marketing_from_history(movie_features)
            boxoffice_context = pd.DataFrame([{
                'movie_id': movie_features.get('movie_id', 'M000'),
                'release_month': 7,
                'release_weekday': 4,
                'holiday_season': 1,
                'marketing_spend': estimated_marketing,
                'num_screens': 4000
            }])
        else:
            if isinstance(boxoffice_context, pd.DataFrame):
                if 'marketing_spend' not in boxoffice_context.columns or boxoffice_context['marketing_spend'].isna().any() or (boxoffice_context['marketing_spend'] <= 0).any():
                    estimated = self._compute_marketing_from_history(movie_features)
                    if 'marketing_spend' not in boxoffice_context.columns:
                        boxoffice_context['marketing_spend'] = estimated
                    else:
                        boxoffice_context['marketing_spend'] = boxoffice_context['marketing_spend'].fillna(estimated)
                        boxoffice_context.loc[boxoffice_context['marketing_spend'] <= 0, 'marketing_spend'] = estimated

        movie_df = pd.DataFrame([movie_features])
        boxoffice_context_copy = boxoffice_context.copy()
        X = self._feature_engineering(movie_df, boxoffice_context_copy, fit=False)
        X = X[self.feature_columns]

        prediction = self.model.predict(X)[0]

        return prediction

    def predict_with_interval(self, movie_features, boxoffice_context=None, confidence=0.9):
        point_prediction = self.predict(movie_features, boxoffice_context)

        error_margin = point_prediction * 0.15

        z_score = {0.8: 1.28, 0.9: 1.645, 0.95: 1.96}.get(confidence, 1.645)

        lower_bound = max(0, point_prediction - z_score * error_margin)
        upper_bound = point_prediction + z_score * error_margin

        marketing_source = 'provided'
        if boxoffice_context is None:
            marketing_source = 'estimated_history_heat'
        elif isinstance(boxoffice_context, pd.DataFrame):
            if 'marketing_spend' in boxoffice_context.columns:
                val = boxoffice_context['marketing_spend'].values[0] if len(boxoffice_context) > 0 else None
                if val is None or (isinstance(val, float) and (pd.isna(val) or val <= 0)):
                    marketing_source = 'estimated_history_heat'

        return {
            'predicted_opening': int(point_prediction),
            'lower_bound': int(lower_bound),
            'upper_bound': int(upper_bound),
            'confidence': confidence,
            'predicted_total': int(point_prediction * 3.2),
            'marketing_spend_source': marketing_source
        }

    def get_feature_importance(self, top_n=15):
        if self.model is None:
            return []

        importance = self.model.feature_importance()
        feature_importance = list(zip(self.feature_columns, importance))
        feature_importance.sort(key=lambda x: x[1], reverse=True)

        return [{'feature': f, 'importance': float(i)} for f, i in feature_importance[:top_n]]

    def get_marketing_estimate(self, movie_features):
        heat_score = self._compute_movie_heat_score(movie_features)
        estimated_spend = self._compute_marketing_from_history(movie_features)
        budget_ratio = estimated_spend / movie_features.get('budget', 1)

        return {
            'estimated_marketing_spend': int(estimated_spend),
            'budget_ratio': round(budget_ratio, 4),
            'heat_score': round(heat_score, 4),
            'historical_avg_ratio': round(self.marketing_stats.get('budget_ratio_mean', 0.3), 4),
            'method': 'history_mean_plus_heat_adjustment'
        }
