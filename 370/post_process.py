"""
后处理模块
二值化、变化类型分类、面积统计
支持地理变换参数计算实际面积
"""

import numpy as np
from skimage.morphology import opening, closing, disk, remove_small_objects, remove_small_holes
from skimage.measure import label, regionprops
from scipy import ndimage
from config import CLASS_NAMES, CLASS_COLORS, PIXEL_SIZE


def compute_pixel_area_from_geotransform(geotransform):
    if geotransform is None:
        return PIXEL_SIZE, PIXEL_SIZE

    try:
        origin_x = geotransform[0]
        pixel_width = abs(geotransform[1])
        rotation_x = geotransform[2]
        origin_y = geotransform[3]
        rotation_y = geotransform[4]
        pixel_height = abs(geotransform[5])

        if rotation_x != 0 or rotation_y != 0:
            pixel_area = pixel_width * pixel_height * np.cos(np.radians(abs(rotation_x)))
        else:
            pixel_area = pixel_width * pixel_height

        return pixel_width, pixel_height

    except (IndexError, TypeError, ValueError):
        return PIXEL_SIZE, PIXEL_SIZE


def compute_geographic_area(pixel_count, geotransform=None, pixel_size=None):
    if pixel_size is None:
        _, pixel_size = compute_pixel_area_from_geotransform(geotransform)
    return pixel_count * pixel_size * pixel_size


def generate_binary_map(change_map, change_prob=None, prob_threshold=0.5):
    binary_map = (change_map > 0).astype(np.uint8)

    if change_prob is not None:
        low_conf_mask = change_prob < prob_threshold
        binary_map[low_conf_mask] = 0

    return binary_map


def morphological_refine(binary_map, min_size=64, min_hole_size=256,
                         open_radius=2, close_radius=3):
    refined = binary_map.copy()

    refined = opening(refined, disk(open_radius))
    refined = closing(refined, disk(close_radius))

    refined = remove_small_objects(refined.astype(bool), min_size=min_size).astype(np.uint8)
    refined = remove_small_holes(refined.astype(bool), area_threshold=min_hole_size).astype(np.uint8)

    return refined


def classify_change_types(change_map, image1, image2, ndvi_threshold=0.2, ndwi_threshold=0.1):
    height, width = change_map.shape
    type_map = np.zeros((height, width), dtype=np.uint8)

    if image1.shape[0] >= 4 and image2.shape[0] >= 4:
        ndvi1 = compute_ndvi(image1)
        ndvi2 = compute_ndvi(image2)
        ndwi1 = compute_ndwi(image1)
        ndwi2 = compute_ndwi(image2)

        change_mask = change_map > 0

        ndvi_diff = ndvi2 - ndvi1
        ndwi_diff = ndwi2 - ndwi1

        building_mask = (change_mask &
                         (ndvi1 < ndvi_threshold) &
                         (ndvi2 < ndvi_threshold) &
                         (ndwi1 < ndwi_threshold) &
                         (ndwi2 < ndwi_threshold))

        vegetation_mask = (change_mask &
                           ((ndvi_diff > ndvi_threshold) | (ndvi_diff < -ndvi_threshold)))

        water_mask = (change_mask &
                      ((ndwi_diff > ndwi_threshold) | (ndwi_diff < -ndwi_threshold)))

        other_mask = change_mask & ~building_mask & ~vegetation_mask & ~water_mask

        type_map[building_mask] = 1
        type_map[vegetation_mask] = 2
        type_map[water_mask] = 3
        type_map[other_mask] = 4
    else:
        type_map = change_map.copy()

    return type_map


def compute_ndvi(image):
    if image.shape[0] >= 4:
        nir = image[3, :, :]
        red = image[2, :, :]
        ndvi = (nir - red) / (nir + red + 1e-10)
        return ndvi
    return None


def compute_ndwi(image):
    if image.shape[0] >= 4:
        nir = image[3, :, :]
        green = image[1, :, :]
        ndwi = (green - nir) / (green + nir + 1e-10)
        return ndwi
    return None


def compute_area_statistics(binary_map, pixel_size=None, geotransform=None):
    stats = {}

    total_pixels = binary_map.size
    changed_pixels = np.sum(binary_map > 0)
    unchanged_pixels = total_pixels - changed_pixels

    if pixel_size is None:
        pixel_width, pixel_height = compute_pixel_area_from_geotransform(geotransform)
        pixel_area = pixel_width * pixel_height
    else:
        pixel_width = pixel_size
        pixel_height = pixel_size
        pixel_area = pixel_size * pixel_size

    stats['total_pixels'] = total_pixels
    stats['changed_pixels'] = changed_pixels
    stats['unchanged_pixels'] = unchanged_pixels
    stats['change_ratio'] = changed_pixels / total_pixels if total_pixels > 0 else 0

    stats['pixel_width'] = pixel_width
    stats['pixel_height'] = pixel_height
    stats['pixel_area'] = pixel_area

    stats['changed_area'] = changed_pixels * pixel_area
    stats['unchanged_area'] = unchanged_pixels * pixel_area
    stats['total_area'] = total_pixels * pixel_area

    if changed_pixels > 0:
        labeled = label(binary_map)
        regions = regionprops(labeled)

        areas = [r.area * pixel_area for r in regions]
        stats['num_regions'] = len(regions)
        stats['min_region_area'] = min(areas)
        stats['max_region_area'] = max(areas)
        stats['mean_region_area'] = np.mean(areas)
        stats['std_region_area'] = np.std(areas)

        bboxes = []
        for r in regions:
            min_row, min_col, max_row, max_col = r.bbox
            bboxes.append({
                'min_row': min_row,
                'min_col': min_col,
                'max_row': max_row,
                'max_col': max_col,
                'width_pixels': max_col - min_col,
                'height_pixels': max_row - min_row,
                'area': r.area * pixel_area,
            })
        stats['region_bboxes'] = bboxes
    else:
        stats['num_regions'] = 0

    return stats


def compute_class_area_statistics(type_map, pixel_size=None, geotransform=None):
    class_stats = {}

    if pixel_size is None:
        pixel_width, pixel_height = compute_pixel_area_from_geotransform(geotransform)
        pixel_area = pixel_width * pixel_height
    else:
        pixel_area = pixel_size * pixel_size

    for class_id, class_name in enumerate(CLASS_NAMES):
        mask = (type_map == class_id)
        pixel_count = np.sum(mask)
        area = pixel_count * pixel_area

        if pixel_count > 0:
            labeled = label(mask.astype(int))
            regions = regionprops(labeled)
            num_regions = len(regions)
            areas = [r.area * pixel_area for r in regions]
            min_area = min(areas)
            max_area = max(areas)
            mean_area = np.mean(areas)
        else:
            num_regions = 0
            min_area = 0
            max_area = 0
            mean_area = 0

        class_stats[class_name] = {
            'pixel_count': pixel_count,
            'area': area,
            'pixel_area_per_pixel': pixel_area,
            'num_regions': num_regions,
            'min_region_area': min_area,
            'max_region_area': max_area,
            'mean_region_area': mean_area,
            'ratio': pixel_count / type_map.size if type_map.size > 0 else 0
        }

    return class_stats


def generate_color_map(type_map):
    height, width = type_map.shape
    color_map = np.zeros((height, width, 3), dtype=np.uint8)

    for class_id, color in enumerate(CLASS_COLORS):
        mask = type_map == class_id
        color_map[mask] = color

    return color_map
