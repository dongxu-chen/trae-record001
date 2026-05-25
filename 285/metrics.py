import cv2
import numpy as np
import time


class Metrics:
    @staticmethod
    def precision_recall(pred_edges, gt_edges, tolerance=1):
        pred = (pred_edges > 0).astype(np.uint8)
        gt = (gt_edges > 0).astype(np.uint8)

        if tolerance > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tolerance + 1, 2 * tolerance + 1))
            gt_dilated = cv2.dilate(gt, kernel)
        else:
            gt_dilated = gt

        tp = np.sum(np.logical_and(pred == 1, gt_dilated == 1))
        fp = np.sum(np.logical_and(pred == 1, gt_dilated == 0))
        fn = np.sum(np.logical_and(pred == 0, gt == 1))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'tp': int(tp),
            'fp': int(fp),
            'fn': int(fn)
        }

    @staticmethod
    def ods_score(pred, gts, tolerance=2):
        if pred.ndim == 3:
            pred = pred[..., 0]
        pred_norm = pred.astype(np.float64) / 255.0 if pred.max() > 1 else pred.astype(np.float64)

        if gts.ndim == 2:
            gts = gts[np.newaxis, ...]

        best_f1 = 0
        best_precision = 0
        best_recall = 0
        best_threshold = 0

        kernel_size = 2 * tolerance + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))

        thresholds = np.linspace(0, 1, 50)
        for threshold in thresholds:
            pred_binary = (pred_norm >= threshold).astype(np.float64)

            for gt in gts:
                gt_binary = (gt > 0.1).astype(np.float64) if gt.max() <= 1 else (gt > 25).astype(np.float64)

                gt_dilated = cv2.dilate(gt_binary, kernel)
                pred_dilated = cv2.dilate(pred_binary, kernel)

                tp = np.sum(pred_binary * gt_dilated)
                fp = np.sum(pred_binary * (1 - gt_dilated))
                fn = np.sum(gt_binary * (1 - pred_dilated))

                precision = tp / (tp + fp + 1e-10)
                recall = tp / (tp + fn + 1e-10)
                f1 = 2 * precision * recall / (precision + recall + 1e-10)

                if f1 > best_f1:
                    best_f1 = f1
                    best_precision = precision
                    best_recall = recall
                    best_threshold = threshold

        return {
            'ods_f1': best_f1,
            'ods_precision': best_precision,
            'ods_recall': best_recall,
            'best_threshold': best_threshold
        }

    @staticmethod
    def ois_score(pred, gts, tolerance=2):
        if pred.ndim == 3:
            pred = pred[..., 0]
        pred_norm = pred.astype(np.float64) / 255.0 if pred.max() > 1 else pred.astype(np.float64)

        if gts.ndim == 2:
            gts = gts[np.newaxis, ...]

        kernel_size = 2 * tolerance + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))

        best_total_f1 = 0
        best_thresholds = np.linspace(0, 1, 50)

        for threshold in best_thresholds:
            pred_binary = (pred_norm >= threshold).astype(np.float64)
            total_f1 = 0

            for gt in gts:
                gt_binary = (gt > 0.1).astype(np.float64) if gt.max() <= 1 else (gt > 25).astype(np.float64)

                gt_dilated = cv2.dilate(gt_binary, kernel)
                pred_dilated = cv2.dilate(pred_binary, kernel)

                tp = np.sum(pred_binary * gt_dilated)
                fp = np.sum(pred_binary * (1 - gt_dilated))
                fn = np.sum(gt_binary * (1 - pred_dilated))

                precision = tp / (tp + fp + 1e-10)
                recall = tp / (tp + fn + 1e-10)
                f1 = 2 * precision * recall / (precision + recall + 1e-10)
                total_f1 += f1

            avg_f1 = total_f1 / len(gts)
            if avg_f1 > best_total_f1:
                best_total_f1 = avg_f1

        return {'ois_f1': best_total_f1}

    @staticmethod
    def compute_all_bsds_metrics(pred_edges, gt_boundaries, tolerance=2):
        if gt_boundaries.ndim == 2:
            gt_boundaries = gt_boundaries[np.newaxis, ...]

        ods_result = Metrics.ods_score(pred_edges, gt_boundaries, tolerance)
        ois_result = Metrics.ois_score(pred_edges, gt_boundaries, tolerance)

        return {**ods_result, **ois_result}

    @staticmethod
    def aggregate_bsds_metrics(metrics_list):
        if not metrics_list:
            return {}

        ods_f1 = np.mean([m['ods_f1'] for m in metrics_list])
        ods_precision = np.mean([m['ods_precision'] for m in metrics_list])
        ods_recall = np.mean([m['ods_recall'] for m in metrics_list])
        ois_f1 = np.mean([m['ois_f1'] for m in metrics_list])

        return {
            'ods_f1': ods_f1,
            'ods_precision': ods_precision,
            'ods_recall': ods_recall,
            'ois_f1': ois_f1,
            'num_samples': len(metrics_list)
        }

    @staticmethod
    def measure_time(func, *args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed

    @staticmethod
    def edge_density(edges):
        return np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
