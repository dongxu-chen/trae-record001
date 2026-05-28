import os
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class MOSScore:
    image_id: str
    score: float
    rater_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    comments: Optional[str] = None


@dataclass
class MOSDataset:
    name: str
    scores: List[MOSScore] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_score(self, score: MOSScore):
        self.scores.append(score)
    
    def get_image_scores(self, image_id: str) -> List[MOSScore]:
        return [s for s in self.scores if s.image_id == image_id]
    
    def get_average_score(self, image_id: Optional[str] = None) -> float:
        if image_id:
            scores = self.get_image_scores(image_id)
        else:
            scores = self.scores
        
        if not scores:
            return 0.0
        return np.mean([s.score for s in scores])
    
    def get_std_score(self, image_id: Optional[str] = None) -> float:
        if image_id:
            scores = self.get_image_scores(image_id)
        else:
            scores = self.scores
        
        if not scores:
            return 0.0
        return np.std([s.score for s in scores])
    
    def get_all_image_ids(self) -> List[str]:
        return list(set([s.image_id for s in self.scores]))
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'created_at': self.created_at,
            'scores': [asdict(s) for s in self.scores]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MOSDataset':
        dataset = cls(name=data['name'], created_at=data.get('created_at', datetime.now().isoformat()))
        for s in data.get('scores', []):
            dataset.add_score(MOSScore(
                image_id=s['image_id'],
                score=s['score'],
                rater_id=s.get('rater_id'),
                timestamp=s.get('timestamp'),
                comments=s.get('comments')
            ))
        return dataset
    
    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'MOSDataset':
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class QualityAspect:
    name: str
    description: str
    weight: float = 1.0


ASPECTS = [
    QualityAspect('overall', '整体视觉质量', 1.0),
    QualityAspect('reflection_removal', '反光去除效果', 1.5),
    QualityAspect('detail_preservation', '细节保留程度', 1.2),
    QualityAspect('naturalness', '色彩自然度', 1.0),
    QualityAspect('artifact', '伪影/畸变程度', 1.3),
    QualityAspect('sharpness', '清晰度', 1.0),
]


