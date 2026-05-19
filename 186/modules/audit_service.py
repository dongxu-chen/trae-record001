import os
import uuid
import shutil
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date

from config.config import UPLOAD_DIR, FRAME_INTERVAL
from models import VideoModel, ViolationModel, FrameModel, ReviewModel
from models.rule_model import SensitiveWordModel, AuditRuleModel
from modules import FrameExtractor, VisionAuditor, OCRAuditor, AuditStatistics, format_time
from modules.content_sanitizer import ContentSanitizer, TextSanitizer
from modules.quality_sampler import QualitySampler


class DramaAuditService:
    def __init__(self):
        pass

    def upload_video(self, file_storage, original_filename: str) -> Dict:
        file_ext = os.path.splitext(original_filename)[1].lower()
        if file_ext not in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm']:
            raise ValueError(f"不支持的文件格式: {file_ext}")

        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        file_storage.save(file_path)
        
        file_size = os.path.getsize(file_path)
        
        video_id = VideoModel.create(
            filename=unique_filename,
            original_name=original_filename,
            file_path=file_path,
            file_size=file_size
        )

        return {
            'video_id': video_id,
            'filename': unique_filename,
            'original_name': original_filename,
            'file_path': file_path,
            'file_size': file_size
        }

    def audit_video(self, video_id: int, frame_interval: float = None, 
                    min_interval: float = 0.5, max_interval: float = 5.0,
                    scene_threshold: float = 0.3, enable_ocr_preprocessing: bool = True,
                    enable_sanitization: bool = True, blur_strength: int = 30) -> Dict:
        video = VideoModel.get_by_id(video_id)
        if not video:
            raise ValueError(f"视频不存在: {video_id}")

        stats = AuditStatistics(video_id=video_id)
        all_violations = []
        scene_summary = None

        try:
            VideoModel.update_status(video_id, 'processing')

            with stats.measure_stage('video_info') as set_detail:
                extractor = FrameExtractor(video['file_path'], video_id)
                video_info = extractor.get_video_info()
                set_detail('duration', video_info['duration'])
                set_detail('resolution', f"{video_info['width']}x{video_info['height']}")
                
                VideoModel.execute_update(
                    "UPDATE videos SET duration = %s, width = %s, height = %s WHERE id = %s",
                    (video_info['duration'], video_info['width'], video_info['height'], video_id)
                )

            with stats.measure_stage('frame_extraction') as set_detail:
                frames = extractor.extract_frames_dynamic(
                    base_interval=frame_interval or FRAME_INTERVAL,
                    min_interval=min_interval,
                    max_interval=max_interval,
                    scene_threshold=scene_threshold
                )
                scene_summary = extractor.get_scene_summary()
                stats.update_stage_metrics(
                    'frame_extraction', 
                    frames_processed=len(frames),
                    scene_changes=scene_summary.get('total_scene_changes', 0)
                )
                set_detail('frame_count', len(frames))
                set_detail('base_interval', frame_interval or FRAME_INTERVAL)
                set_detail('scene_changes', scene_summary.get('total_scene_changes', 0))
                set_detail('avg_scene_duration', scene_summary.get('avg_scene_duration', 0))

            with stats.measure_stage('vision_audit') as set_detail:
                vision_auditor = VisionAuditor(video_id)
                vision_violations, vision_calls, vision_errors = vision_auditor.analyze_frames(frames)
                all_violations.extend(vision_violations)
                stats.update_stage_metrics(
                    'vision_audit',
                    frames_processed=len(frames),
                    violations_detected=len(vision_violations),
                    api_calls=vision_calls,
                    api_errors=vision_errors
                )
                set_detail('violation_types', list(set(v['violation_type'] for v in vision_violations)))

            with stats.measure_stage('ocr_audit') as set_detail:
                ocr_auditor = OCRAuditor(video_id, enable_preprocessing=enable_ocr_preprocessing)
                
                subtitles = ocr_auditor.extract_subtitle_text(video['file_path'])
                if subtitles:
                    ocr_violations, ocr_calls, ocr_errors = ocr_auditor.analyze_subtitles(subtitles)
                    all_violations.extend(ocr_violations)
                    stats.update_stage_metrics(
                        'ocr_audit',
                        frames_processed=len(subtitles),
                        violations_detected=len(ocr_violations),
                        api_calls=ocr_calls,
                        api_errors=ocr_errors
                    )
                    set_detail('subtitle_count', len(subtitles))
                else:
                    ocr_violations, ocr_calls, ocr_errors = ocr_auditor.analyze_frames(frames)
                    all_violations.extend(ocr_violations)
                    preprocessing_stats = ocr_auditor.get_preprocessing_summary()
                    stats.update_stage_metrics(
                        'ocr_audit',
                        frames_processed=len(frames),
                        violations_detected=len(ocr_violations),
                        api_calls=ocr_calls,
                        api_errors=ocr_errors,
                        rotated_frames=preprocessing_stats.get('rotated_frames', 0)
                    )
                    stats.set_ocr_preprocessing_stats(preprocessing_stats)
                    set_detail('mode', 'frame_ocr')
                    set_detail('preprocessing', preprocessing_stats)

            with stats.measure_stage('result_processing') as set_detail:
                unique_violations = self._merge_violations(all_violations)
                
                audit_result = 'violated' if unique_violations else 'passed'
                
                VideoModel.update_audit_result(
                    video_id=video_id,
                    audit_result=audit_result,
                    violation_count=len(unique_violations)
                )
                
                stats.update_daily_stats(passed=(audit_result == 'passed'))
                set_detail('final_violation_count', len(unique_violations))
                set_detail('audit_result', audit_result)

            with stats.measure_stage('sanitization') as set_detail:
                sanitized_path = None
                if unique_violations and enable_sanitization:
                    sanitizer = ContentSanitizer(video['file_path'], video_id)
                    sanitized_path = sanitizer.blur_violation_areas(
                        unique_violations,
                        blur_strength=blur_strength
                    )
                    if sanitized_path:
                        VideoModel.execute_update(
                            "UPDATE videos SET sanitized_path = %s, is_sanitized = 1 WHERE id = %s",
                            (sanitized_path, video_id)
                        )
                        sanitization_summary = sanitizer.get_sanitization_summary()
                        set_detail('sanitized', True)
                        set_detail('sanitized_path', sanitized_path)
                        set_detail('sanitization_summary', sanitization_summary)
                    else:
                        set_detail('sanitized', False)
                        set_detail('error', 'Sanitization failed')

            stats.print_summary()

            return {
                'video_id': video_id,
                'audit_result': audit_result,
                'violation_count': len(unique_violations),
                'violations': unique_violations,
                'video_info': video_info,
                'scene_summary': scene_summary,
                'sanitized_path': sanitized_path,
                'statistics': stats.get_summary()
            }

        except Exception as e:
            VideoModel.update_status(video_id, 'failed')
            raise e

    def _merge_violations(self, violations: List[Dict]) -> List[Dict]:
        time_threshold = 1.0
        merged = []
        used = set()

        for i, v1 in enumerate(violations):
            if i in used:
                continue
            
            group = [v1]
            used.add(i)
            
            for j, v2 in enumerate(violations[i+1:], i+1):
                if j in used:
                    continue
                if v1['violation_type'] == v2['violation_type']:
                    time_diff = abs(v1.get('timestamp', 0) - v2.get('timestamp', 0))
                    if time_diff <= time_threshold:
                        group.append(v2)
                        used.add(j)
            
            if group:
                best = max(group, key=lambda x: x.get('confidence', 0))
                merged.append(best)

        return sorted(merged, key=lambda x: x.get('timestamp', 0))

    def get_audit_result(self, video_id: int) -> Dict:
        video = VideoModel.get_by_id(video_id)
        if not video:
            raise ValueError(f"视频不存在: {video_id}")

        violations = ViolationModel.get_by_video_id(video_id)
        
        return {
            'video': video,
            'violations': violations,
            'violation_count': len(violations)
        }

    def list_videos(self, status: str = None, page: int = 1, page_size: int = 20) -> Dict:
        videos = VideoModel.list_videos(status=status, page=page, page_size=page_size)
        total = VideoModel.count(status=status)
        
        return {
            'videos': videos,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    def delete_video(self, video_id: int) -> bool:
        video = VideoModel.get_by_id(video_id)
        if not video:
            raise ValueError(f"视频不存在: {video_id}")

        try:
            if os.path.exists(video['file_path']):
                os.remove(video['file_path'])
        except:
            pass

        FrameModel.delete_by_video_id(video_id)
        
        frames_dir = os.path.join(os.path.dirname(video['file_path']), 'frames', str(video_id))
        if os.path.exists(frames_dir):
            shutil.rmtree(frames_dir, ignore_errors=True)

        VideoModel.execute_update("DELETE FROM videos WHERE id = %s", (video_id,))
        
        return True

    def get_statistics(self) -> Dict:
        overall = AuditStatistics.get_overall_statistics()
        daily = AuditStatistics.get_daily_statistics()
        quality = AuditStatistics.get_quality_statistics()
        
        return {
            'overall': overall,
            'daily': daily[:7],
            'quality': quality
        }

    def review_violation(self, violation_id: int, reviewer_id: int, reviewer_name: str,
                        is_false_positive: bool, review_note: str = None,
                        review_time: float = None) -> Dict:
        violation = ViolationModel.execute_query(
            "SELECT * FROM violations WHERE id = %s", (violation_id,)
        )
        if not violation:
            raise ValueError(f"违规记录不存在: {violation_id}")
        
        violation = violation[0]
        video_id = violation['video_id']
        violation_type = violation['violation_type']
        
        review_result = 'false_positive' if is_false_positive else 'confirmed'
        
        ReviewModel.create_review(
            video_id=video_id,
            violation_id=violation_id,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            review_result=review_result,
            review_note=review_note,
            review_time=review_time
        )
        
        ReviewModel.update_violation_review(
            violation_id=violation_id,
            is_false_positive=is_false_positive,
            reviewer_id=reviewer_id,
            review_note=review_note
        )
        
        today = date.today().isoformat()
        true_positives = 0 if is_false_positive else 1
        false_positives = 1 if is_false_positive else 0
        
        ReviewModel.update_quality_metrics(
            metric_date=today,
            violation_type=violation_type,
            total_detected=1,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=0
        )
        
        pending_count = ReviewModel.count_pending_violations(video_id=video_id)
        if pending_count == 0:
            ReviewModel.update_video_review_status(video_id, 'completed')
        
        return {
            'violation_id': violation_id,
            'review_result': review_result,
            'pending_count': pending_count
        }

    def get_pending_reviews(self, video_id: int = None, page: int = 1, page_size: int = 20) -> Dict:
        violations = ReviewModel.get_pending_violations(video_id=video_id, page=page, page_size=page_size)
        total = ReviewModel.count_pending_violations(video_id=video_id)
        
        return {
            'violations': violations,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    def get_quality_metrics(self, start_date: str = None, end_date: str = None) -> Dict:
        return AuditStatistics.get_quality_statistics(start_date=start_date, end_date=end_date)

    def sanitize_video(self, video_id: int, blur_strength: int = 30) -> Dict:
        video = VideoModel.get_by_id(video_id)
        if not video:
            raise ValueError(f"视频不存在: {video_id}")

        violations = ViolationModel.get_by_video_id(video_id)
        
        if not violations:
            return {
                'success': True,
                'message': '没有违规内容需要处理',
                'sanitized': False
            }

        sanitizer = ContentSanitizer(video['file_path'], video_id)
        sanitized_path = sanitizer.blur_violation_areas(
            violations,
            blur_strength=blur_strength
        )

        if sanitized_path:
            VideoModel.execute_update(
                "UPDATE videos SET sanitized_path = %s, is_sanitized = 1 WHERE id = %s",
                (sanitized_path, video_id)
            )
            return {
                'success': True,
                'sanitized': True,
                'sanitized_path': sanitized_path,
                'summary': sanitizer.get_sanitization_summary()
            }

        return {
            'success': False,
            'sanitized': False,
            'error': '视频处理失败'
        }

    def mask_sensitive_text(self, text: str, category: str = None, 
                          mask_mode: str = 'full', mask_char: str = '*') -> Dict:
        sensitive_words = SensitiveWordModel.get_active_words(category=category)
        
        if mask_mode == 'full':
            masked_text, replacements = TextSanitizer.mask_text(
                text, sensitive_words, mask_char=mask_char
            )
        elif mask_mode == 'partial':
            masked_text, replacements = TextSanitizer.partial_mask(
                text, sensitive_words, mask_char=mask_char
            )
        else:
            masked_text, replacements = TextSanitizer.mask_text(
                text, sensitive_words, mask_char=mask_char
            )

        return {
            'original_text': text,
            'masked_text': masked_text,
            'replacements': replacements,
            'sensitive_words_detected': len(replacements)
        }

    def get_sensitive_words(self, category: str = None, is_active: bool = None) -> Dict:
        words = SensitiveWordModel.get_all_words(category=category, is_active=is_active)
        categories = SensitiveWordModel.get_word_categories()
        
        return {
            'words': words,
            'categories': categories,
            'total_count': len(words)
        }

    def add_sensitive_word(self, word: str, category: str, severity: str = 'medium',
                          match_mode: str = 'exact') -> Dict:
        word_id = SensitiveWordModel.add_word(word, category, severity, match_mode)
        
        return {
            'success': True,
            'word_id': word_id,
            'word': word,
            'category': category,
            'severity': severity
        }

    def update_sensitive_word(self, word_id: int, **kwargs) -> Dict:
        result = SensitiveWordModel.update_word(word_id, **kwargs)
        
        return {
            'success': result > 0,
            'updated': result
        }

    def delete_sensitive_word(self, word_id: int) -> Dict:
        result = SensitiveWordModel.delete_word(word_id)
        
        return {
            'success': result > 0,
            'deleted': result
        }

    def get_audit_rules(self, rule_type: str = None, is_active: bool = None) -> Dict:
        rules = AuditRuleModel.get_all_rules(rule_type=rule_type, is_active=is_active)
        
        return {
            'rules': rules,
            'total_count': len(rules)
        }

    def add_audit_rule(self, rule_name: str, rule_type: str, violation_type: str,
                      threshold: float = 0.7, config_json: str = None,
                      description: str = None) -> Dict:
        rule_id = AuditRuleModel.add_rule(
            rule_name, rule_type, violation_type, threshold, config_json, description
        )
        
        return {
            'success': True,
            'rule_id': rule_id,
            'rule_name': rule_name
        }

    def update_audit_rule(self, rule_id: int, **kwargs) -> Dict:
        result = AuditRuleModel.update_rule(rule_id, **kwargs)
        
        return {
            'success': result > 0,
            'updated': result
        }

    def delete_audit_rule(self, rule_id: int) -> Dict:
        result = AuditRuleModel.delete_rule(rule_id)
        
        return {
            'success': result > 0,
            'deleted': result
        }

    def get_threshold(self, rule_type: str, violation_type: str) -> float:
        return AuditRuleModel.get_threshold(rule_type, violation_type)

    def run_quality_sampling(self, sample_rate: float = 0.05, 
                            start_date: str = None, end_date: str = None,
                            sample_type: str = 'manual') -> Dict:
        sampler = QualitySampler(sample_rate=sample_rate)
        
        candidates = sampler.get_candidates_for_sampling(
            start_date=start_date,
            end_date=end_date
        )
        
        sampled = sampler.sample_videos(candidates, sample_rate=sample_rate)
        sample_ids = sampler.create_quality_samples(sampled, sample_type)
        
        return {
            'total_candidates': len(candidates),
            'sampled_count': len(sample_ids),
            'sample_rate': len(sample_ids) / len(candidates) if candidates else 0,
            'sampled_video_ids': sample_ids
        }

    def get_pending_quality_samples(self, sample_type: str = None) -> Dict:
        sampler = QualitySampler()
        samples = sampler.get_pending_samples(sample_type=sample_type)
        
        return {
            'samples': samples,
            'total_count': len(samples)
        }

    def audit_quality_sample(self, sample_id: int, auditor_id: int, audit_result: str,
                            audit_note: str = None, audit_time: float = None) -> Dict:
        sampler = QualitySampler()
        result = sampler.audit_sample(sample_id, auditor_id, audit_result, audit_note, audit_time)
        
        return result

    def get_quality_consistency_metrics(self, start_date: str = None, 
                                       end_date: str = None) -> Dict:
        sampler = QualitySampler()
        return sampler.calculate_consistency_metrics(start_date=start_date, end_date=end_date)

    def get_quality_sample_stats(self) -> Dict:
        sampler = QualitySampler()
        return sampler.get_sample_statistics()

    def get_sample_consistency_detail(self, sample_id: int) -> Dict:
        sampler = QualitySampler()
        return sampler.calculate_sample_consistency_detail(sample_id)
