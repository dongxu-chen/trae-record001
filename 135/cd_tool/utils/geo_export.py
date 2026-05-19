import numpy as np
import cv2
import json
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime
import warnings


class GeoJSONExporter:
    def __init__(self,
                 crs: str = "EPSG:4326",
                 min_area: int = 10,
                 simplify_tolerance: float = 1.0):
        self.crs = crs
        self.min_area = min_area
        self.simplify_tolerance = simplify_tolerance
        self.features = []
    
    def mask_to_polygons(self,
                         mask: np.ndarray,
                         transform: Optional[Tuple[float, float, float, float, float, float]] = None,
                         min_area: Optional[int] = None) -> List[Dict]:
        min_area = min_area or self.min_area
        
        if len(mask.shape) > 2:
            mask = mask.squeeze()
        
        mask = (mask > 0).astype(np.uint8)
        
        contours, hierarchy = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        polygons = []
        for cnt in contours:
            if cv2.contourArea(cnt) < min_area:
                continue
            
            if self.simplify_tolerance > 0:
                epsilon = self.simplify_tolerance * cv2.arcLength(cnt, True)
                cnt = cv2.approxPolyDP(cnt, epsilon, True)
            
            if transform is not None:
                geo_coords = self._pixel_to_geo(cnt, transform)
            else:
                geo_coords = cnt[:, 0, :].tolist()
            
            if len(geo_coords) > 2:
                if geo_coords[0] != geo_coords[-1]:
                    geo_coords.append(geo_coords[0])
                
                polygon = {
                    "type": "Polygon",
                    "coordinates": [geo_coords]
                }
                polygons.append(polygon)
        
        return polygons
    
    def _pixel_to_geo(self,
                       contour: np.ndarray,
                       transform: Tuple[float, float, float, float, float, float]) -> List[List[float]]:
        x_origin, pixel_width, _, y_origin, _, pixel_height = transform
        
        coords = []
        for point in contour[:, 0, :]:
            x = x_origin + point[0] * pixel_width
            y = y_origin + point[1] * pixel_height
            coords.append([float(x), float(y)])
        
        return coords
    
    def add_change_feature(self,
                          polygon: Dict,
                          change_type: str = "changed",
                          confidence: Optional[float] = None,
                          area: Optional[float] = None,
                          properties: Optional[Dict] = None) -> int:
        feature = {
            "type": "Feature",
            "properties": {
                "change_type": change_type,
                "timestamp": datetime.now().isoformat()
            },
            "geometry": polygon
        }
        
        if confidence is not None:
            feature["properties"]["confidence"] = float(confidence)
        if area is not None:
            feature["properties"]["area_sqm"] = float(area)
        if properties:
            feature["properties"].update(properties)
        
        self.features.append(feature)
        return len(self.features) - 1
    
    def add_from_mask(self,
                      mask: np.ndarray,
                      transform: Optional[Tuple[float, float, float, float, float, float]] = None,
                      change_type: str = "changed",
                      confidence: Optional[np.ndarray] = None,
                      properties: Optional[Dict] = None) -> List[int]:
        polygons = self.mask_to_polygons(mask, transform)
        
        added_ids = []
        for i, polygon in enumerate(polygons):
            conf = None
            if confidence is not None:
                mask_single = np.zeros_like(mask)
                cv2.fillPoly(mask_single, [np.array(polygon["coordinates"][0][:-1], dtype=np.int32)], 1)
                conf = float(confidence[mask_single > 0].mean())
            
            area = None
            if transform is not None:
                pixel_area = abs(transform[1] * transform[5])
                area = cv2.contourArea(np.array(polygon["coordinates"][0][:-1], dtype=np.float32)) * pixel_area
            
            fid = self.add_change_feature(
                polygon=polygon,
                change_type=change_type,
                confidence=conf,
                area=area,
                properties=properties
            )
            added_ids.append(fid)
        
        return added_ids
    
    def export(self, filepath: str, pretty: bool = True) -> Dict:
        geojson = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": self.crs
                }
            },
            "features": self.features
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(geojson, f, indent=2, ensure_ascii=False)
            else:
                json.dump(geojson, f, ensure_ascii=False)
        
        return geojson
    
    def clear(self):
        self.features = []
    
    @staticmethod
    def read_geotransform_from_world_file(filepath: str) -> Tuple[float, float, float, float, float, float]:
        with open(filepath, 'r') as f:
            lines = [float(line.strip()) for line in f.readlines()[:6]]
        
        return (
            lines[4], lines[0], lines[1],
            lines[5], lines[2], lines[3]
        )


