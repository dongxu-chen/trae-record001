import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from config import EVENT_TABLE, SESSION_TIMEOUT, MAX_PATH_LENGTH, MIN_PATH_FREQUENCY


class PathAnalyzer:
    def __init__(self, db_client):
        self.db = db_client

    def get_user_sessions(self, start_date: str, end_date: str, 
                            user_group: Optional[str] = None,
                            event_filters: Optional[List[str]] = None) -> pd.DataFrame:
        where_conditions = [f"event_time BETWEEN '{start_date}' AND '{end_date}'"]
        
        if user_group:
            where_conditions.append(f"user_group = '{user_group}'")
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            user_id,
            session_id,
            event_name,
            event_time
        FROM {EVENT_TABLE}
        WHERE {where_clause}
        ORDER BY user_id, session_id, event_time
        """
        
        df = self.db.execute_query(query)
        
        if event_filters:
            df = df[df['event_name'].isin(event_filters)]
        
        return df

    def build_session_paths(self, sessions_df: pd.DataFrame) -> pd.DataFrame:
        if sessions_df.empty:
            return pd.DataFrame()

        session_paths = sessions_df.groupby(['user_id', 'session_id'])['event_name'].apply(
            lambda x: ' -> '.join(x)
        ).reset_index(name='path')
        
        session_paths['path_length'] = session_paths['path'].apply(lambda x: len(x.split(' -> ')))
        
        return session_paths

    def get_frequent_paths(self, start_date: str, end_date: str,
                         min_length: int = 2,
                         max_length: int = MAX_PATH_LENGTH,
                         min_frequency: int = MIN_PATH_FREQUENCY,
                         user_group: Optional[str] = None,
                         event_filters: Optional[List[str]] = None,
                         top_n: int = 20) -> pd.DataFrame:
        
        sessions_df = self.get_user_sessions(start_date, end_date, user_group, event_filters)
        if sessions_df.empty:
            return pd.DataFrame()

        paths_df = self.build_session_paths(sessions_df)
        
        paths_df = paths_df[
            (paths_df['path_length'] >= min_length) & 
            (paths_df['path_length'] <= max_length)
        ]

        path_counts = paths_df['path'].value_counts().reset_index()
        path_counts.columns = ['path', 'count']
        path_counts = path_counts[path_counts['count'] >= min_frequency]
        path_counts['percentage'] = (path_counts['count'] / path_counts['count'].sum() * 100).round(2)
        
        return path_counts.head(top_n)

    def get_prefix_paths(self, start_date: str, end_date: str,
                         start_event: str,
                         max_steps: int = 5,
                         user_group: Optional[str] = None) -> pd.DataFrame:
        
        where_conditions = [f"event_time BETWEEN '{start_date}' AND '{end_date}'"]
        if user_group:
            where_conditions.append(f"user_group = '{user_group}'")
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        WITH session_events AS (
            SELECT 
                user_id,
                session_id,
                arraySort(groupArray(event_time)) as events,
                arraySort(groupArray(event_time)) as times
            FROM {EVENT_TABLE}
            WHERE {where_clause}
            GROUP BY user_id, session_id
            HAVING has(events, '{start_event}')
        )
        SELECT 
            user_id,
            session_id,
            events,
            times,
            indexOf(events, '{start_event}') as start_idx
        FROM session_events
        """
        
        df = self.db.execute_query(query)
        
        if df.empty:
            return pd.DataFrame()

        def extract_path(events, start_idx):
            if start_idx <= 0:
                return None
            path_events = events[start_idx-1:min(start_idx + max_steps - 1, len(events))]
            return ' -> '.join(path_events)

        df['path'] = df.apply(lambda row: extract_path(row['events'], row['start_idx']), axis=1)
        df = df.dropna(subset=['path'])
        
        path_counts = df['path'].value_counts().reset_index()
        path_counts.columns = ['path', 'count']
        path_counts['percentage'] = (path_counts['count'] / path_counts['count'].sum() * 100).round(2)
        
        return path_counts

    def get_dropoff_points(self, start_date: str, end_date: str,
                           user_group: Optional[str] = None) -> pd.DataFrame:
        
        sessions_df = self.get_user_sessions(start_date, end_date, user_group)
        if sessions_df.empty:
            return pd.DataFrame()

        paths_df = self.build_session_paths(sessions_df)
        
        all_transitions = defaultdict(int)
        total_sessions = len(paths_df)

        for path in paths_df['path']:
            events = path.split(' -> ')
            for i in range(len(events)):
                all_transitions[events[i]] += 1

        dropoff_data = []
        for event, count in all_transitions.items():
            dropoff_data.append({
                'event': event,
                'sessions_reached': count,
                'dropoff_rate': ((total_sessions - count) / total_sessions * 100).round(2)
            })

        result_df = pd.DataFrame(dropoff_data)
        result_df = result_df.sort_values('sessions_reached', ascending=False)
        
        return result_df

    def get_sankey_data(self, start_date: str, end_date: str,
                         max_depth: int = 5,
                         user_group: Optional[str] = None,
                         event_filters: Optional[List[str]] = None) -> Dict:
        
        sessions_df = self.get_user_sessions(start_date, end_date, user_group, event_filters)
        if sessions_df.empty:
            return {'nodes': [], 'links': []}

        paths_df = self.build_session_paths(sessions_df)
        paths_df = paths_df[paths_df['path_length'] >= 2]

        transitions = defaultdict(int)
        nodes = set()

        for path in paths_df['path']:
            events = path.split(' -> ')
            for i in range(min(len(events) - 1, max_depth - 1)):
                source = events[i]
                target = events[i + 1]
                transitions[(source, target)] += 1
                nodes.add(source)
                nodes.add(target)

        node_list = list(nodes)
        node_index = {node: i for i, node in enumerate(node_list)}
        
        sankey_nodes = [{'name': node} for node in node_list]
        
        sankey_links = [
            {
                'source': node_index[source],
                'target': node_index[target],
                'value': count
            }
            for (source, target), count in transitions.items()
        ]

        return {
            'nodes': sankey_nodes,
            'links': sankey_links
        }
