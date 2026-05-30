import pandas as pd
import numpy as np
from collections import defaultdict
from itertools import combinations
from scipy.linalg import solve


def last_touch_attribution(touchpoints_df):
    converted_users = touchpoints_df[touchpoints_df['converted'] == 1].copy()
    last_touches = converted_users.sort_values('timestamp').groupby('user_id').last().reset_index()
    
    attribution = last_touches.groupby('channel').agg({
        'user_id': 'count',
        'conversion_value': 'sum'
    }).reset_index()
    
    attribution.columns = ['channel', 'last_touch_conversions', 'last_touch_value']
    attribution['last_touch_weight'] = (
        attribution['last_touch_conversions'] / attribution['last_touch_conversions'].sum()
    ).round(4)
    
    return attribution


def first_touch_attribution(touchpoints_df):
    converted_users = touchpoints_df[touchpoints_df['converted'] == 1].copy()
    first_touches = converted_users.sort_values('timestamp').groupby('user_id').first().reset_index()
    
    attribution = first_touches.groupby('channel').agg({
        'user_id': 'count',
        'conversion_value': 'sum'
    }).reset_index()
    
    attribution.columns = ['channel', 'first_touch_conversions', 'first_touch_value']
    attribution['first_touch_weight'] = (
        attribution['first_touch_conversions'] / attribution['first_touch_conversions'].sum()
    ).round(4)
    
    return attribution


def linear_attribution(touchpoints_df):
    converted_users = touchpoints_df[touchpoints_df['converted'] == 1].copy()
    
    converted_users['linear_weight'] = 1 / converted_users['total_touchpoints']
    converted_users['linear_value'] = (
        converted_users['conversion_value'] / converted_users['total_touchpoints']
    )
    
    attribution = converted_users.groupby('channel').agg({
        'linear_weight': 'sum',
        'linear_value': 'sum'
    }).reset_index()
    
    attribution.columns = ['channel', 'linear_conversions', 'linear_value']
    attribution['linear_weight'] = (
        attribution['linear_conversions'] / attribution['linear_conversions'].sum()
    ).round(4)
    
    return attribution


def time_decay_attribution(touchpoints_df, decay_factor=0.5):
    converted_users = touchpoints_df[touchpoints_df['converted'] == 1].copy()
    
    def calculate_time_decay_weights(group):
        n = len(group)
        if n == 1:
            return pd.Series([1.0], index=group.index)
        
        weights = []
        for i in range(n):
            position_from_end = n - 1 - i
            weight = decay_factor ** position_from_end
            weights.append(weight)
        
        weights = np.array(weights) / sum(weights)
        return pd.Series(weights, index=group.index)
    
    converted_users['time_decay_weight'] = converted_users.groupby('user_id').apply(
        calculate_time_decay_weights
    ).reset_index(level=0, drop=True)
    
    converted_users['time_decay_value'] = (
        converted_users['conversion_value'] * converted_users['time_decay_weight']
    )
    
    attribution = converted_users.groupby('channel').agg({
        'time_decay_weight': 'sum',
        'time_decay_value': 'sum'
    }).reset_index()
    
    attribution.columns = ['channel', 'time_decay_conversions', 'time_decay_value']
    total = attribution['time_decay_conversions'].sum()
    attribution['time_decay_weight'] = (
        attribution['time_decay_conversions'] / total
    ).round(4)
    
    return attribution


def position_based_attribution(touchpoints_df, first_weight=0.4, last_weight=0.4):
    converted_users = touchpoints_df[touchpoints_df['converted'] == 1].copy()
    
    def calculate_position_weights(group):
        n = len(group)
        if n == 1:
            return pd.Series([1.0], index=group.index)
        elif n == 2:
            return pd.Series([0.5, 0.5], index=group.index)
        
        middle_weight = (1 - first_weight - last_weight) / (n - 2)
        weights = [first_weight] + [middle_weight] * (n - 2) + [last_weight]
        return pd.Series(weights, index=group.index)
    
    converted_users['position_weight'] = converted_users.groupby('user_id').apply(
        calculate_position_weights
    ).reset_index(level=0, drop=True)
    
    converted_users['position_value'] = (
        converted_users['conversion_value'] * converted_users['position_weight']
    )
    
    attribution = converted_users.groupby('channel').agg({
        'position_weight': 'sum',
        'position_value': 'sum'
    }).reset_index()
    
    attribution.columns = ['channel', 'position_conversions', 'position_value']
    total = attribution['position_conversions'].sum()
    attribution['position_weight'] = (
        attribution['position_conversions'] / total
    ).round(4)
    
    return attribution


