import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, Lasso
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import r2_score, mean_absolute_error
from itertools import combinations, product
import warnings
warnings.filterwarnings('ignore')


def prepare_mmm_data(touchpoints_df, users_df, aggregation_level='weekly'):
    touchpoints = touchpoints_df.copy()
    touchpoints['date'] = pd.to_datetime(touchpoints['timestamp']).dt.date
    
    conversions = users_df[users_df['converted'] == 1].copy()
    conversions['date'] = pd.to_datetime(conversions['conversion_timestamp']).dt.date
    
    if aggregation_level == 'daily':
        freq = 'D'
    elif aggregation_level == 'weekly':
        freq = 'W-MON'
    else:
        freq = 'M'
    
    channels = sorted(touchpoints['channel'].unique())
    devices = sorted(touchpoints['device'].unique())
    
    date_range = pd.date_range(
        start=touchpoints['date'].min(),
        end=max(touchpoints['date'].max(), conversions['date'].max()),
        freq=freq
    )
    
    mmm_data = []
    
    for period_start in date_range:
        period_end = period_start + pd.Timedelta(days=7 if freq == 'W-MON' else (1 if freq == 'D' else 30))
        
        period_mask = (touchpoints['date'] >= period_start.date()) & (touchpoints['date'] < period_end.date())
        period_tp = touchpoints[period_mask]
        
        conv_mask = (conversions['date'] >= period_start.date()) & (conversions['date'] < period_end.date())
        period_conv = conversions[conv_mask]
        
        row = {
            'period': period_start,
            'total_conversions': len(period_conv),
            'total_value': period_conv['conversion_value'].sum()
        }
        
        for channel in channels:
            channel_tp = period_tp[period_tp['channel'] == channel]
            row[f'{channel}_spend'] = channel_tp['cost'].sum()
            row[f'{channel}_impressions'] = len(channel_tp)
            row[f'{channel}_reach'] = channel_tp['user_id'].nunique()
        
        for device in devices:
            device_tp = period_tp[period_tp['device'] == device]
            row[f'{device}_impressions'] = len(device_tp)
        
        mmm_data.append(row)
    
    mmm_df = pd.DataFrame(mmm_data)
    
    return mmm_df, channels, devices


def apply_adstock(spend_series, decay_rate=0.5, max_lag=4):
    n = len(spend_series)
    adstocked = np.zeros(n)
    
    for i in range(n):
        for lag in range(max_lag + 1):
            if i - lag >= 0:
                weight = decay_rate ** lag
                adstocked[i] += weight * spend_series.iloc[i - lag]
    
    return adstocked


def apply_saturation(spend_series, alpha=1.0, mu=1.0):
    spend_series = np.array(spend_series)
    return mu * (1 - np.exp(-alpha * spend_series / np.max(spend_series) + 1e-9))


class MarketingMixModel:
    def __init__(self, model_type='ridge', alpha=1.0, adstock_decay=0.5, saturation_alpha=1.0):
        self.model_type = model_type
        self.alpha = alpha
        self.adstock_decay = adstock_decay
        self.saturation_alpha = saturation_alpha
        self.model = None
        self.scaler = None
        self.channels = None
        self.feature_names = None
        self.coefficients = None
        
    def fit(self, mmm_df, channels, target='total_conversions'):
        self.channels = channels
        
        X = pd.DataFrame()
        for channel in channels:
            spend_col = f'{channel}_spend'
            adstocked = apply_adstock(mmm_df[spend_col], decay_rate=self.adstock_decay)
            saturated = apply_saturation(pd.Series(adstocked), alpha=self.saturation_alpha)
            X[f'{channel}_effective'] = saturated
        
        X['trend'] = np.arange(len(mmm_df))
        X['month'] = mmm_df['period'].dt.month
        X['weekday'] = mmm_df['period'].dt.weekday
        
        X = pd.get_dummies(X, columns=['month', 'weekday'], drop_first=True)
        
        X = X.fillna(0)
        
        self.feature_names = X.columns.tolist()
        
        y = mmm_df[target].values
        y = np.nan_to_num(y, nan=0.0)
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        if self.model_type == 'ridge':
            self.model = Ridge(alpha=self.alpha)
        elif self.model_type == 'lasso':
            self.model = Lasso(alpha=self.alpha)
        else:
            self.model = GradientBoostingRegressor(
                n_estimators=100, max_depth=3, random_state=42
            )
        
        self.model.fit(X_scaled, y)
        
        if hasattr(self.model, 'coef_'):
            self.coefficients = dict(zip(self.feature_names, self.model.coef_))
        
        self.X = X
        self.y = y
        self.X_scaled = X_scaled
        
        return self
    
    def predict(self, mmm_df):
        X = pd.DataFrame()
        for channel in self.channels:
            spend_col = f'{channel}_spend'
            adstocked = apply_adstock(mmm_df[spend_col], decay_rate=self.adstock_decay)
            saturated = apply_saturation(pd.Series(adstocked), alpha=self.saturation_alpha)
            X[f'{channel}_effective'] = saturated
        
        X['trend'] = np.arange(len(mmm_df))
        X['month'] = mmm_df['period'].dt.month
        X['weekday'] = mmm_df['period'].dt.weekday
        
        X = pd.get_dummies(X, columns=['month', 'weekday'], drop_first=True)
        
        X = X.fillna(0)
        
        for col in self.feature_names:
            if col not in X.columns:
                X[col] = 0
        
        X = X[self.feature_names]
        X = X.fillna(0)
        X_scaled = self.scaler.transform(X)
        
        return self.model.predict(X_scaled)
    
    def get_channel_contributions(self):
        contributions = {}
        
        for channel in self.channels:
            col = f'{channel}_effective'
            if col in self.feature_names and self.coefficients is not None:
                contrib = self.coefficients[col] * self.X[col].mean()
            else:
                feature_idx = self.feature_names.index(col)
                if hasattr(self.model, 'feature_importances_'):
                    contrib = self.model.feature_importances_[feature_idx]
                else:
                    contrib = 0
            
            contributions[channel] = max(0, contrib)
        
        total = sum(contributions.values())
        if total > 0:
            contributions = {k: v / total for k, v in contributions.items()}
        
        return contributions
    
    def get_model_stats(self):
        y_pred = self.predict(pd.concat([self.X, pd.DataFrame({'period': self.model.predict(self.X_scaled)})], axis=1))
        y_pred = self.model.predict(self.X_scaled)
        
        r2 = r2_score(self.y, y_pred)
        mae = mean_absolute_error(self.y, y_pred)
        
        cv_scores = cross_val_score(self.model, self.X_scaled, self.y, cv=5, scoring='r2')
        
        return {
            'r2': round(r2, 4),
            'mae': round(mae, 4),
            'cv_r2_mean': round(cv_scores.mean(), 4),
            'cv_r2_std': round(cv_scores.std(), 4)
        }


