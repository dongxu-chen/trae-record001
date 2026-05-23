import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

class UserBehaviorAnalyzer:
    def __init__(self, laplace_smoothing=1.0):
        self.behaviors = ['浏览', '点击', '加购', '购买']
        self.behavior_to_idx = {b: i for i, b in enumerate(self.behaviors)}
        self.idx_to_behavior = {i: b for i, b in enumerate(self.behaviors)}
        self.laplace_smoothing = laplace_smoothing
        self.colors = {
            '浏览': '#636EFA',
            '点击': '#00CC96',
            '加购': '#FFA15A',
            '购买': '#EF553B',
            '其他': '#AB63FA'
        }
        self.behavior_groups = {
            '意向行为': ['浏览', '点击'],
            '转化行为': ['加购', '购买']
        }
    
    def generate_mock_data(self, n_users=1000, seed=42):
        np.random.seed(seed)
        
        data = []
        user_ids = []
        
        for user_id in range(n_users):
            is_new = np.random.random() < 0.3
            is_high_active = np.random.random() < 0.25
            
            if is_new:
                behavior_weights = [0.5, 0.3, 0.15, 0.05]
                seq_length = np.random.randint(2, 6)
            elif is_high_active:
                behavior_weights = [0.25, 0.35, 0.25, 0.15]
                seq_length = np.random.randint(6, 15)
            else:
                behavior_weights = [0.4, 0.3, 0.2, 0.1]
                seq_length = np.random.randint(3, 8)
            
            sequence = np.random.choice(self.behaviors, size=seq_length, p=behavior_weights)
            
            for step, behavior in enumerate(sequence):
                data.append({
                    'user_id': user_id,
                    'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(days=np.random.randint(0, 30), hours=step),
                    'behavior': behavior,
                    'step': step
                })
            
            user_ids.append({
                'user_id': user_id,
                'is_new_customer': is_new,
                'is_high_active': is_high_active
            })
        
        df = pd.DataFrame(data)
        user_df = pd.DataFrame(user_ids)
        
        df = df.sort_values(['user_id', 'timestamp']).reset_index(drop=True)
        return df, user_df
    
    def segment_users(self, df, user_df):
        user_stats = df.groupby('user_id').agg(
            total_behaviors=('behavior', 'count'),
            has_purchase=('behavior', lambda x: '购买' in x.values),
            behavior_days=('timestamp', lambda x: x.dt.date.nunique())
        ).reset_index()
        
        user_df = user_df.merge(user_stats, on='user_id', how='left')
        
        def assign_segment(row):
            if row['is_new_customer']:
                return '新客'
            elif row['is_high_active']:
                return '高活跃'
            else:
                return '老客'
        
        user_df['segment'] = user_df.apply(assign_segment, axis=1)
        
        segment_order = ['新客', '老客', '高活跃']
        user_df['segment'] = pd.Categorical(user_df['segment'], categories=segment_order, ordered=True)
        
        return user_df
    
    def build_sequences(self, df):
        sequences = df.groupby('user_id')['behavior'].apply(list).reset_index()
        sequences.columns = ['user_id', 'sequence']
        sequences['sequence_length'] = sequences['sequence'].apply(len)
        return sequences
    
    def apply_laplace_smoothing(self, counts, n_states):
        alpha = self.laplace_smoothing
        smoothed = counts + alpha
        row_sums = smoothed.sum(axis=1, keepdims=True)
        return smoothed / row_sums
    
    def calculate_transition_matrix(self, sequences, order=1, use_smoothing=True):
        n = len(self.behaviors)
        
        if order == 1:
            transition_counts = np.zeros((n, n))
            
            for seq in sequences:
                for i in range(len(seq) - 1):
                    from_idx = self.behavior_to_idx[seq[i]]
                    to_idx = self.behavior_to_idx[seq[i + 1]]
                    transition_counts[from_idx][to_idx] += 1
            
            if use_smoothing:
                transition_matrix = self.apply_laplace_smoothing(transition_counts, n)
            else:
                row_sums = transition_counts.sum(axis=1, keepdims=True)
                transition_matrix = np.where(row_sums > 0, transition_counts / row_sums, 0)
            
            return pd.DataFrame(
                transition_matrix,
                index=self.behaviors,
                columns=self.behaviors
            )
        
        elif order == 2:
            n_states = n * n
            transition_counts = np.zeros((n_states, n))
            
            for seq in sequences:
                for i in range(len(seq) - 2):
                    from_idx_1 = self.behavior_to_idx[seq[i]]
                    from_idx_2 = self.behavior_to_idx[seq[i + 1]]
                    to_idx = self.behavior_to_idx[seq[i + 2]]
                    state_idx = from_idx_1 * n + from_idx_2
                    transition_counts[state_idx][to_idx] += 1
            
            if use_smoothing:
                transition_matrix = self.apply_laplace_smoothing(transition_counts, n)
            else:
                row_sums = transition_counts.sum(axis=1, keepdims=True)
                transition_matrix = np.where(row_sums > 0, transition_counts / row_sums, 0)
            
            state_labels = [f"{b1}+{b2}" for b1 in self.behaviors for b2 in self.behaviors]
            return pd.DataFrame(
                transition_matrix,
                index=state_labels,
                columns=self.behaviors
            )
    
    def calculate_segmented_transitions(self, sequences_df, user_df, order=1, use_smoothing=True):
        merged = sequences_df.merge(user_df[['user_id', 'segment']], on='user_id', how='left')
        
        segmented_matrices = {}
        for segment in merged['segment'].unique():
            segment_seqs = merged[merged['segment'] == segment]['sequence'].tolist()
            segmented_matrices[segment] = self.calculate_transition_matrix(segment_seqs, order, use_smoothing)
        
        return segmented_matrices
    
    def predict_next_behavior(self, current_behaviors, transition_matrix, order=1, top_k=2):
        n = len(self.behaviors)
        
        if order == 1:
            current_behavior = current_behaviors if isinstance(current_behaviors, str) else current_behaviors[-1]
            if current_behavior not in self.behavior_to_idx:
                return None
            
            current_idx = self.behavior_to_idx[current_behavior]
            probabilities = transition_matrix.iloc[current_idx].values
        else:
            if len(current_behaviors) < 2:
                return None
            
            from_idx_1 = self.behavior_to_idx[current_behaviors[-2]]
            from_idx_2 = self.behavior_to_idx[current_behaviors[-1]]
            state_idx = from_idx_1 * n + from_idx_2
            probabilities = transition_matrix.iloc[state_idx].values
        
        top_indices = np.argsort(probabilities)[::-1][:top_k]
        predictions = []
        
        for idx in top_indices:
            if probabilities[idx] > 0:
                predictions.append({
                    'behavior': self.idx_to_behavior[idx],
                    'probability': probabilities[idx]
                })
        
        return predictions
    
    def create_enhanced_sankey_data(self, transition_matrix, threshold=0.01, group_low_freq=True, group_threshold=0.05):
        node_labels = []
        node_groups = []
        node_colors = []
        
        for b in self.behaviors:
            node_labels.append(f"{b}_开始")
            node_groups.append(b)
            node_colors.append(self.colors[b])
        
        if group_low_freq:
            avg_probs = transition_matrix.mean(axis=0)
            high_freq_behaviors = avg_probs[avg_probs >= group_threshold].index.tolist()
            low_freq_behaviors = avg_probs[avg_probs < group_threshold].index.tolist()
            
            for b in self.behaviors:
                if b in high_freq_behaviors:
                    node_labels.append(f"{b}_结束")
                    node_groups.append(b)
                    node_colors.append(self.colors[b])
            
            if low_freq_behaviors:
                node_labels.append("其他_结束")
                node_groups.append("其他")
                node_colors.append(self.colors['其他'])
        else:
            high_freq_behaviors = self.behaviors
            low_freq_behaviors = []
            for b in self.behaviors:
                node_labels.append(f"{b}_结束")
                node_groups.append(b)
                node_colors.append(self.colors[b])
        
        source = []
        target = []
        value = []
        link_colors = []
        
        n_start = len(self.behaviors)
        
        for i, from_behavior in enumerate(self.behaviors):
            for j, to_behavior in enumerate(self.behaviors):
                prob = transition_matrix.iloc[i, j]
                if prob >= threshold:
                    source.append(i)
                    
                    if group_low_freq and to_behavior in low_freq_behaviors:
                        target_idx = n_start + len(high_freq_behaviors)
                    else:
                        if to_behavior in high_freq_behaviors:
                            target_idx = n_start + high_freq_behaviors.index(to_behavior)
                        else:
                            target_idx = n_start + j
                    
                    target.append(target_idx)
                    value.append(prob * 100)
                    
                    color = self.colors[from_behavior]
                    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
                    link_colors.append(f'rgba({r}, {g}, {b}, 0.4)')
        
        return {
            'node_labels': [l.replace('_开始', '').replace('_结束', '') for l in node_labels],
            'node_groups': node_groups,
            'node_colors': node_colors,
            'source': source,
            'target': target,
            'value': value,
            'link_colors': link_colors,
            'high_freq_behaviors': high_freq_behaviors,
            'low_freq_behaviors': low_freq_behaviors
        }
    
    def plot_enhanced_sankey(self, transition_matrix, title='用户行为流向桑基图', 
                             threshold=0.01, group_low_freq=True, group_threshold=0.05):
        sankey_data = self.create_enhanced_sankey_data(
            transition_matrix, threshold, group_low_freq, group_threshold
        )
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=sankey_data['node_labels'],
                color=sankey_data['node_colors'],
                customdata=sankey_data['node_groups'],
                hovertemplate='%{label}<br>分组: %{customdata}<extra></extra>'
            ),
            link=dict(
                source=sankey_data['source'],
                target=sankey_data['target'],
                value=sankey_data['value'],
                color=sankey_data['link_colors'],
                hovertemplate='转移: %{source.label} → %{target.label}<br>概率: %{value:.1f}%<extra></extra>'
            )
        )])
        
        annotations = []
        if group_low_freq and sankey_data['low_freq_behaviors']:
            annotations.append(dict(
                x=0.95,
                y=1.05,
                text=f"「其他」包含: {', '.join(sankey_data['low_freq_behaviors'])}",
                showarrow=False,
                font=dict(size=10, color='gray'),
                xanchor='right'
            ))
        
        fig.update_layout(
            title=dict(text=title, x=0.5, font_size=16),
            font_size=12,
            height=500,
            annotations=annotations
        )
        
        return fig
    
    def plot_second_order_heatmap(self, transition_matrix, title='二阶转移概率矩阵'):
        fig = px.imshow(
            transition_matrix,
            labels=dict(x='后续行为', y='前两步行为', color='概率'),
            aspect='auto',
            color_continuous_scale='Blues',
            title=title
        )
        
        for i in range(transition_matrix.shape[0]):
            for j in range(transition_matrix.shape[1]):
                fig.add_annotation(
                    x=j, y=i,
                    text=f'{transition_matrix.iloc[i, j]:.1%}',
                    showarrow=False,
                    font=dict(color='black' if transition_matrix.iloc[i, j] < 0.5 else 'white', size=8)
                )
        
        fig.update_layout(height=800, width=700)
        return fig
    
    def plot_transition_heatmap(self, transition_matrix, title='转移概率矩阵'):
        fig = px.imshow(
            transition_matrix,
            labels=dict(x='后续行为', y='当前行为', color='概率'),
            x=self.behaviors,
            y=self.behaviors,
            color_continuous_scale='Blues',
            title=title,
            aspect='auto'
        )
        
        for i in range(len(self.behaviors)):
            for j in range(len(self.behaviors)):
                fig.add_annotation(
                    x=j, y=i,
                    text=f'{transition_matrix.iloc[i, j]:.2%}',
                    showarrow=False,
                    font=dict(color='black' if transition_matrix.iloc[i, j] < 0.5 else 'white')
                )
        
        fig.update_layout(height=500, width=600)
        return fig
    
    def plot_model_comparison(self, sequences, test_sequences=None):
        if test_sequences is None:
            split_idx = int(len(sequences) * 0.8)
            train_seqs = sequences[:split_idx]
            test_seqs = sequences[split_idx:]
        else:
            train_seqs = sequences
            test_seqs = test_sequences
        
        first_order_matrix = self.calculate_transition_matrix(train_seqs, order=1)
        second_order_matrix = self.calculate_transition_matrix(train_seqs, order=2)
        
        first_order_correct = 0
        second_order_correct = 0
        total_predictions = 0
        
        for seq in test_seqs:
            if len(seq) >= 2:
                for i in range(len(seq) - 1):
                    total_predictions += 1
                    
                    first_pred = self.predict_next_behavior(seq[i], first_order_matrix, order=1, top_k=1)
                    if first_pred and first_pred[0]['behavior'] == seq[i + 1]:
                        first_order_correct += 1
            
            if len(seq) >= 3:
                for i in range(len(seq) - 2):
                    second_pred = self.predict_next_behavior(
                        [seq[i], seq[i + 1]], second_order_matrix, order=2, top_k=1
                    )
                    if second_pred and second_pred[0]['behavior'] == seq[i + 2]:
                        second_order_correct += 1
        
        first_order_acc = first_order_correct / max(1, total_predictions)
        second_order_acc = second_order_correct / max(1, sum(1 for seq in test_seqs for _ in range(len(seq) - 2) if len(seq) >= 3))
        
        comparison_data = pd.DataFrame({
            '模型': ['一阶马尔可夫链', '二阶马尔可夫链'],
            '准确率': [first_order_acc, second_order_acc],
            '预测次数': [total_predictions, sum(1 for seq in test_seqs for _ in range(len(seq) - 2) if len(seq) >= 3)]
        })
        
        fig = px.bar(
            comparison_data,
            x='模型',
            y='准确率',
            color='模型',
            text='准确率',
            title='一阶 vs 二阶马尔可夫链预测准确率对比',
            color_discrete_map={'一阶马尔可夫链': '#636EFA', '二阶马尔可夫链': '#00CC96'}
        )
        
        fig.update_traces(texttemplate='%{text:.2%}', textposition='outside')
        fig.update_layout(height=500, yaxis_tickformat='.0%')
        return fig, comparison_data
    
    def plot_segment_comparison(self, segmented_matrices):
        segments = list(segmented_matrices.keys())
        behaviors = self.behaviors
        
        comparison_data = []
        
        for segment in segments:
            matrix = segmented_matrices[segment]
            for from_behavior in behaviors:
                for to_behavior in behaviors:
                    comparison_data.append({
                        '分群': segment,
                        '当前行为': from_behavior,
                        '后续行为': to_behavior,
                        '概率': matrix.loc[from_behavior, to_behavior]
                    })
        
        df = pd.DataFrame(comparison_data)
        
        fig = px.bar(
            df[df['概率'] > 0],
            x='后续行为',
            y='概率',
            color='分群',
            barmode='group',
            facet_col='当前行为',
            title='各分群行为转移概率对比',
            color_discrete_map={'新客': '#636EFA', '老客': '#00CC96', '高活跃': '#FFA15A'}
        )
        
        fig.update_layout(height=500)
        fig.update_yaxes(tickformat='.0%')
        return fig
    
    def plot_segment_distribution(self, user_df):
        segment_counts = user_df['segment'].value_counts().reset_index()
        segment_counts.columns = ['分群', '用户数']
        
        fig = px.pie(
            segment_counts,
            values='用户数',
            names='分群',
            title='用户分群分布',
            color='分群',
            color_discrete_map={'新客': '#636EFA', '老客': '#00CC96', '高活跃': '#FFA15A'}
        )
        
        fig.update_layout(height=400)
        return fig
    
    def generate_behavior_sequence(self, start_state, transition_matrix, order=1, length=10, n_samples=5):
        sequences = []
        
        for _ in range(n_samples):
            if order == 1:
                if isinstance(start_state, str):
                    current = start_state
                    sequence = [current]
                else:
                    current = start_state[-1]
                    sequence = [current]
                
                for _ in range(length - 1):
                    predictions = self.predict_next_behavior(current, transition_matrix, order=1, top_k=len(self.behaviors))
                    if predictions:
                        behaviors = [p['behavior'] for p in predictions]
                        probs = [p['probability'] for p in predictions]
                        probs = np.array(probs) / sum(probs)
                        current = np.random.choice(behaviors, p=probs)
                        sequence.append(current)
                    else:
                        break
            else:
                if len(start_state) >= 2:
                    current_seq = start_state[-2:]
                    sequence = current_seq.copy()
                else:
                    current_seq = start_state
                    sequence = start_state.copy()
                
                for _ in range(length - len(sequence)):
                    predictions = self.predict_next_behavior(current_seq, transition_matrix, order=2, top_k=len(self.behaviors))
                    if predictions:
                        behaviors = [p['behavior'] for p in predictions]
                        probs = [p['probability'] for p in predictions]
                        probs = np.array(probs) / sum(probs)
                        next_behavior = np.random.choice(behaviors, p=probs)
                        sequence.append(next_behavior)
                        current_seq = [current_seq[-1], next_behavior]
                    else:
                        break
            
            sequences.append(sequence)
        
        return sequences
    
    def calculate_path_probability(self, sequence, transition_matrix, order=1):
        if len(sequence) < 2:
            return 1.0
        
        log_prob = 0.0
        n = len(self.behaviors)
        
        for i in range(len(sequence) - 1):
            if order == 1:
                from_behavior = sequence[i]
                to_behavior = sequence[i + 1]
                
                if from_behavior in self.behavior_to_idx and to_behavior in self.behavior_to_idx:
                    prob = transition_matrix.loc[from_behavior, to_behavior]
                    log_prob += np.log(max(prob, 1e-10))
            else:
                if i >= 1:
                    from_1 = sequence[i - 1]
                    from_2 = sequence[i]
                    to_behavior = sequence[i + 1]
                    
                    state = f"{from_1}+{from_2}"
                    if state in transition_matrix.index and to_behavior in transition_matrix.columns:
                        prob = transition_matrix.loc[state, to_behavior]
                        log_prob += np.log(max(prob, 1e-10))
        
        return np.exp(log_prob)
    
    def analyze_churn_risk(self, sequence, transition_matrix, order=1, risk_threshold=0.3):
        churn_patterns = {
            '高风险': ['浏览', '浏览', '浏览'],
            '中风险': ['浏览', '点击', '浏览'],
            '低风险': ['点击', '加购', '点击']
        }
        
        risk_scores = []
        risk_factors = []
        
        if len(sequence) >= 3:
            recent = sequence[-3:]
            path_prob = self.calculate_path_probability(recent, transition_matrix, order=order)
            
            conversion_progress = 0
            if '购买' in recent:
                conversion_progress = 100
            elif '加购' in recent:
                conversion_progress = 60
            elif '点击' in recent:
                conversion_progress = 30
            else:
                conversion_progress = 10
            
            repeat_same = len(set(recent)) == 1
            if repeat_same and recent[0] == '浏览':
                risk_scores.append(0.7)
                risk_factors.append('连续浏览无进展')
            
            no_conversion_signal = '加购' not in recent and '购买' not in recent
            if no_conversion_signal and len(sequence) >= 5:
                risk_scores.append(0.5)
                risk_factors.append('长期无转化意向')
            
            if len(recent) >= 2:
                if order == 1:
                    next_pred = self.predict_next_behavior(recent[-1], transition_matrix, order=1, top_k=3)
                else:
                    next_pred = self.predict_next_behavior(recent[-2:], transition_matrix, order=2, top_k=3)
                
                if next_pred:
                    next_behaviors = [p['behavior'] for p in next_pred]
                    if '购买' not in next_behaviors and '加购' not in next_behaviors[:2]:
                        risk_scores.append(0.4)
                        risk_factors.append('预测下一步无转化意向')
        
        if not risk_scores:
            overall_risk = 0.1
            risk_level = '低风险'
        else:
            overall_risk = np.mean(risk_scores)
            
            if overall_risk >= risk_threshold:
                risk_level = '高风险'
            elif overall_risk >= risk_threshold * 0.5:
                risk_level = '中风险'
            else:
                risk_level = '低风险'
        
        return {
            'risk_level': risk_level,
            'risk_score': overall_risk,
            'risk_factors': risk_factors,
            'conversion_progress': conversion_progress,
            'path_probability': path_prob if 'path_prob' in locals() else None
        }
    
    def plot_churn_risk_gauge(self, risk_score, title='用户流失风险'):
        if risk_score >= 0.5:
            color = '#EF553B'
        elif risk_score >= 0.25:
            color = '#FFA15A'
        else:
            color = '#00CC96'
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=risk_score * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title, 'font': {'size': 24}},
            delta={'reference': 30, 'increasing': {'color': "#EF553B"}, 'decreasing': {'color': "#00CC96"}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': color},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 25], 'color': 'rgba(0, 204, 150, 0.3)'},
                    {'range': [25, 50], 'color': 'rgba(255, 161, 90, 0.3)'},
                    {'range': [50, 100], 'color': 'rgba(239, 85, 59, 0.3)'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ))
        
        fig.update_layout(height=400)
        return fig
    
    def plot_generated_sequences(self, sequences, title='模拟行为路径'):
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set3[:len(sequences)]
        
        for idx, seq in enumerate(sequences):
            y_values = [self.behavior_to_idx[b] for b in seq]
            x_values = list(range(len(seq)))
            
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines+markers',
                name=f'路径 {idx + 1}',
                line=dict(color=colors[idx], width=2),
                marker=dict(size=10, color=colors[idx]),
                text=[f'步骤 {i}: {b}' for i, b in enumerate(seq)],
                hoverinfo='text'
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title='行为步骤',
            yaxis_title='行为类型',
            yaxis=dict(
                tickmode='array',
                tickvals=list(range(len(self.behaviors))),
                ticktext=self.behaviors
            ),
            height=500,
            hovermode='x unified'
        )
        
        return fig
    
    def analyze_by_time_period(self, df, user_df, order=1, use_smoothing=True):
        df = df.copy()
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6])
        
        activity_dates = df['timestamp'].dt.date.unique()
        n_activity_days = len(activity_dates)
        n_promo_days = max(1, int(n_activity_days * 0.2))
        promo_dates = np.random.choice(activity_dates, size=n_promo_days, replace=False)
        df['is_promo'] = df['timestamp'].dt.date.isin(promo_dates)
        
        period_results = {}
        
        weekend_df = df[df['is_weekend']]
        weekday_df = df[~df['is_weekend']]
        
        if len(weekend_df) > 0:
            weekend_sequences = self.build_sequences(weekend_df)
            period_results['周末'] = self.calculate_transition_matrix(
                weekend_sequences['sequence'].tolist(), order, use_smoothing
            )
        
        if len(weekday_df) > 0:
            weekday_sequences = self.build_sequences(weekday_df)
            period_results['工作日'] = self.calculate_transition_matrix(
                weekday_sequences['sequence'].tolist(), order, use_smoothing
            )
        
        promo_df = df[df['is_promo']]
        normal_df = df[~df['is_promo']]
        
        if len(promo_df) > 0:
            promo_sequences = self.build_sequences(promo_df)
            period_results['活动期'] = self.calculate_transition_matrix(
                promo_sequences['sequence'].tolist(), order, use_smoothing
            )
        
        if len(normal_df) > 0:
            normal_sequences = self.build_sequences(normal_df)
            period_results['平日'] = self.calculate_transition_matrix(
                normal_sequences['sequence'].tolist(), order, use_smoothing
            )
        
        period_stats = {
            '周末': {'用户数': weekend_df['user_id'].nunique(), '行为数': len(weekend_df)},
            '工作日': {'用户数': weekday_df['user_id'].nunique(), '行为数': len(weekday_df)},
            '活动期': {'用户数': promo_df['user_id'].nunique(), '行为数': len(promo_df)},
            '平日': {'用户数': normal_df['user_id'].nunique(), '行为数': len(normal_df)}
        }
        
        return period_results, period_stats
    
    def plot_period_comparison(self, period_results, metric='购买', title='时段转化对比'):
        comparison_data = []
        
        for period, matrix in period_results.items():
            for from_behavior in self.behaviors:
                if from_behavior in matrix.index:
                    prob = matrix.loc[from_behavior, metric]
                    comparison_data.append({
                        '时段': period,
                        '当前行为': from_behavior,
                        f'转向{metric}概率': prob
                    })
        
        df = pd.DataFrame(comparison_data)
        
        fig = px.bar(
            df,
            x='当前行为',
            y=f'转向{metric}概率',
            color='时段',
            barmode='group',
            title=title,
            color_discrete_map={
                '工作日': '#636EFA',
                '周末': '#00CC96',
                '平日': '#AB63FA',
                '活动期': '#FFA15A'
            }
        )
        
        fig.update_layout(height=500, yaxis_tickformat='.0%')
        return fig
    
    def plot_behavior_timeline(self, df, user_id=None, n_days=7):
        if user_id is not None:
            plot_df = df[df['user_id'] == user_id].copy()
        else:
            sample_users = df['user_id'].unique()[:5]
            plot_df = df[df['user_id'].isin(sample_users)].copy()
        
        plot_df['date'] = plot_df['timestamp'].dt.date
        plot_df['hour'] = plot_df['timestamp'].dt.hour
        
        fig = px.scatter(
            plot_df,
            x='hour',
            y='user_id',
            color='behavior',
            size_max=15,
            title='用户行为时间分布',
            color_discrete_map=self.colors,
            hover_data=['timestamp', 'behavior']
        )
        
        fig.update_layout(
            xaxis_title='小时',
            yaxis_title='用户ID',
            height=400
        )
        
        return fig
    
    def analyze(self, df=None, user_df=None, order=1, use_smoothing=True):
        if df is None or user_df is None:
            df, user_df = self.generate_mock_data()
        
        user_df = self.segment_users(df, user_df)
        sequences_df = self.build_sequences(df)
        
        all_sequences = sequences_df['sequence'].tolist()
        overall_matrix = self.calculate_transition_matrix(all_sequences, order, use_smoothing)
        segmented_matrices = self.calculate_segmented_transitions(sequences_df, user_df, order, use_smoothing)
        
        overall_matrix_first = self.calculate_transition_matrix(all_sequences, order=1, use_smoothing=use_smoothing)
        if order >= 2:
            overall_matrix_second = self.calculate_transition_matrix(all_sequences, order=2, use_smoothing=use_smoothing)
        else:
            overall_matrix_second = None
        
        period_results, period_stats = self.analyze_by_time_period(df, user_df, order=1, use_smoothing=use_smoothing)
        
        return {
            'df': df,
            'user_df': user_df,
            'sequences_df': sequences_df,
            'overall_matrix': overall_matrix,
            'overall_matrix_first': overall_matrix_first,
            'overall_matrix_second': overall_matrix_second,
            'segmented_matrices': segmented_matrices,
            'period_results': period_results,
            'period_stats': period_stats,
            'order': order
        }
    
    def generate_report(self, analysis_result):
        print("=" * 60)
        print("用户消费行为轨迹分析报告 (增强版)")
        print("=" * 60)
        
        user_df = analysis_result['user_df']
        overall_matrix = analysis_result['overall_matrix']
        segmented_matrices = analysis_result['segmented_matrices']
        order = analysis_result['order']
        
        print(f"\n【分析配置】")
        print(f"- 马尔可夫链阶数: {order}阶")
        print(f"- 拉普拉斯平滑: {'启用' if self.laplace_smoothing > 0 else '禁用'}")
        print(f"- 平滑系数: {self.laplace_smoothing}")
        
        print("\n【用户分群统计】")
        print(user_df['segment'].value_counts())
        
        print(f"\n【总体转移概率矩阵 ({order}阶)】")
        if order == 1:
            print(overall_matrix.round(4) * 100)
        else:
            print(overall_matrix.round(4) * 100)
        
        print("\n【各分群预测示例】")
        for segment in segmented_matrices.keys():
            print(f"\n{segment} - 从'浏览'开始的预测:")
            if order == 1:
                predictions = self.predict_next_behavior('浏览', segmented_matrices[segment], order=1)
            else:
                predictions = self.predict_next_behavior(['浏览', '点击'], segmented_matrices[segment], order=2)
            
            if predictions:
                for pred in predictions:
                    print(f"  → {pred['behavior']}: {pred['probability']:.2%}")
        
        print("\n" + "=" * 60)


