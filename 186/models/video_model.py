from datetime import datetime
from .database import Database


class VideoModel:
    @staticmethod
    def create(filename, original_name, file_path, file_size=None, duration=None, width=None, height=None):
        db = Database()
        query = """
            INSERT INTO videos (filename, original_name, file_path, file_size, duration, width, height, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'processing')
        """
        return db.execute_update(query, (filename, original_name, file_path, file_size, duration, width, height))

    @staticmethod
    def get_by_id(video_id):
        db = Database()
        query = "SELECT * FROM videos WHERE id = %s"
        result = db.execute_query(query, (video_id,))
        return result[0] if result else None

    @staticmethod
    def update_status(video_id, status):
        db = Database()
        query = "UPDATE videos SET status = %s WHERE id = %s"
        return db.execute_update(query, (status, video_id))

    @staticmethod
    def update_audit_result(video_id, audit_result, violation_count=0):
        db = Database()
        query = "UPDATE videos SET audit_result = %s, violation_count = %s, status = 'completed' WHERE id = %s"
        return db.execute_update(query, (audit_result, violation_count, video_id))

    @staticmethod
    def list_videos(status=None, page=1, page_size=20):
        db = Database()
        offset = (page - 1) * page_size
        if status:
            query = "SELECT * FROM videos WHERE status = %s ORDER BY created_at DESC LIMIT %s OFFSET %s"
            return db.execute_query(query, (status, page_size, offset))
        else:
            query = "SELECT * FROM videos ORDER BY created_at DESC LIMIT %s OFFSET %s"
            return db.execute_query(query, (page_size, offset))

    @staticmethod
    def count(status=None):
        db = Database()
        if status:
            query = "SELECT COUNT(*) as count FROM videos WHERE status = %s"
            result = db.execute_query(query, (status,))
        else:
            query = "SELECT COUNT(*) as count FROM videos"
            result = db.execute_query(query)
        return result[0]['count'] if result else 0
