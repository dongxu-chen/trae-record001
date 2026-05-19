from .database import Database


class FrameModel:
    @staticmethod
    def create(video_id, frame_number, timestamp, image_path, width=None, height=None, file_size=None):
        db = Database()
        query = """
            INSERT INTO frames (video_id, frame_number, timestamp, image_path, width, height, file_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return db.execute_update(query, (video_id, frame_number, timestamp, image_path, width, height, file_size))

    @staticmethod
    def get_by_video_id(video_id):
        db = Database()
        query = "SELECT * FROM frames WHERE video_id = %s ORDER BY frame_number"
        return db.execute_query(query, (video_id,))

    @staticmethod
    def count_by_video_id(video_id):
        db = Database()
        query = "SELECT COUNT(*) as count FROM frames WHERE video_id = %s"
        result = db.execute_query(query, (video_id,))
        return result[0]['count'] if result else 0

    @staticmethod
    def delete_by_video_id(video_id):
        db = Database()
        query = "DELETE FROM frames WHERE video_id = %s"
        return db.execute_update(query, (video_id,))
