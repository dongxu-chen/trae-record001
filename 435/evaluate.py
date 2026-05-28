import os
import sys
import cv2
import numpy as np
import torch
import matplotlib.pyplot as plt
from matplotlib import rcParams
from typing import List, Dict

from config import Config
from data import RainSynthesizer
from models import build_model
from utils import (
    calculate_psnr, calculate_ssim,
    SubjectiveEvaluator, ComprehensiveEvaluator, ObjectiveMetrics,
    EdgeAwareLoss
)
from train import load_checkpoint

rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False


class ModelComparator:
    def __init__(self, image_paths: List[str]):
        self.image_paths = image_paths
        self.device = Config.DEVICE
        self.edge_loss = EdgeAwareLoss(loss_type='l1').to(self.device)
        
        self.models = {}
        self.results = {}
    
    def load_model(self, model_name: str, checkpoint_path: str = None, model_type: str = 'resnet'):
        model = build_model(model_type)
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            model, _, epoch, metrics = load_checkpoint(model, None, checkpoint_path)
            print(f"Loaded {model_name} (epoch {epoch})")
        else:
            print(f"Using untrained {model_name}")
        
        self.models[model_name] = model
    
    def evaluate_model(self, model_name: str, intensities: List[str] = ['light', 'medium', 'heavy']):
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")
        
        model = self.models[model_name]
        model.eval()
        
        comprehensive_evaluator = ComprehensiveEvaluator()
        all_metrics = []
        
        for img_path in self.image_paths:
            image_id = os.path.splitext(os.path.basename(img_path))[0]
            
            clean_img = cv2.imread(img_path)
            clean_img = cv2.cvtColor(clean_img, cv2.COLOR_BGR2RGB)
            clean_img = cv2.resize(clean_img, Config.IMAGE_SIZE)
            clean_tensor = torch.from_numpy(clean_img.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0).to(self.device)
            
            for intensity in intensities:
                rain_synth = RainSynthesizer(intensity=intensity)
                rainy_img = rain_synth(clean_img)
                rainy_tensor = torch.from_numpy(rainy_img).permute(2, 0, 1).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    derained_tensor = model(rainy_tensor)
                
                psnr_input = calculate_psnr(rainy_tensor, clean_tensor)
                ssim_input = calculate_ssim(rainy_tensor, clean_tensor)
                psnr_output = calculate_psnr(derained_tensor, clean_tensor)
                ssim_output = calculate_ssim(derained_tensor, clean_tensor)
                
                with torch.no_grad():
                    edge_sim = 1.0 / (1.0 + self.edge_loss(derained_tensor, clean_tensor).item())
                
                objective = ObjectiveMetrics(
                    psnr=psnr_output,
                    ssim=ssim_output,
                    psnr_gain=psnr_output - psnr_input,
                    ssim_gain=ssim_output - ssim_input,
                    edge_similarity=edge_sim
                )
                
                comprehensive_evaluator.add_evaluation(
                    image_id=image_id,
                    method=model_name,
                    rain_intensity=intensity,
                    objective=objective
                )
                
                all_metrics.append({
                    'image_id': image_id,
                    'intensity': intensity,
                    'psnr_input': psnr_input,
                    'ssim_input': ssim_input,
                    'psnr_output': psnr_output,
                    'ssim_output': ssim_output,
                    'psnr_gain': psnr_output - psnr_input,
                    'ssim_gain': ssim_output - ssim_input,
                    'edge_similarity': edge_sim
                })
        
        self.results[model_name] = {
            'comprehensive': comprehensive_evaluator,
            'metrics': all_metrics
        }
        
        return comprehensive_evaluator
    
    def add_subjective_scores(self, model_name: str, use_mock: bool = True):
        if model_name not in self.results:
            raise ValueError(f"Model {model_name} not evaluated")
        
        evaluator = self.results[model_name]['comprehensive']
        subjective_evaluator = SubjectiveEvaluator()
        
        quality_levels = ['excellent', 'good', 'medium', 'poor']
        
        for eval_item in evaluator.evaluations:
            if use_mock:
                if eval_item.rain_intensity == 'light':
                    quality = np.random.choice(quality_levels, p=[0.5, 0.3, 0.15, 0.05])
                elif eval_item.rain_intensity == 'medium':
                    quality = np.random.choice(quality_levels, p=[0.3, 0.4, 0.2, 0.1])
                else:
                    quality = np.random.choice(quality_levels, p=[0.1, 0.3, 0.4, 0.2])
                
                subjective_score = subjective_evaluator.generate_mock_scores(
                    image_id=eval_item.image_id,
                    method=model_name,
                    rain_intensity=eval_item.rain_intensity,
                    quality_level=quality
                )
                
                eval_item.subjective = subjective_score
                eval_item.calculate_combined_score()
        
        subjective_evaluator.save_scores(f'subjective_{model_name}.json')
        return subjective_evaluator
    
    def compare_models(self, save_dir: str = 'results/comparison'):
        os.makedirs(save_dir, exist_ok=True)
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        intensities = ['light', 'medium', 'heavy']
        model_names = list(self.results.keys())
        
        psnr_gains = {m: [] for m in model_names}
        ssim_gains = {m: [] for m in model_names}
        combined_scores = {m: [] for m in model_names}
        
        for model_name in model_names:
            evaluator = self.results[model_name]['comprehensive']
            intensity_breakdown = evaluator.get_intensity_breakdown()
            
            for intensity in intensities:
                if intensity in intensity_breakdown:
                    psnr_gains[model_name].append(intensity_breakdown[intensity]['mean_psnr'])
                    ssim_gains[model_name].append(intensity_breakdown[intensity]['mean_ssim'])
                    combined_scores[model_name].append(intensity_breakdown[intensity]['mean_combined'])
        
        x = np.arange(len(intensities))
        width = 0.25
        
        for i, model_name in enumerate(model_names):
            axes[0, 0].bar(x + i * width, psnr_gains[model_name], width, label=model_name)
        axes[0, 0].set_xticks(x + width / len(model_names))
        axes[0, 0].set_xticklabels(intensities)
        axes[0, 0].set_ylabel('PSNR (dB)')
        axes[0, 0].set_title('各雨强下PSNR对比')
        axes[0, 0].legend()
        
        for i, model_name in enumerate(model_names):
            axes[0, 1].bar(x + i * width, ssim_gains[model_name], width, label=model_name)
        axes[0, 1].set_xticks(x + width / len(model_names))
        axes[0, 1].set_xticklabels(intensities)
        axes[0, 1].set_ylabel('SSIM')
        axes[0, 1].set_title('各雨强下SSIM对比')
        axes[0, 1].legend()
        
        for i, model_name in enumerate(model_names):
            axes[1, 0].bar(x + i * width, combined_scores[model_name], width, label=model_name)
        axes[1, 0].set_xticks(x + width / len(model_names))
        axes[1, 0].set_xticklabels(intensities)
        axes[1, 0].set_ylabel('综合得分')
        axes[1, 0].set_title('各雨强下综合得分对比')
        axes[1, 0].legend()
        
        rankings = {}
        for model_name in model_names:
            evaluator = self.results[model_name]['comprehensive']
            method_rankings = evaluator.get_method_rankings()
            if model_name in method_rankings:
                rankings[model_name] = method_rankings[model_name]['mean_score']
        
        if rankings:
            sorted_rankings = sorted(rankings.items(), key=lambda x: x[1], reverse=True)
            names = [r[0] for r in sorted_rankings]
            scores = [r[1] for r in sorted_rankings]
            
            bars = axes[1, 1].barh(names, scores, color='steelblue')
            axes[1, 1].set_xlabel('综合得分')
            axes[1, 1].set_title('模型综合排名')
            
            for bar, score in zip(bars, scores):
                axes[1, 1].text(score, bar.get_y() + bar.get_height()/2, f'{score:.4f}', 
                               ha='left', va='center')
        
        plt.tight_layout()
        comparison_path = os.path.join(save_dir, 'model_comparison.png')
        plt.savefig(comparison_path, dpi=150, bbox_inches='tight')
        print(f"Model comparison chart saved: {comparison_path}")
        plt.close()
        
        return rankings
    
    def generate_report(self, save_dir: str = 'results/evaluation'):
        os.makedirs(save_dir, exist_ok=True)
        
        report = {
            'models': list(self.models.keys()),
            'results': {}
        }
        
        for model_name in self.results:
            evaluator = self.results[model_name]['comprehensive']
            report['results'][model_name] = {
                'rankings': evaluator.get_method_rankings(),
                'intensity_breakdown': evaluator.get_intensity_breakdown()
            }
            evaluator.save_report(f'evaluation_{model_name}.json')
        
        return report


