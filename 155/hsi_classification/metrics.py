import numpy as np
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    classification_report,
    precision_score,
    recall_score,
    f1_score
)
import matplotlib.pyplot as plt
import seaborn as sns


class Metrics:
    def __init__(self, y_true, y_pred, class_names=None):
        self.y_true = y_true
        self.y_pred = y_pred
        self.class_names = class_names
        
        if y_true.ndim == 2:
            self.y_true = y_true.flatten()
        if y_pred.ndim == 2:
            self.y_pred = y_pred.flatten()
        
        valid_mask = self.y_true > 0
        self.y_true_valid = self.y_true[valid_mask]
        self.y_pred_valid = self.y_pred[valid_mask]
        
        self.unique_classes = np.unique(self.y_true_valid)
        self.num_classes = len(self.unique_classes)

    def overall_accuracy(self):
        return accuracy_score(self.y_true_valid, self.y_pred_valid)

    def average_accuracy(self):
        class_accs = []
        for cls in self.unique_classes:
            mask = self.y_true_valid == cls
            cls_acc = np.mean(self.y_pred_valid[mask] == cls)
            class_accs.append(cls_acc)
        return np.mean(class_accs), class_accs

    def kappa_coefficient(self):
        return cohen_kappa_score(self.y_true_valid, self.y_pred_valid)

    def precision(self, average='macro'):
        return precision_score(self.y_true_valid, self.y_pred_valid, average=average, zero_division=0)

    def recall(self, average='macro'):
        return recall_score(self.y_true_valid, self.y_pred_valid, average=average, zero_division=0)

    def f1_score(self, average='macro'):
        return f1_score(self.y_true_valid, self.y_pred_valid, average=average, zero_division=0)

    def confusion_matrix(self, normalize=None):
        return confusion_matrix(self.y_true_valid, self.y_pred_valid, normalize=normalize)

    def classification_report(self):
        target_names = self.class_names if self.class_names else [f'Class {c}' for c in self.unique_classes]
        return classification_report(
            self.y_true_valid, 
            self.y_pred_valid, 
            target_names=target_names,
            zero_division=0
        )

    def get_all_metrics(self, return_dict=False):
        oa = self.overall_accuracy()
        aa, class_accs = self.average_accuracy()
        kappa = self.kappa_coefficient()
        precision = self.precision()
        recall = self.recall()
        f1 = self.f1_score()
        
        metrics = {
            'Overall Accuracy (OA)': oa * 100,
            'Average Accuracy (AA)': aa * 100,
            'Kappa Coefficient': kappa,
            'Precision (macro)': precision,
            'Recall (macro)': recall,
            'F1-Score (macro)': f1
        }
        
        for i, cls in enumerate(self.unique_classes):
            class_name = self.class_names[i] if self.class_names else f'Class {cls}'
            metrics[f'{class_name} Accuracy'] = class_accs[i] * 100
        
        if return_dict:
            return metrics
        
        report = "=" * 50 + "\n"
        report += "Classification Metrics Report\n"
        report += "=" * 50 + "\n\n"
        
        for key, value in metrics.items():
            if 'Kappa' in key:
                report += f"{key}: {value:.4f}\n"
            else:
                report += f"{key}: {value:.2f}%\n"
        
        return report

    def plot_confusion_matrix(self, figsize=(10, 8), cmap='Blues', normalize=True, 
                              save_path=None, show=True):
        cm = self.confusion_matrix(normalize='true' if normalize else None)
        target_names = self.class_names if self.class_names else [str(c) for c in self.unique_classes]
        
        plt.figure(figsize=figsize)
        
        fmt = '.2f' if normalize else 'd'
        sns.heatmap(cm, annot=True, fmt=fmt, cmap=cmap, 
                    xticklabels=target_names,
                    yticklabels=target_names)
        
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()

    def plot_classification_map(self, original_shape=None, figsize=(12, 6), 
                                save_path=None, show=True):
        if original_shape is None:
            if self.y_true.ndim == 1:
                raise ValueError("Please provide original_shape for 1D predictions")
            pred_map = self.y_pred
            true_map = self.y_true
        else:
            pred_map = self.y_pred.reshape(original_shape)
            true_map = self.y_true.reshape(original_shape)
        
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        im1 = axes[0].imshow(true_map, cmap='tab20')
        axes[0].set_title('Ground Truth')
        axes[0].axis('off')
        plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)
        
        im2 = axes[1].imshow(pred_map, cmap='tab20')
        axes[1].set_title('Prediction')
        axes[1].axis('off')
        plt.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
