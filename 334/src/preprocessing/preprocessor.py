import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder, MinMaxScaler
from sklearn.feature_extraction.text import CountVectorizer
import joblib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def genre_tokenizer(text):
    return text.split(',')


class DataPreprocessor:
    def __init__(self, model_dir='models', max_presale_days=60):
        self.model_dir = model_dir
        self.max_presale_days = max_presale_days
        self.scaler = StandardScaler()
        self.timeseries_scaler = MinMaxScaler(feature_range=(0, 1))
        self.onehot_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        self.label_encoder_director = LabelEncoder()
        self.label_encoder_actor = LabelEncoder()
        self.genre_vectorizer = CountVectorizer(tokenizer=genre_tokenizer, token_pattern=None)
        self.numeric_features = ['promotion_budget_total', 'runtime', 'competition_count', 
                                  'competition_avg_budget', 'pre_sales_total', 
                                  'pre_sales_days', 'pre_sales_growth_rate']
        self.categorical_features = ['release_season', 'is_holiday', 'is_weekend']
        self.text_features = ['genres']
        self.embedding_features = ['director', 'main_actor']
        self.feature_names_ = None
        self.ts_feature_names = ['daily_pre_sales', 'cumulative_promotion_spend']
        self.n_ts_features = len(self.ts_feature_names)
        self.is_fitted_ = False

    def _extract_schedule_features(self, release_date):
        if isinstance(release_date, str):
            release_date = datetime.strptime(release_date, '%Y-%m-%d')
        elif isinstance(release_date, pd.Timestamp):
            release_date = release_date.to_pydatetime()
        
        month = release_date.month
        if month in [1, 2, 3]:
            season = 'Q1'
        elif month in [4, 5, 6]:
            season = 'Q2'
        elif month in [7, 8, 9]:
            season = 'Q3'
        else:
            season = 'Q4'
        
        holidays = [(1, 1), (2, 14), (4, 5), (5, 1), (10, 1), (12, 25)]
        is_holiday = (release_date.month, release_date.day) in holidays
        
        holiday_periods = [
            (datetime(release_date.year, 2, 10), datetime(release_date.year, 2, 17)),
            (datetime(release_date.year, 10, 1), datetime(release_date.year, 10, 7)),
        ]
        for start, end in holiday_periods:
            if start <= release_date <= end:
                is_holiday = True
                break
        
        is_weekend = release_date.weekday() >= 5
        
        return {
            'release_season': season,
            'is_holiday': int(is_holiday),
            'is_weekend': int(is_weekend),
            'release_month': month,
            'release_dayofweek': release_date.weekday()
        }

    def _process_input(self, input_data):
        processed = {}
        processed['genres'] = ','.join(input_data['genres']) if isinstance(input_data['genres'], list) else input_data['genres']
        processed['director'] = input_data['director']
        processed['main_actor'] = input_data['main_actor']
        processed['runtime'] = input_data.get('runtime', 120)
        
        schedule_feats = self._extract_schedule_features(input_data['release_date'])
        processed.update(schedule_feats)
        
        competition = input_data.get('competition_environment', {})
        processed['competition_count'] = competition.get('same_period_movies', 0)
        processed['competition_avg_budget'] = competition.get('average_competitor_budget', 0)
        processed['competition_genre_overlap'] = competition.get('genre_overlap_ratio', 0.5)
        
        pre_sales = input_data.get('pre_sales_data', {})
        processed['pre_sales_total'] = pre_sales.get('total_amount', 0)
        processed['pre_sales_days'] = len(pre_sales.get('daily_sales', [])) if 'daily_sales' in pre_sales else 0
        daily_sales = pre_sales.get('daily_sales', [])
        if len(daily_sales) >= 2:
            processed['pre_sales_growth_rate'] = (daily_sales[-1] - daily_sales[0]) / (daily_sales[0] + 1e-6)
        else:
            processed['pre_sales_growth_rate'] = 0
        
        promotion_data = input_data.get('promotion_timeseries', {})
        daily_promotion = promotion_data.get('daily_spend', [])
        if len(daily_promotion) == 0 and 'promotion_budget' in input_data:
            total_budget = input_data['promotion_budget']
            n_days = max(len(daily_sales), 1)
            daily_promotion = [total_budget / n_days] * n_days
        
        processed['promotion_budget_total'] = sum(daily_promotion) if len(daily_promotion) > 0 else input_data.get('promotion_budget', 0)
        
        cumulative_promotion = np.cumsum(daily_promotion).tolist() if len(daily_promotion) > 0 else []
        
        return processed, daily_sales, cumulative_promotion

    def fit(self, X_structured, X_timeseries=None, y=None):
        processed_list = []
        ts_data_list = []
        
        for x in X_structured:
            processed, daily_sales, cum_promotion = self._process_input(x)
            processed_list.append(processed)
            
            aligned_sales, aligned_promo = self._align_to_release_day(daily_sales, cum_promotion)
            for i in range(len(aligned_sales)):
                ts_data_list.append([aligned_sales[i], aligned_promo[i]])
        
        df = pd.DataFrame(processed_list)
        
        self.scaler.fit(df[self.numeric_features])
        self.onehot_encoder.fit(df[self.categorical_features])
        self.genre_vectorizer.fit(df['genres'])
        
        if len(ts_data_list) > 0:
            self.timeseries_scaler.fit(np.array(ts_data_list))
        
        all_directors = df['director'].tolist() + ['UNKNOWN']
        all_actors = df['main_actor'].tolist() + ['UNKNOWN']
        self.label_encoder_director.fit(all_directors)
        self.label_encoder_actor.fit(all_actors)
        
        genre_features = self.genre_vectorizer.get_feature_names_out()
        self.feature_names_ = (
            self.numeric_features + 
            list(self.onehot_encoder.get_feature_names_out(self.categorical_features)) +
            [f'genre_{g}' for g in genre_features] +
            ['director_encoded', 'actor_encoded', 'release_month', 'release_dayofweek']
        )
        
        self.is_fitted_ = True
        return self

    def _align_to_release_day(self, daily_sales, cumulative_promotion):
        n_days = len(daily_sales)
        
        if n_days == 0:
            return np.zeros(self.max_presale_days), np.zeros(self.max_presale_days)
        
        aligned_sales = np.zeros(self.max_presale_days)
        aligned_promo = np.zeros(self.max_presale_days)
        
        n_use = min(n_days, self.max_presale_days)
        
        aligned_sales[-n_use:] = daily_sales[-n_use:]
        aligned_promo[-n_use:] = cumulative_promotion[-n_use:]
        
        return aligned_sales, aligned_promo

    def transform(self, X_structured, X_timeseries=None):
        if not self.is_fitted_:
            raise RuntimeError("Preprocessor must be fitted before transform")
        
        processed_list = []
        ts_features_list = []
        
        for x in X_structured:
            processed, daily_sales, cum_promotion = self._process_input(x)
            processed_list.append(processed)
            
            aligned_sales, aligned_promo = self._align_to_release_day(daily_sales, cum_promotion)
            ts_features = np.column_stack([aligned_sales, aligned_promo])
            ts_features_list.append(ts_features)
        
        df = pd.DataFrame(processed_list)
        
        numeric_scaled = self.scaler.transform(df[self.numeric_features])
        categorical_encoded = self.onehot_encoder.transform(df[self.categorical_features])
        genre_encoded = self.genre_vectorizer.transform(df['genres']).toarray()
        
        try:
            director_encoded = self.label_encoder_director.transform(df['director']).reshape(-1, 1)
        except ValueError:
            director_encoded = np.array([
                self.label_encoder_director.transform([d])[0] if d in self.label_encoder_director.classes_
                else self.label_encoder_director.transform(['UNKNOWN'])[0]
                for d in df['director']
            ]).reshape(-1, 1)
        
        try:
            actor_encoded = self.label_encoder_actor.transform(df['main_actor']).reshape(-1, 1)
        except ValueError:
            actor_encoded = np.array([
                self.label_encoder_actor.transform([a])[0] if a in self.label_encoder_actor.classes_
                else self.label_encoder_actor.transform(['UNKNOWN'])[0]
                for a in df['main_actor']
            ]).reshape(-1, 1)
        
        other_features = df[['release_month', 'release_dayofweek']].values
        
        X_struct = np.hstack([
            numeric_scaled,
            categorical_encoded,
            genre_encoded,
            director_encoded,
            actor_encoded,
            other_features
        ])
        
        n_samples = len(ts_features_list)
        X_ts_raw = np.array(ts_features_list)
        
        X_ts_flat = X_ts_raw.reshape(-1, self.n_ts_features)
        X_ts_scaled_flat = self.timeseries_scaler.transform(X_ts_flat)
        X_ts = X_ts_scaled_flat.reshape(n_samples, self.max_presale_days, self.n_ts_features)
        
        day_features = np.linspace(-self.max_presale_days + 1, 0, self.max_presale_days).reshape(1, -1, 1)
        day_features = np.repeat(day_features, n_samples, axis=0) / self.max_presale_days
        X_ts = np.concatenate([X_ts, day_features], axis=2)
        self.n_ts_features = X_ts.shape[2]
        
        return X_struct, X_ts

    def fit_transform(self, X_structured, X_timeseries=None, y=None):
        return self.fit(X_structured, X_timeseries, y).transform(X_structured, X_timeseries)

    def save(self, path):
        joblib.dump(self, f'{self.model_dir}/{path}')

    @classmethod
    def load(cls, path, model_dir='models'):
        return joblib.load(f'{model_dir}/{path}')
