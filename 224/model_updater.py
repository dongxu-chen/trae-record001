import pandas as pd
import numpy as np
import joblib
import os
import json
from datetime import datetime
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

class ModelUpdater:
    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        self.history_file = os.path.join(model_dir, 'training_history.json')
        self.model_info_file = os.path.join(model_dir, 'model_info.json')
        
        os.makedirs(model_dir, exist_ok=True)
        
        self.history = self._load_history()
        self.model_info = self._load_model_info()
    
    def _load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def _load_model_info(self):
        if os.path.exists(self.model_info_file):
            with open(self.model_info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'current_version': 0,
            'last_updated': None,
            'total_samples_trained': 0,
            'models': {}
        }
    
    def _save_model_info(self):
        with open(self.model_info_file, 'w', encoding='utf-8') as f:
            json.dump(self.model_info, f, indent=2, ensure_ascii=False)
    
    def save_model(self, model, model_name, feature_engineering=None):
        version = self.model_info['current_version'] + 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        model_filename = f'{model_name.replace(" ", "_")}_v{version}_{timestamp}.pkl'
        model_path = os.path.join(self.model_dir, model_filename)
        
        joblib.dump(model, model_path)
        
        fe_filename = f'feature_engineering_v{version}_{timestamp}.pkl'
        fe_path = os.path.join(self.model_dir, fe_filename)
        if feature_engineering:
            joblib.dump(feature_engineering, fe_path)
        
        self.model_info['current_version'] = version
        self.model_info['last_updated'] = datetime.now().isoformat()
        self.model_info['models'][model_name] = {
            'latest_version': version,
            'latest_path': model_path,
            'fe_path': fe_path if feature_engineering else None
        }
        self._save_model_info()
        
        print(f"✓ 模型已保存: {model_path}")
        return model_path, version
    
    def load_model(self, model_name, version=None):
        if model_name not in self.model_info['models']:
            raise ValueError(f"模型 {model_name} 不存在")
        
        if version is None:
            model_path = self.model_info['models'][model_name]['latest_path']
        else:
            model_files = [f for f in os.listdir(self.model_dir) 
                          if f.startswith(model_name.replace(" ", "_")) and f'_v{version}_' in f]
            if not model_files:
                raise ValueError(f"模型 {model_name} 版本 {version} 不存在")
            model_path = os.path.join(self.model_dir, model_files[0])
        
        model = joblib.load(model_path)
        print(f"✓ 已加载模型: {model_path}")
        return model
    
    def load_feature_engineering(self, model_name):
        if model_name not in self.model_info['models']:
            raise ValueError(f"模型 {model_name} 不存在")
        
        fe_path = self.model_info['models'][model_name]['fe_path']
        if fe_path and os.path.exists(fe_path):
            return joblib.load(fe_path)
        return None
    
    def incremental_update(self, model_name, X_new, y_new, X_val=None, y_val=None, 
                          model_type='xgboost', params=None):
        timestamp = datetime.now().isoformat()
        num_samples = len(X_new)
        
        print(f"\n{'='*60}")
        print(f"模型增量更新 - {model_name}")
        print(f"{'='*60}")
        print(f"更新时间: {timestamp}")
        print(f"新增样本数: {num_samples}")
        
        try:
            existing_model = self.load_model(model_name)
            print("✓ 已加载现有模型进行增量学习")
        except:
            print("✗ 未找到现有模型，将创建新模型")
            existing_model = None
        
        if model_type == 'xgboost':
            if existing_model and hasattr(existing_model, 'get_booster'):
                neg_count = (y_new == 0).sum()
                pos_count = (y_new == 1).sum()
                scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
                
                updated_model = XGBClassifier(
                    n_estimators=existing_model.n_estimators,
                    max_depth=existing_model.max_depth,
                    learning_rate=existing_model.learning_rate,
                    subsample=existing_model.subsample,
                    colsample_bytree=existing_model.colsample_bytree,
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric='logloss',
                    scale_pos_weight=scale_pos_weight
                )
                updated_model.fit(X_new, y_new, xgb_model=existing_model.get_booster())
            else:
                default_params = {
                    'n_estimators': 100,
                    'max_depth': 5,
                    'learning_rate': 0.1,
                    'subsample': 0.8,
                    'colsample_bytree': 0.8
                }
                if params:
                    default_params.update(params)
                
                neg_count = (y_new == 0).sum()
                pos_count = (y_new == 1).sum()
                scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
                
                updated_model = XGBClassifier(
                    **default_params,
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric='logloss',
                    scale_pos_weight=scale_pos_weight
                )
                updated_model.fit(X_new, y_new)
        
        elif model_type == 'logistic_regression':
            default_params = {'C': 1.0, 'max_iter': 1000, 'class_weight': 'balanced'}
            if params:
                default_params.update(params)
            updated_model = LogisticRegression(**default_params, random_state=42)
            updated_model.fit(X_new, y_new)
        
        elif model_type == 'random_forest':
            default_params = {'n_estimators': 100, 'max_depth': 10, 'class_weight': 'balanced'}
            if params:
                default_params.update(params)
            updated_model = RandomForestClassifier(**default_params, random_state=42)
            updated_model.fit(X_new, y_new)
        
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
        
        metrics = self._calculate_metrics(y_new, updated_model.predict(X_new), 
                                         updated_model.predict_proba(X_new)[:, 1])
        
        if X_val is not None and y_val is not None:
            val_metrics = self._calculate_metrics(y_val, updated_model.predict(X_val),
                                                   updated_model.predict_proba(X_val)[:, 1])
            metrics = {**metrics, **{f'val_{k}': v for k, v in val_metrics.items()}}
        
        history_entry = {
            'timestamp': timestamp,
            'model_name': model_name,
            'model_type': model_type,
            'num_samples': num_samples,
            'metrics': metrics
        }
        self.history.append(history_entry)
        self._save_history()
        
        self.model_info['total_samples_trained'] += num_samples
        self._save_model_info()
        
        print(f"\n更新完成!")
        print(f"训练集准确率: {metrics['accuracy']:.4f}")
        print(f"训练集 ROC AUC: {metrics['roc_auc']:.4f}")
        
        return updated_model, metrics
    
    def _calculate_metrics(self, y_true, y_pred, y_pred_proba):
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1': f1_score(y_true, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_true, y_pred_proba)
        }
    
    def scheduled_weekly_update(self, model_name, data_loader_func, model_type='xgboost'):
        print("\n" + "="*60)
        print("执行每周模型更新")
        print("="*60)
        
        X_new, y_new = data_loader_func()
        
        updated_model, metrics = self.incremental_update(
            model_name, X_new, y_new, model_type=model_type
        )
        
        return updated_model, metrics
    
    def get_training_history(self, model_name=None):
        if model_name:
            return [h for h in self.history if h['model_name'] == model_name]
        return self.history
    
    def print_history(self, model_name=None):
        history = self.get_training_history(model_name)
        
        print(f"\n{'='*80}")
        print(f"训练历史记录" + (f" - {model_name}" if model_name else ""))
        print(f"{'='*80}")
        print(f"{'序号':<5} {'时间':<20} {'样本数':<10} {'准确率':<10} {'ROC AUC':<10}")
        print(f"{'-'*80}")
        
        for i, h in enumerate(history):
            ts = datetime.fromisoformat(h['timestamp']).strftime('%Y-%m-%d %H:%M')
            print(f"{i+1:<5} {ts:<20} {h['num_samples']:<10} {h['metrics']['accuracy']:.4f}    {h['metrics']['roc_auc']:.4f}")
        
        print(f"{'='*80}")
    
    def list_all_models(self):
        print(f"\n{'='*60}")
        print("已保存的模型列表")
        print(f"{'='*60}")
        
        for model_name, info in self.model_info['models'].items():
            print(f"\n模型: {model_name}")
            print(f"  最新版本: v{info['latest_version']}")
            print(f"  模型路径: {info['latest_path']}")
            print(f"  特征工程: {info['fe_path']}")
        
        print(f"\n总训练样本数: {self.model_info['total_samples_trained']}")
        print(f"最后更新: {self.model_info['last_updated']}")
        print(f"{'='*60}")


if __name__ == "__main__":
    from data_generator import generate_hr_data
    from feature_engineering import FeatureEngineering
    
    updater = ModelUpdater(model_dir='models')
    
    df = generate_hr_data(num_samples=500)
    fe = FeatureEngineering()
    df_enhanced = fe.create_additional_features(df)
    X, y = fe.fit_transform(df_enhanced)
    
    print("第一次训练...")
    model, metrics = updater.incremental_update(
        'Attrition_XGBoost', X, y, model_type='xgboost'
    )
    updater.save_model(model, 'Attrition_XGBoost', fe)
    
    print("\n模拟增量数据...")
    df_new = generate_hr_data(num_samples=200)
    df_new_enhanced = fe.create_additional_features(df_new)
    X_new, y_new = fe.transform(df_new_enhanced)
    
    print("增量更新...")
    updated_model, new_metrics = updater.incremental_update(
        'Attrition_XGBoost', X_new, y_new, model_type='xgboost'
    )
    updater.save_model(updated_model, 'Attrition_XGBoost', fe)
    
    updater.print_history()
    updater.list_all_models()
    
    loaded_model = updater.load_model('Attrition_XGBoost')
    print(f"\n加载模型预测测试: {loaded_model.predict(X.head(3))}")
