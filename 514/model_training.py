import pandas as pd
import numpy as np
import pickle
import os
from typing import Tuple, List, Dict, Optional
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score
)
from sklearn.preprocessing import StandardScaler
import xgboost as xgb


class UserActivityModel:
    def __init__(self, model_dir: str = 'models'):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.feature_cols = None
        self.class_mapping = {0: 'low', 1: 'medium', 2: 'high'}
        self.class_mapping_inv = {'low': 0, 'medium': 1, 'high': 2}

        os.makedirs(model_dir, exist_ok=True)

    def prepare_data(
        self,
        feature_matrix: pd.DataFrame,
        feature_cols: List[str]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        X = feature_matrix[feature_cols].fillna(0).values
        y = feature_matrix['active_level_encoded'].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.feature_cols = feature_cols

        return X_train_scaled, X_test_scaled, y_train, y_test

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        params: Optional[Dict] = None
    ) -> xgb.XGBClassifier:
        if params is None:
            params = {
                'n_estimators': 200,
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'min_child_weight': 3,
                'gamma': 0.1,
                'reg_alpha': 0.1,
                'reg_lambda': 1.0,
                'objective': 'multi:softprob',
                'num_class': 3,
                'random_state': 42,
                'eval_metric': 'mlogloss',
                'early_stopping_rounds': 50,
                'verbose': 0
            }

        self.model = xgb.XGBClassifier(**params)

        X_train_split, X_val, y_train_split, y_val = train_test_split(
            X_train, y_train, test_size=0.15, random_state=42, stratify=y_train
        )

        self.model.fit(
            X_train_split, y_train_split,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        return self.model

    def cross_validate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv: int = 5
    ) -> Dict:
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

        cv_params = {
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'objective': 'multi:softprob',
            'num_class': 3,
            'random_state': 42,
            'eval_metric': 'mlogloss',
        }
        cv_model = xgb.XGBClassifier(**cv_params)

        cv_scores = cross_val_score(
            cv_model, X_train, y_train, cv=skf, scoring='f1_weighted'
        )

        return {
            'cv_scores': cv_scores,
            'mean_score': cv_scores.mean(),
            'std_score': cv_scores.std()
        }

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        f1_weighted = f1_score(y_test, y_pred, average='weighted')
        precision_weighted = precision_score(y_test, y_pred, average='weighted')
        recall_weighted = recall_score(y_test, y_pred, average='weighted')

        class_report = classification_report(
            y_test, y_pred,
            target_names=['low', 'medium', 'high'],
            output_dict=True
        )

        conf_matrix = confusion_matrix(y_test, y_pred)

        feature_importance = pd.DataFrame({
            'feature': self.feature_cols,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        return {
            'accuracy': accuracy,
            'f1_weighted': f1_weighted,
            'precision_weighted': precision_weighted,
            'recall_weighted': recall_weighted,
            'classification_report': class_report,
            'confusion_matrix': conf_matrix,
            'feature_importance': feature_importance,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba
        }

    def predict(
        self,
        feature_matrix: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        if feature_cols is None:
            feature_cols = self.feature_cols

        X = feature_matrix[feature_cols].fillna(0).values
        X_scaled = self.scaler.transform(X)

        y_pred = self.model.predict(X_scaled)
        y_pred_proba = self.model.predict_proba(X_scaled)

        result_df = feature_matrix[['user_id']].copy()
        result_df['predicted_level'] = [self.class_mapping[p] for p in y_pred]
        result_df['prob_low'] = y_pred_proba[:, 0]
        result_df['prob_medium'] = y_pred_proba[:, 1]
        result_df['prob_high'] = y_pred_proba[:, 2]

        result_df['confidence'] = y_pred_proba.max(axis=1)

        result_df['activity_score'] = (
            result_df['prob_low'] * 25 +
            result_df['prob_medium'] * 50 +
            result_df['prob_high'] * 85
        )

        return result_df

    def predict_future_7d(
        self,
        feature_matrix: pd.DataFrame,
        feature_cols: List[str],
        future_days: int = 7
    ) -> pd.DataFrame:
        base_predictions = self.predict(feature_matrix, feature_cols)

        last_date = pd.Timestamp.now().normalize()
        future_dates = [
            last_date + pd.Timedelta(days=i + 1)
            for i in range(future_days)
        ]

        future_predictions = []
        for _, row in base_predictions.iterrows():
            user_id = row['user_id']
            base_score = row['activity_score']

            for day_idx, date in enumerate(future_dates):
                day_factor = np.random.uniform(0.85, 1.15)
                trend_factor = 1 - 0.01 * day_idx
                daily_score = base_score * day_factor * trend_factor
                daily_score = max(0, min(100, daily_score))

                if daily_score >= 60:
                    level = 'high'
                elif daily_score >= 25:
                    level = 'medium'
                else:
                    level = 'low'

                future_predictions.append({
                    'user_id': user_id,
                    'date': date,
                    'activity_score': round(daily_score, 1),
                    'predicted_level': level,
                })

        return pd.DataFrame(future_predictions)

    def save_model(self, model_name: str = 'user_activity_model'):
        model_path = os.path.join(self.model_dir, f'{model_name}.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_cols': self.feature_cols,
                'class_mapping': self.class_mapping,
            }, f)
        print(f"模型已保存至: {model_path}")

    def load_model(self, model_name: str = 'user_activity_model'):
        model_path = os.path.join(self.model_dir, f'{model_name}.pkl')
        with open(model_path, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.scaler = data['scaler']
        self.feature_cols = data['feature_cols']
        self.class_mapping = data['class_mapping']
        print(f"模型已从 {model_path} 加载")

    def get_feature_importance(self, top_k: int = 20) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("模型尚未训练，请先调用 train() 方法")

        importance_df = pd.DataFrame({
            'feature': self.feature_cols,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        return importance_df.head(top_k)


def train_full_pipeline(
    feature_matrix: pd.DataFrame,
    feature_cols: List[str],
    model_dir: str = 'models'
) -> Tuple[UserActivityModel, Dict]:
    print("=" * 60)
    print("开始训练用户活跃度预测模型")
    print("=" * 60)

    model = UserActivityModel(model_dir=model_dir)

    print("\n1. 准备训练数据...")
    X_train, X_test, y_train, y_test = model.prepare_data(feature_matrix, feature_cols)
    print(f"训练集大小: {X_train.shape}, 测试集大小: {X_test.shape}")

    print("\n2. 训练XGBoost模型...")
    model.train(X_train, y_train)
    print("模型训练完成")

    print("\n3. 交叉验证...")
    cv_results = model.cross_validate(X_train, y_train, cv=5)
    print(f"5折交叉验证 F1 分数: {cv_results['mean_score']:.4f} (±{cv_results['std_score']:.4f})")

    print("\n4. 模型评估...")
    eval_results = model.evaluate(X_test, y_test)
    print(f"测试集准确率: {eval_results['accuracy']:.4f}")
    print(f"测试集加权 F1: {eval_results['f1_weighted']:.4f}")

    print("\n分类报告:")
    print(classification_report(
        y_test, eval_results['y_pred'],
        target_names=['low', 'medium', 'high']
    ))

    print("\n5. 保存模型...")
    model.save_model()

    print("\n" + "=" * 60)
    print("模型训练完成!")
    print("=" * 60)

    return model, eval_results


if __name__ == '__main__':
    from data_generator import generate_all_data
    from feature_engineering import build_feature_matrix, select_features_by_importance

    print("生成模拟数据...")
    behavior_df, labels_df, channel_df, user_cycles = generate_all_data(n_users=200, history_days=30)

    print("构建特征矩阵...")
    feature_matrix, all_feature_cols = build_feature_matrix(behavior_df, labels_df, user_cycles=user_cycles, channel_df=channel_df)

    print("特征选择...")
    top_features = select_features_by_importance(feature_matrix, all_feature_cols, top_k=30)

    model, eval_results = train_full_pipeline(feature_matrix, top_features)

    print("\nTop 10 重要特征:")
    print(eval_results['feature_importance'].head(10))

    print("\n预测示例:")
    predictions = model.predict(feature_matrix, top_features)
    print(predictions.head(10))
