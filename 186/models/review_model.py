from datetime import datetime
from .database import Database


class ReviewModel:
    @staticmethod
    def create_review(video_id: int, violation_id: int, reviewer_id: int, reviewer_name: str,
                     review_result: str, review_note: str = None, review_time: float = None):
        db = Database()
        query = """
            INSERT INTO human_reviews (video_id, violation_id, reviewer_id, reviewer_name, 
                                     review_result, review_note, review_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return db.execute_update(query, (video_id, violation_id, reviewer_id, reviewer_name,
                                        review_result, review_note, review_time))

    @staticmethod
    def update_violation_review(violation_id: int, is_false_positive: bool, reviewer_id: int,
                               review_note: str = None):
        db = Database()
        query = """
            UPDATE violations 
            SET review_status = 'reviewed', 
                is_false_positive = %s, 
                reviewer_id = %s, 
                reviewed_at = NOW(),
                review_note = %s
            WHERE id = %s
        """
        return db.execute_update(query, (1 if is_false_positive else 0, reviewer_id, review_note, violation_id))

    @staticmethod
    def update_video_review_status(video_id: int, review_status: str):
        db = Database()
        query = "UPDATE videos SET review_status = %s WHERE id = %s"
        return db.execute_update(query, (review_status, video_id))

    @staticmethod
    def get_reviews_by_video(video_id: int):
        db = Database()
        query = "SELECT * FROM human_reviews WHERE video_id = %s ORDER BY created_at DESC"
        return db.execute_query(query, (video_id,))

    @staticmethod
    def get_reviews_by_violation(violation_id: int):
        db = Database()
        query = "SELECT * FROM human_reviews WHERE violation_id = %s ORDER BY created_at DESC"
        return db.execute_query(query, (violation_id,))

    @staticmethod
    def get_pending_violations(video_id: int = None, page: int = 1, page_size: int = 20):
        db = Database()
        offset = (page - 1) * page_size
        if video_id:
            query = """
                SELECT v.*, vi.original_name as video_name
                FROM violations v
                LEFT JOIN videos vi ON v.video_id = vi.id
                WHERE v.review_status = 'pending' AND v.video_id = %s
                ORDER BY v.confidence DESC
                LIMIT %s OFFSET %s
            """
            return db.execute_query(query, (video_id, page_size, offset))
        else:
            query = """
                SELECT v.*, vi.original_name as video_name
                FROM violations v
                LEFT JOIN videos vi ON v.video_id = vi.id
                WHERE v.review_status = 'pending'
                ORDER BY v.confidence DESC
                LIMIT %s OFFSET %s
            """
            return db.execute_query(query, (page_size, offset))

    @staticmethod
    def count_pending_violations(video_id: int = None):
        db = Database()
        if video_id:
            query = "SELECT COUNT(*) as count FROM violations WHERE review_status = 'pending' AND video_id = %s"
            result = db.execute_query(query, (video_id,))
        else:
            query = "SELECT COUNT(*) as count FROM violations WHERE review_status = 'pending'"
            result = db.execute_query(query)
        return result[0]['count'] if result else 0

    @staticmethod
    def get_false_positive_rate(start_date: str = None, end_date: str = None, violation_type: str = None):
        db = Database()
        query = """
            SELECT 
                COUNT(*) as total_reviewed,
                SUM(CASE WHEN is_false_positive = 1 THEN 1 ELSE 0 END) as false_positives
            FROM violations 
            WHERE review_status = 'reviewed'
        """
        params = []
        
        if start_date:
            query += " AND DATE(created_at) >= %s"
            params.append(start_date)
        if end_date:
            query += " AND DATE(created_at) <= %s"
            params.append(end_date)
        if violation_type:
            query += " AND violation_type = %s"
            params.append(violation_type)
        
        result = db.execute_query(query, tuple(params))
        if result and result[0]['total_reviewed'] > 0:
            return result[0]['false_positives'] / result[0]['total_reviewed']
        return 0.0

    @staticmethod
    def get_review_stats(start_date: str = None, end_date: str = None):
        db = Database()
        query = """
            SELECT 
                COUNT(DISTINCT video_id) as videos_reviewed,
                COUNT(*) as total_violations_reviewed,
                SUM(CASE WHEN hr.review_result = 'confirmed' THEN 1 ELSE 0 END) as confirmed_violations,
                SUM(CASE WHEN hr.review_result = 'false_positive' THEN 1 ELSE 0 END) as false_positives,
                SUM(CASE WHEN hr.review_result = 'missed' THEN 1 ELSE 0 END) as false_negatives,
                AVG(hr.review_time) as avg_review_time
            FROM human_reviews hr
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND DATE(hr.created_at) >= %s"
            params.append(start_date)
        if end_date:
            query += " AND DATE(hr.created_at) <= %s"
            params.append(end_date)
        
        result = db.execute_query(query, tuple(params))
        return result[0] if result else None

    @staticmethod
    def update_quality_metrics(metric_date: str, violation_type: str, total_detected: int,
                              true_positives: int, false_positives: int, false_negatives: int):
        db = Database()
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        query = """
            INSERT INTO quality_metrics (metric_date, violation_type, total_detected, 
                                        true_positives, false_positives, false_negatives,
                                        precision, recall, f1_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_detected = total_detected + VALUES(total_detected),
                true_positives = true_positives + VALUES(true_positives),
                false_positives = false_positives + VALUES(false_positives),
                false_negatives = false_negatives + VALUES(false_negatives),
                precision = (precision + VALUES(precision)) / 2,
                recall = (recall + VALUES(recall)) / 2,
                f1_score = (f1_score + VALUES(f1_score)) / 2
        """
        return db.execute_update(query, (metric_date, violation_type, total_detected,
                                        true_positives, false_positives, false_negatives,
                                        precision, recall, f1_score))

    @staticmethod
    def get_quality_metrics(start_date: str = None, end_date: str = None, violation_type: str = None):
        db = Database()
        query = "SELECT * FROM quality_metrics WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND metric_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND metric_date <= %s"
            params.append(end_date)
        if violation_type:
            query += " AND violation_type = %s"
            params.append(violation_type)
        
        query += " ORDER BY metric_date DESC"
        return db.execute_query(query, tuple(params))
