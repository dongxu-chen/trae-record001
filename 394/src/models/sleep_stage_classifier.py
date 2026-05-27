import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score, cohen_kappa_score
from sklearn.preprocessing import StandardScaler
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.features.feature_engineer import SleepFeatureExtractor, SleepDataGenerator
from src.signal_processing.preprocessing import SignalPreprocessor


class TimeSeriesAugmentor:
    def __init__(self, jitter_sigma=0.03, scaling_sigma=0.1, warping_sigma=0.2, seed=42):
        self.jitter_sigma = jitter_sigma
        self.scaling_sigma = scaling_sigma
        self.warping_sigma = warping_sigma
        self.seed = seed

    def jittering(self, X, sigma=None):
        if sigma is None:
            sigma = self.jitter_sigma
        np.random.seed(self.seed)
        noise = np.random.normal(0, sigma, X.shape)
        return X + noise

    def scaling(self, X, sigma=None):
        if sigma is None:
            sigma = self.scaling_sigma
        np.random.seed(self.seed)
        scaling_factor = np.random.normal(1, sigma, (X.shape[0], 1))
        return X * scaling_factor

    def time_warping(self, X, sigma=None):
        if sigma is None:
            sigma = self.warping_sigma
        np.random.seed(self.seed)
        n_samples, n_features = X.shape
        warp_steps = int(max(1, n_features * sigma))
        warped = np.zeros_like(X)
        for i in range(n_samples):
            start = np.random.randint(0, n_features - warp_steps) if n_features > warp_steps else 0
            warp_strength = np.random.uniform(0.5, 1.5)
            warped[i] = X[i].copy()
            if start + warp_steps <= n_features:
                warped[i, start:start + warp_steps] *= warp_strength
        return warped

    def permutation(self, X, max_segments=5, seg_mode='equal'):
        np.random.seed(self.seed)
        n_samples, n_features = X.shape
        permuted = np.zeros_like(X)
        for i in range(n_samples):
            n_segs = np.random.randint(1, max_segments + 1)
            if seg_mode == 'equal':
                seg_len = n_features // n_segs
                seg_ends = list(range(seg_len, n_features, seg_len))
                if seg_ends[-1] != n_features:
                    seg_ends.append(n_features)
            else:
                seg_ends = sorted(np.random.choice(range(1, n_features), min(n_segs - 1, n_features - 1), replace=False))
                seg_ends.append(n_features)
            seg_ends = [0] + seg_ends
            segments = []
            for j in range(len(seg_ends) - 1):
                segments.append(X[i, seg_ends[j]:seg_ends[j + 1]])
            np.random.shuffle(segments)
            permuted[i] = np.concatenate(segments)
        return permuted

    def magnitude_warping(self, X, sigma=0.2, knot=4):
        np.random.seed(self.seed)
        n_samples, n_features = X.shape
        warped = np.zeros_like(X)
        for i in range(n_samples):
            x = np.arange(n_features)
            x_knots = np.linspace(0, n_features - 1, knot + 2)[1:-1]
            y_knots = np.random.normal(1, sigma, knot)
            if len(x_knots) < 2:
                warped[i] = X[i]
                continue
            x_interp = np.concatenate([[0], x_knots, [n_features - 1]])
            y_interp = np.concatenate([[1], y_knots, [1]])
            warp_curve = np.interp(x, x_interp, y_interp)
            warped[i] = X[i] * warp_curve
        return warped

    def augment(self, X, y, methods=None, n_augmented=1):
        if methods is None:
            methods = ['jittering', 'scaling', 'magnitude_warping']
        X_aug = [X]
        y_aug = [y]
        for _ in range(n_augmented):
            for method in methods:
                if method == 'jittering':
                    X_aug.append(self.jittering(X))
                elif method == 'scaling':
                    X_aug.append(self.scaling(X))
                elif method == 'time_warping':
                    X_aug.append(self.time_warping(X))
                elif method == 'magnitude_warping':
                    X_aug.append(self.magnitude_warping(X))
                elif method == 'permutation':
                    X_aug.append(self.permutation(X))
                y_aug.append(y)
        return np.vstack(X_aug), np.concatenate(y_aug)


