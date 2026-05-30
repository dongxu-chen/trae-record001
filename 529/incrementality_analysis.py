import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
import warnings
warnings.filterwarnings('ignore')


def prepare_incrementality_data(touchpoints_df, users_df):
    channels = sorted(touchpoints_df['channel'].unique())
    
    user_channel_matrix = []
    
    for user_id, group in touchpoints_df.groupby('user_id'):
        user_channels = group['channel'].unique()
        user_data = {
            'user_id': user_id,
            'converted': group['converted'].iloc[0],
            'conversion_value': group['conversion_value'].iloc[0],
            'total_touchpoints': len(group),
            'total_cost': group['cost'].sum()
        }
        
        for channel in channels:
            user_data[f'has_{channel.replace(" ", "_")}'] = 1 if channel in user_channels else 0
            user_data[f'{channel.replace(" ", "_")}_count'] = (group['channel'] == channel).sum()
            user_data[f'{channel.replace(" ", "_")}_cost'] = group[group['channel'] == channel]['cost'].sum()
        
        user_channel_matrix.append(user_data)
    
    features_df = pd.DataFrame(user_channel_matrix)
    
    return features_df, channels


def calculate_removal_effect(touchpoints_df, users_df, attribution_df, weight_col='ensemble_weight'):
    total_conversions = users_df['converted'].sum()
    total_value = users_df['conversion_value'].sum()
    total_users = len(users_df)
    
    channels = sorted(touchpoints_df['channel'].unique())
    
    removal_results = []
    
    for channel in channels:
        channel_weight = attribution_df[
            attribution_df['channel'] == channel
        ][weight_col].values[0]
        
        users_with_channel = touchpoints_df[
            touchpoints_df['channel'] == channel
        ]['user_id'].unique()
        
        users_without_channel = [u for u in users_df['user_id'] if u not in users_with_channel]
        
        conv_with = users_df[users_df['user_id'].isin(users_with_channel)]['converted'].sum()
        value_with = users_df[users_df['user_id'].isin(users_with_channel)]['conversion_value'].sum()
        users_with_count = len(users_with_channel)
        
        conv_without = users_df[users_df['user_id'].isin(users_without_channel)]['converted'].sum()
        value_without = users_df[users_df['user_id'].isin(users_without_channel)]['conversion_value'].sum()
        users_without_count = len(users_without_channel)
        
        rate_with = conv_with / users_with_count * 100 if users_with_count > 0 else 0
        rate_without = conv_without / users_without_count * 100 if users_without_count > 0 else 0
        
        conversion_lift = rate_with - rate_without
        
        channel_spend = touchpoints_df[touchpoints_df['channel'] == channel]['cost'].sum()
        
        attributed_conversions = channel_weight * total_conversions
        attributed_value = channel_weight * total_value
        
        incremental_conversions = max(0, conv_with - (users_with_count * conv_without / max(total_users, 1)))
        incremental_value = max(0, value_with - (users_with_count * value_without / max(total_users, 1)))
        
        incremental_roi = (incremental_value - channel_spend) / channel_spend * 100 if channel_spend > 0 else 0
        incremental_roas = incremental_value / channel_spend if channel_spend > 0 else 0
        
        removal_results.append({
            'channel': channel,
            'attribution_weight': channel_weight,
            'users_with_channel': users_with_count,
            'users_without_channel': users_without_count,
            'conversions_with_channel': conv_with,
            'conversions_without_channel': conv_without,
            'conversion_rate_with': round(rate_with, 2),
            'conversion_rate_without': round(rate_without, 2),
            'conversion_lift_pct': round(conversion_lift, 2),
            'attributed_conversions': round(attributed_conversions, 2),
            'attributed_value': round(attributed_value, 2),
            'incremental_conversions': round(incremental_conversions, 2),
            'incremental_value': round(incremental_value, 2),
            'channel_spend': round(channel_spend, 2),
            'incremental_roi': round(incremental_roi, 2),
            'incremental_roas': round(incremental_roas, 2)
        })
    
    return pd.DataFrame(removal_results)


