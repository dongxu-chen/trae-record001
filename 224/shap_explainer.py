import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap
import warnings
warnings.filterwarnings('ignore')

class SHAPExplainer:
    def __init__(self, model, model_name, feature_names, X_train):
        self.model = model
        self.model_name = model_name
        self.feature_names = feature_names
        self.X_train = X_train
        self.explainer = None
        self.shap_values = None
        
        self._init_explainer()
        
    def _init_explainer(self):
        if self.model_name == 'XGBoost':
            self.explainer = shap.TreeExplainer(self.model)
        elif self.model_name == 'Random Forest':
            self.explainer = shap.TreeExplainer(self.model)
        elif self.model_name == 'Logistic Regression':
            background_data = shap.sample(self.X_train, 100)
            self.explainer = shap.LinearExplainer(self.model, background_data)
        else:
            background_data = shap.sample(self.X_train, 50)
            self.explainer = shap.KernelExplainer(self.model.predict_proba, background_data)
    
    def compute_shap_values(self, X):
        if self.model_name == 'Logistic Regression':
            self.shap_values = self.explainer.shap_values(X)
        else:
            self.shap_values = self.explainer.shap_values(X)
        
        return self.shap_values
    
    def plot_summary_plot(self, X, max_display=20, save_path=None):
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        plt.figure(figsize=(12, 8))
        
        if self.model_name in ['Random Forest', 'XGBoost']:
            if isinstance(self.shap_values, list):
                shap_vals = self.shap_values[1]
            else:
                shap_vals = self.shap_values
        else:
            shap_vals = self.shap_values
        
        shap.summary_plot(shap_vals, X, feature_names=self.feature_names, 
                          max_display=max_display, plot_type='bar', show=False)
        plt.title(f'{self.model_name} - SHAP特征重要性汇总', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return shap_vals
    
    def plot_beeswarm_summary(self, X, max_display=15, save_path=None):
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        if self.model_name in ['Random Forest', 'XGBoost']:
            if isinstance(self.shap_values, list):
                shap_vals = self.shap_values[1]
            else:
                shap_vals = self.shap_values
        else:
            shap_vals = self.shap_values
        
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_vals, X, feature_names=self.feature_names,
                          max_display=max_display, show=False)
        plt.title(f'{self.model_name} - SHAP Beeswarm图', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_force_plot_single(self, X, employee_idx=0, save_path=None):
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        if self.model_name in ['Random Forest', 'XGBoost']:
            if isinstance(self.shap_values, list):
                shap_vals = self.shap_values[1]
            else:
                shap_vals = self.shap_values
            base_value = self.explainer.expected_value
            if isinstance(base_value, list) or isinstance(base_value, np.ndarray):
                base_value = base_value[1] if len(base_value) > 1 else base_value[0]
        else:
            shap_vals = self.shap_values
            base_value = self.explainer.expected_value
        
        shap.force_plot(base_value, shap_vals[employee_idx, :], 
                        X.iloc[employee_idx, :], feature_names=self.feature_names,
                        matplotlib=True, show=False)
        plt.title(f'员工 {employee_idx+1} - SHAP力图\n离职风险决策因素分解', 
                  fontsize=12, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return {
            'employee_id': employee_idx + 1,
            'base_value': base_value,
            'shap_values': shap_vals[employee_idx, :],
            'feature_values': X.iloc[employee_idx, :]
        }
    
    def plot_decision_plot_single(self, X, employee_idx=0, save_path=None):
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        if self.model_name in ['Random Forest', 'XGBoost']:
            if isinstance(self.shap_values, list):
                shap_vals = self.shap_values[1]
            else:
                shap_vals = self.shap_values
            base_value = self.explainer.expected_value
            if isinstance(base_value, list) or isinstance(base_value, np.ndarray):
                base_value = base_value[1] if len(base_value) > 1 else base_value[0]
        else:
            shap_vals = self.shap_values
            base_value = self.explainer.expected_value
        
        plt.figure(figsize=(10, 8))
        shap.decision_plot(base_value, shap_vals[employee_idx, :],
                           X.iloc[employee_idx, :], feature_names=self.feature_names,
                           show=False)
        plt.title(f'员工 {employee_idx+1} - SHAP决策图', fontsize=12, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def get_top_contributing_features(self, X, employee_idx=0, top_n=10):
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        if self.model_name in ['Random Forest', 'XGBoost']:
            if isinstance(self.shap_values, list):
                shap_vals = self.shap_values[1]
            else:
                shap_vals = self.shap_values
        else:
            shap_vals = self.shap_values
        
        employee_shap = shap_vals[employee_idx, :]
        
        contribution_df = pd.DataFrame({
            'Feature': self.feature_names,
            'SHAP_Value': employee_shap,
            'Feature_Value': X.iloc[employee_idx, :].values
        })
        
        contribution_df['Abs_SHAP'] = abs(contribution_df['SHAP_Value'])
        contribution_df = contribution_df.sort_values('Abs_SHAP', ascending=False).head(top_n)
        contribution_df = contribution_df.drop('Abs_SHAP', axis=1)
        
        return contribution_df
    
    def print_employee_explanation(self, X, employee_idx=0, risk_prob=None, top_n=8):
        print(f"\n{'='*70}")
        print(f"员工 {employee_idx+1} - 离职风险预测解释")
        print(f"{'='*70}")
        
        if risk_prob is not None:
            risk_level = "高风险" if risk_prob > 0.5 else "中等风险" if risk_prob > 0.3 else "低风险"
            print(f"预测离职概率: {risk_prob:.2%} ({risk_level})")
        
        print(f"\n前{top_n}个影响因素:")
        print(f"{'-'*70}")
        print(f"{'特征':<35} {'特征值':<12} {'影响方向':<10} {'影响程度':<10}")
        print(f"{'-'*70}")
        
        contribution_df = self.get_top_contributing_features(X, employee_idx, top_n=top_n)
        
        for _, row in contribution_df.iterrows():
            direction = "↑ 增加风险" if row['SHAP_Value'] > 0 else "↓ 降低风险"
            print(f"{row['Feature']:<35} {row['Feature_Value']:<12.4f} {direction:<10} {abs(row['SHAP_Value']):.4f}")
        
        print(f"{'='*70}")
        
        return contribution_df
    
    def plot_feature_dependence(self, X, feature_name, save_path=None):
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        if self.model_name in ['Random Forest', 'XGBoost']:
            if isinstance(self.shap_values, list):
                shap_vals = self.shap_values[1]
            else:
                shap_vals = self.shap_values
        else:
            shap_vals = self.shap_values
        
        plt.figure(figsize=(10, 6))
        shap.dependence_plot(feature_name, shap_vals, X, 
                             feature_names=self.feature_names, show=False)
        plt.title(f'{feature_name} - 特征依赖图', fontsize=12, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()


if __name__ == "__main__":
    from data_generator import generate_hr_data
    from feature_engineering import FeatureEngineering
    from model_training import ModelTrainer
    
    df = generate_hr_data(num_samples=500)
    
    fe = FeatureEngineering()
    df_enhanced = fe.create_additional_features(df)
    X_processed, y = fe.fit_transform(df_enhanced)
    
    trainer = ModelTrainer()
    X_train, X_test, y_train, y_test = trainer.train_test_split(X_processed, y)
    
    xgb_params = {'n_estimators': [50], 'max_depth': [3], 'learning_rate': [0.1], 
                  'subsample': [0.8], 'colsample_bytree': [0.8]}
    trainer.train_xgboost(X_train, y_train, X_test, y_test, param_grid=xgb_params)
    
    print("\n初始化SHAP解释器...")
    explainer = SHAPExplainer(trainer.models['XGBoost'], 'XGBoost', 
                              fe.get_feature_names(), X_train)
    
    X_sample = X_test.head(10).copy()
    explainer.compute_shap_values(X_sample)
    
    explainer.print_employee_explanation(X_sample, employee_idx=0)
    
    contribution_df = explainer.get_top_contributing_features(X_sample, employee_idx=0)
    print("\n关键贡献特征:")
    print(contribution_df)
