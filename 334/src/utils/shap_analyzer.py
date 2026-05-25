import numpy as np
import shap
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


class ShapAnalyzer:
    def __init__(self, xgb_model, feature_names=None):
        self.xgb_model = xgb_model
        self.feature_names = feature_names
        self.explainer = None
        self.global_shap_values = None
        self.is_initialized_ = False

    def initialize(self, X_background):
        print("\nInitializing SHAP analyzer...")
        
        if isinstance(self.xgb_model.model, list) and len(self.xgb_model.model) > 0:
            base_model = self.xgb_model.model[0]
        else:
            base_model = self.xgb_model.model.estimators_[0]
        
        try:
            self.explainer = shap.TreeExplainer(base_model)
            self.global_shap_values = self.explainer.shap_values(X_background)
        except Exception as e:
            print(f"TreeExplainer failed, using KernelExplainer: {e}")
            background_data = shap.sample(X_background, 100)
            
            def predict_wrapper(X):
                return self.xgb_model.predict(X)
            
            self.explainer = shap.KernelExplainer(predict_wrapper, background_data)
            self.global_shap_values = self.explainer.shap_values(background_data, nsamples=50)
        
        self.is_initialized_ = True
        print("SHAP analyzer initialized successfully.")
        return self

    def get_feature_importance(self, top_n=20, target_index=0):
        if not self.is_initialized_:
            raise RuntimeError("SHAP analyzer must be initialized before use")
        
        shap_vals = self.global_shap_values
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[target_index]
        
        mean_abs_shap = np.mean(np.abs(shap_vals), axis=0)
        
        if len(mean_abs_shap.shape) > 1:
            mean_abs_shap = mean_abs_shap[:, target_index]
        
        feature_names = self.feature_names or [f'feature_{i}' for i in range(len(mean_abs_shap))]
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': mean_abs_shap
        })
        
        importance_df = importance_df.sort_values('importance', ascending=False).reset_index(drop=True)
        
        total_importance = importance_df['importance'].sum()
        if total_importance > 0:
            importance_df['importance_percent'] = (importance_df['importance'] / total_importance * 100).round(2)
        else:
            importance_df['importance_percent'] = 0.0
        
        return importance_df.head(top_n).to_dict('records')

    def get_local_explanation(self, X_single, target_index=0):
        if not self.is_initialized_:
            raise RuntimeError("SHAP analyzer must be initialized before use")
        
        if X_single.ndim == 1:
            X_single = X_single.reshape(1, -1)
        
        shap_values = self.explainer.shap_values(X_single)
        base_value = self.explainer.expected_value
        
        if isinstance(shap_values, list):
            shap_values = shap_values[target_index]
            base_value = base_value[target_index] if isinstance(base_value, list) else base_value
        
        if len(shap_values.shape) > 2:
            shap_values = shap_values[:, :, target_index]
        
        feature_names = self.feature_names or [f'feature_{i}' for i in range(X_single.shape[1])]
        
        local_explanation = []
        for i in range(len(feature_names)):
            local_explanation.append({
                'feature': feature_names[i],
                'value': float(X_single[0, i]),
                'shap_value': float(shap_values[0, i]),
                'impact': 'positive' if shap_values[0, i] > 0 else 'negative'
            })
        
        local_explanation.sort(key=lambda x: abs(x['shap_value']), reverse=True)
        
        return {
            'base_value': float(base_value) if not isinstance(base_value, np.ndarray) else float(base_value[target_index]),
            'explanation': local_explanation
        }

    def get_feature_groups_importance(self, X_single=None):
        feature_names = self.feature_names or []
        
        groups = {
            '宣发与成本': ['promotion_budget', 'competition_avg_budget', 'pre_sales_total'],
            '类型特征': [f for f in feature_names if 'genre' in f],
            '主创团队': ['director_encoded', 'actor_encoded'],
            '档期特征': ['release_season', 'is_holiday', 'is_weekend', 'release_month', 'release_dayofweek'],
            '竞争环境': ['competition_count', 'competition_genre_overlap'],
            '预售数据': ['pre_sales_days', 'pre_sales_growth_rate'],
            '影片属性': ['runtime']
        }
        
        global_importance = self.get_feature_importance(top_n=len(feature_names))
        importance_map = {item['feature']: item['importance'] for item in global_importance}
        
        group_importance = {}
        for group_name, features in groups.items():
            total = 0
            for f in features:
                for feat_name in feature_names:
                    if f in feat_name:
                        total += importance_map.get(feat_name, 0)
            group_importance[group_name] = total
        
        total_all = sum(group_importance.values())
        group_percentages = {}
        for g, v in group_importance.items():
            group_percentages[g] = round(v / total_all * 100, 2) if total_all > 0 else 0
        
        sorted_groups = sorted(group_percentages.items(), key=lambda x: x[1], reverse=True)
        
        result = []
        for rank, (group_name, percentage) in enumerate(sorted_groups, 1):
            result.append({
                'rank': rank,
                'group_name': group_name,
                'importance_percent': percentage
            })
        
        return result

    def analyze_prediction(self, X_struct, target_index=0):
        if X_struct.ndim == 1:
            X_struct = X_struct.reshape(1, -1)
        
        global_importance = self.get_feature_importance(top_n=15, target_index=target_index)
        local_explanation = self.get_local_explanation(X_struct, target_index=target_index)
        group_importance = self.get_feature_groups_importance(X_struct)
        
        return {
            'global_feature_importance': global_importance,
            'local_feature_contribution': local_explanation,
            'feature_group_importance': group_importance
        }