class ChangeStatistics:
    def __init__(self):
        self.stats = {
            'total_pixels': 0,
            'changed_pixels': 0,
            'unchanged_pixels': 0,
            'change_ratio': 0.0,
            'change_regions_count': 0,
            'largest_region_area': 0,
            'mean_region_area': 0,
            'median_region_area': 0
        }
    
    def calculate(self,
                  mask: np.ndarray,
                  pixel_area: float = 1.0) -> Dict:
        mask = (mask > 0).astype(np.uint8)
        
        self.stats['total_pixels'] = int(mask.size)
        self.stats['changed_pixels'] = int(np.sum(mask))
        self.stats['unchanged_pixels'] = self.stats['total_pixels'] - self.stats['changed_pixels']
        self.stats['change_ratio'] = self.stats['changed_pixels'] / max(self.stats['total_pixels'], 1)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        areas = [cv2.contourArea(cnt) * pixel_area for cnt in contours]
        
        self.stats['change_regions_count'] = len(areas)
        if areas:
            self.stats['largest_region_area'] = max(areas)
            self.stats['mean_region_area'] = sum(areas) / len(areas)
            self.stats['median_region_area'] = float(np.median(areas))
        
        return self.stats
    
    def to_dict(self) -> Dict:
        return self.stats


class MultiTemporalChangeAnalyzer:
    def __init__(self):
        self.change_masks = []
        self.timestamps = []
    
    def add_temporal_change(self, mask: np.ndarray, timestamp: str):
        self.change_masks.append((mask > 0).astype(np.uint8))
        self.timestamps.append(timestamp)
    
    def analyze_progression(self) -> Dict:
        if len(self.change_masks) < 2:
            warnings.warn("Need at least 2 time points for progression analysis")
            return {}
        
        cumulative_change = np.zeros_like(self.change_masks[0], dtype=np.int32)
        for mask in self.change_masks:
            cumulative_change += mask
        
        stats = {
            'timestamps': self.timestamps,
            'changes_per_timestamp': [int(np.sum(m)) for m in self.change_masks],
            'cumulative_change_map': cumulative_change.tolist(),
            'persistent_change_regions': int(np.sum(cumulative_change == len(self.change_masks))),
            'new_change_regions': [],
            'total_unique_changed_pixels': int(np.sum(cumulative_change > 0))
        }
        
        for i in range(1, len(self.change_masks)):
            new_changes = self.change_masks[i] & ~self.change_masks[i-1]
            stats['new_change_regions'].append(int(np.sum(new_changes)))
        
        return stats
    
    def export_temporal_geojson(self,
                                 output_dir: str,
                                 transform: Optional[Tuple] = None):
        results = []
        for i, (mask, ts) in enumerate(zip(self.change_masks, self.timestamps)):
            exporter = GeoJSONExporter()
            exporter.add_from_mask(mask, transform, f"change_{i}")
            
            filepath = f"{output_dir}/change_{ts}.geojson"
            geojson = exporter.export(filepath)
            results.append({'timestamp': ts, 'filepath': filepath, 'geojson': geojson})
        
        return results


def visualize_change_regions(image: np.ndarray,
                              mask: np.ndarray,
                              color: Tuple[int, int, int] = (0, 0, 255),
                              alpha: float = 0.5) -> np.ndarray:
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 1:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    if image.dtype != np.uint8:
        image = (image * 255).astype(np.uint8)
    
    overlay = image.copy()
    overlay[mask > 0] = color
    
    result = cv2.addWeighted(image, 1 - alpha, overlay, alpha, 0)
    
    contours, _ = cv2.findContours(
        (mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(result, contours, -1, color, 2)
    
    return result
