import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple
from scipy.integrate import trapezoid


class DetectionEvaluator:
    def __init__(self):
        self._results = {}

    def compute_roc(self, scores: np.ndarray, ground_truth: np.ndarray) -> Dict:
        y_true = ground_truth.flatten().astype(int)
        y_scores = scores.flatten()

        sorted_indices = np.argsort(-y_scores)
        sorted_labels = y_true[sorted_indices]

        n_pos = np.sum(y_true == 1)
        n_neg = np.sum(y_true == 0)

        if n_pos == 0 or n_neg == 0:
            return {
                'fpr': np.array([0, 1]),
                'tpr': np.array([0, 1]),
                'thresholds': np.array([np.inf, -np.inf]),
                'auc': 0.5
            }

        tpr_list = [0.0]
        fpr_list = [0.0]
        thresholds = [y_scores[sorted_indices[0]] + 1]

        tp = 0
        fp = 0

        for i in range(len(sorted_labels)):
            if sorted_labels[i] == 1:
                tp += 1
            else:
                fp += 1

            tpr_list.append(tp / n_pos)
            fpr_list.append(fp / n_neg)
            if i < len(sorted_labels) - 1:
                thresholds.append(y_scores[sorted_indices[i]])
            else:
                thresholds.append(y_scores[sorted_indices[i]] - 1)

        fpr = np.array(fpr_list)
        tpr = np.array(tpr_list)
        thresholds = np.array(thresholds)

        auc = float(trapezoid(tpr, fpr))

        return {
            'fpr': fpr,
            'tpr': tpr,
            'thresholds': thresholds,
            'auc': auc
        }

    def compute_metrics_at_threshold(self, scores: np.ndarray, ground_truth: np.ndarray,
                                      threshold: float) -> Dict:
        y_true = ground_truth.flatten().astype(int)
        y_pred = (scores.flatten() > threshold).astype(int)

        tp = np.sum((y_pred == 1) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        fn = np.sum((y_pred == 0) & (y_true == 1))
        tn = np.sum((y_pred == 0) & (y_true == 0))

        precision = tp / (tp + fp + 1e-10)
        recall = tp / (tp + fn + 1e-10)
        f1 = 2 * precision * recall / (precision + recall + 1e-10)
        accuracy = (tp + tn) / (tp + fp + fn + tn + 1e-10)
        specificity = tn / (tn + fp + 1e-10)
        false_alarm_rate = fp / (fp + tn + 1e-10)

        return {
            'threshold': threshold,
            'tp': int(tp),
            'fp': int(fp),
            'fn': int(fn),
            'tn': int(tn),
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'accuracy': accuracy,
            'specificity': specificity,
            'false_alarm_rate': false_alarm_rate
        }

    def compute_optimal_threshold(self, scores: np.ndarray, ground_truth: np.ndarray,
                                   method: str = 'youden') -> Dict:
        roc_data = self.compute_roc(scores, ground_truth)
        fpr = roc_data['fpr']
        tpr = roc_data['tpr']
        thresholds = roc_data['thresholds']

        if method == 'youden':
            youden_j = tpr - fpr
            optimal_idx = np.argmax(youden_j)
        elif method == 'f1':
            precision = tpr / (tpr + fpr + 1e-10)
            f1 = 2 * precision * tpr / (precision + tpr + 1e-10)
            optimal_idx = np.argmax(f1)
        elif method == 'min_dist':
            dist = np.sqrt(fpr ** 2 + (1 - tpr) ** 2)
            optimal_idx = np.argmin(dist)
        elif method == 'far_001':
            far_mask = fpr <= 0.01
            if np.any(far_mask):
                optimal_idx = np.where(far_mask)[0][-1]
            else:
                optimal_idx = 0
        elif method == 'far_01':
            far_mask = fpr <= 0.1
            if np.any(far_mask):
                optimal_idx = np.where(far_mask)[0][-1]
            else:
                optimal_idx = 0
        else:
            raise ValueError(f"Unknown method: {method}")

        optimal_threshold = thresholds[optimal_idx]
        metrics = self.compute_metrics_at_threshold(scores, ground_truth, optimal_threshold)

        return {
            'optimal_threshold': optimal_threshold,
            'method': method,
            'metrics': metrics,
            'optimal_tpr': tpr[optimal_idx],
            'optimal_fpr': fpr[optimal_idx]
        }

    def compute_full_evaluation(self, scores: np.ndarray, ground_truth: np.ndarray,
                                 name: str = 'detector') -> Dict:
        roc_data = self.compute_roc(scores, ground_truth)

        optimal_results = {}
        for method in ['youden', 'f1', 'min_dist', 'far_001', 'far_01']:
            optimal_results[method] = self.compute_optimal_threshold(scores, ground_truth, method)

        threshold_95 = np.percentile(scores, 95)
        threshold_99 = np.percentile(scores, 99)
        metrics_95 = self.compute_metrics_at_threshold(scores, ground_truth, threshold_95)
        metrics_99 = self.compute_metrics_at_threshold(scores, ground_truth, threshold_99)

        y_true = ground_truth.flatten().astype(int)
        y_scores = scores.flatten()

        bg_scores = y_scores[y_true == 0]
        anom_scores = y_scores[y_true == 1]

        separability = {
            'bg_mean': float(np.mean(bg_scores)) if len(bg_scores) > 0 else 0,
            'bg_std': float(np.std(bg_scores)) if len(bg_scores) > 0 else 0,
            'anom_mean': float(np.mean(anom_scores)) if len(anom_scores) > 0 else 0,
            'anom_std': float(np.std(anom_scores)) if len(anom_scores) > 0 else 0,
            'separation_ratio': 0.0
        }
        if len(bg_scores) > 0 and len(anom_scores) > 0:
            sep = (separability['anom_mean'] - separability['bg_mean'])
            pooled_std = np.sqrt(separability['bg_std'] ** 2 + separability['anom_std'] ** 2)
            separability['separation_ratio'] = sep / (pooled_std + 1e-10)

        result = {
            'name': name,
            'roc': roc_data,
            'auc': roc_data['auc'],
            'optimal': optimal_results,
            'metrics_p95': metrics_95,
            'metrics_p99': metrics_99,
            'separability': separability
        }

        self._results[name] = result
        return result

    def compare_detectors(self, names: Optional[List[str]] = None) -> Dict:
        if names is None:
            names = list(self._results.keys())

        comparison = {}
        for name in names:
            if name in self._results:
                r = self._results[name]
                comparison[name] = {
                    'auc': r['auc'],
                    'optimal_youden_threshold': r['optimal']['youden']['optimal_threshold'],
                    'optimal_youden_f1': r['optimal']['youden']['metrics']['f1'],
                    'p95_precision': r['metrics_p95']['precision'],
                    'p95_recall': r['metrics_p95']['recall'],
                    'p95_f1': r['metrics_p95']['f1'],
                    'separation_ratio': r['separability']['separation_ratio']
                }

        return comparison


class EvaluationVisualizer:
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        self.figsize = figsize

    def plot_roc_curve(self, roc_data: Dict, ax=None, title: str = "ROC Curve",
                        label: Optional[str] = None, color: Optional[str] = None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        fpr = roc_data['fpr']
        tpr = roc_data['tpr']
        auc_val = roc_data['auc']

        lbl = label or f'ROC (AUC = {auc_val:.4f})'
        ax.plot(fpr, tpr, label=lbl, linewidth=2, color=color)
        ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5)
        ax.set_xlim([-0.02, 1.02])
        ax.set_ylim([-0.02, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title(title)
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        return ax

    def plot_roc_comparison(self, results: Dict[str, Dict], ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        colors = plt.cm.Set1(np.linspace(0, 1, len(results)))
        for (name, result), color in zip(results.items(), colors):
            roc = result['roc']
            lbl = f"{name} (AUC={result['auc']:.4f})"
            ax.plot(roc['fpr'], roc['tpr'], label=lbl, linewidth=2, color=color)

        ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5)
        ax.set_xlim([-0.02, 1.02])
        ax.set_ylim([-0.02, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('ROC Curve Comparison')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        return ax

    def plot_precision_recall_curve(self, scores: np.ndarray, ground_truth: np.ndarray, ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        evaluator = DetectionEvaluator()
        roc_data = evaluator.compute_roc(scores, ground_truth)
        fpr = roc_data['fpr']
        tpr = roc_data['tpr']

        precision = tpr / (tpr + fpr + 1e-10)

        ax.plot(tpr, precision, linewidth=2)
        ax.set_xlabel('Recall')
        ax.set_ylabel('Precision')
        ax.set_title('Precision-Recall Curve')
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1.05])
        ax.grid(True, alpha=0.3)
        return ax

    def plot_score_distribution(self, scores: np.ndarray, ground_truth: np.ndarray,
                                 threshold: Optional[float] = None, ax=None,
                                 title: Optional[str] = None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        bg_scores = scores[~ground_truth].flatten()
        anom_scores = scores[ground_truth].flatten()

        ax.hist(bg_scores, bins=80, alpha=0.6, label='Background', density=True, color='steelblue')
        ax.hist(anom_scores, bins=80, alpha=0.6, label='Anomaly', density=True, color='orangered')

        if threshold is not None:
            ax.axvline(threshold, color='green', linestyle='--', linewidth=2,
                        label=f'Threshold={threshold:.2f}')

        ax.set_xlabel('RX Score')
        ax.set_ylabel('Density')
        if title is not None:
            ax.set_title(title)
        else:
            ax.set_title('Score Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        return ax

    def plot_detection_map(self, scores: np.ndarray, ground_truth: np.ndarray,
                            threshold: float, ax=None, title: str = "Detection Map"):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        detection = scores > threshold
        y_true = ground_truth.astype(int)
        y_pred = detection.astype(int)

        result_map = np.zeros_like(y_true, dtype=int)
        result_map[(y_true == 0) & (y_pred == 0)] = 0  # TN
        result_map[(y_true == 0) & (y_pred == 1)] = 1  # FP
        result_map[(y_true == 1) & (y_pred == 0)] = 2  # FN
        result_map[(y_true == 1) & (y_pred == 1)] = 3  # TP

        from matplotlib.colors import ListedColormap
        colors_map = ['#2ecc71', '#e74c3c', '#f39c12', '#3498db']
        labels = ['TN', 'FP', 'FN', 'TP']
        cmap = ListedColormap(colors_map)

        im = ax.imshow(result_map, cmap=cmap, vmin=0, vmax=3)

        import matplotlib.patches as mpatches
        patches = [mpatches.Patch(color=colors_map[i], label=labels[i]) for i in range(4)]
        ax.legend(handles=patches, loc='upper right', fontsize=8)
        ax.set_title(title)
        ax.axis('off')
        return ax

    def plot_full_evaluation(self, scores: np.ndarray, ground_truth: np.ndarray,
                              eval_result: Dict, title_prefix: str = ""):
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        self.plot_roc_curve(eval_result['roc'], ax=axes[0, 0],
                             title=f"{title_prefix} ROC Curve")

        self.plot_score_distribution(scores, ground_truth,
                                      threshold=eval_result['optimal']['youden']['optimal_threshold'],
                                      ax=axes[0, 1])

        self.plot_precision_recall_curve(scores, ground_truth, ax=axes[1, 0])

        self.plot_detection_map(scores, ground_truth,
                                 eval_result['optimal']['youden']['optimal_threshold'],
                                 ax=axes[1, 1],
                                 title=f"{title_prefix} Detection Map")

        plt.tight_layout()
        return fig, axes

    def plot_multiscale_roc(self, scale_scores: Dict[str, np.ndarray],
                             ground_truth: np.ndarray, ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        evaluator = DetectionEvaluator()
        colors = plt.cm.viridis(np.linspace(0, 1, len(scale_scores)))

        for (name, scores), color in zip(scale_scores.items(), colors):
            roc = evaluator.compute_roc(scores, ground_truth)
            ax.plot(roc['fpr'], roc['tpr'], label=f'{name} (AUC={roc["auc"]:.4f})',
                     linewidth=2, color=color)

        ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5)
        ax.set_xlim([-0.02, 1.02])
        ax.set_ylim([-0.02, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('Multi-Scale ROC Comparison')
        ax.legend(loc='lower right', fontsize=9)
        ax.grid(True, alpha=0.3)
        return ax

    def plot_classification_map(self, classification_result: Dict, ax=None,
                                 title: str = "Anomaly Classification"):
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        cmap_data = classification_result['classification_map'].copy().astype(float)
        anomaly_mask = classification_result['anomaly_mask']
        confidence = classification_result['confidence_map']

        display = np.full(cmap_data.shape, np.nan)
        display[anomaly_mask] = cmap_data[anomaly_mask]

        from matplotlib.colors import ListedColormap
        colors_cls = ['#e74c3c', '#2ecc71']
        cmap = ListedColormap(colors_cls)

        im = ax.imshow(display, cmap=cmap, vmin=0, vmax=1)
        ax.set_title(f"{title}\n"
                      f"Man-made: {classification_result['n_man_made']}, "
                      f"Natural: {classification_result['n_natural']}")
        ax.axis('off')

        import matplotlib.patches as mpatches
        patches = [
            mpatches.Patch(color='#e74c3c', label='Man-made'),
            mpatches.Patch(color='#2ecc71', label='Natural')
        ]
        ax.legend(handles=patches, loc='upper right', fontsize=9)
        return ax

    def plot_evaluation_summary(self, eval_result: Dict, ax=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))

        metrics_names = ['AUC', 'Precision\n(P95)', 'Recall\n(P95)', 'F1\n(P95)',
                          'Precision\n(Youden)', 'Recall\n(Youden)', 'F1\n(Youden)']

        values = [
            eval_result['auc'],
            eval_result['metrics_p95']['precision'],
            eval_result['metrics_p95']['recall'],
            eval_result['metrics_p95']['f1'],
            eval_result['optimal']['youden']['metrics']['precision'],
            eval_result['optimal']['youden']['metrics']['recall'],
            eval_result['optimal']['youden']['metrics']['f1']
        ]

        colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12',
                   '#2ecc71', '#e74c3c', '#f39c12']

        bars = ax.bar(metrics_names, values, color=colors, alpha=0.8)
        ax.set_ylim([0, 1.1])
        ax.set_ylabel('Score')
        ax.set_title(f"Evaluation Summary: {eval_result['name']}")

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                     f'{val:.3f}', ha='center', va='bottom', fontsize=9)

        ax.grid(True, alpha=0.3, axis='y')
        return ax
