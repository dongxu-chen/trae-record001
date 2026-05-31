import numpy as np
import pandas as pd
from geopy.distance import geodesic
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class RiderRecommender:
    def __init__(self):
        self.eta_weight = 0.5
        self.load_balance_weight = 0.3
        self.quality_weight = 0.2
        
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    
    def normalize_scores(self, series):
        if len(series) == 0:
            return series
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series([0.5] * len(series), index=series.index)
        return (series - min_val) / (max_val - min_val)
    
    def evaluate_objectives(self, rider, restaurant_lat, restaurant_lon,
                          user_lat, user_lon, prep_time,
                          weather_impact=1.0, traffic_impact=1.0):
        distance_rider_to_rest = self.calculate_distance(
            rider['lat'], rider['lon'],
            restaurant_lat, restaurant_lon
        )
        distance_rest_to_user = self.calculate_distance(
            restaurant_lat, restaurant_lon,
            user_lat, user_lon
        )
        total_distance = distance_rider_to_rest + distance_rest_to_user
        
        rider_to_rest_time = (distance_rider_to_rest / rider['avg_speed']) * 60
        rider_to_rest_time *= weather_impact * traffic_impact
        
        rest_to_user_time = (distance_rest_to_user / rider['avg_speed']) * 60
        rest_to_user_time *= weather_impact * traffic_impact
        
        total_eta = prep_time + rider_to_rest_time + rest_to_user_time
        
        workload_score = rider['current_orders']
        if rider['status'] == '配送中':
            workload_penalty = workload_score * 5
        else:
            workload_penalty = 0
        
        quality_score = (
            rider['on_time_rate'] * 0.4 +
            (rider['rating'] / 5.0) * 0.3 +
            min(1, rider['experience'] / 24) * 0.3
        )
        
        return {
            'eta_min': total_eta,
            'workload_score': workload_score,
            'quality_score': quality_score,
            'rider_to_rest_time': rider_to_rest_time,
            'rest_to_user_time': rest_to_user_time,
            'total_distance_km': total_distance
        }
    
    def multi_objective_score(self, objectives_df, eta_weight=None, 
                            load_balance_weight=None, quality_weight=None):
        if eta_weight is None:
            eta_weight = self.eta_weight
        if load_balance_weight is None:
            load_balance_weight = self.load_balance_weight
        if quality_weight is None:
            quality_weight = self.quality_weight
        
        total_weight = eta_weight + load_balance_weight + quality_weight
        eta_weight /= total_weight
        load_balance_weight /= total_weight
        quality_weight /= total_weight
        
        df = objectives_df.copy()
        
        eta_norm = 1 - self.normalize_scores(df['eta_min'])
        
        workload_norm = 1 - self.normalize_scores(df['workload_score'])
        
        quality_norm = self.normalize_scores(df['quality_score'])
        
        df['eta_score'] = eta_norm
        df['load_balance_score'] = workload_norm
        df['quality_score_norm'] = quality_norm
        
        df['composite_score'] = (
            eta_norm * eta_weight +
            workload_norm * load_balance_weight +
            quality_norm * quality_weight
        )
        
        return df
    
    def pareto_frontier(self, objectives_df):
        points = objectives_df[['eta_min', 'workload_score', 'quality_score']].values
        
        pareto_indices = []
        for i in range(len(points)):
            dominated = False
            for j in range(len(points)):
                if i != j:
                    if (points[j][0] <= points[i][0] and 
                        points[j][1] <= points[i][1] and 
                        points[j][2] >= points[i][2] and
                        (points[j][0] < points[i][0] or 
                         points[j][1] < points[i][1] or 
                         points[j][2] > points[i][2])):
                        dominated = True
                        break
            if not dominated:
                pareto_indices.append(i)
        
        return objectives_df.iloc[pareto_indices]
    
    def recommend_with_eta(self, riders_df, restaurant_lat, restaurant_lon,
                     user_lat, user_lon, order_hour, prep_time,
                     weather_impact=1.0, traffic_impact=1.0, top_k=5,
                     eta_weight=None, load_balance_weight=None, quality_weight=None):
        
        all_objectives = []
        rider_details = []
        
        for _, rider in riders_df.iterrows():
            objectives = self.evaluate_objectives(
                rider, restaurant_lat, restaurant_lon,
                user_lat, user_lon, prep_time,
                weather_impact, traffic_impact
            )
            
            all_objectives.append(objectives)
            
            distance = self.calculate_distance(
                rider['lat'], rider['lon'],
                restaurant_lat, restaurant_lon
            )
            
            rider_details.append({
                'rider_id': rider['rider_id'],
                'name': rider['name'],
                'distance_km': round(distance, 2),
                'avg_speed': rider['avg_speed'],
                'experience_months': rider['experience'],
                'rating': rider['rating'],
                'on_time_rate': rider['on_time_rate'],
                'status': rider['status'],
                'current_orders': rider['current_orders'],
                'estimated_arrival_min': round(objectives['rider_to_rest_time'], 1),
                'rest_to_user_time_min': round(objectives['rest_to_user_time'], 1),
                'prep_time_min': round(prep_time, 1),
                'total_eta_min': round(objectives['eta_min'], 1)
            })
        
        objectives_df = pd.DataFrame(all_objectives)
        details_df = pd.DataFrame(rider_details)
        
        combined_df = pd.concat([details_df, objectives_df[['eta_min', 'workload_score', 'quality_score']]], axis=1)
        
        scored_df = self.multi_objective_score(
            combined_df, eta_weight, load_balance_weight, quality_weight
        )
        
        pareto_df = self.pareto_frontier(scored_df)
        pareto_rider_ids = pareto_df['rider_id'].tolist()
        scored_df['is_pareto_optimal'] = scored_df['rider_id'].isin(pareto_rider_ids)
        
        scored_df = scored_df.sort_values('composite_score', ascending=False)
        
        return scored_df.head(top_k)
    
    def recommend_riders(self, riders_df, restaurant_lat, restaurant_lon,
                       order_hour, weather_impact=1.0, traffic_impact=1.0, top_k=5):
        
        user_lat = restaurant_lat + 0.01
        user_lon = restaurant_lon + 0.01
        
        return self.recommend_with_eta(
            riders_df, restaurant_lat, restaurant_lon,
            user_lat, user_lon, order_hour,
            prep_time=20, weather_impact=weather_impact,
            traffic_impact=traffic_impact, top_k=top_k
        )
    
    def get_workload_distribution(self, riders_df):
        total_riders = len(riders_df)
        idle_riders = len(riders_df[riders_df['status'] == '空闲'])
        busy_riders = total_riders - idle_riders
        
        workload_bins = pd.cut(riders_df['current_orders'], 
                               bins=[-1, 0, 1, 2, float('inf')],
                               labels=['空闲', '1单', '2单', '3单以上'])
        
        workload_dist = workload_bins.value_counts().to_dict()
        
        return {
            'total_riders': total_riders,
            'idle_riders': idle_riders,
            'busy_riders': busy_riders,
            'avg_current_orders': round(riders_df['current_orders'].mean(), 2),
            'utilization_rate': round(busy_riders / total_riders if total_riders > 0 else 0, 2),
            'workload_distribution': workload_dist
        }
    
    def get_rider_workload_stats(self, riders_df):
        return self.get_workload_distribution(riders_df)

if __name__ == '__main__':
    import os
    
    if os.path.exists('data/riders.csv'):
        riders = pd.read_csv('data/riders.csv')
        recommender = RiderRecommender()
        
        restaurant_lat, restaurant_lon = 39.9042, 116.4074
        user_lat, user_lon = 39.8942, 116.3974
        
        print("多目标优化骑手推荐 (ETA权重50%, 负载均衡30%, 质量20%):")
        recs = recommender.recommend_with_eta(
            riders, restaurant_lat, restaurant_lon,
            user_lat, user_lon, 12, 20
        )
        print(recs[['rider_id', 'name', 'total_eta_min', 'composite_score', 
                   'eta_score', 'load_balance_score', 'quality_score_norm',
                   'is_pareto_optimal']])
        
        print("\n骑手工作负载统计:")
        print(recommender.get_workload_distribution(riders))
    else:
        print("请先生成数据")
