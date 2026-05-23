import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (confusion_matrix, precision_score, recall_score, 
                             f1_score, accuracy_score, precision_recall_curve)

class ThresholdOptimizer:
    def __init__(self, model, y_prob, y_true):
        self.model = model
        self.y_prob = y_prob
        self.y_true = y_true
        self.best_threshold = 0.5
        self.threshold_metrics = []
        
        self._compute_all_thresholds()
    
    def _compute_all_thresholds(self):
        thresholds = np.arange(0.1, 0.9, 0.01)
        metrics_list = []
        
        for threshold in thresholds:
            y_pred = (self.y_prob >= threshold).astype(int)
            metrics = self._calculate_metrics(self.y_true, y_pred, threshold)
            metrics_list.append(metrics)
        
        self.threshold_metrics = pd.DataFrame(metrics_list)
    
    def _calculate_metrics(self, y_true, y_pred, threshold):
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (cm[0,0], 0, 0, 0)
        
        return {
            'threshold': threshold,
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1': f1_score(y_true, y_pred, zero_division=0),
            'accuracy': accuracy_score(y_true, y_pred),
            'tp': tp,
            'fp': fp,
            'tn': tn,
            'fn': fn,
            'specificity': tn / (tn + fp) if (tn + fp) > 0 else 0
        }
    
    def find_optimal_threshold(self, metric='f1'):
        if metric == 'f1':
            best_idx = self.threshold_metrics['f1'].idxmax()
        elif metric == 'precision':
            best_idx = self.threshold_metrics['precision'].idxmax()
        elif metric == 'recall':
            best_idx = self.threshold_metrics['recall'].idxmax()
        elif metric == 'balanced':
            self.threshold_metrics['balanced_score'] = (
                self.threshold_metrics['precision'] + self.threshold_metrics['recall']
            ) / 2
            best_idx = self.threshold_metrics['balanced_score'].idxmax()
        else:
            best_idx = self.threshold_metrics['f1'].idxmax()
        
        self.best_threshold = self.threshold_metrics.loc[best_idx, 'threshold']
        
        print(f"\n最佳阈值 (基于{metric}): {self.best_threshold:.2f}")
        self._print_threshold_metrics(self.best_threshold)
        
        return self.best_threshold
    
    def _print_threshold_metrics(self, threshold):
        metrics = self.threshold_metrics.iloc[
            (self.threshold_metrics['threshold'] - threshold).abs().argmin()
        ]
        
        print(f"\n阈值 = {metrics['threshold']:.2f} 时的性能:")
        print(f"  精确率 (Precision): {metrics['precision']:.4f}")
        print(f"  召回率 (Recall): {metrics['recall']:.4f}")
        print(f"  F1 分数: {metrics['f1']:.4f}")
        print(f"  准确率 (Accuracy): {metrics['accuracy']:.4f}")
        print(f"  特异度 (Specificity): {metrics['specificity']:.4f}")
        print(f"  TP={metrics['tp']}, FP={metrics['fp']}, TN={metrics['tn']}, FN={metrics['fn']}")
    
    def evaluate_threshold(self, threshold):
        self._print_threshold_metrics(threshold)
        
        metrics = self.threshold_metrics.iloc[
            (self.threshold_metrics['threshold'] - threshold).abs().argmin()
        ]
        return metrics
    
    def plot_precision_recall_tradeoff(self, save_path=None):
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        ax1 = axes[0]
        ax1.plot(self.threshold_metrics['threshold'], 
                 self.threshold_metrics['precision'], 
                 label='精确率', linewidth=2)
        ax1.plot(self.threshold_metrics['threshold'], 
                 self.threshold_metrics['recall'], 
                 label='召回率', linewidth=2)
        ax1.plot(self.threshold_metrics['threshold'], 
                 self.threshold_metrics['f1'], 
                 label='F1分数', linewidth=2, linestyle='--')
        ax1.axvline(x=self.best_threshold, color='red', linestyle=':', 
                    label=f'最佳阈值={self.best_threshold:.2f}')
        ax1.set_xlabel('分类阈值', fontsize=12)
        ax1.set_ylabel('指标值', fontsize=12)
        ax1.set_title('阈值变化对精确率/召回率/F1的影响', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[1]
        precision, recall, _ = precision_recall_curve(self.y_true, self.y_prob)
        ax2.plot(recall, precision, linewidth=2)
        idx = (np.abs(self.threshold_metrics['threshold'] - self.best_threshold)).argmin()
        best_p = self.threshold_metrics.loc[idx, 'precision']
        best_r = self.threshold_metrics.loc[idx, 'recall']
        ax2.scatter([best_r], [best_p], color='red', s=100, zorder=5,
                   label=f'最佳阈值点 ({best_r:.2f}, {best_p:.2f})')
        ax2.set_xlabel('召回率', fontsize=12)
        ax2.set_ylabel('精确率', fontsize=12)
        ax2.set_title('PR曲线', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_confusion_matrix_at_threshold(self, threshold, save_path=None):
        y_pred = (self.y_prob >= threshold).astype(int)
        cm = confusion_matrix(self.y_true, y_pred)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['预测留存', '预测离职'],
                    yticklabels=['实际留存', '实际离职'], ax=ax)
        ax.set_title(f'混淆矩阵 (阈值 = {threshold:.2f})', fontsize=14, fontweight='bold')
        ax.set_ylabel('实际值', fontsize=12)
        ax.set_xlabel('预测值', fontsize=12)
        
        metrics = self._calculate_metrics(self.y_true, y_pred, threshold)
        info_text = f"精确率: {metrics['precision']:.3f}\n召回率: {metrics['recall']:.3f}\nF1: {metrics['f1']:.3f}"
        plt.figtext(1.3, 0.5, info_text, fontsize=12, 
                    bbox=dict(facecolor='lightgray', alpha=0.5),
                    horizontalalignment='center', verticalalignment='center')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return cm
    
    def interactive_threshold_slider(self):
        print("\n" + "="*70)
        print("阈值调节工具 - 平衡精确率和召回率")
        print("="*70)
        print("\n使用说明:")
        print("  - 提高阈值 → 提高精确率，降低召回率（更少误判离职，但可能漏判）")
        print("  - 降低阈值 → 提高召回率，降低精确率（更多识别离职，但可能误判）")
        print("  - F1分数是精确率和召回率的调和平均")
        print("\n预设阈值方案:")
        
        scenarios = [
            ('保守策略 (高精确率)', 0.7, '尽量减少误判，只对高风险员工预警'),
            ('平衡策略 (F1最优)', self.find_optimal_threshold('f1'), '在精确率和召回率间取得平衡'),
            ('激进策略 (高召回率)', 0.3, '尽量识别所有潜在离职员工，允许更多误判'),
        ]
        
        for name, threshold, desc in scenarios:
            print(f"\n【{name}】阈值 = {threshold:.2f}")
            print(f"  目标: {desc}")
            self.evaluate_threshold(threshold)
        
        print("\n" + "="*70)
        print("自定义阈值测试:")
        print("输入 0.1-0.9 之间的阈值，或输入 'q' 退出")
        print("="*70)
        
        while True:
            user_input = input("\n请输入阈值: ").strip()
            
            if user_input.lower() == 'q':
                break
            
            try:
                threshold = float(user_input)
                if 0.1 <= threshold <= 0.9:
                    self.evaluate_threshold(threshold)
                else:
                    print("请输入 0.1 到 0.9 之间的数值")
            except ValueError:
                print("无效输入，请输入数值或 'q' 退出")
        
        print("\n阈值调节完成!")
        
        return scenarios
    
    def get_threshold_recommendation(self, business_goal='balanced'):
        recommendations = {
            'precision': {
                'threshold': 0.65,
                'description': '高精确率策略 - HR资源有限，只针对高确定离职员工进行干预',
                'use_case': '适用于HR人手紧张、干预成本高的场景'
            },
            'recall': {
                'threshold': 0.35,
                'description': '高召回率策略 - 尽可能识别所有有离职风险的员工',
                'use_case': '适用于离职成本极高、干预成本低的场景'
            },
            'balanced': {
                'threshold': self.find_optimal_threshold('f1'),
                'description': '平衡策略 - 在精确率和召回率之间取得平衡',
                'use_case': '适用于大多数常规业务场景'
            }
        }
        
        rec = recommendations.get(business_goal, recommendations['balanced'])
        
        print(f"\n{'='*70}")
        print(f"阈值建议: {business_goal}")
        print(f"{'='*70}")
        print(f"推荐阈值: {rec['threshold']:.2f}")
        print(f"策略说明: {rec['description']}")
        print(f"适用场景: {rec['use_case']}")
        print(f"{'-'*70}")
        self.evaluate_threshold(rec['threshold'])
        print(f"{'='*70}")
        
        return rec


if __name__ == "__main__":
    from data_generator import generate_hr_data
    from feature_engineering import FeatureEngineering
    from model_training import ModelTrainer
    
    df = generate_hr_data(num_samples=1000)
    
    fe = FeatureEngineering()
    df_enhanced = fe.create_additional_features(df)
    X_processed, y = fe.fit_transform(df_enhanced)
    
    trainer = ModelTrainer()
    X_train, X_test, y_train, y_test = trainer.train_test_split(X_processed, y)
    
    xgb_params = {'n_estimators': [50], 'max_depth': [3], 'learning_rate': [0.1],
                  'subsample': [0.8], 'colsample_bytree': [0.8]}
    trainer.train_xgboost(X_train, y_train, X_test, y_test, param_grid=xgb_params)
    
    model = trainer.models['XGBoost']
    y_prob = model.predict_proba(X_test)[:, 1]
    
    optimizer = ThresholdOptimizer(model, y_prob, y_test)
    
    print("\n找到最佳阈值...")
    optimizer.find_optimal_threshold(metric='f1')
    
    optimizer.plot_precision_recall_tradeoff()
    
    optimizer.get_threshold_recommendation('balanced')