class UpliftModel:
    def __init__(self, model_type='random_forest'):
        self.model_type = model_type
        self.treatment_model = None
        self.control_model = None
        self.feature_names = None
        
    def fit(self, features_df, channels):
        channel_cols = [f'has_{c.replace(" ", "_")}' for c in channels]
        feature_cols = channel_cols + [
            'total_touchpoints', 'total_cost'
        ] + [f'{c.replace(" ", "_")}_count' for c in channels]
        
        self.feature_names = feature_cols
        
        uplift_results = {}
        
        for channel in channels:
            treatment_col = f'has_{channel.replace(" ", "_")}'
            
            treatment_mask = features_df[treatment_col] == 1
            control_mask = features_df[treatment_col] == 0
            
            X_treatment = features_df[treatment_mask][feature_cols].drop(columns=[treatment_col])
            y_treatment = features_df[treatment_mask]['converted']
            
            X_control = features_df[control_mask][feature_cols].drop(columns=[treatment_col])
            y_control = features_df[control_mask]['converted']
            
            if self.model_type == 'random_forest':
                t_model = RandomForestClassifier(
                    n_estimators=100, max_depth=6, random_state=42
                )
                c_model = RandomForestClassifier(
                    n_estimators=100, max_depth=6, random_state=42
                )
            else:
                t_model = LogisticRegression(
                    C=1.0, max_iter=1000, random_state=42
                )
                c_model = LogisticRegression(
                    C=1.0, max_iter=1000, random_state=42
                )
            
            if len(X_treatment) > 10 and len(X_control) > 10:
                t_model.fit(X_treatment, y_treatment)
                c_model.fit(X_control, y_control)
                
                uplift_results[channel] = {
                    'treatment_model': t_model,
                    'control_model': c_model,
                    'treatment_feature_names': X_treatment.columns.tolist()
                }
        
        self.uplift_models = uplift_results
        self.channels = channels
        
        return self
    
    def predict_uplift(self, features_df, channel):
        if channel not in self.uplift_models:
            return None
        
        model_data = self.uplift_models[channel]
        t_model = model_data['treatment_model']
        c_model = model_data['control_model']
        feature_cols = model_data['treatment_feature_names']
        
        treatment_col = f'has_{channel.replace(" ", "_")}'
        
        X = features_df.copy()
        
        if treatment_col in X.columns:
            X = X.drop(columns=[treatment_col])
        
        for col in feature_cols:
            if col not in X.columns:
                X[col] = 0
        
        X = X[feature_cols]
        
        treatment_probs = t_model.predict_proba(X)[:, 1]
        control_probs = c_model.predict_proba(X)[:, 1]
        
        uplift = treatment_probs - control_probs
        
        return uplift


def calculate_uplift_by_channel(features_df, channels, uplift_model):
    uplift_summary = []
    
    for channel in channels:
        treatment_col = f'has_{channel.replace(" ", "_")}"'
        treatment_col = f'has_{channel.replace(" ", "_")}'
        
        treatment_users = features_df[features_df[treatment_col] == 1]
        control_users = features_df[features_df[treatment_col] == 0]
        
        uplift_scores = uplift_model.predict_uplift(features_df, channel)
        
        if uplift_scores is not None:
            avg_uplift = uplift_scores.mean()
            max_uplift = uplift_scores.max()
            treatment_uplift = uplift_scores[features_df[treatment_col] == 1].mean()
        else:
            avg_uplift = 0
            max_uplift = 0
            treatment_uplift = 0
        
        observed_conv_rate_treatment = treatment_users['converted'].mean() * 100
        observed_conv_rate_control = control_users['converted'].mean() * 100
        
        observed_uplift = observed_conv_rate_treatment - observed_conv_rate_control
        
        treatment_value = treatment_users['conversion_value'].mean()
        control_value = control_users['conversion_value'].mean()
        
        value_uplift = treatment_value - control_value
        
        treatment_cost = treatment_users[f'{channel.replace(" ", "_")}_cost'].sum()
        treatment_users_count = len(treatment_users)
        
        if treatment_users_count > 0:
            cac = treatment_cost / treatment_users_count
        else:
            cac = 0
        
        uplift_summary.append({
            'channel': channel,
            'treatment_users': treatment_users_count,
            'control_users': len(control_users),
            'observed_conv_rate_treatment': round(observed_conv_rate_treatment, 2),
            'observed_conv_rate_control': round(observed_conv_rate_control, 2),
            'observed_uplift_pct': round(observed_uplift, 2),
            'modeled_avg_uplift': round(avg_uplift * 100, 2),
            'modeled_treatment_uplift': round(treatment_uplift * 100, 2),
            'avg_value_treatment': round(treatment_value, 2),
            'avg_value_control': round(control_value, 2),
            'value_uplift': round(value_uplift, 2),
            'total_channel_cost': round(treatment_cost, 2),
            'cac': round(cac, 2)
        })
    
    return pd.DataFrame(uplift_summary)


