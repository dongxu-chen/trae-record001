from .database import Database


class ViolationModel:
    @staticmethod
    def create(video_id, violation_type, violation_type_name, timestamp=None, confidence=0.0, 
               description=None, ocr_text=None, image_path=None, frame_id=None):
        db = Database()
        query = """
            INSERT INTO violations (video_id, frame_id, violation_type, violation_type_name, 
                                   timestamp, confidence, description, ocr_text, image_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return db.execute_update(query, (video_id, frame_id, violation_type, violation_type_name,
                                        timestamp, confidence, description, ocr_text, image_path))

    @staticmethod
    def get_by_video_id(video_id):
        db = Database()
        query = "SELECT * FROM violations WHERE video_id = %s ORDER BY timestamp"
        return db.execute_query(query, (video_id,))

    @staticmethod
    def count_by_type(violation_type=None, start_date=None, end_date=None):
        db = Database()
        query = "SELECT violation_type, violation_type_name, COUNT(*) as count FROM violations WHERE 1=1"
        params = []
        
        if violation_type:
            query += " AND violation_type = %s"
            params.append(violation_type)
        if start_date:
            query += " AND DATE(created_at) >= %s"
            params.append(start_date)
        if end_date:
            query += " AND DATE(created_at) <= %s"
            params.append(end_date)
        
        query += " GROUP BY violation_type, violation_type_name"
        return db.execute_query(query, tuple(params))
