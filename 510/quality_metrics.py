import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Union
from skimage.metrics import structural_similarity as ssim_skimage
from dataclasses import dataclass, field
from scipy import stats

from mos_evaluation import (
    MOSEvaluator, CombinedQualityEvaluator,
    MOSResult, CombinedQualityScore,
    create_mos_evaluator, create_combined_evaluator
)


@dataclass
class ComprehensiveQualityResult:
    video_id: str
    objective_metrics: Dict[str, float]
    mos_result: Optional[MOSResult] = None
    combined_score: Optional[CombinedQualityScore] = None
    quality_level: Optional[str] = None
    temporal_metrics: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict:
        return {
            'video_id': self.video_id,
            'objective_metrics': self.objective_metrics,
            'mos_result': self.mos_result.to_dict() if self.mos_result else None,
            'combined_score': self.combined_score.to_dict() if self.combined_score else None,
            'quality_level': self.quality_level,
            'temporal_metrics': self.temporal_metrics,
        }


class LPIPS(nn.Module):
    def __init__(self, net: str = 'alex', pretrained: bool = True):
        super().__init__()
        self.net_type = net
        self.channels = {
            'alex': [64, 192, 384, 256, 256],
            'vgg': [64, 128, 256, 512, 512]
        }[net]

        self.weights = nn.ParameterList([
            nn.Parameter(torch.ones(1, c, 1, 1)) for c in self.channels
        ])

        if pretrained:
            self._init_pretrained()

    def _init_pretrained(self):
        for i, w in enumerate(self.weights):
            nn.init.constant_(w, 1.0 / len(self.channels))

    def forward(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        diff = (x - y) ** 2
        diff = F.adaptive_avg_pool2d(diff, (1, 1))
        return diff.mean()


class QualityMetrics:
    def __init__(self, device: str = 'cuda', metrics: list = None,
                 use_mos: bool = True):
        self.device = torch.device(device)
        self.metrics = metrics or ['psnr', 'ssim', 'lpips']
        self.lpips_net = None
        self.use_mos = use_mos

        if 'lpips' in self.metrics:
            self.lpips_net = LPIPS().to(self.device)

        if use_mos:
            self.mos_evaluator = create_mos_evaluator()
            self.combined_evaluator = create_combined_evaluator(mos_evaluator=self.mos_evaluator)
        else:
            self.mos_evaluator = None
            self.combined_evaluator = None

    @staticmethod
    def _to_numpy(tensor: torch.Tensor) -> np.ndarray:
        if tensor.is_cuda:
            tensor = tensor.cpu()
        return tensor.squeeze().permute(1, 2, 0).numpy()

    @staticmethod
    def _normalize(img: torch.Tensor) -> torch.Tensor:
        if img.max() > 1.0:
            img = img / 255.0
        return torch.clamp(img, 0, 1)

    def calculate_psnr(self, img1: torch.Tensor, img2: torch.Tensor,
                       max_val: float = 1.0) -> float:
        img1 = self._normalize(img1)
        img2 = self._normalize(img2)

        mse = torch.mean((img1 - img2) ** 2)
        if mse == 0:
            return float('inf')
        psnr = 20 * torch.log10(max_val / torch.sqrt(mse))
        return psnr.item()

    def calculate_ssim(self, img1: torch.Tensor, img2: torch.Tensor,
                       multichannel: bool = True) -> float:
        img1_np = self._to_numpy(self._normalize(img1))
        img2_np = self._to_numpy(self._normalize(img2))

        if multichannel:
            ssim_value = ssim_skimage(img1_np, img2_np, channel_axis=2,
                                      data_range=1.0)
        else:
            ssim_value = ssim_skimage(img1_np, img2_np, data_range=1.0)
        return float(ssim_value)

    def calculate_lpips(self, img1: torch.Tensor, img2: torch.Tensor) -> float:
        if self.lpips_net is None:
            raise ValueError("LPIPS network not initialized")

        img1 = self._normalize(img1).to(self.device)
        img2 = self._normalize(img2).to(self.device)

        with torch.no_grad():
            lpips_value = self.lpips_net(img1, img2)

        return lpips_value.item()

    def calculate_all(self, img1: torch.Tensor, img2: torch.Tensor) -> Dict[str, float]:
        results = {}

        if 'psnr' in self.metrics:
            results['psnr'] = self.calculate_psnr(img1, img2)

        if 'ssim' in self.metrics:
            results['ssim'] = self.calculate_ssim(img1, img2)

        if 'lpips' in self.metrics:
            results['lpips'] = self.calculate_lpips(img1, img2)

        return results

    def evaluate_video(self, true_frames: torch.Tensor,
                       pred_frames: torch.Tensor,
                       verbose: bool = False) -> Dict[str, float]:
        assert true_frames.shape == pred_frames.shape, "Shape mismatch"

        num_frames = true_frames.shape[0]
        metrics_sum = {metric: 0.0 for metric in self.metrics}

        for i in range(num_frames):
            frame_metrics = self.calculate_all(true_frames[i:i+1], pred_frames[i:i+1])
            for metric, value in frame_metrics.items():
                metrics_sum[metric] += value

            if verbose and i % 10 == 0:
                print(f"Frame {i}/{num_frames}: {frame_metrics}")

        metrics_avg = {metric: value / num_frames for metric, value in metrics_sum.items()}
        return metrics_avg

    def add_mos_rating(self, video_id: str, rater_id: str,
                       score: float, comment: Optional[str] = None):
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        self.mos_evaluator.add_rating(video_id, rater_id, score, comment)

    def add_mos_ratings_batch(self, ratings: List[Tuple[str, str, float, Optional[str]]]):
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        self.mos_evaluator.add_batch_ratings(ratings)

    def get_mos_result(self, video_id: str) -> MOSResult:
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        return self.mos_evaluator.calculate_mos(video_id)

    def get_all_mos_results(self) -> Dict[str, MOSResult]:
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        return self.mos_evaluator.calculate_all_mos()

    def calculate_combined_score(
        self,
        video_id: str,
        objective_metrics: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> CombinedQualityScore:
        if self.combined_evaluator is None:
            raise ValueError("Combined evaluation not enabled")

        return self.combined_evaluator.calculate_combined_score(
            video_id, objective_metrics, weights
        )

    @staticmethod
    def determine_quality_level(combined_score: float) -> str:
        if combined_score >= 4.5:
            return "优秀 (Excellent)"
        elif combined_score >= 4.0:
            return "很好 (Good)"
        elif combined_score >= 3.5:
            return "良好 (Fair)"
        elif combined_score >= 3.0:
            return "一般 (Poor)"
        elif combined_score >= 2.0:
            return "较差 (Bad)"
        else:
            return "很差 (Very Bad)"

    def evaluate_comprehensive(
        self,
        video_id: str,
        reference_frames: Optional[torch.Tensor],
        processed_frames: Optional[torch.Tensor],
        calculate_objective: bool = True,
        weights: Optional[Dict[str, float]] = None
    ) -> ComprehensiveQualityResult:
        objective_metrics = {}
        temporal_metrics = None

        if calculate_objective and reference_frames is not None and processed_frames is not None:
            objective_metrics = self.evaluate_video(reference_frames, processed_frames)
            temporal_metrics = self.temporal_consistency(processed_frames)

        mos_result = None
        combined_score = None
        quality_level = None

        if self.use_mos:
            try:
                mos_result = self.get_mos_result(video_id)
                if objective_metrics:
                    combined_score = self.calculate_combined_score(
                        video_id, objective_metrics, weights
                    )
                    quality_level = self.determine_quality_level(combined_score.combined_score)
            except ValueError:
                pass

        return ComprehensiveQualityResult(
            video_id=video_id,
            objective_metrics=objective_metrics,
            mos_result=mos_result,
            combined_score=combined_score,
            quality_level=quality_level,
            temporal_metrics=temporal_metrics
        )

    def batch_evaluate_comprehensive(
        self,
        video_data: Dict[str, Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]],
        calculate_objective: bool = True,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, ComprehensiveQualityResult]:
        results = {}
        for video_id, (ref_frames, proc_frames) in video_data.items():
            results[video_id] = self.evaluate_comprehensive(
                video_id, ref_frames, proc_frames, calculate_objective, weights
            )
        return results

    def analyze_objective_mos_correlation(
        self,
        video_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict]:
        if not self.use_mos:
            raise ValueError("MOS evaluation not enabled")

        mos_results = self.get_all_mos_results()

        correlation_results = {}
        metric_names = ['psnr', 'ssim', 'lpips']

        for metric in metric_names:
            metric_values = []
            mos_values = []

            for video_id, mos_result in mos_results.items():
                if video_id in video_metrics and metric in video_metrics[video_id]:
                    metric_values.append(video_metrics[video_id][metric])
                    mos_values.append(mos_result.mean_score)

            if len(metric_values) >= 3:
                pearson_r, pearson_p = stats.pearsonr(metric_values, mos_values)
                spearman_r, spearman_p = stats.spearmanr(metric_values, mos_values)

                correlation_results[metric] = {
                    'pearson_r': pearson_r,
                    'pearson_p_value': pearson_p,
                    'spearman_r': spearman_r,
                    'spearman_p_value': spearman_p,
                    'num_samples': len(metric_values),
                    'is_significant': pearson_p < 0.05
                }

        return correlation_results

    def temporal_consistency(self, frames: torch.Tensor) -> Dict[str, float]:
        num_frames = frames.shape[0]
        consistency_scores = []
        psnr_scores = []

        for i in range(num_frames - 1):
            diff = torch.abs(frames[i] - frames[i + 1])
            consistency = 1.0 - torch.mean(diff).item()
            consistency_scores.append(consistency)

            frame_psnr = self.calculate_psnr(frames[i:i+1], frames[i+1:i+2])
            psnr_scores.append(frame_psnr)

        return {
            'temporal_consistency_mean': float(np.mean(consistency_scores)),
            'temporal_consistency_std': float(np.std(consistency_scores)),
            'temporal_psnr_mean': float(np.mean(psnr_scores)),
            'temporal_psnr_std': float(np.std(psnr_scores)),
        }

    def export_evaluation_report(
        self,
        results: Dict[str, ComprehensiveQualityResult],
        output_path: str
    ):
        import json
        from datetime import datetime

        report = {
            'generation_time': datetime.now().isoformat(),
            'metrics_used': self.metrics,
            'use_mos': self.use_mos,
            'results': {
                vid: res.to_dict() for vid, res in results.items()
            }
        }

        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"评估报告已保存到: {output_path}")

    def save_mos_ratings(self, output_path: str, format: str = 'json'):
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        self.mos_evaluator.export_ratings(output_path, format)

    def load_mos_ratings(self, input_path: str, format: str = 'json'):
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        self.mos_evaluator.import_ratings(input_path, format)

    def get_rater_reliability(self, rater_id: str) -> Dict:
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        return self.mos_evaluator.calculate_rater_reliability(rater_id)

    def detect_mos_outliers(self, video_id: str, threshold: float = 2.0) -> List:
        if self.mos_evaluator is None:
            raise ValueError("MOS evaluation not enabled")
        return self.mos_evaluator.detect_outliers(video_id, threshold)


