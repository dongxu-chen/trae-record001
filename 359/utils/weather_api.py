import requests
import math
import json
import os
import hashlib
from datetime import datetime, timedelta
from config import Config


class WeatherAPI:
    GRID_SIZE = 0.1
    
    def __init__(self, use_mock=None, cache_enabled=True):
        self.api_key = Config.WEATHER_API_KEY
        self.use_mock = use_mock if use_mock is not None else (not self.api_key or Config.USE_MOCK_DATA)
        self.base_url = 'https://restapi.amap.com/v3/weather/weatherInfo'
        
        self.cache_enabled = cache_enabled
        self.cache_dir = 'cache'
        self.weather_cache_file = os.path.join(self.cache_dir, 'weather_cache.json')
        self.precipitation_cache_file = os.path.join(self.cache_dir, 'precipitation_cache.json')
        self._weather_cache = {}
        self._precipitation_cache = {}
        
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
            self._load_cache()
    
    def _load_cache(self):
        for cache_file, cache_dict in [
            (self.weather_cache_file, self._weather_cache),
            (self.precipitation_cache_file, self._precipitation_cache)
        ]:
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_dict.update(json.load(f))
                except (json.JSONDecodeError, IOError):
                    pass
    
    def _save_cache(self):
        for cache_file, cache_dict in [
            (self.weather_cache_file, self._weather_cache),
            (self.precipitation_cache_file, self._precipitation_cache)
        ]:
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_dict, f, ensure_ascii=False, indent=2)
            except IOError:
                pass
    
    @staticmethod
    def _snap_to_grid(lng, lat):
        grid_lng = round(lng / WeatherAPI.GRID_SIZE) * WeatherAPI.GRID_SIZE
        grid_lat = round(lat / WeatherAPI.GRID_SIZE) * WeatherAPI.GRID_SIZE
        return grid_lng, grid_lat
    
    @staticmethod
    def _get_grid_key(lng, lat, date=None):
        grid_lng, grid_lat = WeatherAPI._snap_to_grid(lng, lat)
        date_str = date.strftime('%Y%m%d') if date else datetime.now().strftime('%Y%m%d')
        return f"{grid_lng:.1f}_{grid_lat:.1f}_{date_str}"
    
    def get_weather_grid(self, lng, lat, date=None, radius_km=20):
        grid_key = self._get_grid_key(lng, lat, date)
        
        if self.cache_enabled and grid_key in self._precipitation_cache:
            cached = self._precipitation_cache[grid_key]
            cache_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
            if datetime.now() - cache_time < timedelta(hours=3):
                return cached['data']
        
        if self.use_mock:
            grid_data = self._mock_precipitation_grid(lng, lat, date, radius_km)
        else:
            grid_data = self._fetch_precipitation_grid(lng, lat, date, radius_km)
        
        if self.cache_enabled:
            self._precipitation_cache[grid_key] = {
                'data': grid_data,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
        
        return grid_data
    
    def _fetch_precipitation_grid(self, lng, lat, date=None, radius_km=20):
        grid_points = []
        steps = int(radius_km / 5)
        step_size = 0.05
        
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                p_lng = lng + i * step_size
                p_lat = lat + j * step_size
                
                distance = math.sqrt((i * step_size * 111) ** 2 + (j * step_size * 111) ** 2)
                if distance > radius_km:
                    continue
                
                params = {
                    'key': Config.AMAP_API_KEY,
                    'city': f"{p_lng},{p_lat}",
                    'extensions': 'base'
                }
                
                try:
                    response = requests.get(self.base_url, params=params, timeout=2)
                    data = response.json()
                    
                    if data.get('status') == '1' and data.get('lives'):
                        live = data['lives'][0]
                        weather = live['weather']
                        temp = float(live['temperature'])
                        
                        precipitation = self._weather_to_precipitation(weather, temp)
                        
                        grid_points.append({
                            'lng': p_lng,
                            'lat': p_lat,
                            'precipitation': precipitation['rate'],
                            'precipitation_type': precipitation['type'],
                            'weather': weather,
                            'temperature': temp,
                            'humidity': float(live['humidity']),
                            'distance': distance
                        })
                except:
                    pass
        
        if not grid_points:
            return self._mock_precipitation_grid(lng, lat, date, radius_km)
        
        return {
            'center_lng': lng,
            'center_lat': lat,
            'grid_size': WeatherAPI.GRID_SIZE,
            'radius_km': radius_km,
            'points': grid_points,
            'avg_precipitation': sum(p['precipitation'] for p in grid_points) / len(grid_points),
            'max_precipitation': max(p['precipitation'] for p in grid_points),
            'precipitation_coverage': sum(1 for p in grid_points if p['precipitation'] > 0) / len(grid_points)
        }
    
    def _mock_precipitation_grid(self, lng, lat, date=None, radius_km=20):
        import random
        
        seed = int(lng * 1000 + lat * 1000 + (date.timetuple().tm_yday if date else 0))
        random.seed(seed)
        
        grid_points = []
        steps = int(radius_km / 5)
        step_size = 0.05
        
        center_precipitation = random.choice([0, 0, 0, 0.5, 2, 5, 10, 20])
        precipitation_decay = random.uniform(0.8, 1.2)
        weather_type = random.choice(['晴', '晴', '晴', '多云', '阴', '小雨', '中雨', '大雨', '雷阵雨', '小雪'])
        base_temp = 20 + random.uniform(-15, 15)
        
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                p_lng = lng + i * step_size
                p_lat = lat + j * step_size
                
                distance = math.sqrt((i * step_size * 111) ** 2 + (j * step_size * 111) ** 2)
                if distance > radius_km:
                    continue
                
                distance_factor = max(0, 1 - (distance / radius_km) * precipitation_decay)
                local_precipitation = center_precipitation * distance_factor * random.uniform(0.7, 1.3)
                local_precipitation = max(0, local_precipitation)
                
                if local_precipitation > 10:
                    local_weather = '大雨' if base_temp > 0 else '大雪'
                elif local_precipitation > 2:
                    local_weather = '中雨' if base_temp > 0 else '中雪'
                elif local_precipitation > 0.1:
                    local_weather = '小雨' if base_temp > 0 else '小雪'
                elif local_precipitation > 0:
                    local_weather = '阴'
                else:
                    local_weather = random.choice(['晴', '多云'])
                
                local_temp = base_temp + random.uniform(-2, 2) - (distance / 100)
                
                precipitation = self._weather_to_precipitation(local_weather, local_temp)
                
                grid_points.append({
                    'lng': p_lng,
                    'lat': p_lat,
                    'precipitation': precipitation['rate'],
                    'precipitation_type': precipitation['type'],
                    'weather': local_weather,
                    'temperature': local_temp,
                    'humidity': random.randint(30, 95),
                    'distance': distance
                })
        
        return {
            'center_lng': lng,
            'center_lat': lat,
            'grid_size': WeatherAPI.GRID_SIZE,
            'radius_km': radius_km,
            'points': grid_points,
            'avg_precipitation': sum(p['precipitation'] for p in grid_points) / len(grid_points),
            'max_precipitation': max(p['precipitation'] for p in grid_points),
            'precipitation_coverage': sum(1 for p in grid_points if p['precipitation'] > 0) / len(grid_points)
        }
    
    @staticmethod
    def _weather_to_precipitation(weather, temperature):
        precipitation_map = {
            '晴': {'rate': 0, 'type': 'none'},
            '多云': {'rate': 0, 'type': 'none'},
            '阴': {'rate': 0.05, 'type': 'none'},
            '小雨': {'rate': 0.5, 'type': 'rain'},
            '中雨': {'rate': 2.5, 'type': 'rain'},
            '大雨': {'rate': 8, 'type': 'rain'},
            '暴雨': {'rate': 20, 'type': 'rain'},
            '雷阵雨': {'rate': 5, 'type': 'rain'},
            '小雪': {'rate': 0.3, 'type': 'snow'},
            '中雪': {'rate': 1.5, 'type': 'snow'},
            '大雪': {'rate': 5, 'type': 'snow'},
            '雾': {'rate': 0, 'type': 'fog'},
            '霾': {'rate': 0, 'type': 'haze'}
        }
        
        result = precipitation_map.get(weather, {'rate': 0, 'type': 'none'})
        
        if result['type'] == 'snow' and temperature > 2:
            result['type'] = 'rain'
            result['rate'] *= 0.7
        elif result['type'] == 'rain' and temperature < -2:
            result['type'] = 'snow'
            result['rate'] *= 1.3
        
        return result
    
    def get_weather(self, city, date=None, coords=None):
        if coords is not None:
            lng, lat = coords
        else:
            lng, lat = Config.CITY_COORDS.get(city, [116.4074, 39.9042])
        
        cache_key = f"{city}_{lng}_{lat}_{date if date else 'now'}"
        
        if self.cache_enabled and cache_key in self._weather_cache:
            return self._weather_cache[cache_key]
        
        if self.use_mock:
            result = self._mock_weather(city, date)
        else:
            params = {
                'key': Config.AMAP_API_KEY,
                'city': city,
                'extensions': 'base'
            }
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if data.get('status') == '1' and data.get('lives'):
                live = data['lives'][0]
                result = {
                    'weather': live['weather'],
                    'temperature': float(live['temperature']),
                    'winddirection': live['winddirection'],
                    'windpower': live['windpower'],
                    'humidity': float(live['humidity'])
                }
            else:
                result = self._mock_weather(city, date)
        
        grid_data = self.get_weather_grid(lng, lat, date)
        result.update({
            'precipitation_rate': grid_data['avg_precipitation'],
            'precipitation_max': grid_data['max_precipitation'],
            'precipitation_coverage': grid_data['precipitation_coverage'],
            'precipitation_grid': grid_data,
            'lng': lng,
            'lat': lat
        })
        
        if self.cache_enabled:
            self._weather_cache[cache_key] = result
            self._save_cache()
        
        return result
    
    def _mock_weather(self, city, date=None):
        import random
        weather_types = ['晴', '多云', '阴', '小雨', '中雨', '大雨', '雷阵雨', '小雪', '中雪', '雾']
        weather_weights = [0.35, 0.25, 0.15, 0.1, 0.05, 0.03, 0.02, 0.02, 0.02, 0.01]
        
        random.seed(hash(city + str(date)) if date else hash(city))
        
        weather = random.choices(weather_types, weights=weather_weights, k=1)[0]
        
        base_temp = 20
        if '哈尔滨' in city or '长春' in city or '沈阳' in city:
            base_temp = 10
        elif '广州' in city or '深圳' in city or '海口' in city:
            base_temp = 28
        
        temperature = base_temp + random.randint(-10, 10)
        winddirections = ['东', '南', '西', '北', '东北', '东南', '西北', '西南']
        winddirection = random.choice(winddirections)
        windpower = random.randint(1, 6)
        humidity = random.randint(30, 90)
        
        return {
            'weather': weather,
            'temperature': temperature,
            'winddirection': winddirection,
            'windpower': str(windpower),
            'humidity': humidity
        }
    
    @staticmethod
    def weather_to_score(weather, precipitation_rate=0, precipitation_coverage=0):
        weather_scores = {
            '晴': 1.0,
            '多云': 1.0,
            '阴': 0.95,
            '小雨': 0.85,
            '中雨': 0.75,
            '大雨': 0.65,
            '暴雨': 0.5,
            '雷阵雨': 0.7,
            '小雪': 0.8,
            '中雪': 0.7,
            '大雪': 0.55,
            '雾': 0.6,
            '霾': 0.75
        }
        
        base_score = weather_scores.get(weather, 0.9)
        
        precipitation_factor = max(0.5, 1.0 - (precipitation_rate / 20) * 0.4)
        coverage_factor = 1.0 - precipitation_coverage * 0.2
        
        final_score = base_score * precipitation_factor * coverage_factor
        return max(0.3, final_score)
    
    @staticmethod
    def precipitation_to_impact(precipitation_rate, precipitation_type):
        if precipitation_rate <= 0:
            return 0
        elif precipitation_rate < 0.5:
            return 0.05 if precipitation_type == 'rain' else 0.08
        elif precipitation_rate < 2.5:
            return 0.15 if precipitation_type == 'rain' else 0.2
        elif precipitation_rate < 8:
            return 0.3 if precipitation_type == 'rain' else 0.35
        else:
            return 0.5 if precipitation_type == 'rain' else 0.55
