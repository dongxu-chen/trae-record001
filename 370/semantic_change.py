"""
语义变化检测模块
识别具体变化类型：新建、拆除、翻新
"""

import os
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from post_process import (
    compute_ndvi, compute_ndwi, morphological_refine,
    generate_binary_map, label, regionprops
)
from config import CLASS_COLORS


SEMANTIC_CHANGE_TYPES = [
    '未变化',
    '新建建筑物',
    '拆除建筑物',
    '建筑物翻新',
    '植被增加',
    '植被减少',
    '水体增加',
    '水体减少',
    '其他变化'
]

SEMANTIC_CHANGE_COLORS = [
    [0, 0, 0],
    [255, 100, 100],
    [100, 100, 255],
    [255, 200, 0],
    [0, 200, 100],
    [100, 255, 100],
    [0, 100, 255],
    [100, 200, 255],
    [150, 150, 150],
]


@dataclass
class SemanticChangeRegion:
    bbox: Tuple[int, int, int, int]
    semantic_type: str
    semantic_type_id: int
    area_pixels: int
    area_units: float
    centroid: Tuple[float, float]
    confidence: float
    ndvi_before: float
    ndvi_after: float
    ndwi_before: float
    ndwi_after: float
    brightness_before: float
    brightness_after: float


class SemanticChangeDetector:
    def __init__(self, ndvi_threshold: float = 0.2, ndwi_threshold: float = 0.1,
                 brightness_threshold: float = 0.15):
        self.ndvi_threshold = ndvi_threshold
        self.ndwi_threshold = ndwi_threshold
        self.brightness_threshold = brightness_threshold

    def classify_semantic_change(self, image1: np.ndarray, image2: np.ndarray,
                                  change_map: np.ndarray) -> np.ndarray:
        height, width = change_map.shape
        semantic_map = np.zeros((height, width), dtype=np.uint8)

        ndvi1 = compute_ndvi(image1)
        ndvi2 = compute_ndvi(image2)
        ndwi1 = compute_ndwi(image1)
        ndwi2 = compute_ndwi(image2)

        brightness1 = self._compute_brightness(image1)
        brightness2 = self._compute_brightness(image2)

        change_mask = change_map > 0

        ndvi_diff = ndvi2 - ndvi1 if ndvi1 is not None else None
        ndwi_diff = ndwi2 - ndwi1 if ndwi1 is not None else None
        brightness_diff = brightness2 - brightness1

        building_before = self._detect_building(image1, ndvi1, ndwi1, brightness1)
        building_after = self._detect_building(image2, ndvi2, ndwi2, brightness2)

        new_building = change_mask & ~building_before & building_after
        demolished_building = change_mask & building_before & ~building_after
        renovated_building = change_mask & building_before & building_after & (np.abs(brightness_diff) > self.brightness_threshold)

        if ndvi_diff is not None:
            vegetation_increase = change_mask & ~building_before & ~building_after & (ndvi_diff > self.ndvi_threshold)
            vegetation_decrease = change_mask & ~building_before & ~building_after & (ndvi_diff < -self.ndvi_threshold)
        else:
            vegetation_increase = np.zeros_like(change_mask, dtype=bool)
            vegetation_decrease = np.zeros_like(change_mask, dtype=bool)

        if ndwi_diff is not None:
            water_increase = change_mask & ~building_before & ~building_after & (ndwi_diff > self.ndwi_threshold)
            water_decrease = change_mask & ~building_before & ~building_after & (ndwi_diff < -self.ndwi_threshold)
        else:
            water_increase = np.zeros_like(change_mask, dtype=bool)
            water_decrease = np.zeros_like(change_mask, dtype=bool)

        semantic_map[new_building] = 1
        semantic_map[demolished_building] = 2
        semantic_map[renovated_building] = 3
        semantic_map[vegetation_increase] = 4
        semantic_map[vegetation_decrease] = 5
        semantic_map[water_increase] = 6
        semantic_map[water_decrease] = 7

        other_mask = change_mask & (semantic_map == 0)
        semantic_map[other_mask] = 8

        return semantic_map

    def _detect_building(self, image: np.ndarray, ndvi: Optional[np.ndarray],
                          ndwi: Optional[np.ndarray], brightness: np.ndarray) -> np.ndarray:
        height, width = image.shape[-2], image.shape[-1]
        building_mask = np.ones((height, width), dtype=bool)

        if ndvi is not None:
            building_mask &= (ndvi < self.ndvi_threshold)

        if ndwi is not None:
            building_mask &= (ndwi < self.ndwi_threshold)

        brightness_q75 = np.percentile(brightness, 75)
        building_mask &= (brightness > brightness_q75 * 0.6)

        return building_mask

    def _compute_brightness(self, image: np.ndarray) -> np.ndarray:
        if image.shape[0] >= 3:
            brightness = np.mean(image[:3], axis=0)
        else:
            brightness = np.mean(image, axis=0)

        min_val = np.min(brightness)
        max_val = np.max(brightness)
        if max_val > min_val:
            brightness = (brightness - min_val) / (max_val - min_val)
        return brightness

    def extract_change_regions(self, semantic_map: np.ndarray,
                                image1: np.ndarray, image2: np.ndarray,
                                pixel_area: float = 1.0,
                                min_region_size: int = 50) -> List[SemanticChangeRegion]:
        regions = []

        ndvi1 = compute_ndvi(image1)
        ndvi2 = compute_ndvi(image2)
        ndwi1 = compute_ndwi(image1)
        ndwi2 = compute_ndwi(image2)
        brightness1 = self._compute_brightness(image1)
        brightness2 = self._compute_brightness(image2)

        for type_id in range(1, len(SEMANTIC_CHANGE_TYPES)):
            mask = (semantic_map == type_id).astype(np.uint8)
            if np.sum(mask) == 0:
                continue

            mask = morphological_refine(mask, min_size=min_region_size, min_hole_size=min_region_size)
            labeled = label(mask)
            props = regionprops(labeled)

            for prop in props:
                min_row, min_col, max_row, max_col = prop.bbox

                region_mask = (labeled == prop.label)

                region_ndvi1 = np.mean(ndvi1[region_mask]) if ndvi1 is not None else 0
                region_ndvi2 = np.mean(ndvi2[region_mask]) if ndvi2 is not None else 0
                region_ndwi1 = np.mean(ndwi1[region_mask]) if ndwi1 is not None else 0
                region_ndwi2 = np.mean(ndwi2[region_mask]) if ndwi2 is not None else 0
                region_brightness1 = np.mean(brightness1[region_mask])
                region_brightness2 = np.mean(brightness2[region_mask])

                confidence = self._compute_confidence(
                    type_id, region_ndvi1, region_ndvi2,
                    region_ndwi1, region_ndwi2,
                    region_brightness1, region_brightness2
                )

                region = SemanticChangeRegion(
                    bbox=(min_row, min_col, max_row, max_col),
                    semantic_type=SEMANTIC_CHANGE_TYPES[type_id],
                    semantic_type_id=type_id,
                    area_pixels=prop.area,
                    area_units=prop.area * pixel_area,
                    centroid=prop.centroid,
                    confidence=confidence,
                    ndvi_before=region_ndvi1,
                    ndvi_after=region_ndvi2,
                    ndwi_before=region_ndwi1,
                    ndwi_after=region_ndwi2,
                    brightness_before=region_brightness1,
                    brightness_after=region_brightness2
                )
                regions.append(region)

        return regions

    def _compute_confidence(self, type_id: int, ndvi1: float, ndvi2: float,
                             ndwi1: float, ndwi2: float,
                             b1: float, b2: float) -> float:
        if type_id == 1:
            if ndvi1 < self.ndvi_threshold and ndvi2 < self.ndvi_threshold and b2 > b1 * 1.2:
                return min(abs(b2 - b1) / self.brightness_threshold, 1.0)
        elif type_id == 2:
            if ndvi1 < self.ndvi_threshold and ndvi2 > self.ndvi_threshold:
                return min(abs(ndvi2 - ndvi1) / self.ndvi_threshold, 1.0)
        elif type_id == 3:
            if ndvi1 < self.ndvi_threshold and ndvi2 < self.ndvi_threshold:
                return min(abs(b2 - b1) / self.brightness_threshold, 1.0)
        elif type_id == 4:
            if ndvi2 > ndvi1:
                return min((ndvi2 - ndvi1) / self.ndvi_threshold, 1.0)
        elif type_id == 5:
            if ndvi2 < ndvi1:
                return min((ndvi1 - ndvi2) / self.ndvi_threshold, 1.0)
        elif type_id == 6:
            if ndwi2 > ndwi1:
                return min((ndwi2 - ndwi1) / self.ndwi_threshold, 1.0)
        elif type_id == 7:
            if ndwi2 < ndwi1:
                return min((ndwi1 - ndwi2) / self.ndwi_threshold, 1.0)

        return 0.5

    def generate_semantic_color_map(self, semantic_map: np.ndarray) -> np.ndarray:
        height, width = semantic_map.shape
        color_map = np.zeros((height, width, 3), dtype=np.uint8)

        for type_id, color in enumerate(SEMANTIC_CHANGE_COLORS):
            mask = semantic_map == type_id
            color_map[mask] = color

        return color_map

    def summarize_semantic_changes(self, regions: List[SemanticChangeRegion]) -> Dict:
        summary = {}

        type_counts = {t: 0 for t in SEMANTIC_CHANGE_TYPES}
        type_areas = {t: 0.0 for t in SEMANTIC_CHANGE_TYPES}

        for region in regions:
            type_counts[region.semantic_type] += 1
            type_areas[region.semantic_type] += region.area_units

        summary['total_regions'] = len(regions)
        summary['by_type_count'] = type_counts
        summary['by_type_area'] = type_areas

        if regions:
            confidences = [r.confidence for r in regions]
            areas = [r.area_units for r in regions]
            summary['mean_confidence'] = np.mean(confidences)
            summary['mean_area'] = np.mean(areas)
            summary['min_area'] = np.min(areas)
            summary['max_area'] = np.max(areas)

        return summary