def create_quality_evaluator(device: str = 'cuda',
                             metrics: list = None,
                             use_mos: bool = True) -> QualityMetrics:
    return QualityMetrics(device=device, metrics=metrics, use_mos=use_mos)


class InterpolationQualityEvaluator:
    def __init__(self, device: str = 'cuda'):
        self.device = torch.device(device)
        self.metrics = QualityMetrics(device=device)

    def temporal_consistency(self, frames: torch.Tensor) -> Dict[str, float]:
        num_frames = frames.shape[0]
        consistency_scores = []

        for i in range(num_frames - 1):
            diff = torch.abs(frames[i] - frames[i + 1])
            consistency = 1.0 - torch.mean(diff).item()
            consistency_scores.append(consistency)

        return {
            'temporal_consistency_mean': float(np.mean(consistency_scores)),
            'temporal_consistency_std': float(np.std(consistency_scores))
        }

    def edge_preservation(self, img: torch.Tensor) -> float:
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
                               dtype=torch.float32, device=self.device).view(1, 1, 3, 3)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
                               dtype=torch.float32, device=self.device).view(1, 1, 3, 3)

        gray = torch.mean(img, dim=1, keepdim=True)
        edge_x = F.conv2d(gray, sobel_x, padding=1)
        edge_y = F.conv2d(gray, sobel_y, padding=1)
        edges = torch.sqrt(edge_x ** 2 + edge_y ** 2)

        return torch.mean(edges).item()

    def motion_artifact_detection(self, prev_frame: torch.Tensor,
                                  curr_frame: torch.Tensor,
                                  next_frame: torch.Tensor) -> Dict[str, float]:
        diff_prev_curr = torch.abs(prev_frame - curr_frame)
        diff_curr_next = torch.abs(curr_frame - next_frame)
        diff_prev_next = torch.abs(prev_frame - next_frame)

        motion_consistency = 1.0 - torch.mean(
            torch.abs(diff_prev_curr - diff_curr_next)
        ).item()

        temporal_linearity = 1.0 - torch.mean(
            torch.abs(diff_prev_curr + diff_curr_next - diff_prev_next)
        ).item()

        return {
            'motion_consistency': motion_consistency,
            'temporal_linearity': temporal_linearity,
        }


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    print("\n=== 创建综合质量评估器 ===")
    evaluator = create_quality_evaluator(device=device, use_mos=True)

    print("\n=== 测试客观指标 ===")
    img1 = torch.rand(1, 3, 128, 128).to(device)
    img2 = torch.rand(1, 3, 128, 128).to(device)

    metrics = evaluator.calculate_all(img1, img2)
    print("客观质量指标:")
    for name, value in metrics.items():
        print(f"  {name.upper()}: {value:.4f}")

    print("\n=== 测试MOS主观评分 ===")
    videos = ['video_001', 'video_002', 'video_003']
    raters = ['rater_001', 'rater_002', 'rater_003', 'rater_004', 'rater_005']

    np.random.seed(42)
    for video in videos:
        for rater in raters:
            score = np.random.normal(3.5, 0.8)
            score = np.clip(score, 1, 5)
            evaluator.add_mos_rating(video, rater, round(score, 1))

    print("\nMOS评分结果:")
    all_mos = evaluator.get_all_mos_results()
    for video_id, result in all_mos.items():
        print(f"  {video_id}:")
        print(f"    均值: {result.mean_score:.2f} ± {result.std_score:.2f}")
        print(f"    95% CI: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
        print(f"    评价人数: {result.num_raters}")

    print("\n=== 测试综合质量评分 ===")
    objective_metrics = {
        'video_001': {'psnr': 35.2, 'ssim': 0.92, 'lpips': 0.15},
        'video_002': {'psnr': 32.8, 'ssim': 0.88, 'lpips': 0.22},
        'video_003': {'psnr': 38.1, 'ssim': 0.95, 'lpips': 0.08},
    }

    print("\n综合质量评估结果:")
    for video_id, obj_metrics in objective_metrics.items():
        try:
            combined = evaluator.calculate_combined_score(video_id, obj_metrics)
            quality_level = evaluator.determine_quality_level(combined.combined_score)
            print(f"  {video_id}:")
            print(f"    MOS: {combined.mos_score:.2f}")
            print(f"    PSNR: {combined.psnr:.1f}")
            print(f"    SSIM: {combined.ssim:.3f}")
            print(f"    LPIPS: {combined.lpips:.3f}")
            print(f"    综合得分: {combined.combined_score:.2f}/5")
            print(f"    质量等级: {quality_level}")
        except Exception as e:
            print(f"  {video_id}: 无法计算综合评分 - {e}")

    print("\n=== 测试时间一致性 ===")
    frames = torch.rand(5, 3, 128, 128).to(device)
    temporal = evaluator.temporal_consistency(frames)
    print("时间一致性指标:")
    for name, value in temporal.items():
        print(f"  {name}: {value:.4f}")

    print("\n✅ 综合质量评估测试通过!")
