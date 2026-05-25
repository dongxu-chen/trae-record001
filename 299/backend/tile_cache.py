import os
import io
import numpy as np
from PIL import Image
from functools import lru_cache
import threading
import time
from config import CACHE_DIR, TILE_CONFIG, AQI_COLORS, LOG_MAX
from data_service import data_service


class TileCacheManager:
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.tile_size = TILE_CONFIG['tile_size']
        self.min_zoom = TILE_CONFIG['min_zoom']
        self.max_zoom = TILE_CONFIG['max_zoom']
        self.pregenerate_hours = TILE_CONFIG['pregenerate_hours']
        self.memory_cache = {}
        self.memory_cache_size = TILE_CONFIG['memory_cache_size']
        self.cache_lock = threading.Lock()
        
        os.makedirs(self.cache_dir, exist_ok=True)
        self._init_color_lut()

    def _init_color_lut(self):
        aqi_levels = [
            (0, 50, (0, 228, 0)),
            (50, 100, (0, 228, 0), (255, 255, 0)),
            (100, 150, (255, 255, 0), (255, 126, 0)),
            (150, 200, (255, 126, 0), (255, 0, 0)),
            (200, 300, (255, 0, 0), (153, 0, 76)),
            (300, 500, (153, 0, 76), (126, 0, 35)),
        ]
        
        self.color_lut = np.zeros((501, 3), dtype=np.uint8)
        
        for level in aqi_levels:
            if len(level) == 3:
                start, end, color = level
                self.color_lut[start:end+1] = color
            else:
                start, end, color1, color2 = level
                for aqi in range(start, end + 1):
                    t = (aqi - start) / (end - start)
                    r = int(color1[0] + (color2[0] - color1[0]) * t)
                    g = int(color1[1] + (color2[1] - color1[1]) * t)
                    b = int(color1[2] + (color2[2] - color1[2]) * t)
                    self.color_lut[aqi] = [r, g, b]

    def _tile_to_lonlat(self, x, y, z):
        n = 2.0 ** z
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = np.arctan(np.sinh(np.pi * (1 - 2 * y / n)))
        lat_deg = lat_rad * 180.0 / np.pi
        return lon_deg, lat_deg

    def _get_tile_bounds(self, x, y, z):
        x0, y0 = self._tile_to_lonlat(x, y, z)
        x1, y1 = self._tile_to_lonlat(x + 1, y + 1, z)
        return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]

    def _sample_aqi_data(self, aqi_data, data_bounds, tile_bounds, size):
        data_lon_min, data_lat_min, data_lon_max, data_lat_max = data_bounds
        tile_lon_min, tile_lat_min, tile_lon_max, tile_lat_max = tile_bounds
        
        ny, nx = aqi_data.shape
        
        lons = np.linspace(tile_lon_min, tile_lon_max, size)
        lats = np.linspace(tile_lat_max, tile_lat_min, size)
        
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        i = ((lon_grid - data_lon_min) / (data_lon_max - data_lon_min)) * (nx - 1)
        j = ((lat_grid - data_lat_min) / (data_lat_max - data_lat_min)) * (ny - 1)
        
        i0 = np.floor(np.clip(i, 0, nx - 2)).astype(int)
        j0 = np.floor(np.clip(j, 0, ny - 2)).astype(int)
        i1 = i0 + 1
        j1 = j0 + 1
        
        fx = i - i0
        fy = j - j0
        
        aqi_flat = np.array(aqi_data)
        
        v00 = aqi_flat[j0, i0]
        v10 = aqi_flat[j0, i1]
        v01 = aqi_flat[j1, i0]
        v11 = aqi_flat[j1, i1]
        
        sampled = (1 - fx) * (1 - fy) * v00 + fx * (1 - fy) * v10 + (1 - fx) * fy * v01 + fx * fy * v11
        
        mask = (lon_grid >= data_lon_min) & (lon_grid <= data_lon_max) & \
               (lat_grid >= data_lat_min) & (lat_grid <= data_lat_max)
        sampled[~mask] = -1
        
        return sampled

    def _render_tile_image(self, sampled_aqi, opacity=0.7):
        size = sampled_aqi.shape[0]
        
        rgba = np.zeros((size, size, 4), dtype=np.uint8)
        
        valid_mask = sampled_aqi >= 0
        clipped_aqi = np.clip(sampled_aqi[valid_mask], 0, 500).astype(int)
        
        rgba[valid_mask, :3] = self.color_lut[clipped_aqi]
        rgba[valid_mask, 3] = int(opacity * 255)
        rgba[~valid_mask, 3] = 0
        
        return rgba

    def get_tile_path(self, z, x, y, t):
        return os.path.join(self.cache_dir, str(z), str(x), f"{y}_{t}.png")

    def generate_tile(self, z, x, y, t, opacity=0.7):
        if z < self.min_zoom or z > self.max_zoom:
            return None
        
        cache_key = f"{z}_{x}_{y}_{t}"
        
        with self.cache_lock:
            if cache_key in self.memory_cache:
                return self.memory_cache[cache_key]
        
        tile_path = self.get_tile_path(z, x, y, t)
        if os.path.exists(tile_path):
            try:
                with open(tile_path, 'rb') as f:
                    tile_data = f.read()
                with self.cache_lock:
                    self._add_to_memory_cache(cache_key, tile_data)
                return tile_data
            except:
                pass
        
        aqi_result = data_service.get_aqi_data(t)
        if not aqi_result:
            return None
        
        tile_bounds = self._get_tile_bounds(x, y, z)
        sampled = self._sample_aqi_data(
            np.array(aqi_result['aqi_data']),
            aqi_result['bounds'],
            tile_bounds,
            self.tile_size
        )
        
        if np.all(sampled < 0):
            empty = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
            buffer = io.BytesIO()
            empty.save(buffer, 'PNG')
            tile_data = buffer.getvalue()
        else:
            rgba = self._render_tile_image(sampled, opacity)
            img = Image.fromarray(rgba, 'RGBA')
            buffer = io.BytesIO()
            img.save(buffer, 'PNG', optimize=True)
            tile_data = buffer.getvalue()
            
            os.makedirs(os.path.dirname(tile_path), exist_ok=True)
            with open(tile_path, 'wb') as f:
                f.write(tile_data)
        
        with self.cache_lock:
            self._add_to_memory_cache(cache_key, tile_data)
        
        return tile_data

    def _add_to_memory_cache(self, key, data):
        if len(self.memory_cache) >= self.memory_cache_size:
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
        self.memory_cache[key] = data

    def pregenerate_tiles(self, progress_callback=None):
        metadata = data_service.get_metadata()
        total_steps = min(self.pregenerate_hours, metadata['time_steps'])
        
        total_tiles = 0
        for z in range(self.min_zoom, self.max_zoom - 2):
            n = 2 ** z
            for t in range(total_steps):
                for x in range(n):
                    for y in range(n):
                        tile_path = self.get_tile_path(z, x, y, t)
                        if not os.path.exists(tile_path):
                            lon, lat = self._tile_to_lonlat(x + 0.5, y + 0.5, z)
                            if (100 <= lon <= 130 and 20 <= lat <= 45):
                                self.generate_tile(z, x, y, t)
                                total_tiles += 1
                                if progress_callback and total_tiles % 100 == 0:
                                    progress_callback(total_tiles)
        
        return total_tiles

    def get_cache_status(self):
        total_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(self.cache_dir):
            for f in files:
                if f.endswith('.png'):
                    total_files += 1
                    total_size += os.path.getsize(os.path.join(root, f))
        
        return {
            'disk_tiles': total_files,
            'disk_size_mb': round(total_size / (1024 * 1024), 2),
            'memory_tiles': len(self.memory_cache),
            'cache_dir': self.cache_dir
        }

    def clear_cache(self):
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_cache.clear()
        return True


tile_cache = TileCacheManager()
