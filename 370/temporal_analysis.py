"""
多时相变化时序分析模块
连续监测多时相遥感影像的变化趋势
"""

import os
import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    try:
        import tifffile
        TIFFFILE_AVAILABLE = True
    except ImportError:
        TIFFFILE_AVAILABLE = False


@dataclass
class TimePoint:
    index: int
    date: Optional[str]
    image_path: str
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class ChangeEvent:
    start_index: int
    end_index: int
    pixel: Tuple[int, int]
    change_magnitude: float
    change_type: str
    confidence: float


class TemporalChangeAnalyzer:
    def __init__(self, image_paths: List[str], dates: Optional[List[str]] = None):
        self.image_paths = image_paths
        self.num_times = len(image_paths)

        if dates is None:
            self.dates = [f"T{i}" for i in range(self.num_times)]
        else:
            assert len(dates) == self.num_times, "dates长度必须与image_paths匹配"
            self.dates = dates

        self.time_points = [
            TimePoint(index=i, date=self.dates[i], image_path=path)
            for i, path in enumerate(image_paths)
        ]

        self.images = []
        self.pixel_area = 1.0
        self.geotransform = None
        self.projection = None
        self.width = 0
        self.height = 0
        self.bands = 0

        self._load_images()

    def _load_images(self):
        from data_loader import read_geotiff

        print(f"加载 {self.num_times} 个时相的影像...")
        for i, path in enumerate(self.image_paths):
            img, proj, gt, w, h, b = read_geotiff(path)
            self.images.append(img)

            if i == 0:
                self.geotransform = gt
                self.projection = proj
                self.width = w
                self.height = h
                self.bands = b

        self.images = np.array(self.images)
        print(f"  尺寸: {self.height}x{self.width}, 波段数: {self.bands}")

    def compute_temporal_metrics(self) -> Dict[str, np.ndarray]:
        print("计算时序指标...")

        metrics = {}

        ndvi_sequence = self._compute_ndvi_sequence()
        if ndvi_sequence is not None:
            metrics['ndvi'] = ndvi_sequence
            metrics['ndvi_mean'] = np.mean(ndvi_sequence, axis=0)
            metrics['ndvi_std'] = np.std(ndvi_sequence, axis=0)
            metrics['ndvi_trend'] = self._compute_trend(ndvi_sequence)
            metrics['ndvi_breakpoints'] = self._detect_breakpoints(ndvi_sequence)

        brightness_sequence = self._compute_brightness_sequence()
        metrics['brightness'] = brightness_sequence
        metrics['brightness_mean'] = np.mean(brightness_sequence, axis=0)
        metrics['brightness_std'] = np.std(brightness_sequence, axis=0)
        metrics['brightness_trend'] = self._compute_trend(brightness_sequence)

        change_intensity = self._compute_change_intensity()
        metrics['change_intensity'] = change_intensity

        change_frequency = self._compute_change_frequency()
        metrics['change_frequency'] = change_frequency

        metrics['change_magnitude'] = np.abs(np.diff(self.images, axis=0)).sum(axis=(1, 2, 3))

        return metrics

    def _compute_ndvi_sequence(self) -> Optional[np.ndarray]:
        if self.bands < 4:
            return None

        nir = self.images[:, 3, :, :]
        red = self.images[:, 2, :, :]
        ndvi = (nir - red) / (nir + red + 1e-10)
        return ndvi

    def _compute_brightness_sequence(self) -> np.ndarray:
        if self.bands >= 3:
            brightness = np.mean(self.images[:, :3, :, :], axis=1)
        else:
            brightness = np.mean(self.images, axis=1)
        return brightness

    def _compute_trend(self, sequence: np.ndarray) -> np.ndarray:
        T = sequence.shape[0]
        x = np.arange(T)
        x_mean = np.mean(x)

        numerator = np.sum((x - x_mean)[:, np.newaxis, np.newaxis] * sequence, axis=0)
        denominator = np.sum((x - x_mean) ** 2)

        trend = numerator / denominator if denominator != 0 else np.zeros_like(sequence[0])
        return trend

    def _detect_breakpoints(self, sequence: np.ndarray, threshold: float = 2.0) -> np.ndarray:
        T, H, W = sequence.shape
        breakpoints = np.zeros((H, W), dtype=np.int32)

        for t in range(1, T - 1):
            prev_std = np.std(sequence[:t], axis=0)
            curr_std = np.std(sequence[t:], axis=0)
            prev_mean = np.mean(sequence[:t], axis=0)
            curr_mean = np.mean(sequence[t:], axis=0)

            z_score = np.abs(curr_mean - prev_mean) / np.sqrt(prev_std ** 2 + curr_std ** 2 + 1e-10)

            mask = (z_score > threshold) & (breakpoints == 0)
            breakpoints[mask] = t

        return breakpoints

    def _compute_change_intensity(self) -> np.ndarray:
        diff = np.abs(np.diff(self.images, axis=0))
        intensity = np.max(diff, axis=1)
        return intensity

    def _compute_change_frequency(self, threshold: float = 0.15) -> np.ndarray:
        diff = np.abs(np.diff(self.images, axis=0))
        mean_diff = np.mean(diff, axis=1)
        change_mask = mean_diff > threshold
        frequency = np.sum(change_mask, axis=0)
        return frequency

    def detect_change_events(self, pixel_threshold: float = 0.2) -> List[ChangeEvent]:
        print("检测变化事件...")

        change_events = []
        brightness = self._compute_brightness_sequence()

        T, H, W = brightness.shape

        for t in range(T - 1):
            diff = np.abs(brightness[t + 1] - brightness[t])
            change_mask = diff > pixel_threshold

            for y, x in zip(*np.where(change_mask)):
                magnitude = diff[y, x]

                before = brightness[t, y, x]
                after = brightness[t + 1, y, x]

                if after > before * 1.3:
                    change_type = "brightening"
                elif after < before * 0.7:
                    change_type = "darkening"
                else:
                    change_type = "modified"

                event = ChangeEvent(
                    start_index=t,
                    end_index=t + 1,
                    pixel=(y, x),
                    change_magnitude=magnitude,
                    change_type=change_type,
                    confidence=min(magnitude / pixel_threshold, 1.0)
                )
                change_events.append(event)

        print(f"  检测到 {len(change_events)} 个变化事件")
        return change_events

    def generate_temporal_profile(self, y: int, x: int) -> Dict:
        profile = {
            'pixel': (y, x),
            'dates': self.dates,
            'ndvi_values': [],
            'brightness_values': [],
            'band_values': []
        }

        ndvi = self._compute_ndvi_sequence()
        brightness = self._compute_brightness_sequence()

        if ndvi is not None:
            profile['ndvi_values'] = ndvi[:, y, x].tolist()
        profile['brightness_values'] = brightness[:, y, x].tolist()

        for b in range(self.bands):
            profile['band_values'].append({
                'band': b,
                'values': self.images[:, b, y, x].tolist()
            })

        return profile

    def summarize_changes(self) -> Dict:
        metrics = self.compute_temporal_metrics()

        summary = {
            'num_time_points': self.num_times,
            'dates': self.dates,
            'image_size': (self.height, self.width),
            'num_bands': self.bands,
            'total_pixels': self.height * self.width,
            'change_magnitude_over_time': metrics.get('change_magnitude', []).tolist(),
            'mean_change_intensity': float(np.mean(metrics.get('change_intensity', 0))),
            'max_change_frequency': int(np.max(metrics.get('change_frequency', 0))),
            'pixels_with_changes': int(np.sum(metrics.get('change_frequency', 0) > 0)),
        }

        if 'ndvi_trend' in metrics:
            ndvi_trend = metrics['ndvi_trend']
            summary['ndvi_increasing_pixels'] = int(np.sum(ndvi_trend > 0.01))
            summary['ndvi_decreasing_pixels'] = int(np.sum(ndvi_trend < -0.01))
            summary['ndvi_stable_pixels'] = int(np.sum(np.abs(ndvi_trend) <= 0.01))

        if 'brightness_trend' in metrics:
            bt = metrics['brightness_trend']
            summary['brightness_increasing_pixels'] = int(np.sum(bt > 0.01))
            summary['brightness_decreasing_pixels'] = int(np.sum(bt < -0.01))
            summary['brightness_stable_pixels'] = int(np.sum(np.abs(bt) <= 0.01))

        return summary

    def save_temporal_metrics(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)

        from data_loader import write_geotiff

        metrics = self.compute_temporal_metrics()

        if 'ndvi_trend' in metrics:
            write_geotiff(
                os.path.join(output_dir, 'ndvi_trend.tif'),
                metrics['ndvi_trend'].astype(np.float32),
                self.projection, self.geotransform
            )

        if 'brightness_trend' in metrics:
            write_geotiff(
                os.path.join(output_dir, 'brightness_trend.tif'),
                metrics['brightness_trend'].astype(np.float32),
                self.projection, self.geotransform
            )

        if 'change_intensity' in metrics:
            for t in range(metrics['change_intensity'].shape[0]):
                write_geotiff(
                    os.path.join(output_dir, f'change_intensity_T{self.dates[t]}.tif'),
                    metrics['change_intensity'][t].astype(np.float32),
                    self.projection, self.geotransform
                )

        write_geotiff(
            os.path.join(output_dir, 'change_frequency.tif'),
            metrics.get('change_frequency', np.zeros((self.height, self.width))).astype(np.float32),
            self.projection, self.geotransform
        )

        if 'ndvi_breakpoints' in metrics:
            write_geotiff(
                os.path.join(output_dir, 'ndvi_breakpoints.tif'),
                metrics['ndvi_breakpoints'].astype(np.float32),
                self.projection, self.geotransform
            )

        print(f"时序指标已保存至: {output_dir}")


def run_temporal_analysis(image_paths: List[str], output_dir: str, dates: Optional[List[str]] = None):
    analyzer = TemporalChangeAnalyzer(image_paths, dates)

    print("\n" + "=" * 60)
    print("多时相变化时序分析")
    print("=" * 60)

    summary = analyzer.summarize_changes()

    print("\n分析摘要:")
    for key, value in summary.items():
        if isinstance(value, list):
            print(f"  {key}: {[f'{v:.4f}' for v in value]}")
        else:
            print(f"  {key}: {value}")

    analyzer.save_temporal_metrics(output_dir)

    return analyzer, summary
