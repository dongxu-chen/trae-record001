import time
import json
from datetime import datetime, date
from typing import Dict, List, Optional
from contextlib import contextmanager
from models import StatsModel, ReviewModel


class AuditStatistics:
    def __init__(self, video_id: Optional[int] = None):
        self.video_id = video_id
        self.stages: Dict[str, Dict] = {}
        self.total_duration = 0.0
        self.total_api_calls = 0
        self.total_api_errors = 0
        self.total_frames_processed = 0
        self.total_violations_detected = 0
        self.scene_changes_detected = 0
        self.rotated_frames = 0
        self.ocr_preprocessing_stats = None

    @contextmanager
    def measure_stage(self, stage_name: str):
        start_time = time.time()
        stage_data = {
            'start_time': start_time,
            'end_time': None,
            'duration': None,
            'frames_processed': 0,
            'violations_detected': 0,
            'api_calls': 0,
            'api_errors': 0,
            'scene_changes': 0,
            'rotated_frames': 0,
            'details': {}
        }
        
        try:
            yield lambda key, value: stage_data['details'].__setitem__(key, value)
        finally:
            end_time = time.time()
            stage_data['end_time'] = end_time
            stage_data['duration'] = end_time - start_time
            
            self.stages[stage_name] = stage_data
            self.total_duration += stage_data['duration']
            self._save_stage(stage_name, stage_data)

    def update_stage_metrics(self, stage_name: str, frames_processed: int = 0,
                            violations_detected: int = 0, api_calls: int = 0,
                            api_errors: int = 0, scene_changes: int = 0,
                            rotated_frames: int = 0, details: Optional[Dict] = None):
        if stage_name in self.stages:
            stage = self.stages[stage_name]
            stage['frames_processed'] += frames_processed
            stage['violations_detected'] += violations_detected
            stage['api_calls'] += api_calls
            stage['api_errors'] += api_errors
            stage['scene_changes'] += scene_changes
            stage['rotated_frames'] += rotated_frames
            
            if details:
                stage['details'].update(details)
            
            self.total_frames_processed += frames_processed
            self.total_violations_detected += violations_detected
            self.total_api_calls += api_calls
            self.total_api_errors += api_errors
            self.scene_changes_detected += scene_changes
            self.rotated_frames += rotated_frames

    def set_ocr_preprocessing_stats(self, stats: Dict):
        self.ocr_preprocessing_stats = stats

    def _save_stage(self, stage_name: str, stage_data: Dict):
        if self.video_id:
            try:
                StatsModel.create_audit_stat(
                    video_id=self.video_id,
                    stage=stage_name,
                    duration=stage_data['duration'],
                    frames_processed=stage_data['frames_processed'],
                    violations_detected=stage_data['violations_detected'],
                    api_calls=stage_data['api_calls'],
                    api_errors=stage_data['api_errors'],
                    details=json.dumps(stage_data['details'], ensure_ascii=False) if stage_data['details'] else None
                )
            except Exception as e:
                print(f"Warning: Failed to save stage stats: {e}")

    def get_stage_summary(self, stage_name: str) -> Optional[Dict]:
        return self.stages.get(stage_name)

    def get_summary(self) -> Dict:
        summary = {
            'video_id': self.video_id,
            'total_duration': round(self.total_duration, 3),
            'total_api_calls': self.total_api_calls,
            'total_api_errors': self.total_api_errors,
            'total_frames_processed': self.total_frames_processed,
            'total_violations_detected': self.total_violations_detected,
            'scene_changes_detected': self.scene_changes_detected,
            'rotated_frames': self.rotated_frames,
            'stages': {
                name: {
                    'duration': round(data['duration'], 3),
                    'frames_processed': data['frames_processed'],
                    'violations_detected': data['violations_detected'],
                    'api_calls': data['api_calls'],
                    'api_errors': data['api_errors'],
                    'scene_changes': data.get('scene_changes', 0),
                    'rotated_frames': data.get('rotated_frames', 0)
                }
                for name, data in self.stages.items()
            },
            'avg_time_per_frame': round(
                self.total_duration / self.total_frames_processed, 4
            ) if self.total_frames_processed > 0 else 0,
            'violation_rate': round(
                self.total_violations_detected / self.total_frames_processed, 4
            ) if self.total_frames_processed > 0 else 0,
            'frames_per_scene': round(
                self.total_frames_processed / (self.scene_changes_detected + 1), 2
            ) if self.scene_changes_detected > 0 else self.total_frames_processed
        }
        
        if self.ocr_preprocessing_stats:
            summary['ocr_preprocessing'] = self.ocr_preprocessing_stats
        
        return summary

    def update_daily_stats(self, passed: bool = False):
        today = date.today().isoformat()
        try:
            StatsModel.update_daily_stat(
                stat_date=today,
                total_videos=1,
                passed_videos=1 if passed else 0,
                violated_videos=0 if passed else 1,
                total_frames=self.total_frames_processed,
                total_violations=self.total_violations_detected,
                avg_processing_time=self.total_duration,
                total_api_calls=self.total_api_calls
            )
        except Exception as e:
            print(f"Warning: Failed to update daily stats: {e}")

    @staticmethod
    def get_overall_statistics() -> Optional[Dict]:
        base_stats = StatsModel.get_overall_stats()
        
        if not base_stats:
            return None
        
        review_stats = ReviewModel.get_review_stats()
        quality_metrics = ReviewModel.get_quality_metrics()
        
        total_reviewed = review_stats.get('total_violations_reviewed', 0) if review_stats else 0
        false_positives = review_stats.get('false_positives', 0) if review_stats else 0
        
        overall_stats = {
            **base_stats,
            'total_reviewed': total_reviewed,
            'false_positives': false_positives,
            'false_negative': review_stats.get('false_negatives', 0) if review_stats else 0,
            'review_rate': (
                total_reviewed / base_stats.get('total_violations', 1)
                if base_stats.get('total_violations', 0) > 0
                else 0
            ),
            'false_positive_rate': (
                false_positives / total_reviewed
                if total_reviewed > 0
                else 0
            ),
            'quality_metrics': quality_metrics[:10] if quality_metrics else []
        }
        
        return overall_stats

    @staticmethod
    def get_daily_statistics(start_date: str = None, end_date: str = None) -> List[Dict]:
        return StatsModel.get_daily_stats(start_date, end_date)

    @staticmethod
    def get_audit_history(video_id: int = None, stage: str = None,
                         start_date: str = None, end_date: str = None) -> List[Dict]:
        return StatsModel.get_audit_stats(video_id, stage, start_date, end_date)

    @staticmethod
    def get_quality_statistics(start_date: str = None, end_date: str = None) -> Dict:
        review_stats = ReviewModel.get_review_stats(start_date, end_date)
        quality_metrics = ReviewModel.get_quality_metrics(start_date, end_date)
        
        total_reviewed = review_stats.get('total_violations_reviewed', 0) if review_stats else 0
        false_positives = review_stats.get('false_positives', 0) if review_stats else 0
        false_negatives = review_stats.get('false_negatives', 0) if review_stats else 0
        confirmed = review_stats.get('confirmed_violations', 0) if review_stats else 0
        
        precision = confirmed / (confirmed + false_positives) if (confirmed + false_positives) > 0 else 0.0
        recall = confirmed / (confirmed + false_negatives) if (confirmed + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            'review_stats': review_stats,
            'metrics_by_type': quality_metrics,
            'overall_metrics': {
                'total_reviewed': total_reviewed,
                'confirmed': confirmed,
                'false_positives': false_positives,
                'false_negatives': false_negatives,
                'precision': round(precision, 4),
                'recall': round(recall, 4),
                'f1_score': round(f1_score, 4),
                'false_positive_rate': round(false_positives / total_reviewed, 4) if total_reviewed > 0 else 0,
                'avg_review_time': review_stats.get('avg_review_time', 0) if review_stats else 0
            }
        }

    def print_summary(self):
        summary = self.get_summary()
        print("\n" + "="*60)
        print("审核统计报告")
        print("="*60)
        print(f"视频ID: {summary['video_id']}")
        print(f"总处理时间: {summary['total_duration']:.3f} 秒")
        print(f"处理帧数: {summary['total_frames_processed']}")
        print(f"检测到场景切换: {summary['scene_changes_detected']} 次")
        print(f"旋转校正帧数: {summary['rotated_frames']}")
        print(f"检测违规数: {summary['total_violations_detected']}")
        print(f"API调用次数: {summary['total_api_calls']}")
        print(f"API错误次数: {summary['total_api_errors']}")
        print(f"平均每帧处理时间: {summary['avg_time_per_frame']:.4f} 秒")
        print(f"违规率: {summary['violation_rate']:.2%}")
        print(f"平均每场景帧数: {summary['frames_per_scene']}")
        print("\n各阶段详情:")
        print("-"*60)
        for stage_name, stage_data in summary['stages'].items():
            print(f"  {stage_name}:")
            print(f"    耗时: {stage_data['duration']:.3f} 秒")
            print(f"    处理帧数: {stage_data['frames_processed']}")
            print(f"    违规数: {stage_data['violations_detected']}")
            print(f"    API调用: {stage_data['api_calls']}")
            if stage_data.get('scene_changes'):
                print(f"    场景切换: {stage_data['scene_changes']}")
        print("="*60 + "\n")


def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:06.3f}"
    elif minutes > 0:
        return f"{minutes}:{secs:06.3f}"
    else:
        return f"{secs:.3f}s"