def detect_semantic_changes(image1_path: str, image2_path: str, binary_map: np.ndarray,
                            output_dir: str, pixel_area: float = 1.0,
                            min_region_size: int = 50) -> Dict:
    from data_loader import read_geotiff, write_geotiff

    img1, proj, gt, _, _, _ = read_geotiff(image1_path)
    img2, _, _, _, _, _ = read_geotiff(image2_path)

    detector = SemanticChangeDetector()
    semantic_map = detector.classify_semantic_change(img1, img2, binary_map)

    regions = detector.extract_change_regions(
        semantic_map, img1, img2, pixel_area,
        min_region_size=min_region_size
    )

    color_map = detector.generate_semantic_color_map(semantic_map)

    os.makedirs(output_dir, exist_ok=True)

    write_geotiff(
        os.path.join(output_dir, 'semantic_change_map.tif'),
        semantic_map.astype(np.float32),
        proj, gt
    )

    color_3ch = np.transpose(color_map, (2, 0, 1))
    write_geotiff(
        os.path.join(output_dir, 'semantic_change_color.tif'),
        color_3ch.astype(np.float32),
        proj, gt
    )

    summary = detector.summarize_semantic_changes(regions)

    print("\n" + "=" * 60)
    print("语义变化检测摘要")
    print("=" * 60)
    print(f"总变化区域数: {summary['total_regions']}")
    print("\n按类型统计:")
    for type_name in SEMANTIC_CHANGE_TYPES[1:]:
        count = summary['by_type_count'][type_name]
        area = summary['by_type_area'][type_name]
        if count > 0:
            print(f"  {type_name}: {count} 个区域, 总面积 {area:.2f}")

    if 'mean_confidence' in summary:
        print(f"\n平均置信度: {summary['mean_confidence']:.4f}")
        print(f"平均区域面积: {summary['mean_area']:.4f}")

    return {
        'semantic_map': semantic_map,
        'color_map': color_map,
        'regions': regions,
        'summary': summary
    }
