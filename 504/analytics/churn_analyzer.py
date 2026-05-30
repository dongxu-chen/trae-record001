import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from config import EVENT_TABLE


class ChurnAnalyzer:
    def __init__(self, db_client):
        self.db = db_client

    def get_churn_rate(self, start_date: str, end_date: str,
                        churn_days: int = 7,
                        user_group: Optional[str] = None) -> Dict:
        where_conditions = []
        if user_group:
            where_conditions.append(f"user_group = '{user_group}'")
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        query = f"""
        WITH user_activity AS (
            SELECT 
                user_id,
                min(event_time) as first_activity,
                max(event_time) as last_activity
            FROM {EVENT_TABLE}
            WHERE {where_clause}
            GROUP BY user_id
        ),
        active_users AS (
            SELECT count(*) as total
            FROM user_activity
            WHERE first_activity <= '{end_date}'
        ),
        churned_users AS (
            SELECT count(*) as churned
            FROM user_activity
            WHERE first_activity <= '{end_date}'
              AND last_activity < ('{end_date}'::DateTime - INTERVAL {churn_days} DAY)
        )
        SELECT 
            total as total_users,
            churned as churned_users,
            (churned / total * 100) as churn_rate
        FROM active_users, churned_users
        """
        
        result = self.db.execute_query(query)
        
        if result.empty:
            return {}

        return {
            'total_users': int(result['total_users'].iloc[0]),
            'churned_users': int(result['churned_users'].iloc[0]),
            'churn_rate': round(result['churn_rate'].iloc[0], 2),
            'churn_days': churn_days
        }

    def get_churn_by_event(self, start_date: str, end_date: str,
                           churn_days: int = 7,
                           user_group: Optional[str] = None) -> pd.DataFrame:
        where_conditions = [f"event_time BETWEEN '{start_date}' AND '{end_date}'"]
        if user_group:
            where_conditions.append(f"user_group = '{user_group}'")
        where_clause = " AND ".join(where_conditions)

        query = f"""
        WITH user_last_activity AS (
            SELECT 
                user_id,
                max(event_time) as last_activity
            FROM {EVENT_TABLE}
            WHERE {where_clause}
            GROUP BY user_id
        ),
        user_churn_status AS (
            SELECT 
                user_id,
                if(last_activity < ('{end_date}'::DateTime - INTERVAL {churn_days} DAY), 1, 0) as is_churned
            FROM user_last_activity
        ),
        user_events AS (
            SELECT 
                u.user_id,
                e.event_name,
                u.is_churned
            FROM user_churn_status u
            JOIN {EVENT_TABLE} e ON u.user_id = e.user_id
            WHERE e.event_time BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT 
            event_name,
            count(DISTINCT user_id) as total_users,
            sum(is_churned) as churned_users,
            (sum(is_churned) / count(DISTINCT user_id) * 100) as churn_rate
        FROM user_events
        GROUP BY event_name
        ORDER BY churn_rate DESC
        """
        
        result = self.db.execute_query(query)
        
        if not result.empty:
            result['churn_rate'] = result['churn_rate'].round(2)
        
        return result

    def get_retention_cohort(self, start_date: str, end_date: str,
                             cohort_period: str = 'week',
                             user_group: Optional[str] = None) -> pd.DataFrame:
        where_conditions = []
        if user_group:
            where_conditions.append(f"user_group = '{user_group}'")
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        date_trunc = "toMonday" if cohort_period == 'week' else "toStartOfMonth"
        
        query = f"""
        WITH user_cohorts AS (
            SELECT 
                user_id,
                {date_trunc}(min(event_time)) as cohort_date
            FROM {EVENT_TABLE}
            WHERE {where_clause}
            GROUP BY user_id
        ),
        user_activity_by_period AS (
            SELECT 
                c.user_id,
                c.cohort_date,
                {date_trunc}(e.event_time) as activity_date,
                dateDiff('{cohort_period}', c.cohort_date, {date_trunc}(e.event_time)) as period_number
            FROM user_cohorts c
            JOIN {EVENT_TABLE} e ON c.user_id = e.user_id
            WHERE {where_clause}
            GROUP BY c.user_id, c.cohort_date, activity_date, period_number
        )
        SELECT 
            cohort_date,
            period_number,
            count(DISTINCT user_id) as active_users
        FROM user_activity_by_period
        WHERE period_number >= 0
        GROUP BY cohort_date, period_number
        ORDER BY cohort_date, period_number
        """
        
        result = self.db.execute_query(query)
        
        if result.empty:
            return pd.DataFrame()

        cohort_sizes = result[result['period_number'] == 0].set_index('cohort_date')['active_users']
        result['cohort_size'] = result['cohort_date'].map(cohort_sizes)
        result['retention_rate'] = (result['active_users'] / result['cohort_size'] * 100).round(2)
        
        return result

    def get_churn_nodes(self, start_date: str, end_date: str,
                        churn_days: int = 7,
                        user_group: Optional[str] = None) -> pd.DataFrame:
        sessions_query = f"""
        SELECT 
            user_id,
            session_id,
            groupArray(event_name) as events,
            max(event_time) as session_end
        FROM {EVENT_TABLE}
        WHERE event_time BETWEEN '{start_date}' AND '{end_date}'
          {f"AND user_group = '{user_group}'" if user_group else ""}
        GROUP BY user_id, session_id
        ORDER BY user_id, session_end
        """
        
        sessions_df = self.db.execute_query(sessions_query)
        
        if sessions_df.empty:
            return pd.DataFrame()

        last_sessions = sessions_df.groupby('user_id').last().reset_index()
        
        churn_threshold = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=churn_days)
        last_sessions['is_churned'] = last_sessions['session_end'] < churn_threshold
        
        churned_sessions = last_sessions[last_sessions['is_churned']]
        
        last_events = []
        for _, row in churned_sessions.iterrows():
            events = row['events']
            if events:
                last_events.append(events[-1])
        
        if not last_events:
            return pd.DataFrame()
        
        event_counts = pd.Series(last_events).value_counts().reset_index()
        event_counts.columns = ['last_event', 'churn_count']
        event_counts['percentage'] = (event_counts['churn_count'] / event_counts['churn_count'].sum() * 100).round(2)
        
        return event_counts