class SleepStageClassifier:
    def __init__(self, model_path=None, use_augmentation=True, use_dropout=True):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.class_names = ['清醒', '浅睡', '深睡', 'REM']
        self.use_augmentation = use_augmentation
        self.use_dropout = use_dropout
        self.augmentor = TimeSeriesAugmentor()
        self.training_history = None
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)

    def prepare_dataset(self, raw_data_list):
        all_features = []
        all_labels = []
        preprocessor = SignalPreprocessor()
        extractor = SleepFeatureExtractor()
        for data in raw_data_list:
            hr_clean = preprocessor.process_heart_rate(data['heart_rate'])
            resp_clean = preprocessor.process_respiration(data['respiration'])
            act_clean = preprocessor.process_activity(data['activity'])
            features_df, _ = extractor.extract_all_features(hr_clean, resp_clean, act_clean)
            labels = data['sleep_stages'][:len(features_df)]
            all_features.append(features_df)
            all_labels.extend(labels)
        X = pd.concat(all_features, ignore_index=True)
        y = np.array(all_labels)
        self.feature_names = X.columns.tolist()
        return X, y

    def train(self, X, y, test_size=0.2, random_state=42, n_augment_rounds=2):
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        if self.use_augmentation:
            X_train_aug, y_train_aug = self.augmentor.augment(
                X_train_scaled, y_train,
                methods=['jittering', 'scaling', 'magnitude_warping'],
                n_augmented=n_augment_rounds
            )
        else:
            X_train_aug, y_train_aug = X_train_scaled, y_train

        params = {
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.7,
            'colsample_bytree': 0.7,
            'objective': 'multi:softmax',
            'num_class': 4,
            'random_state': random_state,
            'eval_metric': 'mlogloss',
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'min_child_weight': 5,
            'gamma': 0.1,
            'max_delta_step': 1,
            'early_stopping_rounds': 50,
        }

        if self.use_dropout:
            params.update({
                'subsample': 0.6,
                'colsample_bytree': 0.6,
                'colsample_bylevel': 0.8,
                'colsample_bynode': 0.8,
            })

        self.model = XGBClassifier(**params)

        self.model.fit(
            X_train_aug, y_train_aug,
            eval_set=[(X_test_scaled, y_test)],
            verbose=0
        )

        y_pred = self.model.predict(X_test_scaled)

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
        cv_model = XGBClassifier(**{k: v for k, v in params.items() if k != 'early_stopping_rounds'})
        cv_scores = cross_val_score(cv_model, X_train_aug, y_train_aug, cv=cv, scoring='accuracy')

        y_train_pred = self.model.predict(X_train_scaled)
        train_acc = accuracy_score(y_train, y_train_pred)
        test_acc = accuracy_score(y_test, y_pred)
        overfit_gap = train_acc - test_acc

        results = {
            'test_accuracy': test_acc,
            'train_accuracy': train_acc,
            'overfit_gap': overfit_gap,
            'cv_mean_accuracy': cv_scores.mean(),
            'cv_std_accuracy': cv_scores.std(),
            'macro_f1': f1_score(y_test, y_pred, average='macro'),
            'weighted_f1': f1_score(y_test, y_pred, average='weighted'),
            'cohen_kappa': cohen_kappa_score(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred, target_names=self.class_names),
            'confusion_matrix': confusion_matrix(y_test, y_pred)
        }

        self.training_history = results
        return results

    def predict(self, X):
        if self.model is None:
            raise ValueError("Model not trained or loaded!")
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        return predictions, probabilities

    def predict_with_uncertainty(self, X, n_bootstrap=100):
        if self.model is None:
            raise ValueError("Model not trained or loaded!")
        X_scaled = self.scaler.transform(X)
        base_pred = self.model.predict(X_scaled)
        base_proba = self.model.predict_proba(X_scaled)
        bootstrap_preds = []
        np.random.seed(42)
        for _ in range(n_bootstrap):
            X_aug = self.augmentor.jittering(X_scaled, sigma=0.01)
            pred = self.model.predict(X_aug)
            bootstrap_preds.append(pred)
        bootstrap_preds = np.array(bootstrap_preds)
        prediction_variance = np.var(bootstrap_preds, axis=0)
        confidence = np.mean(bootstrap_preds == base_pred.reshape(1, -1), axis=0)
        return {
            'predictions': base_pred,
            'probabilities': base_proba,
            'prediction_variance': prediction_variance,
            'confidence': confidence
        }

    def predict_single_night(self, hr_data, resp_data, act_data):
        preprocessor = SignalPreprocessor()
        extractor = SleepFeatureExtractor()
        hr_clean = preprocessor.process_heart_rate(hr_data)
        resp_clean = preprocessor.process_respiration(resp_data)
        act_clean = preprocessor.process_activity(act_data)
        features_df, timestamps = extractor.extract_all_features(hr_clean, resp_clean, act_data)
        predictions, probabilities = self.predict(features_df)
        stages = [self.class_names[pred] for pred in predictions]
        return {
            'stages': stages,
            'predictions': predictions,
            'probabilities': probabilities,
            'timestamps': timestamps,
            'features': features_df
        }

    def save_model(self, model_dir='models'):
        os.makedirs(model_dir, exist_ok=True)
        joblib.dump(self.model, os.path.join(model_dir, 'sleep_stage_model.joblib'))
        joblib.dump(self.scaler, os.path.join(model_dir, 'scaler.joblib'))
        joblib.dump(self.feature_names, os.path.join(model_dir, 'feature_names.joblib'))

    def load_model(self, model_dir='models'):
        self.model = joblib.load(os.path.join(model_dir, 'sleep_stage_model.joblib'))
        self.scaler = joblib.load(os.path.join(model_dir, 'scaler.joblib'))
        self.feature_names = joblib.load(os.path.join(model_dir, 'feature_names.joblib'))

    def get_feature_importance(self, importance_type='weight'):
        if self.model is None:
            raise ValueError("Model not trained or loaded!")
        importance_types = ['weight', 'gain', 'cover', 'total_gain', 'total_cover']
        importances = {}
        for imp_type in importance_types:
            try:
                importances[imp_type] = self.model.get_booster().get_score(
                    importance_type=imp_type
                )
            except Exception:
                pass
        if importance_type in importances:
            importance_dict = importances[importance_type]
            if hasattr(self, 'feature_names') and self.feature_names:
                feature_importance = pd.DataFrame({
                    'feature': self.feature_names,
                    'importance': [importance_dict.get(f'f{i}', 0) for i in range(len(self.feature_names))]
                }).sort_values('importance', ascending=False)
            else:
                feature_importance = pd.DataFrame({
                    'feature': list(importance_dict.keys()),
                    'importance': list(importance_dict.values())
                }).sort_values('importance', ascending=False)
        else:
            importance = self.model.feature_importances_
            feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)
        return feature_importance


