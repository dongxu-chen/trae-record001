import os
import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SubjectiveScore:
    image_id: str
    method: str
    rain_intensity: str
    overall_quality: float
    rain_removal: float
    detail_preservation: float
    naturalness: float
    artifacts: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            'image_id': self.image_id,
            'method': self.method,
            'rain_intensity': self.rain_intensity,
            'overall_quality': self.overall_quality,
            'rain_removal': self.rain_removal,
            'detail_preservation': self.detail_preservation,
            'naturalness': self.naturalness,
            'artifacts': self.artifacts,
            'timestamp': self.timestamp
        }


@dataclass
class ObjectiveMetrics:
    psnr: float
    ssim: float
    psnr_gain: float
    ssim_gain: float
    edge_similarity: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'psnr': self.psnr,
            'ssim': self.ssim,
            'psnr_gain': self.psnr_gain,
            'ssim_gain': self.ssim_gain,
            'edge_similarity': self.edge_similarity
        }


@dataclass
class ComprehensiveScore:
    image_id: str
    method: str
    rain_intensity: str
    objective: ObjectiveMetrics
    subjective: Optional[SubjectiveScore] = None
    combined_score: float = 0.0
    
    def calculate_combined_score(self, 
                                 objective_weight: float = 0.6, 
                                 subjective_weight: float = 0.4) -> float:
        psnr_norm = min(self.objective.psnr / 40.0, 1.0)
        ssim_norm = self.objective.ssim
        
        obj_score = (psnr_norm + ssim_norm) / 2
        
        if self.subjective is not None:
            subj_score = (
                self.subjective.overall_quality +
                self.subjective.rain_removal +
                self.subjective.detail_preservation +
                self.subjective.naturalness +
                (5 - self.subjective.artifacts)
            ) / 25.0
        else:
            subj_score = obj_score
        
        self.combined_score = objective_weight * obj_score + subjective_weight * subj_score
        return self.combined_score
    
    def to_dict(self) -> dict:
        return {
            'image_id': self.image_id,
            'method': self.method,
            'rain_intensity': self.rain_intensity,
            'objective': self.objective.to_dict(),
            'subjective': self.subjective.to_dict() if self.subjective else None,
            'combined_score': self.combined_score
        }


class SubjectiveEvaluator:
    def __init__(self, save_dir: str = 'results/evaluation'):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.scores: List[SubjectiveScore] = []
    
    def get_score_from_input(self, image_id: str, method: str, rain_intensity: str) -> SubjectiveScore:
        print(f"\n=== 主观评分 - 图像: {image_id}, 方法: {method}, 雨强: {rain_intensity} ===")
        print("请按1-5分评分（1=最差，5=最好）")
        
        overall_quality = self._get_valid_score("整体质量")
        rain_removal = self._get_valid_score("去雨效果")
        detail_preservation = self._get_valid_score("细节保留")
        naturalness = self._get_valid_score("自然度")
        artifacts = self._get_valid_score("伪影程度（1=无，5=严重）")
        
        score = SubjectiveScore(
            image_id=image_id,
            method=method,
            rain_intensity=rain_intensity,
            overall_quality=overall_quality,
            rain_removal=rain_removal,
            detail_preservation=detail_preservation,
            naturalness=naturalness,
            artifacts=artifacts
        )
        
        self.scores.append(score)
        return score
    
    def _get_valid_score(self, prompt: str) -> float:
        while True:
            try:
                score = float(input(f"{prompt}: "))
                if 1 <= score <= 5:
                    return score
                else:
                    print("请输入1-5之间的数字")
            except ValueError:
                print("请输入有效的数字")
    
    def generate_mock_scores(self, image_id: str, method: str, rain_intensity: str, 
                            quality_level: str = 'good') -> SubjectiveScore:
        if quality_level == 'excellent':
            base_score = np.random.uniform(4.5, 5.0)
        elif quality_level == 'good':
            base_score = np.random.uniform(3.5, 4.5)
        elif quality_level == 'medium':
            base_score = np.random.uniform(2.5, 3.5)
        elif quality_level == 'poor':
            base_score = np.random.uniform(1.0, 2.5)
        else:
            base_score = np.random.uniform(3.0, 4.0)
        
        score = SubjectiveScore(
            image_id=image_id,
            method=method,
            rain_intensity=rain_intensity,
            overall_quality=base_score + np.random.uniform(-0.2, 0.2),
            rain_removal=base_score + np.random.uniform(-0.3, 0.3),
            detail_preservation=base_score + np.random.uniform(-0.2, 0.2),
            naturalness=base_score + np.random.uniform(-0.2, 0.2),
            artifacts=5.0 - base_score + np.random.uniform(-0.3, 0.3)
        )
        
        self.scores.append(score)
        return score
    
    def save_scores(self, filename: str = None):
        if filename is None:
            filename = f'subjective_scores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        filepath = os.path.join(self.save_dir, filename)
        scores_dict = [s.to_dict() for s in self.scores]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scores_dict, f, ensure_ascii=False, indent=2)
        
        print(f"主观评分已保存至: {filepath}")
        return filepath
    
    def load_scores(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            scores_dict = json.load(f)
        
        self.scores = []
        for s in scores_dict:
            self.scores.append(SubjectiveScore(**s))
        
        print(f"已加载 {len(self.scores)} 条主观评分记录")
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        if not self.scores:
            return {}
        
        stats = {}
        attributes = ['overall_quality', 'rain_removal', 'detail_preservation', 'naturalness', 'artifacts']
        
        for attr in attributes:
            values = [getattr(s, attr) for s in self.scores]
            stats[attr] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values)
            }
        
        return stats


