import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional, Any
import os
import warnings
warnings.filterwarnings('ignore')


class SHAPAnalyzer:
    def __init__(self, model, feature_names: List[str], target_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        self.target_names = target_names
        self.explainers = {}
        self.shap_values = {}
        self.is_initialized = False
    
    def initialize_explainers(self, X_train: np.ndarray) -> None:
        for i, target in enumerate(self.target_names):
            estimator = self.model.estimators_[i]
            explainer = shap.TreeExplainer(estimator)
            self.explainers[target] = explainer
        
        self.is_initialized = True
    
    def compute_shap_values(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        if not self.is_initialized:
            raise ValueError("SHAP解释器未初始化，请先调用initialize_explainers")
        
        shap_values = {}
        for target in self.target_names:
            explainer = self.explainers[target]
            sv = explainer.shap_values(X)
            shap_values[target] = sv
            self.shap_values[target] = sv
        
        return shap_values
    
    def get_feature_importance(self, X: Optional[np.ndarray] = None, 
                              top_n: int = 15) -> pd.DataFrame:
        if not self.shap_values and X is not None:
            self.compute_shap_values(X)
        
        if not self.shap_values:
            raise ValueError("需要先计算SHAP值")
        
        importance_data = []
        
        for target in self.target_names:
            sv = self.shap_values[target]
            mean_abs_shap = np.mean(np.abs(sv), axis=0)
            
            for j, feat in enumerate(self.feature_names):
                importance_data.append({
                    'target': target,
                    'feature': feat,
                    'shap_importance': mean_abs_shap[j]
                })
        
        df = pd.DataFrame(importance_data)
        return df.sort_values(['target', 'shap_importance'], ascending=[True, False])
    
    def plot_summary(self, X: np.ndarray, target: Optional[str] = None,
                    save_path: Optional[str] = None, 
                    max_display: int = 15, 
                    show: bool = False) -> Optional[plt.Figure]:
        if not self.is_initialized:
            self.initialize_explainers(X)
        
        if target is None:
            target = self.target_names[0]
        
        if target not in self.shap_values:
            self.compute_shap_values(X)
        
        shap_vals = self.shap_values[target]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        shap.summary_plot(
            shap_vals, X, 
            feature_names=self.feature_names,
            max_display=max_display,
            plot_type="dot",
            show=False
        )
        plt.title(f"SHAP Summary Plot - {target}", fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        
        return fig
    
    def plot_bar(self, X: np.ndarray, target: Optional[str] = None,
                 save_path: Optional[str] = None,
                 max_display: int = 15,
                 show: bool = False) -> Optional[plt.Figure]:
        if not self.is_initialized:
            self.initialize_explainers(X)
        
        if target is None:
            target = self.target_names[0]
        
        if target not in self.shap_values:
            self.compute_shap_values(X)
        
        shap_vals = self.shap_values[target]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        shap.summary_plot(
            shap_vals, X,
            feature_names=self.feature_names,
            max_display=max_display,
            plot_type="bar",
            show=False
        )
        plt.title(f"SHAP Feature Importance - {target}", fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        
        return fig
    
    def plot_dependence(self, X: np.ndarray, feature: str, 
                        target: Optional[str] = None,
                        interaction_feature: Optional[str] = None,
                        save_path: Optional[str] = None,
                        show: bool = False) -> Optional[plt.Figure]:
        if not self.is_initialized:
            self.initialize_explainers(X)
        
        if target is None:
            target = self.target_names[0]
        
        if target not in self.shap_values:
            self.compute_shap_values(X)
        
        shap_vals = self.shap_values[target]
        feat_idx = self.feature_names.index(feature)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        shap.dependence_plot(
            feat_idx, shap_vals, X,
            feature_names=self.feature_names,
            interaction_index=interaction_feature,
            show=False
        )
        plt.title(f"SHAP Dependence Plot - {feature}", fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        
        return fig
    
    def explain_single_prediction(self, X: np.ndarray, 
                                  sample_idx: int = 0,
                                  target: Optional[str] = None,
                                  save_path: Optional[str] = None,
                                  show: bool = False) -> Dict[str, Any]:
        if not self.is_initialized:
            self.initialize_explainers(X)
        
        if target is None:
            target = self.target_names[0]
        
        explainer = self.explainers[target]
        sample = X[sample_idx:sample_idx+1]
        shap_values_sample = explainer.shap_values(sample)
        base_value = explainer.expected_value
        
        feature_values = sample[0]
        
        shap_contributions = []
        for i, feat in enumerate(self.feature_names):
            shap_contributions.append({
                'feature': feat,
                'value': float(feature_values[i]),
                'shap_value': float(shap_values_sample[0][i]),
                'abs_shap': abs(float(shap_values_sample[0][i]))
            })
        
        df_contrib = pd.DataFrame(shap_contributions)
        df_contrib = df_contrib.sort_values('abs_shap', ascending=False)
        
        prediction = self.model.predict(sample)[0][self.target_names.index(target)]
        
        result = {
            'target': target,
            'base_value': float(base_value),
            'prediction': float(prediction),
            'contributions': df_contrib
        }
        
        return result
    
    def plot_waterfall(self, X: np.ndarray, sample_idx: int = 0,
                       target: Optional[str] = None,
                       max_display: int = 10,
                       save_path: Optional[str] = None,
                       show: bool = False) -> Optional[plt.Figure]:
        if not self.is_initialized:
            self.initialize_explainers(X)
        
        if target is None:
            target = self.target_names[0]
        
        explainer = self.explainers[target]
        sample = X[sample_idx:sample_idx+1]
        
        explanation = shap.Explanation(
            values=explainer.shap_values(sample)[0],
            base_values=explainer.expected_value,
            data=sample[0],
            feature_names=self.feature_names
        )
        
        fig, ax = plt.subplots(figsize=(10, 8))
        shap.waterfall_plot(explanation, max_display=max_display, show=False)
        plt.title(f"SHAP Waterfall Plot - {target} (Sample {sample_idx})", fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        
        return fig
    
    def plot_force(self, X: np.ndarray, sample_idx: int = 0,
                   target: Optional[str] = None,
                   save_path: Optional[str] = None,
                   show: bool = False) -> Optional[Any]:
        if not self.is_initialized:
            self.initialize_explainers(X)
        
        if target is None:
            target = self.target_names[0]
        
        explainer = self.explainers[target]
        sample = X[sample_idx:sample_idx+1]
        shap_values_sample = explainer.shap_values(sample)
        base_value = explainer.expected_value
        
        fig = shap.force_plot(
            base_value, shap_values_sample, sample,
            feature_names=self.feature_names,
            show=False
        )
        
        if save_path:
            shap.save_html(save_path, fig)
        
        if show:
            shap.initjs()
            return fig
        
        return fig
    
    def generate_all_plots(self, X_train: np.ndarray, X_test: np.ndarray,
                          output_dir: str = "plots") -> Dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        
        if not self.is_initialized:
            self.initialize_explainers(X_train)
        
        self.compute_shap_values(X_test)
        
        plot_paths = {}
        
        for target in self.target_names:
            target_safe = target.replace('/', '_')
            
            summary_path = f"{output_dir}/summary_{target_safe}.png"
            self.plot_summary(X_test, target, save_path=summary_path, show=False)
            plot_paths[f'summary_{target_safe}'] = summary_path
            
            bar_path = f"{output_dir}/bar_{target_safe}.png"
            self.plot_bar(X_test, target, save_path=bar_path, show=False)
            plot_paths[f'bar_{target_safe}'] = bar_path
            
            df_imp = self.get_feature_importance()
            top_features = df_imp[df_imp['target'] == target]['feature'].head(3).tolist()
            
            for feat in top_features:
                dep_path = f"{output_dir}/dependence_{target_safe}_{feat}.png"
                self.plot_dependence(X_test, feat, target, save_path=dep_path, show=False)
                plot_paths[f'dependence_{target_safe}_{feat}'] = dep_path
            
            for idx in range(min(3, len(X_test))):
                waterfall_path = f"{output_dir}/waterfall_{target_safe}_sample{idx}.png"
                self.plot_waterfall(X_test, idx, target, save_path=waterfall_path, show=False)
                plot_paths[f'waterfall_{target_safe}_sample{idx}'] = waterfall_path
        
        return plot_paths
    
    def get_shap_values_for_streamlit(self, X: np.ndarray) -> Dict[str, Any]:
        if not self.is_initialized:
            self.initialize_explainers(X)
        
        shap_values = self.compute_shap_values(X)
        
        return {
            'shap_values': shap_values,
            'expected_values': {
                target: float(self.explainers[target].expected_value)
                for target in self.target_names
            },
            'feature_names': self.feature_names,
            'target_names': self.target_names
        }


def run_shap_analysis(model, X_train: np.ndarray, X_test: np.ndarray,
                     feature_names: List[str], target_names: List[str],
                     output_dir: str = "plots") -> SHAPAnalyzer:
    print("=== SHAP 可解释性分析 ===")
    
    analyzer = SHAPAnalyzer(model, feature_names, target_names)
    analyzer.initialize_explainers(X_train)
    
    print("\n计算SHAP值...")
    analyzer.compute_shap_values(X_test)
    
    print("\n特征重要性 (基于SHAP):")
    df_imp = analyzer.get_feature_importance()
    for target in target_names:
        print(f"\n{target}:")
        df_target = df_imp[df_imp['target'] == target].head(10)
        for _, row in df_target.iterrows():
            print(f"  {row['feature']}: {row['shap_importance']:.4f}")
    
    print(f"\n生成图表到 {output_dir}/ ...")
    plot_paths = analyzer.generate_all_plots(X_train, X_test, output_dir)
    
    print(f"\n已生成 {len(plot_paths)} 个图表")
    
    return analyzer


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.features.data_generator import generate_full_dataset
    from src.models.xgboost_model import train_full_pipeline
    
    print("生成数据...")
    df_levels, df_players = generate_full_dataset(n_levels=100, n_players=200)
    
    print("\n训练模型...")
    model, data = train_full_pipeline(df_levels, use_actual=True)
    
    print("\n执行SHAP分析...")
    analyzer = run_shap_analysis(
        model.model, data['X_train'], data['X_test'],
        data['feature_names'], data['target_names']
    )
    
    print("\n单个样本解释:")
    explanation = analyzer.explain_single_prediction(data['X_test'], sample_idx=0)
    print(f"目标: {explanation['target']}")
    print(f"基准值: {explanation['base_value']:.4f}")
    print(f"预测值: {explanation['prediction']:.4f}")
    print("\nTop 5 贡献特征:")
    print(explanation['contributions'].head())
