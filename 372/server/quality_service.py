import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import cv2


@dataclass
class QualityIssue:
    type: str
    severity: str
    description: str
    frame_idx: Optional[int] = None
    annotation_id: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class QualityReport:
    total_annotations: int = 0
    issues: List[QualityIssue] = field(default_factory=list)
    overlap_regions: List[dict] = field(default_factory=list)
    missing_regions: List[dict] = field(default_factory=list)
    quality_score: float = 100.0
    details: dict = field(default_factory=dict)


class QualityCheckService:
    _instance = None

    def __init__(self):
        self.min_annotation_size = 50
        self.max_overlap_ratio = 0.3
        self.min_coverage = 0.0

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def check_annotations(
        self,
        annotations: List[dict],
        width: int,
        height: int,
        image: Optional[np.ndarray] = None
    ) -> QualityReport:
        report = QualityReport()
        report.total_annotations = len(annotations)
        
        if len(annotations) == 0:
            report.issues.append(QualityIssue(
                type='empty',
                severity='warning',
                description='No annotations found'
            ))
            report.quality_score = 0
            return report
        
        masks = []
        for ann in annotations:
            mask = self._annotation_to_mask(ann, width, height)
            masks.append(mask)
        
        overlap_issues, overlap_regions = self._check_overlaps(masks, annotations)
        report.issues.extend(overlap_issues)
        report.overlap_regions = overlap_regions
        
        size_issues = self._check_annotation_sizes(masks, annotations, width, height)
        report.issues.extend(size_issues)
        
        boundary_issues = self._check_boundary_issues(annotations, width, height)
        report.issues.extend(boundary_issues)
        
        if image is not None:
            missing_issues, missing_regions = self._detect_missing_regions(
                masks, image, width, height
            )
            report.issues.extend(missing_issues)
            report.missing_regions = missing_regions
        
        label_issues = self._check_labels(annotations)
        report.issues.extend(label_issues)
        
        total_issues = len(report.issues)
        critical_count = len([i for i in report.issues if i.severity == 'critical'])
        warning_count = len([i for i in report.issues if i.severity == 'warning'])
        
        report.quality_score = max(0, 100 - critical_count * 20 - warning_count * 5)
        report.details = {
            'critical_count': critical_count,
            'warning_count': warning_count,
            'total_issues': total_issues
        }
        
        return report

    def _annotation_to_mask(
        self,
        annotation: dict,
        width: int,
        height: int
    ) -> np.ndarray:
        mask = np.zeros((height, width), dtype=np.uint8)
        ann_type = annotation.get('type')
        
        if ann_type == 'polygon':
            points = np.array(
                [(p['x'], p['y']) for p in annotation.get('points', [])],
                dtype=np.int32
            )
            if len(points) >= 3:
                cv2.fillPoly(mask, [points], 255)
        
        elif ann_type == 'rectangle':
            x = int(annotation.get('x', 0))
            y = int(annotation.get('y', 0))
            w = int(annotation.get('width', 0))
            h = int(annotation.get('height', 0))
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
        
        elif ann_type == 'point':
            pos = annotation.get('position', {})
            cx = int(pos.get('x', 0))
            cy = int(pos.get('y', 0))
            r = int(annotation.get('radius', 5))
            cv2.circle(mask, (cx, cy), r, 255, -1)
        
        elif ann_type == 'brush':
            points = np.array(
                [(p['x'], p['y']) for p in annotation.get('points', [])],
                dtype=np.int32
            )
            stroke = int(annotation.get('strokeWidth', 5))
            if len(points) >= 2:
                cv2.polylines(mask, [points], False, 255, stroke)
        
        elif ann_type == 'sam':
            sam_mask = np.array(annotation.get('mask', []), dtype=np.uint8)
            w = annotation.get('width', width)
            h = annotation.get('height', height)
            if len(sam_mask) == w * h:
                sam_mask = sam_mask.reshape((h, w))
                mask[:h, :w] = np.where(sam_mask > 127, 255, 0)
        
        return mask

    def _check_overlaps(
        self,
        masks: List[np.ndarray],
        annotations: List[dict]
    ) -> Tuple[List[QualityIssue], List[dict]]:
        issues = []
        overlap_regions = []
        
        if len(masks) < 2:
            return issues, overlap_regions
        
        for i in range(len(masks)):
            for j in range(i + 1, len(masks)):
                intersection = np.logical_and(masks[i] > 0, masks[j] > 0)
                union = np.logical_or(masks[i] > 0, masks[j] > 0)
                
                if np.any(intersection):
                    iou = np.sum(intersection) / (np.sum(union) + 1e-6)
                    overlap_ratio_i = np.sum(intersection) / (np.sum(masks[i] > 0) + 1e-6)
                    overlap_ratio_j = np.sum(intersection) / (np.sum(masks[j] > 0) + 1e-6)
                    
                    if iou > self.max_overlap_ratio or max(overlap_ratio_i, overlap_ratio_j) > 0.5:
                        severity = 'critical' if iou > 0.5 else 'warning'
                        issues.append(QualityIssue(
                            type='overlap',
                            severity=severity,
                            description=f'Overlap between annotation {i+1} and {j+1} (IoU: {iou:.2f})',
                            annotation_id=annotations[i].get('id'),
                            details={
                                'overlap_with': annotations[j].get('id'),
                                'iou': float(iou),
                                'overlap_ratio_1': float(overlap_ratio_i),
                                'overlap_ratio_2': float(overlap_ratio_j)
                            }
                        ))
                        
                        overlap_regions.append({
                            'annotation_1': annotations[i].get('id'),
                            'annotation_2': annotations[j].get('id'),
                            'iou': float(iou),
                            'overlap_pixels': int(np.sum(intersection))
                        })
        
        return issues, overlap_regions

    def _check_annotation_sizes(
        self,
        masks: List[np.ndarray],
        annotations: List[dict],
        width: int,
        height: int
    ) -> List[QualityIssue]:
        issues = []
        total_pixels = width * height
        min_pixels = max(self.min_annotation_size, int(total_pixels * 0.001))
        
        for idx, mask in enumerate(masks):
            area = np.sum(mask > 0)
            
            if area < min_pixels:
                issues.append(QualityIssue(
                    type='too_small',
                    severity='warning',
                    description=f'Annotation {idx+1} is very small ({area} pixels)',
                    annotation_id=annotations[idx].get('id'),
                    details={'area': int(area), 'min_required': min_pixels}
                ))
            
            if area > total_pixels * 0.9:
                issues.append(QualityIssue(
                    type='too_large',
                    severity='warning',
                    description=f'Annotation {idx+1} covers most of the image ({area/total_pixels*100:.1f}%)',
                    annotation_id=annotations[idx].get('id'),
                    details={'coverage': float(area/total_pixels)}
                ))
        
        return issues

    def _check_boundary_issues(
        self,
        annotations: List[dict],
        width: int,
        height: int
    ) -> List[QualityIssue]:
        issues = []
        
        for idx, ann in enumerate(annotations):
            ann_type = ann.get('type')
            
            if ann_type == 'polygon':
                points = ann.get('points', [])
                for p in points:
                    if p['x'] < 0 or p['x'] >= width or p['y'] < 0 or p['y'] >= height:
                        issues.append(QualityIssue(
                            type='out_of_bounds',
                            severity='critical',
                            description=f'Annotation {idx+1} has points outside image bounds',
                            annotation_id=ann.get('id')
                        ))
                        break
            
            elif ann_type == 'rectangle':
                x = ann.get('x', 0)
                y = ann.get('y', 0)
                w = ann.get('width', 0)
                h = ann.get('height', 0)
                
                if x < 0 or y < 0 or x + w > width or y + h > height:
                    issues.append(QualityIssue(
                        type='out_of_bounds',
                        severity='critical',
                        description=f'Annotation {idx+1} extends outside image bounds',
                        annotation_id=ann.get('id')
                    ))
        
        return issues

    def _detect_missing_regions(
        self,
        masks: List[np.ndarray],
        image: np.ndarray,
        width: int,
        height: int
    ) -> Tuple[List[QualityIssue], List[dict]]:
        issues = []
        missing_regions = []
        
        if len(masks) == 0:
            return issues, missing_regions
        
        annotated_mask = np.zeros((height, width), dtype=np.uint8)
        for mask in masks:
            annotated_mask = np.maximum(annotated_mask, mask)
        
        unannotated_mask = annotated_mask == 0
        
        if np.sum(unannotated_mask) == 0:
            return issues, missing_regions
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        edges = cv2.Canny(gray, 50, 150)
        edges_unannotated = cv2.bitwise_and(edges, edges, mask=unannotated_mask.astype(np.uint8))
        
        edge_density = np.sum(edges_unannotated > 0) / (np.sum(unannotated_mask) + 1e-6)
        
        if edge_density > 0.05 and np.sum(unannotated_mask) > width * height * 0.1:
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                unannotated_mask.astype(np.uint8), connectivity=8
            )
            
            for i in range(1, num_labels):
                component_area = stats[i, cv2.CC_STAT_AREA]
                if component_area > width * height * 0.05:
                    component_mask = (labels == i).astype(np.uint8)
                    component_edges = cv2.bitwise_and(edges, edges, mask=component_mask)
                    
                    if np.sum(component_edges > 0) / component_area > 0.02:
                        x = stats[i, cv2.CC_STAT_LEFT]
                        y = stats[i, cv2.CC_STAT_TOP]
                        w = stats[i, cv2.CC_STAT_WIDTH]
                        h = stats[i, cv2.CC_STAT_HEIGHT]
                        
                        issues.append(QualityIssue(
                            type='potential_missing',
                            severity='warning',
                            description=f'Potential unannotated region at ({x}, {y}) with size {w}x{h}',
                            details={
                                'x': int(x),
                                'y': int(y),
                                'width': int(w),
                                'height': int(h),
                                'area': int(component_area)
                            }
                        ))
                        
                        missing_regions.append({
                            'x': int(x),
                            'y': int(y),
                            'width': int(w),
                            'height': int(h),
                            'area': int(component_area)
                        })
        
        return issues, missing_regions

    def _check_labels(self, annotations: List[dict]) -> List[QualityIssue]:
        issues = []
        
        for idx, ann in enumerate(annotations):
            label = ann.get('label', '')
            if not label or label == 'unlabeled':
                issues.append(QualityIssue(
                    type='missing_label',
                    severity='warning',
                    description=f'Annotation {idx+1} has no label assigned',
                    annotation_id=ann.get('id')
                ))
        
        return issues

    def check_video_annotations(
        self,
        frame_annotations: Dict[int, List[dict]],
        width: int,
        height: int
    ) -> QualityReport:
        all_issues = []
        total_annotations = 0
        
        for frame_idx, annotations in frame_annotations.items():
            if len(annotations) == 0:
                all_issues.append(QualityIssue(
                    type='empty_frame',
                    severity='info',
                    description=f'Frame {frame_idx} has no annotations',
                    frame_idx=frame_idx
                ))
                continue
            
            total_annotations += len(annotations)
            
            frame_report = self.check_annotations(annotations, width, height)
            for issue in frame_report.issues:
                issue.frame_idx = frame_idx
                all_issues.append(issue)
        
        frame_indices = sorted(frame_annotations.keys())
        if len(frame_indices) > 1:
            for i in range(len(frame_indices) - 1):
                current_idx = frame_indices[i]
                next_idx = frame_indices[i + 1]
                
                current_count = len(frame_annotations[current_idx])
                next_count = len(frame_annotations[next_idx])
                
                if abs(current_count - next_count) > max(1, current_count * 0.5):
                    all_issues.append(QualityIssue(
                        type='inconsistent_count',
                        severity='warning',
                        description=f'Annotation count changed significantly between frames {current_idx} and {next_idx} ({current_count} -> {next_count})',
                        details={
                            'frame_1': current_idx,
                            'frame_2': next_idx,
                            'count_1': current_count,
                            'count_2': next_count
                        }
                    ))
        
        report = QualityReport()
        report.total_annotations = total_annotations
        report.issues = all_issues
        
        critical_count = len([i for i in all_issues if i.severity == 'critical'])
        warning_count = len([i for i in all_issues if i.severity == 'warning'])
        report.quality_score = max(0, 100 - critical_count * 15 - warning_count * 3)
        report.details = {
            'critical_count': critical_count,
            'warning_count': warning_count,
            'total_issues': len(all_issues),
            'frames_checked': len(frame_annotations)
        }
        
        return report


quality_check_service = QualityCheckService.get_instance()
