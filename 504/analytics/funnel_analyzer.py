import pandas as pd
from typing import List, Dict, Optional
from config import EVENT_TABLE


class FunnelAnalyzer:
    def __init__(self, db_client):
        self.db = db_client

    def build_funnel(self, start_date: str, end_date: str,
                     funnel_steps: List[str],
                     user_group: Optional[str] = None) -> pd.DataFrame:
        if len(funnel_steps) < 2:
            raise ValueError("漏斗至少需要2个步骤")

        where_conditions = [f"event_time BETWEEN '{start_date}' AND '{end_date}'"]
        if user_group:
            where_conditions.append(f"user_group = '{user_group}'")
        where_clause = " AND ".join(where_conditions)

        case_statements = []
        for i, step in enumerate(funnel_steps):
            case_statements.append(
                f"sum(if(event_name = '{step}', 1, 0)) > 0 as step_{i+1}"
            )
        
        case_str = ", ".join(case_statements)
        
        query = f"""
        WITH user_events AS (
            SELECT 
                user_id,
                {case_str}
            FROM {EVENT_TABLE}
            WHERE {where_clause}
            GROUP BY user_id
        )
        SELECT 
            count(*) as total_users,
            {', '.join([f'sum(step_{i+1}) as step_{i+1}_users' for i in range(len(funnel_steps))])}
        FROM user_events
        """
        
        result = self.db.execute_query(query)
        
        if result.empty:
            return pd.DataFrame()

        funnel_data = []
        total_users = result['total_users'].iloc[0]
        
        for i, step in enumerate(funnel_steps):
            step_users = result[f'step_{i+1}_users'].iloc[0]
            conversion_rate = (step_users / total_users * 100) if total_users > 0 else 0
            
            if i == 0:
                step_conversion = 100.0
            else:
                prev_users = result[f'step_{i}_users'].iloc[0]
                step_conversion = (step_users / prev_users * 100) if prev_users > 0 else 0
            
            funnel_data.append({
                'step': step,
                'step_number': i + 1,
                'users': step_users,
                'conversion_from_start': round(conversion_rate, 2),
                'conversion_from_previous': round(step_conversion, 2),
                'dropoff': round(100 - step_conversion, 2)
            })

        return pd.DataFrame(funnel_data)

    def get_funnel_details(self, start_date: str, end_date: str,
                           funnel_steps: List[str],
                           user_group: Optional[str] = None) -> Dict:
        funnel_df = self.build_funnel(start_date, end_date, funnel_steps, user_group)
        
        if funnel_df.empty:
            return {}

        total_users = funnel_df['users'].iloc[0]
        final_users = funnel_df['users'].iloc[-1]
        overall_conversion = (final_users / total_users * 100) if total_users > 0 else 0

        return {
            'funnel_data': funnel_df,
            'total_users': total_users,
            'converted_users': final_users,
            'overall_conversion_rate': round(overall_conversion, 2),
            'avg_step_conversion': round(funnel_df['conversion_from_previous'].mean(), 2),
            'biggest_dropoff_step': funnel_df.loc[funnel_df['dropoff'].idxmax(), 'step'],
            'biggest_dropoff_rate': round(funnel_df['dropoff'].max(), 2)
        }

    def compare_funnels(self, start_date: str, end_date: str,
                        funnel_steps: List[str],
                        group_a: str,
                        group_b: str) -> pd.DataFrame:
        funnel_a = self.build_funnel(start_date, end_date, funnel_steps, group_a)
        funnel_b = self.build_funnel(start_date, end_date, funnel_steps, group_b)

        if funnel_a.empty or funnel_b.empty:
            return pd.DataFrame()

        merged = pd.merge(
            funnel_a[['step', 'step_number', 'users', 'conversion_from_start']],
            funnel_b[['step', 'users', 'conversion_from_start']],
            on='step',
            suffixes=('_a', '_b')
        )

        merged['user_diff'] = merged['users_b'] - merged['users_a']
        merged['conversion_diff'] = (merged['conversion_from_start_b'] - 
                                      merged['conversion_from_start_a']).round(2)

        return merged
