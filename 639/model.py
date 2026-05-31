import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, mean_absolute_error, mean_squared_error
import joblib
import os


class DelayPredictionModel:
    def __init__(self):
        self.delay_model = None
        self.compensation_model = None
        self.range_model = None
        self.feature_names = []
        
    def train_delay_classifier(self, X, y, test_size=0.2, random_state=42):
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        self.delay_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=1,
            min_child_weight=3,
            random_state=random_state,
            eval_metric='logloss',
            use_label_encoder=False
        )
        
        self.delay_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        y_pred = self.delay_model.predict(X_test)
        y_prob = self.delay_model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_prob)
        }
        
        print(f"延误分类模型 - Accuracy: {metrics['accuracy']:.4f}, ROC-AUC: {metrics['roc_auc']:.4f}")
        
        return metrics
    
    def train_compensation_regressor(self, X, y, test_size=0.2, random_state=42):
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        self.compensation_model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=0.1,
            min_child_weight=5,
            random_state=random_state,
            eval_metric='mae'
        )
        
        self.compensation_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        y_pred = self.compensation_model.predict(X_test)
        
        metrics = {
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred))
        }
        
        print(f"赔付回归模型 - MAE: {metrics['mae']:.2f}元, RMSE: {metrics['rmse']:.2f}元")
        
        return metrics
    
    def train_compensation_range_classifier(self, X, y, test_size=0.2, random_state=42):
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        self.range_model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            eval_metric='mlogloss',
            use_label_encoder=False
        )
        
        self.range_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        y_pred = self.range_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"赔付区间分类模型 - Accuracy: {accuracy:.4f}")
        
        return {'accuracy': accuracy}
    
    def train_all(self, X, y_delay, y_compensation, y_range, feature_names):
        self.feature_names = feature_names
        
        print("\n开始训练模型...")
        self.train_delay_classifier(X, y_delay)
        self.train_compensation_regressor(X, y_compensation)
        self.train_compensation_range_classifier(X, y_range)
        print("模型训练完成!\n")
    
    def predict(self, X):
        if self.delay_model is None:
            raise ValueError("模型未训练!")
        
        delay_prob = self.delay_model.predict_proba(X)[:, 1][0]
        is_delayed = int(delay_prob > 0.5)
        
        compensation_amount = self.compensation_model.predict(X)[0]
        compensation_amount = max(0, compensation_amount)
        
        range_pred = self.range_model.predict(X)[0]
        range_prob = self.range_model.predict_proba(X)[0]
        
        return {
            'delay_probability': float(delay_prob),
            'is_delayed': is_delayed,
            'compensation_amount': float(compensation_amount),
            'compensation_range_pred': int(range_pred),
            'compensation_range_probabilities': range_prob.tolist()
        }
    
    def get_feature_importance(self, top_n=15):
        if self.delay_model is None:
            raise ValueError("模型未训练!")
        
        importance = self.delay_model.get_booster().get_score(importance_type='weight')
        importance_df = pd.DataFrame({
            'feature': list(importance.keys()),
            'importance': list(importance.values())
        }).sort_values('importance', ascending=False).head(top_n)
        
        return importance_df
    
    def save(self, model_dir='models'):
        os.makedirs(model_dir, exist_ok=True)
        
        joblib.dump(self.delay_model, f'{model_dir}/delay_model.pkl')
        joblib.dump(self.compensation_model, f'{model_dir}/compensation_model.pkl')
        joblib.dump(self.range_model, f'{model_dir}/range_model.pkl')
        joblib.dump(self.feature_names, f'{model_dir}/feature_names.pkl')
        
        print(f"模型已保存到 {model_dir}/ 目录")
    
    def load(self, model_dir='models'):
        self.delay_model = joblib.load(f'{model_dir}/delay_model.pkl')
        self.compensation_model = joblib.load(f'{model_dir}/compensation_model.pkl')
        self.range_model = joblib.load(f'{model_dir}/range_model.pkl')
        self.feature_names = joblib.load(f'{model_dir}/feature_names.pkl')
        
        print("模型加载成功!")


def get_compensation_range_bounds(range_label):
    ranges = {
        '无赔付': (0, 0),
        '0-150元': (0, 150),
        '150-300元': (150, 300),
        '300-500元': (300, 500),
        '500-800元': (500, 800),
        '800元以上': (800, float('inf'))
    }
    return ranges.get(range_label, (0, 0))


if __name__ == '__main__':
    from data_generator import generate_flight_data
    from feature_engineering import prepare_training_data
    
    print("生成数据...")
    df = generate_flight_data(n_samples=8000)
    
    print("特征工程...")
    X, y_delay, y_minutes, y_comp, y_range, range_enc, fe = prepare_training_data(df)
    
    model = DelayPredictionModel()
    model.train_all(X, y_delay, y_comp, y_range, X.columns.tolist())
    
    model.save()
    
    print("\n特征重要性:")
    print(model.get_feature_importance(top_n=10))
