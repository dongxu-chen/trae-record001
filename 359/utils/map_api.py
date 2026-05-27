import requests
import math
import json
import os
import hashlib
import re
from datetime import datetime, timedelta
from config import Config


class MapAPI:
    def __init__(self, use_mock=None, cache_enabled=True, cache_ttl_days=30):
        self.api_key = Config.AMAP_API_KEY
        self.use_mock = use_mock if use_mock is not None else (not self.api_key or Config.USE_MOCK_DATA)
        self.base_url = 'https://restapi.amap.com/v3'
        
        self.cache_enabled = cache_enabled
        self.cache_ttl = timedelta(days=cache_ttl_days)
        self.cache_dir = 'cache'
        self.geocode_cache_file = os.path.join(self.cache_dir, 'geocode_cache.json')
        self.route_cache_file = os.path.join(self.cache_dir, 'route_cache.json')
        self.address_alias_file = os.path.join(self.cache_dir, 'address_alias.json')
        
        self._geocode_cache = {}
        self._route_cache = {}
        self._address_alias = {}
        
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
            self._load_cache()
    
    def _load_cache(self):
        for cache_file, cache_dict in [
            (self.geocode_cache_file, self._geocode_cache),
            (self.route_cache_file, self._route_cache),
            (self.address_alias_file, self._address_alias)
        ]:
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_dict.update(json.load(f))
                except (json.JSONDecodeError, IOError):
                    pass
    
    def _save_cache(self):
        for cache_file, cache_dict in [
            (self.geocode_cache_file, self._geocode_cache),
            (self.route_cache_file, self._route_cache),
            (self.address_alias_file, self._address_alias)
        ]:
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_dict, f, ensure_ascii=False, indent=2)
            except IOError:
                pass
    
    @staticmethod
    def _normalize_address(address):
        if not address:
            return address
        
        address = address.strip()
        address = re.sub(r'\s+', '', address)
        address = re.sub(r'[，,。.、/\\]', '', address)
        address = re.sub(r'^(中国|中华人民共和国)', '', address)
        
        for city in Config.CITY_COORDS.keys():
            if city in address and address.startswith(city) and not address.startswith(city + '市'):
                address = address.replace(city, city + '市', 1)
        
        return address
    
    @staticmethod
    def _hash_address(address):
        normalized = MapAPI._normalize_address(address)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _get_cached_geocode(self, address):
        if not self.cache_enabled:
            return None
        
        addr_hash = self._hash_address(address)
        normalized = self._normalize_address(address)
        
        if addr_hash in self._address_alias:
            addr_hash = self._address_alias[addr_hash]
        
        cached = self._geocode_cache.get(addr_hash)
        if cached:
            cached_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
            if datetime.now() - cached_time < self.cache_ttl:
                self._address_alias[self._hash_address(address)] = addr_hash
                return (cached['lng'], cached['lat'])
        
        return None
    
    def _set_cached_geocode(self, address, coords):
        if not self.cache_enabled or coords is None:
            return
        
        addr_hash = self._hash_address(address)
        self._geocode_cache[addr_hash] = {
            'address': self._normalize_address(address),
            'lng': coords[0],
            'lat': coords[1],
            'timestamp': datetime.now().isoformat()
        }
        self._save_cache()
    
    def _get_cached_route(self, origin, destination):
        if not self.cache_enabled:
            return None
        
        route_key = hashlib.md5(
            f"{origin[0]:.6f},{origin[1]:.6f}-{destination[0]:.6f},{destination[1]:.6f}".encode('utf-8')
        ).hexdigest()
        
        cached = self._route_cache.get(route_key)
        if cached:
            cached_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
            if datetime.now() - cached_time < self.cache_ttl:
                return {
                    'distance': cached['distance'],
                    'duration': cached['duration'],
                    'tolls': cached.get('tolls', 0),
                    'from_cache': True
                }
        
        return None
    
    def _set_cached_route(self, origin, destination, route_info):
        if not self.cache_enabled or route_info is None:
            return
        
        route_key = hashlib.md5(
            f"{origin[0]:.6f},{origin[1]:.6f}-{destination[0]:.6f},{destination[1]:.6f}".encode('utf-8')
        ).hexdigest()
        
        self._route_cache[route_key] = {
            'origin': [origin[0], origin[1]],
            'destination': [destination[0], destination[1]],
            'distance': route_info['distance'],
            'duration': route_info['duration'],
            'tolls': route_info.get('tolls', 0),
            'timestamp': datetime.now().isoformat()
        }
        self._save_cache()
    
    def geocode(self, address):
        cached = self._get_cached_geocode(address)
        if cached is not None:
            return cached
        
        if self.use_mock:
            coords = self._mock_geocode(address)
            self._set_cached_geocode(address, coords)
            return coords
        
        params = {
            'key': self.api_key,
            'address': address
        }
        response = requests.get(f'{self.base_url}/geocode/geo', params=params)
        data = response.json()
        
        if data.get('status') == '1' and data.get('geocodes'):
            location = data['geocodes'][0]['location'].split(',')
            coords = (float(location[0]), float(location[1]))
            self._set_cached_geocode(address, coords)
            return coords
        
        return None
    
    def _mock_geocode(self, address):
        for city, coords in Config.CITY_COORDS.items():
            if city in address:
                return coords[0] + (0.01 * (hash(address) % 10)), coords[1] + (0.01 * (hash(address) % 8))
        return 116.4074, 39.9042
    
    def get_route_distance(self, origin, destination, strategy=1):
        cached = self._get_cached_route(origin, destination)
        if cached is not None:
            return cached
        
        if self.use_mock:
            route_info = self._mock_route_distance(origin, destination)
            self._set_cached_route(origin, destination, route_info)
            return route_info
        
        origin_str = f'{origin[0]},{origin[1]}'
        destination_str = f'{destination[0]},{destination[1]}'
        
        params = {
            'key': self.api_key,
            'origin': origin_str,
            'destination': destination_str,
            'strategy': strategy
        }
        response = requests.get(f'{self.base_url}/direction/driving', params=params)
        data = response.json()
        
        if data.get('status') == '1' and data.get('route', {}).get('paths'):
            path = data['route']['paths'][0]
            route_info = {
                'distance': float(path['distance']) / 1000,
                'duration': float(path['duration']) / 3600,
                'tolls': float(path.get('tolls', 0))
            }
            self._set_cached_route(origin, destination, route_info)
            return route_info
        
        return None
    
    def _mock_route_distance(self, origin, destination):
        lat1, lon1 = origin[1], origin[0]
        lat2, lon2 = destination[1], destination[0]
        
        radius = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        straight_distance = radius * c
        
        road_factor = 1.2 + 0.3 * (hash(f"{origin}{destination}") % 10) / 10
        distance = straight_distance * road_factor
        avg_speed = 60 + (hash(f"speed{origin}{destination}") % 40)
        duration = distance / avg_speed
        
        return {
            'distance': round(distance, 2),
            'duration': round(duration, 2),
            'tolls': round(distance * 0.5, 2) if distance > 100 else 0,
            'from_cache': False
        }
    
    def calculate_distance(self, from_address, to_address):
        origin = self.geocode(from_address)
        destination = self.geocode(to_address)
        
        if origin and destination:
            return self.get_route_distance(origin, destination)
        return None
    
    def get_cache_stats(self):
        return {
            'geocode_count': len(self._geocode_cache),
            'route_count': len(self._route_cache),
            'alias_count': len(self._address_alias)
        }
    
    def clear_cache(self):
        self._geocode_cache.clear()
        self._route_cache.clear()
        self._address_alias.clear()
        for f in [self.geocode_cache_file, self.route_cache_file, self.address_alias_file]:
            if os.path.exists(f):
                os.remove(f)
        self._save_cache()
