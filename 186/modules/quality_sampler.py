import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from models.database import Database
from models import VideoModel, ViolationModel, ReviewModel


class QualitySampler:
    def __init__(self, sample_rate: float = 0.05, min_samples: int = 1):
        self.sample_rate = sample_rate
        self.min_samples = min_samples

    def get_candidates_for_sampling(self, start_date: str = None, 
                                    end_date: str = None,
                                    exclude_sampled: bool = True) -> List[Dict]:
        db = Database()
        query = """
            SELECT v.*, 
                   (SELECT COUNT(*) FROM violations v2 WHERE v2.video_id = v.id) as violation_count,
                   (SELECT COUNT(*) FROM human_reviews hr WHERE hr.video_id = v.id) as review_count
            FROM videos v
            WHERE v.status = 'completed' AND v.audit_result IS NOT NULL
        """
        params = []
        
        if exclude_sampled:
            query += " AND v.is_quality_sample = 0"
        
        if start_date:
            query += " AND DATE(v.created_at) >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(v.created_at) <= %s"
            params.append(end_date)
        
        query += " ORDER BY v.created_at DESC"
        
        return db.execute_query(query, params)

    def sample_videos(self, candidates: List[Dict], sample_rate: float = None,
                     min_samples: int = None) -> List[Dict]:
        rate = sample_rate or self.sample_rate
        min_samp = min_samples or self.min_samples
        
        if not candidates:
            return []
        
        total_count = len(candidates)
        sample_count = max(min_samp, int(total_count * rate))
        sample_count = min(sample_count, total_count)
        
        if sample_count <= 0:
            return []
        
        weighted_candidates = self._weight_candidates(candidates)
        sampled = random.sample(weighted_candidates, sample_count)
        
        return sampled

    def _weight_candidates(self, candidates: List[Dict]) -> List[Dict]:
        weighted = []
        
        for video in candidates:
            weight = 1.0
            
            if video.get('violation_count', 0) > 0:
                weight *= 1.5
            
            if video.get('review_count', 0) == 0:
                weight *= 1.2
            
            audit_result = video.get('audit_result', '')
            if audit_result == 'violated':
                weight *= 1.3
            elif audit_result == 'pending':
                weight *= 0.8
            
            weighted.append({**video, 'sample_weight': weight})
        
        return weighted

    def create_quality_samples(self, sampled_videos: List[Dict], 
                               sample_type: str = 'random') -> List[int]:
        db = Database()
        sample_ids = []
        
        for video in sampled_videos:
            video_id = video.get('id')
            if not video_id:
                continue
            
            query = """
                INSERT INTO quality_samples (video_id, sample_type, is_audited)
                VALUES (%s, %s, 0)
            """
            db.execute_update(query, (video_id, sample_type))
            
            db.execute_update(
                "UPDATE videos SET is_quality_sample = 1 WHERE id = %s",
                (video_id,)
            )
            
            sample_ids.append(video_id)
        
        return sample_ids

    def run_daily_sampling(self, sample_type: str = 'daily') -> Dict:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        candidates = self.get_candidates_for_sampling(
            start_date=yesterday.strftime('%Y-%m-%d'),
            end_date=yesterday.strftime('%Y-%m-%d')
        )
        
        sampled = self.sample_videos(candidates)
        sample_ids = self.create_quality_samples(sampled, sample_type)
        
        return {
            'date': yesterday.strftime('%Y-%m-%d'),
            'total_candidates': len(candidates),
            'sampled_count': len(sample_ids),
            'sample_rate': len(sample_ids) / len(candidates) if candidates else 0,
            'sampled_video_ids': sample_ids
        }

    def get_pending_samples(self, sample_type: str = None) -> List[Dict]:
        db = Database()
        query = """
            SELECT qs.*, v.filename, v.original_name, v.audit_result,
                   v.violation_count as total_violations
            FROM quality_samples qs
            JOIN videos v ON qs.video_id = v.id
            WHERE qs.is_audited = 0
        """
        params = []
        
        if sample_type:
            query += " AND qs.sample_type = %s"
            params.append(sample_type)
        
        query += " ORDER BY qs.sampled_at DESC"
        
        return db.execute_query(query, params)

    def audit_sample(self, sample_id: int, auditor_id: int, audit_result: str,
                    audit_note: str = None, audit_time: float = None) -> Dict:
        db = Database()
        
        sample = db.execute_query(
            "SELECT * FROM quality_samples WHERE id = %s",
            (sample_id,)
        )
        if not sample:
            return {'success': False, 'error': 'Sample not found'}
        
        sample = sample[0]
        video_id = sample['video_id']
        
        ai_violations = ViolationModel.get_by_video_id(video_id)
        ai_result = 'violated' if ai_violations else 'passed'
        
        consistency_score = self._calculate_consistency(
            ai_result, audit_result, ai_violations
        )
        
        query = """
            UPDATE quality_samples 
            SET is_audited = 1, auditor_id = %s, audit_result = %s,
                audit_note = %s, audit_time = %s, consistency_score = %s,
                audited_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        db.execute_update(query, (auditor_id, audit_result, audit_note, 
                                 audit_time, consistency_score, sample_id))
        
        return {
            'success': True,
            'ai_result': ai_result,
            'human_result': audit_result,
            'consistency_score': consistency_score
        }

    def _calculate_consistency(self, ai_result: str, human_result: str,
                              ai_violations: List[Dict]) -> float:
        if ai_result == human_result:
            return 1.0
        
        if ai_result == 'violated' and human_result == 'passed':
            return 0.0
        
        if ai_result == 'passed' and human_result == 'violated':
            return 0.0
        
        return 0.5

    def calculate_consistency_metrics(self, start_date: str = None,
                                     end_date: str = None) -> Dict:
        db = Database()
        query = """
            SELECT qs.*, v.audit_result as ai_result
            FROM quality_samples qs
            JOIN videos v ON qs.video_id = v.id
            WHERE qs.is_audited = 1
        """
        params = []
        
        if start_date:
            query += " AND DATE(qs.audited_at) >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(qs.audited_at) <= %s"
            params.append(end_date)
        
        samples = db.execute_query(query, params)
        
        if not samples:
            return {
                'total_samples': 0,
                'consistent_count': 0,
                'inconsistent_count': 0,
                'consistency_rate': 0.0,
                'avg_consistency_score': 0.0
            }
        
        total = len(samples)
        consistent = sum(1 for s in samples if s.get('consistency_score', 0) >= 0.9)
        inconsistent = total - consistent
        avg_score = sum(s.get('consistency_score', 0) for s in samples) / total
        
        ai_violated = sum(1 for s in samples if s.get('ai_result') == 'violated')
        human_violated = sum(1 for s in samples if s.get('audit_result') == 'violated')
        
        false_positives = sum(1 for s in samples 
                            if s.get('ai_result') == 'violated' 
                            and s.get('audit_result') == 'passed')
        false_negatives = sum(1 for s in samples 
                            if s.get('ai_result') == 'passed' 
                            and s.get('audit_result') == 'violated')
        
        return {
            'total_samples': total,
            'consistent_count': consistent,
            'inconsistent_count': inconsistent,
            'consistency_rate': consistent / total,
            'avg_consistency_score': avg_score,
            'ai_violated_count': ai_violated,
            'human_violated_count': human_violated,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'false_positive_rate': false_positives / total if total > 0 else 0,
            'false_negative_rate': false_negatives / total if total > 0 else 0
        }

    def get_sample_statistics(self) -> Dict:
        db = Database()
        
        stats = db.execute_query("""
            SELECT 
                COUNT(*) as total_samples,
                SUM(CASE WHEN is_audited = 1 THEN 1 ELSE 0 END) as audited_samples,
                SUM(CASE WHEN is_audited = 0 THEN 1 ELSE 0 END) as pending_samples,
                AVG(CASE WHEN is_audited = 1 THEN consistency_score ELSE NULL END) as avg_consistency
            FROM quality_samples
        """)[0]
        
        by_type = db.execute_query("""
            SELECT sample_type, 
                   COUNT(*) as count,
                   SUM(CASE WHEN is_audited = 1 THEN 1 ELSE 0 END) as audited
            FROM quality_samples
            GROUP BY sample_type
        """)
        
        return {
            'total_samples': stats['total_samples'] or 0,
            'audited_samples': stats['audited_samples'] or 0,
            'pending_samples': stats['pending_samples'] or 0,
            'avg_consistency_score': float(stats['avg_consistency'] or 0),
            'by_sample_type': by_type
        }

    def calculate_sample_consistency_detail(self, sample_id: int) -> Dict:
        db = Database()
        
        sample = db.execute_query(
            "SELECT * FROM quality_samples WHERE id = %s",
            (sample_id,)
        )
        if not sample or not sample[0].get('is_audited'):
            return {}
        
        sample = sample[0]
        video_id = sample['video_id']
        
        ai_violations = ViolationModel.get_by_video_id(video_id)
        human_reviews = ReviewModel.get_by_video_id(video_id)
        
        ai_violation_ids = set(v['id'] for v in ai_violations)
        confirmed_ids = set()
        false_positive_ids = set()
        
        for review in human_reviews:
            v_id = review.get('violation_id')
            if v_id:
                if review.get('review_result') == 'confirmed':
                    confirmed_ids.add(v_id)
                elif review.get('review_result') == 'false_positive':
                    false_positive_ids.add(v_id)
        
        human_detections = len(confirmed_ids)
        ai_detections = len(ai_violation_ids)
        
        if ai_detections > 0 or human_detections > 0:
            intersection = len(confirmed_ids)
            union = len(ai_violation_ids | confirmed_ids)
            jaccard = intersection / union if union > 0 else 0
        else:
            jaccard = 1.0
        
        return {
            'sample_id': sample_id,
            'video_id': video_id,
            'ai_detections': ai_detections,
            'human_detections': human_detections,
            'false_positives': len(false_positive_ids),
            'true_positives': len(confirmed_ids),
            'jaccard_similarity': jaccard,
            'ai_violation_ids': list(ai_violation_ids),
            'confirmed_ids': list(confirmed_ids),
            'false_positive_ids': list(false_positive_ids)
        }