class MOSEvaluator:
    def __init__(self):
        self.aspects = ASPECTS
    
    def create_mos_dataset(self, name: str) -> MOSDataset:
        return MOSDataset(name=name)
    
    def add_aspect_score(
        self,
        dataset: MOSDataset,
        image_id: str,
        scores: Dict[str, float],
        rater_id: Optional[str] = None,
        comments: Optional[str] = None
    ) -> float:
        total_weight = sum(a.weight for a in self.aspects if a.name in scores)
        if total_weight == 0:
            return 0.0
        
        weighted_score = 0.0
        for aspect in self.aspects:
            if aspect.name in scores:
                weighted_score += scores[aspect.name] * aspect.weight / total_weight
        
        dataset.add_score(MOSScore(
            image_id=image_id,
            score=weighted_score,
            rater_id=rater_id,
            comments=comments
        ))
        
        return weighted_score
    
    def evaluate_objective(
        self,
        restored: np.ndarray,
        ground_truth: Optional[np.ndarray] = None,
        input_image: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        from .evaluator import Evaluator
        evaluator = Evaluator()
        
        if ground_truth is not None and input_image is not None:
            metrics = evaluator.evaluate(restored, ground_truth, input_image)
        elif ground_truth is not None:
            metrics = {
                'psnr': evaluator.compute_psnr(restored, ground_truth),
                'ssim': evaluator.compute_ssim(restored, ground_truth),
                'rmse': evaluator.compute_rmse(restored, ground_truth),
                'mae': evaluator.compute_mae(restored, ground_truth),
                'edge_preservation': evaluator.compute_edge_preservation(restored, ground_truth)
            }
        else:
            metrics = {
                'niqe': evaluator.compute_niqe(restored)
            }
        
        return metrics
    
    def compute_objective_mos(
        self,
        objective_metrics: Dict[str, float],
        method: str = 'weighted'
    ) -> float:
        if method == 'weighted':
            weights = {
                'psnr': 0.3,
                'ssim': 0.3,
                'ssim_improvement': 0.15,
                'psnr_improvement': 0.15,
                'reflection_suppression': 0.1
            }
            
            score = 0.0
            total_weight = 0.0
            
            for metric, weight in weights.items():
                if metric in objective_metrics and not np.isnan(objective_metrics[metric]):
                    value = objective_metrics[metric]
                    
                    if metric == 'psnr':
                        normalized = np.clip((value - 10) / 30, 0, 1) * 4 + 1
                    elif metric == 'ssim':
                        normalized = value * 4 + 1
                    elif metric in ['psnr_improvement', 'ssim_improvement']:
                        normalized = np.clip((value + 5) / 15, 0, 1) * 4 + 1
                    elif metric == 'reflection_suppression':
                        normalized = value * 4 + 1
                    else:
                        normalized = np.clip(value / 5, 0, 1) * 4 + 1
                    
                    score += normalized * weight
                    total_weight += weight
            
            return score / total_weight if total_weight > 0 else 3.0
        
        elif method == 'regression':
            psnr = objective_metrics.get('psnr', 20)
            ssim = objective_metrics.get('ssim', 0.5)
            
            mos = 1.0 + 0.12 * psnr + 3.0 * ssim
            return np.clip(mos, 1, 5)
        
        return 3.0
    
    def compute_comprehensive_score(
        self,
        subjective_mos: Optional[float],
        objective_metrics: Dict[str, float],
        alpha: float = 0.6
    ) -> Dict[str, float]:
        objective_mos = self.compute_objective_mos(objective_metrics)
        
        if subjective_mos is None:
            subjective_mos = objective_mos
        
        comprehensive = alpha * subjective_mos + (1 - alpha) * objective_mos
        
        return {
            'subjective_mos': subjective_mos,
            'objective_mos': objective_mos,
            'comprehensive_score': comprehensive,
            'confidence': self._compute_confidence(subjective_mos, objective_mos)
        }
    
    def _compute_confidence(self, subjective: float, objective: float) -> float:
        diff = abs(subjective - objective)
        confidence = 1.0 - diff / 4.0
        return max(0, min(1, confidence))
    
    def compute_correlation(
        self,
        subjective_scores: List[float],
        objective_scores: List[float]
    ) -> Dict[str, float]:
        if len(subjective_scores) != len(objective_scores) or len(subjective_scores) < 2:
            return {'pearson': 0.0, 'spearman': 0.0, 'kendall': 0.0}
        
        pearson = np.corrcoef(subjective_scores, objective_scores)[0, 1]
        
        from scipy import stats
        spearman = stats.spearmanr(subjective_scores, objective_scores)[0]
        kendall = stats.kendalltau(subjective_scores, objective_scores)[0]
        
        return {
            'pearson': pearson,
            'spearman': spearman,
            'kendall': kendall
        }
    
    def analyze_rater_reliability(
        self,
        dataset: MOSDataset
    ) -> Dict[str, Any]:
        rater_scores = {}
        for score in dataset.scores:
            rater = score.rater_id or 'unknown'
            if rater not in rater_scores:
                rater_scores[rater] = []
            rater_scores[rater].append(score.score)
        
        reliability = {}
        all_means = [np.mean(scores) for scores in rater_scores.values()]
        overall_mean = np.mean(all_means)
        
        for rater, scores in rater_scores.items():
            rater_mean = np.mean(scores)
            rater_std = np.std(scores)
            bias = rater_mean - overall_mean
            
            reliability[rater] = {
                'mean_score': rater_mean,
                'std_score': rater_std,
                'bias': bias,
                'num_ratings': len(scores),
                'consistency': 1.0 - min(1.0, rater_std / 2.0)
            }
        
        return reliability
    
    def plot_mos_distribution(
        self,
        dataset: MOSDataset,
        save_path: Optional[str] = None,
        show: bool = False
    ):
        image_ids = dataset.get_all_image_ids()
        avg_scores = [dataset.get_average_score(img_id) for img_id in image_ids]
        std_scores = [dataset.get_std_score(img_id) for img_id in image_ids]
        
        sorted_idx = np.argsort(avg_scores)
        sorted_scores = np.array(avg_scores)[sorted_idx]
        sorted_std = np.array(std_scores)[sorted_idx]
        sorted_ids = [image_ids[i] for i in sorted_idx]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        ax1.bar(range(len(sorted_scores)), sorted_scores, yerr=sorted_std, 
               capsize=5, color='steelblue', alpha=0.7)
        ax1.set_xlabel('Images', fontsize=12)
        ax1.set_ylabel('MOS Score', fontsize=12)
        ax1.set_title('MOS Scores by Image', fontsize=14, fontweight='bold')
        ax1.set_ylim(0, 5.5)
        ax1.axhline(y=3.0, color='r', linestyle='--', alpha=0.5, label='Neutral')
        ax1.legend()
        
        all_scores = [s.score for s in dataset.scores]
        ax2.hist(all_scores, bins=np.arange(0.5, 6, 1), color='lightcoral', 
                edgecolor='black', alpha=0.7)
        ax2.set_xlabel('Score', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.set_title('Score Distribution', fontsize=14, fontweight='bold')
        ax2.axvline(x=np.mean(all_scores), color='r', linestyle='--', 
                   label=f'Mean: {np.mean(all_scores):.2f}')
        ax2.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=100, bbox_inches='tight')
        
        if show:
            plt.show()
        
        plt.close()
    
    def plot_subjective_objective_correlation(
        self,
        subjective_scores: List[float],
        objective_scores: List[float],
        correlation: Dict[str, float],
        save_path: Optional[str] = None,
        show: bool = False
    ):
        fig, ax = plt.subplots(figsize=(8, 6))
        
        ax.scatter(objective_scores, subjective_scores, s=100, alpha=0.7, 
                  color='steelblue', edgecolor='black')
        
        if len(subjective_scores) >= 2:
            z = np.polyfit(objective_scores, subjective_scores, 1)
            p = np.poly1d(z)
            x_range = np.linspace(min(objective_scores), max(objective_scores), 100)
            ax.plot(x_range, p(x_range), 'r--', linewidth=2, 
                   label=f'Fit: y={z[0]:.2f}x+{z[1]:.2f}')
        
        ax.set_xlabel('Objective MOS', fontsize=12)
        ax.set_ylabel('Subjective MOS', fontsize=12)
        ax.set_title('Subjective vs Objective MOS', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 5.5)
        ax.set_ylim(0, 5.5)
        ax.plot([0, 5.5], [0, 5.5], 'k--', alpha=0.3, label='Perfect correlation')
        
        corr_text = f"Pearson: {correlation.get('pearson', 0):.3f}\n"
        corr_text += f"Spearman: {correlation.get('spearman', 0):.3f}\n"
        corr_text += f"Kendall: {correlation.get('kendall', 0):.3f}"
        ax.text(0.05, 0.95, corr_text, transform=ax.transAxes, 
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax.legend(loc='lower right')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=100, bbox_inches='tight')
        
        if show:
            plt.show()
        
        plt.close()
    
    def generate_comprehensive_report(
        self,
        dataset: MOSDataset,
        objective_results: Optional[Dict[str, Dict[str, float]]] = None,
        output_dir: str = 'output/mos_analysis'
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        
        report = {
            'dataset_name': dataset.name,
            'num_images': len(dataset.get_all_image_ids()),
            'num_ratings': len(dataset.scores),
            'overall_mos': dataset.get_average_score(),
            'overall_std': dataset.get_std_score()
        }
        
        per_image = {}
        for img_id in dataset.get_all_image_ids():
            img_mos = dataset.get_average_score(img_id)
            img_std = dataset.get_std_score(img_id)
            
            entry = {
                'mos': img_mos,
                'std': img_std,
                'num_ratings': len(dataset.get_image_scores(img_id))
            }
            
            if objective_results and img_id in objective_results:
                obj_metrics = objective_results[img_id]
                comp = self.compute_comprehensive_score(img_mos, obj_metrics)
                entry.update(obj_metrics)
                entry.update(comp)
            
            per_image[img_id] = entry
        
        report['per_image'] = per_image
        
        if objective_results:
            subjective_list = []
            objective_list = []
            for img_id in per_image:
                if 'objective_mos' in per_image[img_id]:
                    subjective_list.append(per_image[img_id]['mos'])
                    objective_list.append(per_image[img_id]['objective_mos'])
            
            if len(subjective_list) >= 2:
                correlation = self.compute_correlation(subjective_list, objective_list)
                report['correlation'] = correlation
                
                self.plot_subjective_objective_correlation(
                    subjective_list, objective_list, correlation,
                    save_path=os.path.join(output_dir, 'correlation_plot.png')
                )
        
        self.plot_mos_distribution(
            dataset,
            save_path=os.path.join(output_dir, 'mos_distribution.png')
        )
        
        reliability = self.analyze_rater_reliability(dataset)
        report['rater_reliability'] = reliability
        
        with open(os.path.join(output_dir, 'mos_report.json'), 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report