def main():
    analyzer = UserBehaviorAnalyzer(laplace_smoothing=1.0)
    
    print("正在生成模拟数据并进行分析...")
    result = analyzer.analyze(order=1)
    
    analyzer.generate_report(result)
    
    print("\n正在生成可视化图表...")
    
    fig1 = analyzer.plot_enhanced_sankey(
        result['overall_matrix_first'], 
        '总体用户行为流向桑基图 (增强版)',
        group_low_freq=True,
        group_threshold=0.1
    )
    fig1.write_html('sankey_overall_enhanced.html')
    
    fig2 = analyzer.plot_transition_heatmap(result['overall_matrix_first'], '总体转移概率矩阵')
    fig2.write_html('heatmap_overall.html')
    
    result_second = analyzer.analyze(order=2)
    fig3 = analyzer.plot_second_order_heatmap(result_second['overall_matrix_second'], '二阶转移概率矩阵')
    fig3.write_html('heatmap_second_order.html')
    
    fig4, comp_data = analyzer.plot_model_comparison(result['sequences_df']['sequence'].tolist())
    fig4.write_html('model_comparison.html')
    print("\n【模型对比结果】")
    print(comp_data)
    
    fig5 = analyzer.plot_segment_comparison(result['segmented_matrices'])
    fig5.write_html('segment_comparison.html')
    
    fig6 = analyzer.plot_segment_distribution(result['user_df'])
    fig6.write_html('segment_distribution.html')
    
    print("\n分析完成！已生成以下HTML文件：")
    print("- sankey_overall_enhanced.html (增强版桑基图)")
    print("- heatmap_overall.html (总体热力图)")
    print("- heatmap_second_order.html (二阶转移热力图)")
    print("- model_comparison.html (模型对比)")
    print("- segment_comparison.html (分群对比)")
    print("- segment_distribution.html (分群分布)")


if __name__ == '__main__':
    main()
