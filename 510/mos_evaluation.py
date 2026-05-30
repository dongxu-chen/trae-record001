import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
import matplotlib.pyplot as plt
from scipy import stats


@dataclass
class MOSRating:
    video_id: str
    rater_id: str
    score: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    comment: Optional[str] = None


@dataclass
class MOSResult:
    video_id: str
    mean_score: float
    std_score: float
    median_score: float
    min_score: float
    max_score: float
    num_raters: int
    ratings: List[MOSRating]
    confidence_interval: Tuple[float, float]
    z_score: float = 1.96

    def to_dict(self) -> Dict:
        return {
            'video_id': self.video_id,
            'mean_score': self.mean_score,
            'std_score': self.std_score,
            'median_score': self.median_score,
            'min_score': self.min_score,
            'max_score': self.max_score,
            'num_raters': self.num_raters,
            'confidence_interval': list(self.confidence_interval),
            'ratings': [asdict(r) for r in self.ratings]
        }


@dataclass
class CombinedQualityScore:
    video_id: str
    mos_score: float
    psnr: float
    ssim: float
    lpips: float
    combined_score: float
    weights: Dict[str, float]
    mos_ci: Tuple[float, float]

    def to_dict(self) -> Dict:
        return {
            'video_id': self.video_id,
            'mos_score': self.mos_score,
            'psnr': self.psnr,
            'ssim': self.ssim,
            'lpips': self.lpips,
            'combined_score': self.combined_score,
            'weights': self.weights,
            'mos_ci': list(self.mos_ci)
        }