def run_incrementality_test(touchpoints_df, users_df, channel, n_bootstraps=1000):
    channel_users = touchpoints_df[
        touchpoints_df['channel'] == channel
    ]['user_id'].unique()
    
    with_channel = users_df[users_df['user_id'].isin(channel_users)].copy()
    without_channel = users_df[~users_df['user_id'].isin(channel_users)].copy()
    
    conv_with = with_channel['converted'].mean()
    conv_without = without_channel['converted'].mean()
    
    value_with = with_channel['conversion_value'].mean()
    value_without = without_channel['conversion_value'].mean()
    
    observed_diff_conv = conv_with - conv_without
    observed_diff_value = value_with - value_without
    
    bootstrap_diffs_conv = []
    bootstrap_diffs_value = []
    
    for _ in range(n_bootstraps):
        sample_with = with_channel.sample(frac=1.0, replace=True)
        sample_without = without_channel.sample(frac=1.0, replace=True)
        
        diff_conv = sample_with['converted'].mean() - sample_without['converted'].mean()
        diff_value = sample_with['conversion_value'].mean() - sample_without['conversion_value'].mean()
        
        bootstrap_diffs_conv.append(diff_conv)
        bootstrap_diffs_value.append(diff_value)
    
    bootstrap_diffs_conv = np.array(bootstrap_diffs_conv)
    bootstrap_diffs_value = np.array(bootstrap_diffs_value)
    
    p_value_conv = (bootstrap_diffs_conv <= 0).mean()
    p_value_value = (bootstrap_diffs_value <= 0).mean()
    
    ci_lower_conv = np.percentile(bootstrap_diffs_conv, 2.5)
    ci_upper_conv = np.percentile(bootstrap_diffs_conv, 97.5)
    
    ci_lower_value = np.percentile(bootstrap_diffs_value, 2.5)
    ci_upper_value = np.percentile(bootstrap_diffs_value, 97.5)
    
    is_significant_conv = (ci_lower_conv > 0) or (ci_upper_conv < 0)
    is_significant_value = (ci_lower_value > 0) or (ci_upper_value < 0)
    
    return {
        'channel': channel,
        'conversion_rate_with': round(conv_with * 100, 2),
        'conversion_rate_without': round(conv_without * 100, 2),
        'observed_diff_conv_pct': round(observed_diff_conv * 100, 2),
        'p_value_conv': round(p_value_conv, 4),
        'ci_95_lower_conv': round(ci_lower_conv * 100, 2),
        'ci_95_upper_conv': round(ci_upper_conv * 100, 2),
        'is_significant_conv': bool(is_significant_conv),
        'avg_value_with': round(value_with, 2),
        'avg_value_without': round(value_without, 2),
        'observed_diff_value': round(observed_diff_value, 2),
        'p_value_value': round(p_value_value, 4),
        'ci_95_lower_value': round(ci_lower_value, 2),
        'ci_95_upper_value': round(ci_upper_value, 2),
        'is_significant_value': bool(is_significant_value),
        'bootstrap_diffs_conv': bootstrap_diffs_conv,
        'bootstrap_diffs_value': bootstrap_diffs_value
    }


def run_full_incrementality_analysis(touchpoints_df, users_df, attribution_df, weight_col='ensemble_weight'):
    features_df, channels = prepare_incrementality_data(touchpoints_df, users_df)
    
    removal_effect = calculate_removal_effect(
        touchpoints_df, users_df, attribution_df, weight_col
    )
    
    uplift_model = UpliftModel(model_type='random_forest')
    uplift_model.fit(features_df, channels)
    
    uplift_summary = calculate_uplift_by_channel(features_df, channels, uplift_model)
    
    significance_tests = {}
    for channel in channels:
        significance_tests[channel] = run_incrementality_test(
            touchpoints_df, users_df, channel
        )
    
    return {
        'features_df': features_df,
        'channels': channels,
        'removal_effect': removal_effect,
        'uplift_model': uplift_model,
        'uplift_summary': uplift_summary,
        'significance_tests': significance_tests
    }


if __name__ == '__main__':
    from data_generator import generate_attribution_data
    from attribution_models import run_all_attribution_models
    from shap_attribution import shap_based_attribution, combine_all_attributions
    
    users_df, touchpoints_df = generate_attribution_data(n_users=1000)
    
    rule_attr = run_all_attribution_models(touchpoints_df)
    shap_attr, _ = shap_based_attribution(touchpoints_df)
    combined = combine_all_attributions(rule_attr, shap_attr)
    
    print("运行增量性分析...")
    results = run_full_incrementality_analysis(
        touchpoints_df, users_df, combined
    )
    
    print("\n=== 移除效应 TOP 5 (按增量转化) ===")
    print(results['removal_effect'][
        ['channel', 'incremental_conversions', 'incremental_value', 'incremental_roi']
    ].sort_values('incremental_conversions', ascending=False).head().to_string(index=False))
    
    print("\n=== Uplift 摘要 TOP 5 (按观测提升) ===")
    print(results['uplift_summary'][
        ['channel', 'observed_uplift_pct', 'modeled_avg_uplift', 'value_uplift']
    ].sort_values('observed_uplift_pct', ascending=False).head().to_string(index=False))
    
    print("\n=== 显著性检验 (Google Search) ===")
    sig = results['significance_tests']['Google Search']
    print(f"  转化率提升: {sig['observed_diff_conv_pct']}% (p={sig['p_value_conv']})")
    print(f"  95% CI: [{sig['ci_95_lower_conv']}%, {sig['ci_95_upper_conv']}%]")
    print(f"  显著: {sig['is_significant_conv']}")
