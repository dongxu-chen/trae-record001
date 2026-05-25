import os
import numpy as np
import pandas as pd
import tensorflow as tf
import config


class FeatureImportanceAnalyzer:
    def __init__(self, model, feature_names=None):
        self.model = model
        self.feature_names = feature_names or [
            'title', 'tags', 'category', 'user_id', 
            'user_history', 'duration', 'cover'
        ]
        self.importance_scores = {}
        self.permutation_importance = {}
        
    def analyze_linear_weights(self, target='click'):
        importance = {}
        
        if hasattr(self.model, 'linear_embeddings'):
            for feat_name, layer in self.model.linear_embeddings.items():
                weights = layer.get_weights()
                if weights:
                    weight_magnitude = np.mean(np.abs(weights[0]))
                    importance[feat_name] = float(weight_magnitude)
        
        total = sum(importance.values()) if importance else 1
        normalized = {k: v / total for k, v in importance.items()}
        
        self.importance_scores['linear'] = normalized
        return normalized
    
    def permutation_feature_importance(self, features, labels, 
                                       num_permutations=5, target='click'):
        baseline_preds = self.model.predict(features, verbose=0)
        
        if self.model.num_tasks == 1:
            baseline_auc = self._calculate_auc(labels, baseline_preds)
        else:
            target_idx = config.MULTI_TARGET.index(target) if target in config.MULTI_TARGET else 0
            baseline_auc = self._calculate_auc(
                labels[:, target_idx], baseline_preds[:, target_idx]
            )
        
        importance = {}
        
        for feat_name in self.feature_names:
            if feat_name not in features:
                continue
                
            auc_decreases = []
            
            for _ in range(num_permutations):
                permuted_features = features.copy()
                feat_data = permuted_features[feat_name]
                
                if isinstance(feat_data, np.ndarray):
                    permuted_indices = np.random.permutation(len(feat_data))
                    permuted_features[feat_name] = feat_data[permuted_indices]
                
                permuted_preds = self.model.predict(permuted_features, verbose=0)
                
                if self.model.num_tasks == 1:
                    permuted_auc = self._calculate_auc(labels, permuted_preds)
                else:
                    permuted_auc = self._calculate_auc(
                        labels[:, target_idx], permuted_preds[:, target_idx]
                    )
                
                auc_decrease = baseline_auc - permuted_auc
                auc_decreases.append(auc_decrease)
            
            importance[feat_name] = {
                'mean_decrease': float(np.mean(auc_decreases)),
                'std_decrease': float(np.std(auc_decreases)),
                'baseline_auc': float(baseline_auc)
            }
        
        self.permutation_importance[target] = importance
        return importance
    
    def _calculate_auc(self, y_true, y_pred):
        try:
            from sklearn.metrics import roc_auc_score
            return roc_auc_score(y_true, y_pred)
        except:
            return 0.5
    
    def analyze_embedding_variance(self):
        variance_importance = {}
        
        if hasattr(self.model, 'embedding_layers'):
            for feat_name, layer in self.model.embedding_layers.items():
                weights = layer.get_weights()
                if weights:
                    embeddings = weights[0]
                    variance = np.mean(np.var(embeddings, axis=0))
                    variance_importance[feat_name] = float(variance)
        
        total = sum(variance_importance.values()) if variance_importance else 1
        normalized = {k: v / total for k, v in variance_importance.items()}
        
        self.importance_scores['embedding_variance'] = normalized
        return normalized
    
    def combined_importance(self, features=None, labels=None, target='click'):
        linear_importance = self.analyze_linear_weights(target)
        embedding_importance = self.analyze_embedding_variance()
        
        permutation_importance = {}
        if features is not None and labels is not None:
            perm_importance = self.permutation_feature_importance(features, labels, target=target)
            permutation_importance = {
                k: v['mean_decrease'] for k, v in perm_importance.items()
            }
        
        all_features = set(list(linear_importance.keys()) + 
                          list(embedding_importance.keys()) +
                          list(permutation_importance.keys()))
        
        combined = {}
        for feat in all_features:
            scores = []
            if feat in linear_importance:
                scores.append(linear_importance[feat])
            if feat in embedding_importance:
                scores.append(embedding_importance[feat])
            if feat in permutation_importance:
                scores.append(max(0, permutation_importance[feat]))
            
            if scores:
                combined[feat] = float(np.mean(scores))
        
        sorted_features = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        
        self.importance_scores['combined'] = dict(sorted_features)
        return dict(sorted_features)
    
    def get_top_features(self, n=10, method='combined'):
        if method not in self.importance_scores:
            return {}
        
        scores = self.importance_scores[method]
        sorted_features = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_features[:n])
    
    def save_report(self, path, features=None, labels=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        report = {
            'linear_importance': self.analyze_linear_weights(),
            'embedding_variance': self.analyze_embedding_variance(),
            'summary': {}
        }
        
        if features is not None and labels is not None:
            for target in config.MULTI_TARGET[:self.model.num_tasks]:
                report[f'permutation_{target}'] = self.permutation_feature_importance(
                    features, labels, target=target
                )
                report[f'combined_{target}'] = self.combined_importance(
                    features, labels, target=target
                )
        
        report['summary']['top_features_click'] = self.get_top_features(
            config.FEATURE_IMPORTANCE_TOP_N, 
            'combined_click' if 'combined_click' in report else 'linear'
        )
        
        np.save(path, report, allow_pickle=True)
        print(f"Feature importance report saved to {path}")
        
        return report
    
    def print_report(self, target='click'):
        print("=" * 60)
        print(f"Feature Importance Report - Target: {target}")
        print("=" * 60)
        
        print("\n1. Linear Weight Importance:")
        linear = self.importance_scores.get('linear', {})
        for feat, score in sorted(linear.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   {feat:15s}: {score:.4f}")
        
        print("\n2. Embedding Variance Importance:")
        var = self.importance_scores.get('embedding_variance', {})
        for feat, score in sorted(var.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   {feat:15s}: {score:.4f}")
        
        perm_key = f'permutation_{target}'
        if perm_key in self.importance_scores:
            print(f"\n3. Permutation Importance (Target: {target}):")
            perm = self.importance_scores[perm_key]
            for feat, info in sorted(perm.items(), key=lambda x: x[1]['mean_decrease'], reverse=True)[:5]:
                print(f"   {feat:15s}: {info['mean_decrease']:.4f} (±{info['std_decrease']:.4f})")
        
        combined_key = f'combined_{target}'
        if combined_key in self.importance_scores:
            print(f"\n4. Combined Importance (Top {config.FEATURE_IMPORTANCE_TOP_N}):")
            combined = self.importance_scores[combined_key]
            for i, (feat, score) in enumerate(sorted(combined.items(), key=lambda x: x[1], reverse=True)[:config.FEATURE_IMPORTANCE_TOP_N], 1):
                print(f"   {i}. {feat:15s}: {score:.4f}")
        
        print("\n" + "=" * 60)