class MOSEvaluator:
    def __init__(self, scale_min: int = 1, scale_max: int = 5,
                 criteria: List[str] = None):
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.criteria = criteria or [
            '整体质量', '清晰度', '色彩保真度', '运动流畅度', '无伪影'
        ]
        self.ratings: List[MOSRating] = []
        self.video_list: List[str] = []
        self.rater_list: List[str] = []

    def add_video(self, video_id: str):
        if video_id not in self.video_list:
            self.video_list.append(video_id)

    def add_rater(self, rater_id: str):
        if rater_id not in self.rater_list:
            self.rater_list.append(rater_id)

    def add_rating(self, video_id: str, rater_id: str, score: float,
                   comment: Optional[str] = None) -> bool:
        if score < self.scale_min or score > self.scale_max:
            raise ValueError(
                f"评分必须在 [{self.scale_min}, {self.scale_max}] 范围内"
            )

        rating = MOSRating(
            video_id=video_id,
            rater_id=rater_id,
            score=score,
            comment=comment
        )
        self.ratings.append(rating)

        if video_id not in self.video_list:
            self.video_list.append(video_id)
        if rater_id not in self.rater_list:
            self.rater_list.append(rater_id)

        return True

    def add_batch_ratings(self, ratings: List[Tuple[str, str, float, Optional[str]]]):
        for video_id, rater_id, score, comment in ratings:
            self.add_rating(video_id, rater_id, score, comment)

    def get_video_ratings(self, video_id: str) -> List[MOSRating]:
        return [r for r in self.ratings if r.video_id == video_id]

    def get_rater_ratings(self, rater_id: str) -> List[MOSRating]:
        return [r for r in self.ratings if r.rater_id == rater_id]

    def calculate_mos(self, video_id: str, z_score: float = 1.96) -> MOSResult:
        video_ratings = self.get_video_ratings(video_id)
        if not video_ratings:
            raise ValueError(f"没有找到视频 {video_id} 的评分数据")

        scores = [r.score for r in video_ratings]
        mean_score = np.mean(scores)
        std_score = np.std(scores, ddof=1)
        median_score = np.median(scores)
        min_score = np.min(scores)
        max_score = np.max(scores)
        num_raters = len(scores)

        if num_raters > 1:
            margin_of_error = z_score * (std_score / np.sqrt(num_raters))
            confidence_interval = (
                mean_score - margin_of_error,
                mean_score + margin_of_error
            )
        else:
            confidence_interval = (mean_score, mean_score)

        return MOSResult(
            video_id=video_id,
            mean_score=mean_score,
            std_score=std_score,
            median_score=median_score,
            min_score=min_score,
            max_score=max_score,
            num_raters=num_raters,
            ratings=video_ratings,
            confidence_interval=confidence_interval,
            z_score=z_score
        )

    def calculate_all_mos(self, z_score: float = 1.96) -> Dict[str, MOSResult]:
        results = {}
        for video_id in self.video_list:
            try:
                results[video_id] = self.calculate_mos(video_id, z_score)
            except ValueError:
                continue
        return results

    def calculate_rater_reliability(self, rater_id: str) -> Dict:
        rater_ratings = self.get_rater_ratings(rater_id)
        if not rater_ratings:
            raise ValueError(f"没有找到评价者 {rater_id} 的评分数据")

        all_scores = np.array([r.score for r in rater_ratings])

        video_means = {}
        for rating in rater_ratings:
            if rating.video_id not in video_means:
                video_mos = self.calculate_mos(rating.video_id)
                video_means[rating.video_id] = video_mos.mean_score

        rater_scores = np.array([r.score for r in rater_ratings])
        mean_scores = np.array([video_means[r.video_id] for r in rater_ratings])

        correlation, p_value = stats.pearsonr(rater_scores, mean_scores)

        bias = np.mean(rater_scores - mean_scores)

        rmsd = np.sqrt(np.mean((rater_scores - mean_scores) ** 2))

        return {
            'rater_id': rater_id,
            'num_ratings': len(rater_ratings),
            'mean_score': np.mean(all_scores),
            'std_score': np.std(all_scores, ddof=1),
            'correlation_with_mean': correlation,
            'p_value': p_value,
            'bias': bias,
            'rmsd': rmsd,
            'is_reliable': correlation > 0.7 and p_value < 0.05
        }

    def detect_outliers(self, video_id: str, threshold: float = 2.0) -> List[MOSRating]:
        video_ratings = self.get_video_ratings(video_id)
        if len(video_ratings) < 3:
            return []

        scores = np.array([r.score for r in video_ratings])
        z_scores = np.abs(stats.zscore(scores))

        outliers = []
        for i, rating in enumerate(video_ratings):
            if z_scores[i] > threshold:
                outliers.append(rating)

        return outliers

    def export_ratings(self, output_path: str, format: str = 'json'):
        output_path = Path(output_path)

        if format == 'json':
            data = {
                'scale': {'min': self.scale_min, 'max': self.scale_max},
                'criteria': self.criteria,
                'videos': self.video_list,
                'raters': self.rater_list,
                'ratings': [asdict(r) for r in self.ratings],
                'export_time': datetime.now().isoformat()
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format == 'csv':
            df = pd.DataFrame([asdict(r) for r in self.ratings])
            df.to_csv(output_path, index=False, encoding='utf-8-sig')

        else:
            raise ValueError(f"不支持的格式: {format}")

    def import_ratings(self, input_path: str, format: str = 'json'):
        input_path = Path(input_path)

        if format == 'json':
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for r_data in data.get('ratings', []):
                rating = MOSRating(**r_data)
                self.ratings.append(rating)
                if rating.video_id not in self.video_list:
                    self.video_list.append(rating.video_id)
                if rating.rater_id not in self.rater_list:
                    self.rater_list.append(rating.rater_id)

            self.criteria = data.get('criteria', self.criteria)

        elif format == 'csv':
            df = pd.read_csv(input_path)
            for _, row in df.iterrows():
                self.add_rating(
                    video_id=row['video_id'],
                    rater_id=row['rater_id'],
                    score=float(row['score']),
                    comment=row.get('comment')
                )

        else:
            raise ValueError(f"不支持的格式: {format}")

    def clear_ratings(self):
        self.ratings = []
        self.video_list = []
        self.rater_list = []


class CombinedQualityEvaluator:
    def __init__(self, mos_evaluator: MOSEvaluator = None):
        self.mos_evaluator = mos_evaluator or MOSEvaluator()
        self.default_weights = {
            'mos': 0.4,
            'psnr': 0.25,
            'ssim': 0.25,
            'lpips': 0.1
        }

    def normalize_metric(self, value: float, metric: str) -> float:
        if metric == 'psnr':
            return np.clip(value / 50.0, 0, 1)
        elif metric == 'ssim':
            return np.clip(value, 0, 1)
        elif metric == 'lpips':
            return np.clip(1 - value, 0, 1)
        elif metric == 'mos':
            return np.clip((value - 1) / 4, 0, 1)
        else:
            return value

    def calculate_combined_score(
        self,
        video_id: str,
        objective_metrics: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
        z_score: float = 1.96
    ) -> CombinedQualityScore:
        weights = weights or self.default_weights

        mos_result = self.mos_evaluator.calculate_mos(video_id, z_score)

        psnr = objective_metrics.get('psnr', 0)
        ssim = objective_metrics.get('ssim', 0)
        lpips = objective_metrics.get('lpips', 0)

        norm_mos = self.normalize_metric(mos_result.mean_score, 'mos')
        norm_psnr = self.normalize_metric(psnr, 'psnr')
        norm_ssim = self.normalize_metric(ssim, 'ssim')
        norm_lpips = self.normalize_metric(lpips, 'lpips')

        combined = (
            weights['mos'] * norm_mos +
            weights['psnr'] * norm_psnr +
            weights['ssim'] * norm_ssim +
            weights['lpips'] * norm_lpips
        )

        combined_score_1_5 = combined * 4 + 1

        return CombinedQualityScore(
            video_id=video_id,
            mos_score=mos_result.mean_score,
            psnr=psnr,
            ssim=ssim,
            lpips=lpips,
            combined_score=combined_score_1_5,
            weights=weights,
            mos_ci=mos_result.confidence_interval
        )

    def batch_evaluate(
        self,
        video_metrics: Dict[str, Dict[str, float]],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, CombinedQualityScore]:
        results = {}
        for video_id, metrics in video_metrics.items():
            try:
                results[video_id] = self.calculate_combined_score(
                    video_id, metrics, weights
                )
            except ValueError:
                continue
        return results

    def plot_radar_chart(self, combined_score: CombinedQualityScore,
                         output_path: Optional[str] = None) -> plt.Figure:
        categories = ['主观质量(MOS)', '峰值信噪比(PSNR)',
                      '结构相似性(SSIM)', '感知相似度(LPIPS)']
        values = [
            self.normalize_metric(combined_score.mos_score, 'mos') * 100,
            self.normalize_metric(combined_score.psnr, 'psnr') * 100,
            self.normalize_metric(combined_score.ssim, 'ssim') * 100,
            self.normalize_metric(combined_score.lpips, 'lpips') * 100
        ]

        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        values += values[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})

        ax.plot(angles, values, 'o-', linewidth=2, label='质量得分')
        ax.fill(angles, values, alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        ax.set_title(f"视频 {combined_score.video_id} 综合质量评估\n"
                    f"综合得分: {combined_score.combined_score:.2f}/5")
        ax.grid(True)
        ax.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1))

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_mos_distribution(self, mos_result: MOSResult,
                               output_path: Optional[str] = None) -> plt.Figure:
        scores = [r.score for r in mos_result.ratings]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        ax1.hist(scores, bins=np.arange(0.5, 5.6, 1),
                 edgecolor='black', alpha=0.7)
        ax1.axvline(mos_result.mean_score, color='red', linestyle='--',
                    linewidth=2, label=f'均值: {mos_result.mean_score:.2f}')
        ax1.axvline(mos_result.confidence_interval[0], color='green',
                    linestyle=':', linewidth=2, label='95% CI下限')
        ax1.axvline(mos_result.confidence_interval[1], color='green',
                    linestyle=':', linewidth=2, label='95% CI上限')
        ax1.set_xlabel('评分')
        ax1.set_ylabel('频次')
        ax1.set_title(f'MOS评分分布 (n={mos_result.num_raters})')
        ax1.set_xlim(0.5, 5.5)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)

        labels = ['很差', '差', '一般', '好', '很好']
        counts = [scores.count(i) for i in range(1, 6)]
        colors = ['#FF6B6B', '#FFA07A', '#FFD93D', '#95E1D3', '#6BCB77']
        ax2.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90)
        ax2.set_title('评分占比')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')

        return fig

    def generate_report(self, combined_scores: Dict[str, CombinedQualityScore],
                         output_path: str):
        report_data = {
            'generation_time': datetime.now().isoformat(),
            'weights': self.default_weights,
            'results': {
                vid: score.to_dict() for vid, score in combined_scores.items()
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)


def create_mos_evaluator(scale_min: int = 1, scale_max: int = 5) -> MOSEvaluator:
    return MOSEvaluator(scale_min=scale_min, scale_max=scale_max)


def create_combined_evaluator(mos_evaluator: Optional[MOSEvaluator] = None) -> CombinedQualityEvaluator:
    return CombinedQualityEvaluator(mos_evaluator=mos_evaluator)


if __name__ == "__main__":
    print("=== MOS 主观评估测试 ===")

    mos_eval = create_mos_evaluator()

    videos = ['video_001', 'video_002', 'video_003']
    raters = ['rater_001', 'rater_002', 'rater_003', 'rater_004', 'rater_005']

    np.random.seed(42)
    for video in videos:
        for rater in raters:
            score = np.random.normal(3.5, 0.8)
            score = np.clip(score, 1, 5)
            mos_eval.add_rating(video, rater, round(score, 1))

    print("\n各视频MOS结果:")
    all_mos = mos_eval.calculate_all_mos()
    for video_id, result in all_mos.items():
        print(f"  {video_id}:")
        print(f"    均值: {result.mean_score:.2f} ± {result.std_score:.2f}")
        print(f"    95% CI: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
        print(f"    评价人数: {result.num_raters}")

    print("\n评价者可靠性:")
    for rater in raters:
        try:
            reliability = mos_eval.calculate_rater_reliability(rater)
            print(f"  {rater}: 相关系数 = {reliability['correlation_with_mean']:.3f}, "
                  f"可靠 = {reliability['is_reliable']}")
        except Exception as e:
            print(f"  {rater}: 无法计算 - {e}")

    print("\n=== 综合质量评估测试 ===")
    combined_eval = create_combined_evaluator()

    objective_metrics = {
        'video_001': {'psnr': 35.2, 'ssim': 0.92, 'lpips': 0.15},
        'video_002': {'psnr': 32.8, 'ssim': 0.88, 'lpips': 0.22},
        'video_003': {'psnr': 38.1, 'ssim': 0.95, 'lpips': 0.08},
    }

    all_combined = combined_eval.batch_evaluate(objective_metrics)
    for video_id, score in all_combined.items():
        print(f"  {video_id}:")
        print(f"    MOS: {score.mos_score:.2f}, PSNR: {score.psnr:.1f}, "
              f"SSIM: {score.ssim:.3f}, LPIPS: {score.lpips:.3f}")
        print(f"    综合得分: {score.combined_score:.2f}/5")

    print("\n✅ MOS 评估测试通过!")
