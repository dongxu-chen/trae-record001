import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report

import xgboost as xgb

class ModelTrainer:
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.models = {}
        self.results = {}
        self.best_model = None
        self.best_model_name = None
        
    def train_test_split(self, X, y, test_size=0.2, stratify=True):
        stratify_param = y if stratify else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=stratify_param
        )
        print(f"训练集大小: {X_train.shape}, 测试集大小: {X_test.shape}")
        print(f"训练集离职率: {y_train.mean():.2%}")
        print(f"测试集离职率: {y_test.mean():.2%}")
        return X_train, X_test, y_train, y_test
    
    def train_logistic_regression(self, X_train, y_train, X_test, y_test, param_grid=None):
        print("\n" + "="*60)
        print("训练逻辑回归模型...")
        print("="*60)
        
        if param_grid is None:
            param_grid = {
                'C': [0.01, 0.1, 1, 10, 100],
                'penalty': ['l2'],
                'solver': ['liblinear', 'lbfgs'],
                'max_iter': [1000]
            }
        
        lr = LogisticRegression(random_state=self.random_state, class_weight='balanced')
        grid_search = GridSearchCV(lr, param_grid, cv=5, scoring='roc_auc', n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        best_lr = grid_search.best_estimator_
        y_pred = best_lr.predict(X_test)
        y_pred_proba = best_lr.predict_proba(X_test)[:, 1]
        
        metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)
        
        self.models['Logistic Regression'] = best_lr
        self.results['Logistic Regression'] = {
            'metrics': metrics,
            'best_params': grid_search.best_params_,
            'cv_score': grid_search.best_score_
        }
        
        self._print_results("Logistic Regression", metrics, grid_search.best_params_)
        
        return best_lr, metrics
    
    def train_random_forest(self, X_train, y_train, X_test, y_test, param_grid=None):
        print("\n" + "="*60)
        print("训练随机森林模型...")
        print("="*60)
        
        if param_grid is None:
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5],
                'min_samples_leaf': [1, 2],
                'max_features': ['sqrt', 'log2']
            }
        
        rf = RandomForestClassifier(random_state=self.random_state, class_weight='balanced')
        grid_search = GridSearchCV(rf, param_grid, cv=5, scoring='roc_auc', n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        best_rf = grid_search.best_estimator_
        y_pred = best_rf.predict(X_test)
        y_pred_proba = best_rf.predict_proba(X_test)[:, 1]
        
        metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)
        
        self.models['Random Forest'] = best_rf
        self.results['Random Forest'] = {
            'metrics': metrics,
            'best_params': grid_search.best_params_,
            'cv_score': grid_search.best_score_
        }
        
        self._print_results("Random Forest", metrics, grid_search.best_params_)
        
        return best_rf, metrics
    
    def train_xgboost(self, X_train, y_train, X_test, y_test, param_grid=None):
        print("\n" + "="*60)
        print("训练XGBoost模型...")
        print("="*60)
        
        neg_count = (y_train == 0).sum()
        pos_count = (y_train == 1).sum()
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
        print(f"样本平衡 - 留存: {neg_count}, 离职: {pos_count}, scale_pos_weight: {scale_pos_weight:.2f}")
        
        if param_grid is None:
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.2],
                'subsample': [0.8, 1.0],
                'colsample_bytree': [0.8, 1.0]
            }
        
        xgb_model = xgb.XGBClassifier(
            random_state=self.random_state,
            use_label_encoder=False,
            eval_metric='logloss',
            objective='binary:logistic',
            scale_pos_weight=scale_pos_weight
        )
        
        grid_search = GridSearchCV(xgb_model, param_grid, cv=5, scoring='roc_auc', n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        best_xgb = grid_search.best_estimator_
        y_pred = best_xgb.predict(X_test)
        y_pred_proba = best_xgb.predict_proba(X_test)[:, 1]
        
        metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)
        
        self.models['XGBoost'] = best_xgb
        self.results['XGBoost'] = {
            'metrics': metrics,
            'best_params': grid_search.best_params_,
            'cv_score': grid_search.best_score_
        }
        
        self._print_results("XGBoost", metrics, grid_search.best_params_)
        
        return best_xgb, metrics
    
    def train_all_models(self, X_train, y_train, X_test, y_test):
        print("开始训练所有模型...")
        
        self.train_logistic_regression(X_train, y_train, X_test, y_test)
        self.train_random_forest(X_train, y_train, X_test, y_test)
        self.train_xgboost(X_train, y_train, X_test, y_test)
        
        self._find_best_model()
        
        return self.models, self.results
    
    def _calculate_metrics(self, y_true, y_pred, y_pred_proba):
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred),
            'recall': recall_score(y_true, y_pred),
            'f1': f1_score(y_true, y_pred),
            'roc_auc': roc_auc_score(y_true, y_pred_proba)
        }
    
    def _print_results(self, model_name, metrics, best_params):
        print(f"\n{model_name} 模型结果:")
        print(f"准确率 (Accuracy): {metrics['accuracy']:.4f}")
        print(f"精确率 (Precision): {metrics['precision']:.4f}")
        print(f"召回率 (Recall): {metrics['recall']:.4f}")
        print(f"F1分数: {metrics['f1']:.4f}")
        print(f"ROC AUC: {metrics['roc_auc']:.4f}")
        print(f"最佳参数: {best_params}")
    
    def _find_best_model(self):
        best_roc_auc = 0
        for model_name, result in self.results.items():
            if result['metrics']['roc_auc'] > best_roc_auc:
                best_roc_auc = result['metrics']['roc_auc']
                self.best_model_name = model_name
                self.best_model = self.models[model_name]
        
        print("\n" + "="*60)
        print(f"最佳模型: {self.best_model_name} (ROC AUC: {best_roc_auc:.4f})")
        print("="*60)
    
    def compare_models(self):
        comparison = pd.DataFrame({
            model_name: {
                'Accuracy': result['metrics']['accuracy'],
                'Precision': result['metrics']['precision'],
                'Recall': result['metrics']['recall'],
                'F1': result['metrics']['f1'],
                'ROC AUC': result['metrics']['roc_auc'],
                'CV ROC AUC': result['cv_score']
            }
            for model_name, result in self.results.items()
        }).T
        
        print("\n" + "="*60)
        print("模型性能对比")
        print("="*60)
        print(comparison.round(4))
        
        return comparison
    
    def get_feature_importance(self, model_name, feature_names):
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 未训练")
        
        model = self.models[model_name]
        
        if model_name == 'Logistic Regression':
            importance = np.abs(model.coef_[0])
        else:
            importance = model.feature_importances_
        
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importance
        }).sort_values('Importance', ascending=False).reset_index(drop=True)
        
        return importance_df
    
    def plot_confusion_matrix(self, model_name, X_test, y_test, save_path=None):
        model = self.models[model_name]
        y_pred = model.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['留存', '离职'], 
                    yticklabels=['留存', '离职'])
        plt.title(f'{model_name} - 混淆矩阵')
        plt.ylabel('真实值')
        plt.xlabel('预测值')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return cm
    
    def predict_employee_risk(self, model_name, X_employee):
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 未训练")
        
        model = self.models[model_name]
        risk_prob = model.predict_proba(X_employee)[:, 1]
        
        return risk_prob


if __name__ == "__main__":
    from data_generator import generate_hr_data
    from feature_engineering import FeatureEngineering
    
    df = generate_hr_data(num_samples=2000)
    
    fe = FeatureEngineering(scaling_method='standard')
    df_enhanced = fe.create_additional_features(df)
    X_processed, y = fe.fit_transform(df_enhanced)
    
    trainer = ModelTrainer(random_state=42)
    X_train, X_test, y_train, y_test = trainer.train_test_split(X_processed, y)
    
    models, results = trainer.train_all_models(X_train, y_train, X_test, y_test)
    
    comparison = trainer.compare_models()
    
    feature_importance = trainer.get_feature_importance('XGBoost', fe.get_feature_names())
    print("\n前10个最重要特征:")
    print(feature_importance.head(10))