def calculate_channel_synergy(mmm_df, channels, target='total_conversions'):
    synergy_matrix = pd.DataFrame(index=channels, columns=channels, dtype=float)
    
    spend_cols = [f'{c}_spend' for c in channels]
    X_base = mmm_df[spend_cols].copy()
    y = mmm_df[target].values
    
    base_model = Ridge(alpha=1.0)
    base_model.fit(X_base, y)
    base_r2 = r2_score(y, base_model.predict(X_base))
    
    for c1, c2 in combinations(channels, 2):
        X_interaction = X_base.copy()
        X_interaction[f'{c1}_x_{c2}'] = X_base[f'{c1}_spend'] * X_base[f'{c2}_spend']
        
        model = Ridge(alpha=1.0)
        model.fit(X_interaction, y)
        new_r2 = r2_score(y, model.predict(X_interaction))
        
        synergy_gain = new_r2 - base_r2
        
        interaction_coef = model.coef_[-1]
        
        synergy_value = synergy_gain * np.sign(interaction_coef)
        synergy_matrix.loc[c1, c2] = round(synergy_value, 6)
        synergy_matrix.loc[c2, c1] = round(synergy_value, 6)
    
    for c in channels:
        synergy_matrix.loc[c, c] = 0
    
    return synergy_matrix


def analyze_synergy_pairs(synergy_matrix, threshold=0.01):
    positive_pairs = []
    negative_pairs = []
    
    for c1, c2 in combinations(synergy_matrix.columns, 2):
        value = synergy_matrix.loc[c1, c2]
        if value > threshold:
            positive_pairs.append((c1, c2, value))
        elif value < -threshold:
            negative_pairs.append((c1, c2, value))
    
    positive_pairs.sort(key=lambda x: x[2], reverse=True)
    negative_pairs.sort(key=lambda x: x[2])
    
    return {
        'positive_synergies': positive_pairs,
        'negative_synergies': negative_pairs
    }


def run_mmm_analysis(touchpoints_df, users_df, target='total_conversions'):
    mmm_df, channels, devices = prepare_mmm_data(touchpoints_df, users_df)
    
    mmm_model = MarketingMixModel(
        model_type='ridge',
        alpha=1.0,
        adstock_decay=0.5,
        saturation_alpha=1.5
    )
    mmm_model.fit(mmm_df, channels, target=target)
    
    contributions = mmm_model.get_channel_contributions()
    model_stats = mmm_model.get_model_stats()
    
    synergy_matrix = calculate_channel_synergy(mmm_df, channels, target=target)
    synergy_pairs = analyze_synergy_pairs(synergy_matrix)
    
    mmm_contributions_df = pd.DataFrame([
        {'channel': channel, 'mmm_weight': round(weight, 4)}
        for channel, weight in contributions.items()
    ]).sort_values('mmm_weight', ascending=False)
    
    return {
        'mmm_df': mmm_df,
        'channels': channels,
        'devices': devices,
        'model': mmm_model,
        'contributions': mmm_contributions_df,
        'model_stats': model_stats,
        'synergy_matrix': synergy_matrix,
        'synergy_pairs': synergy_pairs
    }


if __name__ == '__main__':
    from data_generator import generate_attribution_data
    
    users_df, touchpoints_df = generate_attribution_data(n_users=2000)
    
    print("运行营销组合建模...")
    results = run_mmm_analysis(touchpoints_df, users_df)
    
    print("\n=== 模型统计 ===")
    for k, v in results['model_stats'].items():
        print(f"  {k}: {v}")
    
    print("\n=== 渠道贡献度 ===")
    print(results['contributions'].to_string(index=False))
    
    print("\n=== 正协同效应 TOP 5 ===")
    for c1, c2, v in results['synergy_pairs']['positive_synergies'][:5]:
        print(f"  {c1} + {c2}: {v:.6f}")
