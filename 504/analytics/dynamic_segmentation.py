import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class DimensionType(Enum):
    CATEGORICAL = "categorical"
    NUMERICAL = "numerical"
    DATE = "date"
    BOOLEAN = "boolean"


class Operator(Enum):
    EQUALS = "等于"
    NOT_EQUALS = "不等于"
    CONTAINS = "包含"
    NOT_CONTAINS = "不包含"
    GREATER_THAN = "大于"
    LESS_THAN = "小于"
    GREATER_EQUAL = "大于等于"
    LESS_EQUAL = "小于等于"
    IN = "在列表中"
    NOT_IN = "不在列表中"
    STARTS_WITH = "开头是"
    ENDS_WITH = "结尾是"


@dataclass
class SegmentCondition:
    dimension: str
    operator: Operator
    value: Any
    dimension_type: DimensionType = DimensionType.CATEGORICAL


@dataclass
class Segment:
    name: str
    conditions: List[SegmentCondition] = field(default_factory=list)
    logic: str = "AND"
    color: str = "#5470c6"


class DynamicSegmentation:
    def __init__(self):
        self.available_dimensions = {
            'user_group': {
                'type': DimensionType.CATEGORICAL,
                'label': '用户分组',
                'column': 'user_group'
            },
            'device_type': {
                'type': DimensionType.CATEGORICAL,
                'label': '设备类型',
                'column': 'device_type'
            },
            'os': {
                'type': DimensionType.CATEGORICAL,
                'label': '操作系统',
                'column': 'os'
            },
            'browser': {
                'type': DimensionType.CATEGORICAL,
                'label': '浏览器',
                'column': 'browser'
            },
            'session_count': {
                'type': DimensionType.NUMERICAL,
                'label': '会话数',
                'aggregation': 'nunique',
                'column': 'session_id'
            },
            'event_count': {
                'type': DimensionType.NUMERICAL,
                'label': '事件数',
                'aggregation': 'count',
                'column': 'event_name'
            },
            'path_length': {
                'type': DimensionType.NUMERICAL,
                'label': '平均路径长度',
                'aggregation': 'mean_path_length'
            },
            'has_purchase': {
                'type': DimensionType.BOOLEAN,
                'label': '是否购买',
                'event': 'purchase'
            },
            'has_checkout': {
                'type': DimensionType.BOOLEAN,
                'label': '是否结算',
                'event': 'checkout_start'
            },
            'has_add_to_cart': {
                'type': DimensionType.BOOLEAN,
                'label': '是否加购',
                'event': 'add_to_cart'
            },
            'first_seen_days': {
                'type': DimensionType.NUMERICAL,
                'label': '首次访问天数',
                'aggregation': 'days_since_first'
            },
            'last_seen_days': {
                'type': DimensionType.NUMERICAL,
                'label': '最近访问天数',
                'aggregation': 'days_since_last'
            }
        }

    def get_operators_for_type(self, dim_type: DimensionType) -> List[Operator]:
        operator_mapping = {
            DimensionType.CATEGORICAL: [
                Operator.EQUALS, Operator.NOT_EQUALS,
                Operator.CONTAINS, Operator.NOT_CONTAINS,
                Operator.IN, Operator.NOT_IN,
                Operator.STARTS_WITH, Operator.ENDS_WITH
            ],
            DimensionType.NUMERICAL: [
                Operator.EQUALS, Operator.NOT_EQUALS,
                Operator.GREATER_THAN, Operator.LESS_THAN,
                Operator.GREATER_EQUAL, Operator.LESS_EQUAL,
                Operator.IN, Operator.NOT_IN
            ],
            DimensionType.DATE: [
                Operator.EQUALS, Operator.NOT_EQUALS,
                Operator.GREATER_THAN, Operator.LESS_THAN,
                Operator.GREATER_EQUAL, Operator.LESS_EQUAL
            ],
            DimensionType.BOOLEAN: [
                Operator.EQUALS
            ]
        }
        return operator_mapping.get(dim_type, [])

    def get_dimension_values(self, df: pd.DataFrame, dimension: str) -> List[Any]:
        dim_config = self.available_dimensions.get(dimension)
        if not dim_config:
            return []
        
        column = dim_config.get('column', dimension)
        
        if dim_config['type'] == DimensionType.CATEGORICAL:
            return df[column].unique().tolist()
        elif dim_config['type'] == DimensionType.BOOLEAN:
            return [True, False]
        else:
            return []

    def compute_user_features(self, df: pd.DataFrame) -> pd.DataFrame:
        user_features = df.groupby('user_id').agg(
            user_group=('user_group', 'first'),
            device_type=('device_type', lambda x: x.mode()[0] if len(x) > 0 else None),
            os=('os', lambda x: x.mode()[0] if len(x) > 0 else None),
            browser=('browser', lambda x: x.mode()[0] if len(x) > 0 else None),
            session_count=('session_id', 'nunique'),
            event_count=('event_name', 'count'),
            first_seen=('event_time', 'min'),
            last_seen=('event_time', 'max'),
            events=('event_name', list)
        ).reset_index()
        
        user_features['has_purchase'] = user_features['events'].apply(
            lambda x: 'purchase' in x or 'checkout_complete' in x
        )
        user_features['has_checkout'] = user_features['events'].apply(
            lambda x: 'checkout_start' in x
        )
        user_features['has_add_to_cart'] = user_features['events'].apply(
            lambda x: 'add_to_cart' in x
        )
        
        user_features['first_seen_days'] = (
            pd.Timestamp.now() - user_features['first_seen']
        ).dt.total_seconds() / 86400
        
        user_features['last_seen_days'] = (
            pd.Timestamp.now() - user_features['last_seen']
        ).dt.total_seconds() / 86400
        
        return user_features

    def evaluate_condition(self, user_features: pd.Series, 
                            condition: SegmentCondition) -> bool:
        dim_value = user_features.get(condition.dimension)
        
        if dim_value is None:
            return False
        
        op = condition.operator
        target = condition.value
        
        if op == Operator.EQUALS:
            return dim_value == target
        elif op == Operator.NOT_EQUALS:
            return dim_value != target
        elif op == Operator.CONTAINS:
            return target in str(dim_value)
        elif op == Operator.NOT_CONTAINS:
            return target not in str(dim_value)
        elif op == Operator.GREATER_THAN:
            return dim_value > target
        elif op == Operator.LESS_THAN:
            return dim_value < target
        elif op == Operator.GREATER_EQUAL:
            return dim_value >= target
        elif op == Operator.LESS_EQUAL:
            return dim_value <= target
        elif op == Operator.IN:
            return dim_value in target
        elif op == Operator.NOT_IN:
            return dim_value not in target
        elif op == Operator.STARTS_WITH:
            return str(dim_value).startswith(str(target))
        elif op == Operator.ENDS_WITH:
            return str(dim_value).endswith(str(target))
        
        return False

    def segment_users(self, user_features: pd.DataFrame, 
                      segment: Segment) -> pd.DataFrame:
        if not segment.conditions:
            result = user_features.copy()
            result['segment'] = segment.name
            return result
        
        mask = pd.Series([True] * len(user_features), index=user_features.index)
        
        for i, condition in enumerate(segment.conditions):
            condition_mask = user_features.apply(
                lambda x: self.evaluate_condition(x, condition),
                axis=1
            )
            
            if i == 0:
                mask = condition_mask
            elif segment.logic == "AND":
                mask = mask & condition_mask
            else:
                mask = mask | condition_mask
        
        result = user_features[mask].copy()
        result['segment'] = segment.name
        return result

    def create_segments_from_df(self, df: pd.DataFrame, 
                                 segments: List[Segment]) -> Dict[str, pd.DataFrame]:
        user_features = self.compute_user_features(df)
        
        segment_results = {}
        all_segmented_users = set()
        
        for segment in segments:
            segment_df = self.segment_users(user_features, segment)
            segment_users = set(segment_df['user_id'].tolist())
            new_users = segment_users - all_segmented_users
            segment_results[segment.name] = segment_df[segment_df['user_id'].isin(new_users)]
            all_segmented_users.update(new_users)
        
        unsegmented_users = set(user_features['user_id']) - all_segmented_users
        if unsegmented_users:
            unsegmented_df = user_features[user_features['user_id'].isin(unsegmented_users)].copy()
            unsegmented_df['segment'] = '未分群'
            segment_results['未分群'] = unsegmented_df
        
        return segment_results

    def get_segment_summary(self, segment_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        summary_data = []
        
        for segment_name, segment_df in segment_results.items():
            user_count = len(segment_df)
            if user_count == 0:
                continue
            
            summary_data.append({
                'segment': segment_name,
                'user_count': user_count,
                'avg_session_count': round(segment_df['session_count'].mean(), 2),
                'avg_event_count': round(segment_df['event_count'].mean(), 2),
                'purchase_rate': round(segment_df['has_purchase'].mean() * 100, 2),
                'cart_rate': round(segment_df['has_add_to_cart'].mean() * 100, 2),
                'checkout_rate': round(segment_df['has_checkout'].mean() * 100, 2)
            })
        
        return pd.DataFrame(summary_data).sort_values('user_count', ascending=False)

    def get_segment_paths(self, df: pd.DataFrame, 
                           segment_user_ids: List[str],
                           min_length: int = 2,
                           max_length: int = 8,
                           top_n: int = 20) -> pd.DataFrame:
        segment_df = df[df['user_id'].isin(segment_user_ids)]
        
        session_paths = segment_df.groupby(['user_id', 'session_id'])['event_name'].apply(
            lambda x: ' -> '.join(x)
        ).reset_index(name='path')
        
        session_paths['path_length'] = session_paths['path'].apply(
            lambda x: len(x.split(' -> '))
        )
        
        filtered_paths = session_paths[
            (session_paths['path_length'] >= min_length) &
            (session_paths['path_length'] <= max_length)
        ]
        
        path_counts = filtered_paths['path'].value_counts().reset_index()
        path_counts.columns = ['path', 'count']
        path_counts['percentage'] = (
            path_counts['count'] / path_counts['count'].sum() * 100
        ).round(2)
        
        return path_counts.head(top_n)

    def get_segment_sankey_data(self, df: pd.DataFrame,
                                 segment_user_ids: List[str],
                                 max_depth: int = 5,
                                 low_freq_threshold: float = 1.0) -> Dict:
        from .advanced_sankey import AdvancedSankeyAnalyzer
        
        segment_df = df[df['user_id'].isin(segment_user_ids)]
        
        session_paths = segment_df.groupby(['user_id', 'session_id'])['event_name'].apply(
            lambda x: ' -> '.join(x)
        ).reset_index(name='path')
        
        path_counts = session_paths['path'].value_counts().reset_index()
        path_counts.columns = ['path', 'count']
        
        sankey_analyzer = AdvancedSankeyAnalyzer()
        return sankey_analyzer.create_grouped_sankey_data(
            path_counts,
            max_depth=max_depth,
            low_freq_threshold=low_freq_threshold
        )
