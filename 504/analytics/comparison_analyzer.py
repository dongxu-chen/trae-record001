import pandas as pd
from typing import Dict, List, Optional, Tuple
from config import EVENT_TABLE


class ComparisonAnalyzer:
    def __init__(self, db_client):
        self.db = db_client

    def compare_periods(self, 
                         period1_start: str, period1_end: str,
                         period2_start: str, period2_end: str,
                         user_group: Optional[str] = None) -> Dict:
        from .path_analyzer import PathAnalyzer
        
        path_analyzer = PathAnalyzer(self.db)
        
        paths1 = path_analyzer.get_frequent_paths(period1_start, period1_end, user_group=user_group)
        paths2 = path_analyzer.get_frequent_paths(period2_start, period2_end, user_group=user_group)
        
        merged = pd.merge(
            paths1[['path', 'count', 'percentage']],
            paths2[['path', 'count', 'percentage']],
            on='path',
            how='outer',
            suffixes=('_p1', '_p2')
        ).fillna(0)
        
        merged['count_diff'] = merged['count_p2'] - merged['count_p1']
        merged['count_change_pct'] = ((merged['count_p2'] - merged['count_p1']) / 
                                       merged['count_p1'].replace(0, 1) * 100).round(2)
        
        return {
            'period1': {'start': period1_start, 'end': period1_end},
            'period2': {'start': period2_start, 'end': period2_end},
            'comparison_data': merged.sort_values('count_p1', ascending=False)
        }

    def compare_groups(self, start_date: str, end_date: str,
                        group_a: str, group_b: str) -> Dict:
        from .path_analyzer import PathAnalyzer
        
        path_analyzer = PathAnalyzer(self.db)
        
        paths_a = path_analyzer.get_frequent_paths(start_date, end_date, user_group=group_a)
        paths_b = path_analyzer.get_frequent_paths(start_date, end_date, user_group=group_b)
        
        merged = pd.merge(
            paths_a[['path', 'count', 'percentage']],
            paths_b[['path', 'count', 'percentage']],
            on='path',
            how='outer',
            suffixes=('_a', '_b')
        ).fillna(0)
        
        merged['count_diff'] = merged['count_b'] - merged['count_a']
        merged['count_change_pct'] = ((merged['count_b'] - merged['count_a']) / 
                                       merged['count_a'].replace(0, 1) * 100).round(2)
        
        return {
            'group_a': group_a,
            'group_b': group_b,
            'comparison_data': merged.sort_values('count_a', ascending=False)
        }

    def get_group_metrics(self, start_date: str, end_date: str) -> pd.DataFrame:
        where_clause = f"event_time BETWEEN '{start_date}' AND '{end_date}'"
        
        query = f"""
        SELECT 
            user_group,
            count(DISTINCT user_id) as user_count,
            count(DISTINCT session_id) as session_count,
            count(*) as event_count,
            round(count(*) / count(DISTINCT session_id), 2) as avg_events_per_session
        FROM {EVENT_TABLE}
        WHERE {where_clause}
        GROUP BY user_group
        ORDER BY user_count DESC
        """
        
        return self.db.execute_query(query)

    def get_group_path_similarity(self, start_date: str, end_date: str,
                                   group_a: str, group_b: str,
                                   top_n: int = 20) -> Dict:
        from .path_analyzer import PathAnalyzer
        
        path_analyzer = PathAnalyzer(self.db)
        
        paths_a = path_analyzer.get_frequent_paths(start_date, end_date, user_group=group_a, top_n=top_n)
        paths_b = path_analyzer.get_frequent_paths(start_date, end_date, user_group=group_b, top_n=top_n)
        
        paths_a_set = set(paths_a['path'].tolist())
        paths_b_set = set(paths_b['path'].tolist())
        
        common_paths = paths_a_set & paths_b_set
        unique_to_a = paths_a_set - paths_b_set
        unique_to_b = paths_b_set - paths_a_set
        
        jaccard_similarity = len(common_paths) / len(paths_a_set | paths_b_set) if (paths_a_set | paths_b_set) else 0
        
        return {
            'group_a': group_a,
            'group_b': group_b,
            'common_paths_count': len(common_paths),
            'unique_to_a_count': len(unique_to_a),
            'unique_to_b_count': len(unique_to_b),
            'jaccard_similarity': round(jaccard_similarity * 100, 2),
            'common_paths': list(common_paths)[:10],
            'unique_to_a': list(unique_to_a)[:10],
            'unique_to_b': list(unique_to_b)[:10]
        }