def demo_subjective_evaluation():
    print("=" * 60)
    print("主观评分系统演示")
    print("=" * 60)
    
    evaluator = SubjectiveEvaluator()
    
    print("\n模拟生成3个样本的主观评分...")
    
    quality_levels = ['excellent', 'good', 'medium', 'poor']
    for i in range(3):
        intensity = ['light', 'medium', 'heavy'][i]
        quality = np.random.choice(quality_levels)
        score = evaluator.generate_mock_scores(
            image_id=f'sample_{i+1}',
            method='ResNet-GAN',
            rain_intensity=intensity,
            quality_level=quality
        )
        print(f"样本{i+1} ({intensity}): 整体质量={score.overall_quality:.2f}, "
              f"去雨效果={score.rain_removal:.2f}, 细节保留={score.detail_preservation:.2f}")
    
    stats = evaluator.get_statistics()
    print("\n统计结果:")
    for attr, data in stats.items():
        print(f"  {attr:20s}: {data['mean']:.2f} ± {data['std']:.2f}")
    
    evaluator.save_scores()


def demo_comprehensive_evaluation():
    print("\n" + "=" * 60)
    print("综合评估演示")
    print("=" * 60)
    
    test_image = 'data/test/sample.jpg'
    if not os.path.exists(test_image):
        print(f"Test image not found: {test_image}")
        return
    
    comparator = ModelComparator([test_image])
    
    comparator.load_model('Baseline')
    comparator.load_model('With-Edge-Loss')
    
    print("\n评估 Baseline 模型...")
    comparator.evaluate_model('Baseline')
    
    print("\n评估 With-Edge-Loss 模型...")
    comparator.evaluate_model('With-Edge-Loss')
    
    print("\n添加模拟主观评分...")
    comparator.add_subjective_scores('Baseline')
    comparator.add_subjective_scores('With-Edge-Loss')
    
    print("\n生成对比图表...")
    rankings = comparator.compare_models()
    
    print("\n模型排名:")
    for i, (name, score) in enumerate(rankings.items(), 1):
        print(f"  {i}. {name:20s}: {score:.4f}")
    
    comparator.generate_report()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='综合评估系统')
    parser.add_argument('--mode', type=str, default='demo',
                       choices=['demo', 'subjective', 'comprehensive', 'compare'])
    parser.add_argument('--test_dir', type=str, default='data/test')
    
    args = parser.parse_args()
    
    if args.mode == 'demo':
        demo_subjective_evaluation()
        demo_comprehensive_evaluation()
    elif args.mode == 'subjective':
        demo_subjective_evaluation()
    elif args.mode == 'comprehensive':
        demo_comprehensive_evaluation()


if __name__ == '__main__':
    main()
