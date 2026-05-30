import pandas as pd
import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')


def prepare_features_for_model(touchpoints_df):
    user_features = touchpoints_df.groupby('user_id').agg({
        'channel': list,
        'touchpoint_position': list,
        'total_touchpoints': 'first',
        'converted': 'first',
        'conversion_value': 'first',
        'cost': 'sum'
    }).reset_index()
    
    channels = sorted(touchpoints_df['channel'].unique())
    
    feature_matrix = []
    for _, row in user_features.iterrows():
        features = {
            'total_touchpoints': row['total_touchpoints'],
            'total_cost': row['cost']
        }
        
        for channel in channels:
            features[f'{channel}_count'] = row['channel'].count(channel)
            features[f'{channel}_first'] = 1 if row['channel'][0] == channel else 0
            features[f'{channel}_last'] = 1 if row['channel'][-1] == channel else 0
        
        feature_matrix.append(features)
    
    features_df = pd.DataFrame(feature_matrix)
    features_df['converted'] = user_features['converted'].values
    features_df['conversion_value'] = user_features['conversion_value'].values
    
    return features_df, channels


class SHAPAttribution:
    def __init__(self, model_type='gradient_boosting', regularization_strength=1.0):
        self.model_type = model_type
        self.regularization_strength = regularization_strength
        self.model = None
        self.explainer = None
        self.shap_values = None
        self.feature_names = None
        self.channels = None
        
    def fit(self, touchpoints_df):
        features_df, channels = prepare_features_for_model(touchpoints_df)
        self.channels = channels
        
        feature_cols = [c for c in features_df.columns if c not in ['converted', 'conversion_value']]
        X = features_df[feature_cols]
        y = features_df['converted']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        reg = self.regularization_strength
        
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100, 
                max_depth=max(3, int(10 / reg)),
                min_samples_leaf=max(1, int(5 * reg)),
                min_samples_split=max(2, int(10 * reg)),
                max_features='sqrt',
                random_state=42,
                n_jobs=-1
            )
        else:
            learning_rate = 0.1 / reg
            self.model = GradientBoostingClassifier(
                n_estimators=100, 
                max_depth=max(3, int(5 / reg)),
                min_samples_leaf=max(1, int(5 * reg)),
                min_samples_split=max(2, int(10 * reg)),
                subsample=min(1.0, 0.8 / reg + 0.2),
                learning_rate=learning_rate,
                random_state=42
            )
        
        self.model.fit(X_train, y_train)
        
        self.explainer = shap.TreeExplainer(self.model)
        self.shap_values = self.explainer.shap_values(X)
        self.feature_names = feature_cols
        self.X = X
        self.features_df = features_df
        
        return self
    
    def get_channel_attribution(self):
        if self.shap_values is None:
            raise ValueError("Model not fitted yet")
        
        if isinstance(self.shap_values, list):
            shap_values_class1 = self.shap_values[1]
        else:
            shap_values_class1 = self.shap_values
        
        shap_df = pd.DataFrame(shap_values_class1, columns=self.feature_names)
        
        channel_attribution = {}
        
        for channel in self.channels:
            channel_features = [
                f'{channel}_count',
                f'{channel}_first',
                f'{channel}_last'
            ]
            
            channel_shap = shap_df[channel_features].sum(axis=1)
            avg_shap_value = channel_shap.mean()
            total_shap_value = channel_shap.sum()
            channel_attribution[channel] = {
                'avg_shap_value': avg_shap_value,
                'total_shap_value': total_shap_value,
                'abs_mean_shap': abs(channel_shap).mean()
            }
        
        total_shap = sum(
            max(0, v['total_shap_value']) 
            for v in channel_attribution.values()
        )
        
        attribution_results = []
        for channel in self.channels:
            data = channel_attribution[channel]
            weight = max(0, data['total_shap_value']) / total_shap if total_shap > 0 else 0
            
            attribution_results.append({
                'channel': channel,
                'shap_avg_value': round(data['avg_shap_value'], 4),
                'shap_total_value': round(data['total_shap_value'], 4),
                'shap_abs_mean': round(data['abs_mean_shap'], 4),
                'shap_weight': round(weight, 4)
            })
        
        return pd.DataFrame(attribution_results)
    
    def get_feature_importance(self):
        if self.shap_values is None:
            raise ValueError("Model not fitted yet")
        
        if isinstance(self.shap_values, list):
            shap_values_class1 = self.shap_values[1]
        else:
            shap_values_class1 = self.shap_values
        
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'shap_importance': np.abs(shap_values_class1).mean(axis=0)
        }).sort_values('shap_importance', ascending=False)
        
        return feature_importance
    
    def get_shap_summary_data(self):
        if self.shap_values is None:
            raise ValueError("Model not fitted yet")
        
        if isinstance(self.shap_values, list):
            shap_values_class1 = self.shap_values[1]
        else:
            shap_values_class1 = self.shap_values
        
        return {
            'shap_values': shap_values_class1,
            'features': self.X,
            'feature_names': self.feature_names,
            'expected_value': self.explainer.expected_value[1] if isinstance(self.explainer.expected_value, list) else self.explainer.expected_value
        }


def shap_based_attribution(touchpoints_df, model_type='gradient_boosting', regularization_strength=1.0):
    model = SHAPAttribution(model_type=model_type, regularization_strength=regularization_strength)
    model.fit(touchpoints_df)
    attribution = model.get_channel_attribution()
    return attribution, model


def combine_all_attributions(rule_based_attributions, shap_attribution, prior_alpha=1.0):
    combined = rule_based_attributions.merge(
        shap_attribution[['channel', 'shap_weight', 'shap_avg_value']],
        on='channel',
        how='outer'
    )
    
    weight_columns = [
        'last_touch_weight',
        'first_touch_weight',
        'linear_weight',
        'time_decay_weight',
        'position_weight',
        'markov_weight',
        'shap_weight'
    ]
    
    for col in weight_columns:
        if col in combined.columns:
            combined[col] = combined[col].fillna(0)
    
    available_weights = [c for c in weight_columns if c in combined.columns]
    
    n_channels = len(combined)
    uniform_prior = 1.0 / n_channels
    
    raw_ensemble = combined[available_weights].mean(axis=1)
    
    prior = np.ones(n_channels) * prior_alpha * uniform_prior
    regularized = raw_ensemble.values + prior
    combined['ensemble_weight'] = (regularized / regularized.sum()).round(4)
    
    for col in available_weights:
        raw = combined[col].values
        prior_vec = np.ones(n_channels) * prior_alpha * uniform_prior
        regularized_col = raw + prior_vec
        combined[col + '_regularized'] = (regularized_col / regularized_col.sum()).round(4)
    
    return combined


if __name__ == '__main__':
    from data_generator import generate_attribution_data
    
    users_df, touchpoints_df = generate_attribution_data(n_users=2000)
    print("运行SHAP归因分析...")
    
    shap_attr, model = shap_based_attribution(touchpoints_df)
    print("\nSHAP归因结果:")
    print(shap_attr[['channel', 'shap_weight', 'shap_avg_value']])
    
    print("\n特征重要性:")
    print(model.get_feature_importance().head(10))
