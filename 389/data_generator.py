import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple


class AdDataGenerator:
    def __init__(self, n_users: int = 10000, n_ads: int = 100, n_impressions: int = 50000,
                 n_positions: int = 5, random_seed: int = 42):
        self.n_users = n_users
        self.n_ads = n_ads
        self.n_impressions = n_impressions
        self.n_positions = n_positions
        self.random_seed = random_seed
        np.random.seed(self.random_seed)

    def generate_user_profiles(self) -> pd.DataFrame:
        user_ids = np.arange(1, self.n_users + 1)
        ages = np.random.randint(18, 65, size=self.n_users)
        genders = np.random.choice(['male', 'female', 'unknown'], size=self.n_users, p=[0.45, 0.45, 0.10])
        cities = np.random.choice(['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen', 'Hangzhou', 'Chengdu', 'Wuhan'],
                                   size=self.n_users, p=[0.2, 0.2, 0.12, 0.12, 0.1, 0.12, 0.14])
        interests = np.random.choice(['sports', 'tech', 'fashion', 'finance', 'travel', 'food', 'education'],
                                      size=self.n_users)
        activity_levels = np.random.choice(['low', 'medium', 'high'], size=self.n_users, p=[0.3, 0.4, 0.3])
        user_values = np.random.exponential(scale=100, size=self.n_users).round(2)
        history_clicks = np.random.poisson(lam=5, size=self.n_users)
        history_conversions = np.random.poisson(lam=0.5, size=self.n_users)

        df_users = pd.DataFrame({
            'user_id': user_ids,
            'age': ages,
            'gender': genders,
            'city': cities,
            'interest': interests,
            'activity_level': activity_levels,
            'user_value': user_values,
            'history_clicks': history_clicks,
            'history_conversions': history_conversions
        })
        return df_users

    def generate_ad_campaigns(self) -> pd.DataFrame:
        ad_ids = np.arange(1, self.n_ads + 1)
        categories = np.random.choice(['sports', 'tech', 'fashion', 'finance', 'travel', 'food', 'education'],
                                       size=self.n_ads)
        base_bids = np.random.uniform(0.5, 10.0, size=self.n_ads).round(4)
        current_budgets = np.random.uniform(1000, 50000, size=self.n_ads).round(2)
        ad_quality_scores = np.random.uniform(0.5, 1.0, size=self.n_ads).round(4)

        df_ads = pd.DataFrame({
            'ad_id': ad_ids,
            'category': categories,
            'base_bid': base_bids,
            'current_budget': current_budgets,
            'ad_quality_score': ad_quality_scores
        })
        return df_ads

    def generate_ad_positions(self) -> pd.DataFrame:
        position_ids = np.arange(1, self.n_positions + 1)
        position_names = [
            'Top Banner',
            'Sidebar Top',
            'In-Feed',
            'Sidebar Bottom',
            'Footer'
        ]
        position_names = position_names[:self.n_positions]
        position_values = [100.0 * (0.5 ** (i - 1)) for i in range(1, self.n_positions + 1)]
        base_impression_capacities = [10000, 8000, 15000, 6000, 4000]
        base_impression_capacities = base_impression_capacities[:self.n_positions]

        df_positions = pd.DataFrame({
            'position_id': position_ids,
            'position_name': position_names,
            'position_value': np.round(position_values, 2),
            'base_impression_capacity': base_impression_capacities
        })
        return df_positions

    def generate_impression_logs(self, df_users: pd.DataFrame, df_ads: pd.DataFrame,
                                  df_positions: pd.DataFrame) -> pd.DataFrame:
        impression_ids = np.arange(1, self.n_impressions + 1)
        user_indices = np.random.choice(self.n_users, size=self.n_impressions)
        ad_indices = np.random.choice(self.n_ads, size=self.n_impressions)
        user_ids = df_users['user_id'].values[user_indices]
        ad_ids = df_ads['ad_id'].values[ad_indices]

        position_probs = df_positions['base_impression_capacity'].values / df_positions['base_impression_capacity'].sum()
        position_indices = np.random.choice(self.n_positions, size=self.n_impressions, p=position_probs)
        position_ids = df_positions['position_id'].values[position_indices]
        position_values = df_positions['position_value'].values[position_indices]

        base_time = datetime(2026, 5, 1)
        timestamps = [base_time + timedelta(seconds=int(s))
                      for s in np.random.uniform(0, 2592000, size=self.n_impressions)]

        interest_match = (df_users['interest'].values[user_indices] ==
                          df_ads['category'].values[ad_indices]).astype(int)
        city_match = (df_users['city'].values[user_indices] ==
                      np.random.choice(['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen'], size=self.n_impressions)).astype(int)

        normalized_position_value = position_values / position_values.max()

        click_prob = (0.02 +
                      0.03 * interest_match +
                      0.01 * city_match +
                      0.001 * (df_users['user_value'].values[user_indices] / 50) +
                      0.005 * (df_ads['ad_quality_score'].values[ad_indices] - 0.5) +
                      0.02 * normalized_position_value +
                      np.random.normal(0, 0.005, self.n_impressions))
        click_prob = np.clip(click_prob, 0.001, 0.5)
        clicks = np.random.binomial(1, click_prob)

        conversion_prob = np.where(clicks == 1,
                                   0.1 + 0.05 * interest_match + 0.03 * normalized_position_value +
                                   np.random.normal(0, 0.02, self.n_impressions),
                                   0)
        conversion_prob = np.clip(conversion_prob, 0, 0.8)
        conversions = np.random.binomial(1, conversion_prob)

        conversion_values = np.where(conversions == 1,
                                     np.random.uniform(10, 200, self.n_impressions).round(2) * normalized_position_value,
                                     0)

        df_impressions = pd.DataFrame({
            'impression_id': impression_ids,
            'user_id': user_ids,
            'ad_id': ad_ids,
            'position_id': position_ids,
            'position_value': position_values,
            'timestamp': timestamps,
            'interest_match': interest_match,
            'city_match': city_match,
            'click': clicks,
            'conversion': conversions,
            'conversion_value': conversion_values
        })
        return df_impressions

    def generate_auction_logs(self, df_impressions: pd.DataFrame,
                               df_ads: pd.DataFrame,
                               df_positions: pd.DataFrame,
                               n_competitors: int = 5) -> pd.DataFrame:
        auction_ids = np.arange(1, self.n_impressions + 1)
        impression_ids = df_impressions['impression_id'].values
        timestamps = df_impressions['timestamp'].values
        position_ids = df_impressions['position_id'].values
        winning_ad_ids = df_impressions['ad_id'].values

        position_values = df_positions.set_index('position_id')['position_value'].to_dict()
        ad_base_bids = df_ads.set_index('ad_id')['base_bid'].to_dict()
        ad_quality_scores = df_ads.set_index('ad_id')['ad_quality_score'].to_dict()

        auction_data = {
            'auction_id': auction_ids,
            'impression_id': impression_ids,
            'timestamp': timestamps,
            'position_id': position_ids,
            'winning_ad_id': winning_ad_ids
        }

        bid_columns = []
        ad_id_columns = []

        for i in range(1, n_competitors + 1):
            bid_col = f'bid_{i}'
            ad_id_col = f'ad_id_{i}'
            bid_columns.append(bid_col)
            ad_id_columns.append(ad_id_col)

            competitor_bids = []
            competitor_ad_ids = []

            for idx in range(self.n_impressions):
                pos_id = position_ids[idx]
                pos_value = position_values.get(pos_id, 1.0)
                pos_factor = pos_value / 100.0

                winner_ad_id = winning_ad_ids[idx]
                available_ads = [aid for aid in df_ads['ad_id'].values if aid != winner_ad_id]

                if i == 1:
                    current_ad_id = winner_ad_id
                    base_bid = ad_base_bids.get(current_ad_id, 1.0)
                    quality_score = ad_quality_scores.get(current_ad_id, 0.7)
                    bid = base_bid * quality_score * (0.8 + 0.4 * pos_factor) * np.random.uniform(0.9, 1.1)
                else:
                    if len(available_ads) > 0:
                        current_ad_id = np.random.choice(available_ads)
                        available_ads = [aid for aid in available_ads if aid != current_ad_id]
                    else:
                        current_ad_id = np.random.choice(df_ads['ad_id'].values)
                    base_bid = ad_base_bids.get(current_ad_id, 1.0)
                    quality_score = ad_quality_scores.get(current_ad_id, 0.7)
                    bid = base_bid * quality_score * (0.7 + 0.3 * pos_factor) * np.random.uniform(0.8, 1.2)

                bid = max(0.01, round(bid, 4))
                competitor_bids.append(bid)
                competitor_ad_ids.append(current_ad_id)

            auction_data[bid_col] = np.array(competitor_bids)
            auction_data[ad_id_col] = np.array(competitor_ad_ids)

        actual_paid_prices = []
        for idx in range(self.n_impressions):
            bids = [auction_data[bid_col][idx] for bid_col in bid_columns]
            sorted_bids = sorted(bids, reverse=True)
            if len(sorted_bids) >= 2:
                actual_paid = sorted_bids[1]
            else:
                actual_paid = sorted_bids[0] * 0.9 if sorted_bids else 0.01
            actual_paid_prices.append(round(actual_paid, 4))

        auction_data['actual_paid_price'] = np.array(actual_paid_prices)

        df_auctions = pd.DataFrame(auction_data)

        column_order = ['auction_id', 'impression_id', 'timestamp', 'position_id', 'winning_ad_id', 'actual_paid_price']
        for i in range(1, n_competitors + 1):
            column_order.append(f'ad_id_{i}')
            column_order.append(f'bid_{i}')
        df_auctions = df_auctions[column_order]

        return df_auctions

    def generate_all_data(self, n_competitors: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        df_users = self.generate_user_profiles()
        df_ads = self.generate_ad_campaigns()
        df_positions = self.generate_ad_positions()
        df_impressions = self.generate_impression_logs(df_users, df_ads, df_positions)
        df_auctions = self.generate_auction_logs(df_impressions, df_ads, df_positions, n_competitors)
        return df_users, df_ads, df_positions, df_impressions, df_auctions


def prepare_model_data(df_impressions: pd.DataFrame, df_users: pd.DataFrame,
                       df_ads: pd.DataFrame, df_positions: pd.DataFrame = None) -> Tuple:
    df = df_impressions.merge(df_users, on='user_id', how='left')
    df = df.merge(df_ads, on='ad_id', how='left')

    if df_positions is not None:
        df = df.merge(df_positions[['position_id', 'position_name', 'position_value']], on='position_id', how='left')
    else:
        df['position_name'] = 'Unknown'
        df['position_value'] = 50.0

    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    feature_cols = [
        'age', 'gender', 'city', 'interest', 'activity_level',
        'user_value', 'history_clicks', 'history_conversions',
        'category', 'base_bid', 'ad_quality_score',
        'interest_match', 'city_match',
        'position_id', 'position_name', 'position_value',
        'hour', 'day_of_week', 'is_weekend'
    ]

    X = df[feature_cols].copy()
    X = pd.get_dummies(X, columns=['gender', 'city', 'interest', 'activity_level', 'category', 'position_name'], drop_first=True)

    T = df['click'].values
    Y = df['conversion_value'].values
    ad_ids = df['ad_id'].values
    user_ids = df['user_id'].values
    impression_ids = df['impression_id'].values

    return X, T, Y, ad_ids, user_ids, impression_ids, df
