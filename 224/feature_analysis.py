import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

class FeatureAnalysis:
    def __init__(self, feature_names):
        self.feature_names = feature_names
        self.importances = {}
        
    def add_model_importance(self, model_name, importance_df):
        self.importances[model_name] = importance_df
        
    def plot_feature_importance(self, model_name, top_n=15, save_path=None, figsize=(12, 8)):
        if model_name not in self.importances:
            raise ValueError(f"模型 {model_name} 的特征重要性未提供")
        
        importance_df = self.importances[model_name].head(top_n)
        
        plt.figure(figsize=figsize)
        sns.barplot(x='Importance', y='Feature', data=importance_df, palette='viridis')
        plt.title(f'{model_name} - 前{top_n}个重要特征', fontsize=16, fontweight='bold')
        plt.xlabel('重要性', fontsize=12)
        plt.ylabel('特征', fontsize=12)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return importance_df
    
    def plot_comparison_top_features(self, top_n=10, save_path=None, figsize=(14, 10)):
        model_names = list(self.importances.keys())
        
        if len(model_names) < 2:
            print("至少需要2个模型进行对比")
            return
        
        fig, axes = plt.subplots(1, len(model_names), figsize=figsize)
        
        for i, model_name in enumerate(model_names):
            importance_df = self.importances[model_name].head(top_n)
            ax = axes[i] if len(model_names) > 1 else axes
            
            sns.barplot(x='Importance', y='Feature', data=importance_df, palette='viridis', ax=ax)
            ax.set_title(f'{model_name}', fontsize=14, fontweight='bold')
            ax.set_xlabel('重要性', fontsize=10)
            ax.set_ylabel('特征', fontsize=10)
        
        plt.suptitle(f'模型特征重要性对比 (前{top_n}个)', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def get_common_important_features(self, top_n=10):
        top_features = {}
        for model_name, importance_df in self.importances.items():
            top_features[model_name] = set(importance_df.head(top_n)['Feature'].tolist())
        
        common_features = set.intersection(*top_features.values())
        
        print(f"前{top_n}个特征中，所有模型共有的重要特征 ({len(common_features)}个):")
        for feature in common_features:
            print(f"  - {feature}")
        
        return list(common_features)
    
    def create_importance_summary(self, top_n=20):
        summary_data = []
        
        for model_name, importance_df in self.importances.items():
            top_df = importance_df.head(top_n).copy()
            top_df['Model'] = model_name
            top_df['Rank'] = range(1, len(top_df) + 1)
            summary_data.append(top_df)
        
        summary_df = pd.concat(summary_data, ignore_index=True)
        
        return summary_df
    
    def plot_model_performance_comparison(self, results_df, save_path=None, figsize=(14, 8)):
        metrics = ['Accuracy', 'Precision', 'Recall', 'F1', 'ROC AUC']
        
        fig, axes = plt.subplots(2, 3, figsize=figsize)
        axes = axes.flatten()
        
        for i, metric in enumerate(metrics):
            ax = axes[i]
            results_df[metric].plot(kind='bar', ax=ax, color=sns.color_palette('viridis', len(results_df)))
            ax.set_title(f'{metric} 对比', fontsize=12, fontweight='bold')
            ax.set_ylabel(metric)
            ax.set_xlabel('模型')
            ax.tick_params(axis='x', rotation=45)
            
            for j, v in enumerate(results_df[metric]):
                ax.text(j, v, f'{v:.3f}', ha='center', va='bottom')
        
        axes[-1].axis('off')
        plt.suptitle('模型性能指标对比', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def analyze_correlation(self, X, top_features=None, save_path=None, figsize=(14, 12)):
        if top_features is not None:
            X = X[top_features]
        
        corr_matrix = X.corr()
        
        plt.figure(figsize=figsize)
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f', 
                    cmap='coolwarm', center=0, square=True, linewidths=0.5)
        plt.title('特征相关性热力图', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return corr_matrix
    
    def print_importance_rankings(self, top_n=15):
        for model_name, importance_df in self.importances.items():
            print(f"\n{'='*60}")
            print(f"{model_name} - 特征重要性排名 (前{top_n}个)")
            print(f"{'='*60}")
            print(f"{'排名':<6} {'特征':<35} {'重要性':<10}")
            print(f"{'-'*60}")
            
            for i, row in importance_df.head(top_n).iterrows():
                print(f"{i+1:<6} {row['Feature']:<35} {row['Importance']:.6f}")


if __name__ == "__main__":
    from data_generator import generate_hr_data
    from feature_engineering import FeatureEngineering
    from model_training import ModelTrainer
    
    df = generate_hr_data(num_samples=2000)
    
    fe = FeatureEngineering(scaling_method='standard')
    df_enhanced = fe.create_additional_features(df)
    X_processed, y = fe.fit_transform(df_enhanced)
    
    trainer = ModelTrainer(random_state=42)
    X_train, X_test, y_train, y_test = trainer.train_test_split(X_processed, y)
    
    models, results = trainer.train_all_models(X_train, y_train, X_test, y_test)
    
    analysis = FeatureAnalysis(fe.get_feature_names())
    
    for model_name in models.keys():
        importance_df = trainer.get_feature_importance(model_name, fe.get_feature_names())
        analysis.add_model_importance(model_name, importance_df)
    
    analysis.print_importance_rankings(top_n=10)
    
    analysis.plot_feature_importance('XGBoost', top_n=15)
    
    analysis.get_common_important_features(top_n=10)