class ComprehensiveEvaluator:
    def __init__(self, save_dir: str = 'results/evaluation'):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.evaluations: List[ComprehensiveScore] = []
    
    def add_evaluation(self, image_id: str, method: str, rain_intensity: str,
                       objective: ObjectiveMetrics, 
                       subjective: Optional[SubjectiveScore] = None) -> ComprehensiveScore:
        evaluation = ComprehensiveScore(
            image_id=image_id,
            method=method,
            rain_intensity=rain_intensity,
            objective=objective,
            subjective=subjective
        )
        evaluation.calculate_combined_score()
        self.evaluations.append(evaluation)
        return evaluation
    
    def get_method_rankings(self) -> Dict[str, Dict]:
        method_scores = {}
        
        for eval_item in self.evaluations:
            method = eval_item.method
            if method not in method_scores:
                method_scores[method] = []
            method_scores[method].append(eval_item.combined_score)
        
        rankings = {}
        for method, scores in method_scores.items():
            rankings[method] = {
                'mean_score': np.mean(scores),
                'std_score': np.std(scores),
                'count': len(scores)
            }
        
        return dict(sorted(rankings.items(), key=lambda x: x[1]['mean_score'], reverse=True))
    
    def get_intensity_breakdown(self) -> Dict[str, Dict]:
        intensity_scores = {}
        
        for eval_item in self.evaluations:
            intensity = eval_item.rain_intensity
            if intensity not in intensity_scores:
                intensity_scores[intensity] = {'combined': [], 'psnr': [], 'ssim': []}
            
            intensity_scores[intensity]['combined'].append(eval_item.combined_score)
            intensity_scores[intensity]['psnr'].append(eval_item.objective.psnr)
            intensity_scores[intensity]['ssim'].append(eval_item.objective.ssim)
        
        results = {}
        for intensity, data in intensity_scores.items():
            results[intensity] = {
                'mean_combined': np.mean(data['combined']),
                'mean_psnr': np.mean(data['psnr']),
                'mean_ssim': np.mean(data['ssim']),
                'count': len(data['combined'])
            }
        
        return results
    
    def save_report(self, filename: str = None):
        if filename is None:
            filename = f'comprehensive_evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        filepath = os.path.join(self.save_dir, filename)
        report = {
            'evaluations': [e.to_dict() for e in self.evaluations],
            'method_rankings': self.get_method_rankings(),
            'intensity_breakdown': self.get_intensity_breakdown(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"综合评估报告已保存至: {filepath}")
        return filepath
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print("综合评估报告")
        print("=" * 60)
        
        rankings = self.get_method_rankings()
        print("\n方法排名:")
        for i, (method, stats) in enumerate(rankings.items(), 1):
            print(f"  {i}. {method:20s}: 综合得分 = {stats['mean_score']:.4f} ± {stats['std_score']:.4f} (n={stats['count']})")
        
        intensity_breakdown = self.get_intensity_breakdown()
        print("\n雨强分析:")
        for intensity, stats in intensity_breakdown.items():
            print(f"  {intensity:8s}: PSNR = {stats['mean_psnr']:.2f}dB, SSIM = {stats['mean_ssim']:.4f}, 综合 = {stats['mean_combined']:.4f}")
        
        print("\n" + "=" * 60)


def calculate_combined_metric(psnr: float, ssim: float, 
                              psnr_weight: float = 0.5, 
                              ssim_weight: float = 0.5) -> float:
    psnr_norm = min(psnr / 40.0, 1.0)
    ssim_norm = ssim
    return psnr_weight * psnr_norm + ssim_weight * ssim_norm
