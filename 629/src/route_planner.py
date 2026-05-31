import numpy as np
import pandas as pd
from geopy.distance import geodesic
from dataclasses import dataclass
from typing import List, Tuple, Dict
import warnings
warnings.filterwarnings('ignore')

@dataclass
class Location:
    lat: float
    lon: float
    name: str = None

class RoutePlanner:
    def __init__(self):
        pass
    
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        return geodesic((loc1.lat, loc1.lon), (loc2.lat, loc2.lon)).kilometers
    
    def calculate_route_distance(self, locations: List[Location]) -> float:
        total_distance = 0
        for i in range(len(locations) - 1):
            total_distance += self.calculate_distance(locations[i], locations[i+1])
        return total_distance
    
    def estimate_travel_time(self, distance: float, avg_speed: float = 25, 
                             traffic_factor: float = 1.0,
                             weather_factor: float = 1.0) -> float:
        base_time = (distance / avg_speed) * 60
        return base_time * traffic_factor * weather_factor
    
    def plan_delivery_route(self, 
                            rider_location: Location,
                            restaurant: Location,
                            user: Location,
                            avg_speed: float = 25,
                            traffic_factor: float = 1.0,
                            weather_factor: float = 1.0) -> Dict:
        route = [
            rider_location,
            restaurant,
            user
        ]
        
        distance_rider_to_rest = self.calculate_distance(rider_location, restaurant)
        distance_rest_to_user = self.calculate_distance(restaurant, user)
        total_distance = distance_rider_to_rest + distance_rest_to_user
        
        travel_time_rider_to_rest = self.estimate_travel_time(
            distance_rider_to_rest, avg_speed, traffic_factor, weather_factor
        )
        travel_time_rest_to_user = self.estimate_travel_time(
            distance_rest_to_user, avg_speed, traffic_factor, weather_factor
        )
        total_travel_time = travel_time_rider_to_rest + travel_time_rest_to_user
        
        waypoints = [
            {"name": loc.name, "lat": loc.lat, "lon": loc.lon}
            for loc in route
        ]
        
        return {
            "waypoints": waypoints,
            "distance_rider_to_rest_km": round(distance_rider_to_rest, 2),
            "distance_rest_to_user_km": round(distance_rest_to_user, 2),
            "total_distance_km": round(total_distance, 2),
            "travel_time_rider_to_rest_min": round(travel_time_rider_to_rest, 1),
            "travel_time_rest_to_user_min": round(travel_time_rest_to_user, 1),
            "total_travel_time_min": round(total_travel_time, 1),
            "route_coordinates": [(loc.lat, loc.lon) for loc in route]
        }
    
    def optimize_multi_stop_route(self, 
                                  rider_location: Location,
                                  deliveries: List[Tuple[Location, Location]],
                                  avg_speed: float = 25,
                                  traffic_factor: float = 1.0,
                                  weather_factor: float = 1.0) -> Dict:
        all_locations = [rider_location]
        for rest, user in deliveries:
            all_locations.extend([rest, user])
        
        best_order = list(range(len(all_locations)))
        best_distance = float('inf')
        
        if len(all_locations) <= 6:
            import itertools
            for perm in itertools.permutations(range(1, len(all_locations))):
                order = [0] + list(perm)
                
                rest_indices = [i for i in range(1, len(all_locations), 2)]
                user_indices = [i for i in range(2, len(all_locations), 2)]
                
                valid = True
                for ri, ui in zip(rest_indices, user_indices):
                    if order.index(ri) > order.index(ui):
                        valid = False
                        break
                
                if valid:
                    distance = sum(
                        self.calculate_distance(all_locations[order[i]], all_locations[order[i+1]])
                        for i in range(len(order) - 1)
                    )
                    if distance < best_distance:
                        best_distance = distance
                        best_order = order
        
        optimized_route = [all_locations[i] for i in best_order]
        total_travel_time = self.estimate_travel_time(
            best_distance, avg_speed, traffic_factor, weather_factor
        )
        
        return {
            "optimized_route": [{"name": loc.name, "lat": loc.lat, "lon": loc.lon} for loc in optimized_route],
            "total_distance_km": round(best_distance, 2),
            "estimated_travel_time_min": round(total_travel_time, 1),
            "route_coordinates": [(loc.lat, loc.lon) for loc in optimized_route]
        }
    
    def get_directions(self, route: List[Tuple[float, float]]) -> List[str]:
        directions = []
        for i in range(len(route) - 1):
            start = route[i]
            end = route[i + 1]
            
            lat_diff = end[0] - start[0]
            lon_diff = end[1] - start[1]
            
            direction = ""
            if abs(lat_diff) > abs(lon_diff):
                direction = "向北" if lat_diff > 0 else "向南"
            else:
                direction = "向东" if lon_diff > 0 else "向西"
            
            distance = self.calculate_distance(
                Location(start[0], start[1]),
                Location(end[0], end[1])
            )
            
            directions.append(f"{direction}行驶 {distance:.2f} 公里")
        
        return directions

if __name__ == '__main__':
    planner = RoutePlanner()
    
    rider = Location(39.9142, 116.4174, "骑手位置")
    restaurant = Location(39.9042, 116.4074, "餐厅")
    user = Location(39.8942, 116.3974, "用户")
    
    result = planner.plan_delivery_route(rider, restaurant, user)
    print("路径规划结果:")
    print(f"总距离: {result['total_distance_km']} km")
    print(f"预计时间: {result['total_travel_time_min']} 分钟")
    print(f"路点: {[wp['name'] for wp in result['waypoints']]}")
