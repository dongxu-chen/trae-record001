from datetime import datetime
from .database import Database


class StatsModel:
    @staticmethod
    def create_audit_stat(video_id, stage, duration, frames_processed=0, violations_detected=0, 
                          api_calls=0, api_errors=0, details=None):
        db = Database()
        query = """
            INSERT INTO audit_stats (video_id, stage, duration, frames_processed, 
                                   violations_detected, api_calls, api_errors, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return db.execute_update(query, (video_id, stage, duration, frames_processed,
                                        violations_detected, api_calls, api_errors, details))

    @staticmethod
    def get_audit_stats(video_id=None, stage=None, start_date=None, end_date=None):
        db = Database()
        query = "SELECT * FROM audit_stats WHERE 1=1"
        params = []
        
        if video_id:
            query += " AND video_id = %s"
            params.append(video_id)
        if stage:
            query += " AND stage = %s"
            params.append(stage)
        if start_date:
            query += " AND DATE(created_at) >= %s"
            params.append(start_date)
        if end_date:
            query += " AND DATE(created_at) <= %s"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC"
        return db.execute_query(query, tuple(params))

    @staticmethod
    def get_daily_stats(start_date=None, end_date=None):
        db = Database()
        query = "SELECT * FROM daily_stats WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND stat_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND stat_date <= %s"
            params.append(end_date)
        
        query += " ORDER BY stat_date DESC"
        return db.execute_query(query, tuple(params))

    @staticmethod
    def update_daily_stat(stat_date, total_videos=0, passed_videos=0, violated_videos=0,
                         total_frames=0, total_violations=0, avg_processing_time=0, total_api_calls=0):
        db = Database()
        query = """
            INSERT INTO daily_stats (stat_date, total_videos, passed_videos, violated_videos,
                                   total_frames, total_violations, avg_processing_time, total_api_calls)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_videos = total_videos + VALUES(total_videos),
                passed_videos = passed_videos + VALUES(passed_videos),
                violated_videos = violated_videos + VALUES(violated_videos),
                total_frames = total_frames + VALUES(total_frames),
                total_violations = total_violations + VALUES(total_violations),
                avg_processing_time = (avg_processing_time + VALUES(avg_processing_time)) / 2,
                total_api_calls = total_api_calls + VALUES(total_api_calls)
        """
        return db.execute_update(query, (stat_date, total_videos, passed_videos, violated_videos,
                                        total_frames, total_violations, avg_processing_time, total_api_calls))

    @staticmethod
    def get_overall_stats():
        db = Database()
        query = """
            SELECT 
                COUNT(DISTINCT v.id) as total_videos,
                SUM(CASE WHEN v.audit_result = 'passed' THEN 1 ELSE 0 END) as passed_videos,
                SUM(CASE WHEN v.audit_result = 'violated' THEN 1 ELSE 0 END) as violated_videos,
                COUNT(DISTINCT f.id) as total_frames,
                COUNT(DISTINCT vi.id) as total_violations,
                SUM(s.duration) as total_processing_time,
                SUM(s.api_calls) as total_api_calls
            FROM videos v
            LEFT JOIN frames f ON v.id = f.video_id
            LEFT JOIN violations vi ON v.id = vi.video_id
            LEFT JOIN audit_stats s ON v.id = s.video_id
        """
        result = db.execute_query(query)
        return result[0] if result else None