class MarkovAttribution:
    def __init__(self, removal_effect=True, smoothing_alpha=1.0):
        self.removal_effect = removal_effect
        self.smoothing_alpha = smoothing_alpha
        self.channels = None
        self.transition_matrix = None
        self.attribution = None
        
    def fit(self, touchpoints_df):
        journeys = touchpoints_df.groupby('user_id').agg({
            'channel': list,
            'converted': 'first'
        }).reset_index()
        
        self.channels = sorted(touchpoints_df['channel'].unique())
        
        all_states = self.channels + ['START', 'CONVERSION', 'NULL']
        n_states = len(all_states)
        state_to_idx = {s: i for i, s in enumerate(all_states)}
        
        transition_counts = np.full((n_states, n_states), self.smoothing_alpha)
        
        for _, row in journeys.iterrows():
            path = row['channel']
            converted = row['converted'] == 1
            
            current_state = 'START'
            for channel in path:
                transition_counts[state_to_idx[current_state], state_to_idx[channel]] += 1
                current_state = channel
            
            if converted:
                transition_counts[state_to_idx[current_state], state_to_idx['CONVERSION']] += 1
            else:
                transition_counts[state_to_idx[current_state], state_to_idx['NULL']] += 1
        
        transition_matrix = transition_counts / transition_counts.sum(axis=1, keepdims=True)
        transition_matrix = np.nan_to_num(transition_matrix)
        
        self.transition_matrix = transition_matrix
        self.state_to_idx = state_to_idx
        self.all_states = all_states
        
        return self
    
    def calculate_conversion_probability(self, transition_matrix):
        transient_states = [s for s in self.all_states if s not in ['CONVERSION', 'NULL']]
        n_transient = len(transient_states)
        
        Q = np.zeros((n_transient, n_transient))
        R = np.zeros((n_transient, 2))
        
        for i, s in enumerate(transient_states):
            for j, s2 in enumerate(transient_states):
                Q[i, j] = transition_matrix[self.state_to_idx[s], self.state_to_idx[s2]]
            R[i, 0] = transition_matrix[self.state_to_idx[s], self.state_to_idx['CONVERSION']]
            R[i, 1] = transition_matrix[self.state_to_idx[s], self.state_to_idx['NULL']]
        
        I = np.eye(n_transient)
        N = solve(I - Q, np.eye(n_transient))
        
        absorption_probs = N @ R
        
        start_idx = transient_states.index('START')
        return absorption_probs[start_idx, 0]
    
    def get_attribution(self):
        if self.transition_matrix is None:
            raise ValueError("Model not fitted yet")
        
        base_conv_prob = self.calculate_conversion_probability(self.transition_matrix)
        
        removal_effects = {}
        for channel in self.channels:
            modified_matrix = self.transition_matrix.copy()
            channel_idx = self.state_to_idx[channel]
            null_idx = self.state_to_idx['NULL']
            
            modified_matrix[:, null_idx] += modified_matrix[:, channel_idx]
            modified_matrix[:, channel_idx] = 0
            
            new_conv_prob = self.calculate_conversion_probability(modified_matrix)
            removal_effect = (base_conv_prob - new_conv_prob) / base_conv_prob if base_conv_prob > 0 else 0
            removal_effects[channel] = max(0, removal_effect)
        
        total_effect = sum(removal_effects.values())
        attribution = {}
        for channel in self.channels:
            attribution[channel] = removal_effects[channel] / total_effect if total_effect > 0 else 0
        
        self.attribution = attribution
        return attribution


def markov_chain_attribution(touchpoints_df):
    model = MarkovAttribution()
    model.fit(touchpoints_df)
    attribution_values = model.get_attribution()
    
    total_conversions = touchpoints_df[touchpoints_df['converted'] == 1]['user_id'].nunique()
    total_value = touchpoints_df[touchpoints_df['converted'] == 1]['conversion_value'].sum()
    
    attribution = pd.DataFrame([
        {
            'channel': channel,
            'markov_conversions': weight * total_conversions,
            'markov_value': weight * total_value,
            'markov_weight': round(weight, 4)
        }
        for channel, weight in attribution_values.items()
    ])
    
    return attribution


def run_all_attribution_models(touchpoints_df):
    last_touch = last_touch_attribution(touchpoints_df)
    first_touch = first_touch_attribution(touchpoints_df)
    linear = linear_attribution(touchpoints_df)
    time_decay = time_decay_attribution(touchpoints_df)
    position = position_based_attribution(touchpoints_df)
    markov = markov_chain_attribution(touchpoints_df)
    
    all_attributions = last_touch.merge(first_touch, on='channel', how='outer')
    all_attributions = all_attributions.merge(linear, on='channel', how='outer')
    all_attributions = all_attributions.merge(time_decay, on='channel', how='outer')
    all_attributions = all_attributions.merge(position, on='channel', how='outer')
    all_attributions = all_attributions.merge(markov, on='channel', how='outer')
    
    all_attributions = all_attributions.fillna(0)
    
    return all_attributions


def regularize_weights(weights, prior_alpha=1.0):
    weights = np.array(weights)
    prior = np.ones(len(weights)) * prior_alpha
    regularized = weights + prior
    regularized = regularized / regularized.sum()
    return regularized


if __name__ == '__main__':
    from data_generator import generate_attribution_data
    
    users_df, touchpoints_df = generate_attribution_data(n_users=1000)
    print("运行所有归因模型...")
    
    all_attributions = run_all_attribution_models(touchpoints_df)
    print("\n归因结果:")
    print(all_attributions[['channel', 'last_touch_weight', 'linear_weight', 'time_decay_weight', 'markov_weight']])