def train_and_save_model():
    print("=" * 60)
    print("训练带数据增强和Dropout正则化的XGBoost睡眠阶段分类器")
    print("=" * 60)
    print("\n正在生成模拟睡眠数据...")
    generator = SleepDataGenerator(n_subjects=20, n_nights=3, n_epochs=720)
    all_data = generator.generate_all_data()
    print(f"生成了 {len(all_data)} 晚睡眠数据")
    classifier = SleepStageClassifier(use_augmentation=True, use_dropout=True)
    print("正在准备数据集...")
    X, y = classifier.prepare_dataset(all_data)
    print(f"原始数据集大小: {X.shape}, 标签分布: {np.bincount(y)}")
    print("开始训练XGBoost模型 (数据增强 + Dropout正则化)...")
    results = classifier.train(X, y, n_augment_rounds=2)
    print("\n" + "=" * 60)
    print("训练结果:")
    print("=" * 60)
    print(f"训练集准确率: {results['train_accuracy']:.4f}")
    print(f"测试集准确率: {results['test_accuracy']:.4f}")
    print(f"过拟合差距: {results['overfit_gap']:.4f}")
    print(f"交叉验证平均准确率: {results['cv_mean_accuracy']:.4f} (+/- {results['cv_std_accuracy']:.4f})")
    print(f"Macro F1: {results['macro_f1']:.4f}")
    print(f"Weighted F1: {results['weighted_f1']:.4f}")
    print(f"Cohen's Kappa: {results['cohen_kappa']:.4f}")
    print("\n分类报告:")
    print(results['classification_report'])
    if results['overfit_gap'] > 0.05:
        print("\n⚠️ 警告: 检测到过拟合，已启用更强的正则化")
    print("\n正在保存模型...")
    classifier.save_model()
    print("模型已保存到 models/ 目录")
    return classifier


if __name__ == "__main__":
    train_and_save_model()
