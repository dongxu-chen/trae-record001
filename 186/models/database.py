import pymysql
from datetime import datetime
from config.config import MYSQL_CONFIG


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.connection = None
        return cls._instance

    def connect(self):
        if not self.connection or self.connection.open is False:
            self.connection = pymysql.connect(**MYSQL_CONFIG)
        return self.connection

    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()

    def execute_query(self, query, params=None):
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def execute_update(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cursor:
            result = cursor.execute(query, params or ())
            conn.commit()
            return result


def init_database():
    db = Database()
    conn = db.connect()

    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                original_name VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size BIGINT,
                duration FLOAT,
                width INT,
                height INT,
                status VARCHAR(50) DEFAULT 'pending',
                audit_result VARCHAR(50) DEFAULT 'pending',
                violation_count INT DEFAULT 0,
                review_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_status (status),
                INDEX idx_audit_result (audit_result),
                INDEX idx_review_status (review_status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frames (
                id INT AUTO_INCREMENT PRIMARY KEY,
                video_id INT NOT NULL,
                frame_number INT NOT NULL,
                timestamp FLOAT NOT NULL,
                image_path VARCHAR(500) NOT NULL,
                width INT,
                height INT,
                file_size INT,
                is_near_scene TINYINT(1) DEFAULT 0,
                interval_used FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                INDEX idx_video_id (video_id),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                video_id INT NOT NULL,
                frame_id INT,
                violation_type VARCHAR(50) NOT NULL,
                violation_type_name VARCHAR(100) NOT NULL,
                timestamp FLOAT,
                confidence FLOAT NOT NULL,
                description TEXT,
                ocr_text TEXT,
                image_path VARCHAR(500),
                review_status VARCHAR(50) DEFAULT 'pending',
                is_false_positive TINYINT(1) DEFAULT 0,
                reviewer_id INT,
                reviewed_at TIMESTAMP NULL,
                review_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                FOREIGN KEY (frame_id) REFERENCES frames(id) ON DELETE SET NULL,
                INDEX idx_video_id (video_id),
                INDEX idx_violation_type (violation_type),
                INDEX idx_confidence (confidence),
                INDEX idx_review_status (review_status),
                INDEX idx_is_false_positive (is_false_positive)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS human_reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                video_id INT NOT NULL,
                violation_id INT,
                reviewer_id INT NOT NULL,
                reviewer_name VARCHAR(100),
                review_result VARCHAR(50) NOT NULL,
                review_note TEXT,
                review_time FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE SET NULL,
                INDEX idx_video_id (video_id),
                INDEX idx_violation_id (violation_id),
                INDEX idx_reviewer_id (reviewer_id),
                INDEX idx_review_result (review_result)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                video_id INT,
                stage VARCHAR(50) NOT NULL,
                duration FLOAT NOT NULL,
                frames_processed INT DEFAULT 0,
                violations_detected INT DEFAULT 0,
                api_calls INT DEFAULT 0,
                api_errors INT DEFAULT 0,
                scene_changes_detected INT DEFAULT 0,
                rotated_frames INT DEFAULT 0,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE SET NULL,
                INDEX idx_video_id (video_id),
                INDEX idx_stage (stage)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stat_date DATE NOT NULL UNIQUE,
                total_videos INT DEFAULT 0,
                passed_videos INT DEFAULT 0,
                violated_videos INT DEFAULT 0,
                total_frames INT DEFAULT 0,
                total_violations INT DEFAULT 0,
                avg_processing_time FLOAT DEFAULT 0,
                total_api_calls INT DEFAULT 0,
                total_reviews INT DEFAULT 0,
                false_positives INT DEFAULT 0,
                false_negative INT DEFAULT 0,
                avg_review_time FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_stat_date (stat_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE NOT NULL,
                violation_type VARCHAR(50) NOT NULL,
                total_detected INT DEFAULT 0,
                true_positives INT DEFAULT 0,
                false_positives INT DEFAULT 0,
                false_negatives INT DEFAULT 0,
                precision FLOAT DEFAULT 0,
                recall FLOAT DEFAULT 0,
                f1_score FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_date_type (metric_date, violation_type),
                INDEX idx_metric_date (metric_date),
                INDEX idx_violation_type (violation_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensitive_words (
                id INT AUTO_INCREMENT PRIMARY KEY,
                word VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                severity VARCHAR(20) DEFAULT 'medium',
                is_active TINYINT(1) DEFAULT 1,
                match_mode VARCHAR(20) DEFAULT 'exact',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_word (word),
                INDEX idx_category (category),
                INDEX idx_severity (severity),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_rules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                rule_name VARCHAR(100) NOT NULL,
                rule_type VARCHAR(50) NOT NULL,
                violation_type VARCHAR(50) NOT NULL,
                threshold FLOAT DEFAULT 0.7,
                is_active TINYINT(1) DEFAULT 1,
                config_json TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_rule_type (rule_type),
                INDEX idx_violation_type (violation_type),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_samples (
                id INT AUTO_INCREMENT PRIMARY KEY,
                video_id INT NOT NULL,
                sample_type VARCHAR(50) NOT NULL,
                is_audited TINYINT(1) DEFAULT 0,
                auditor_id INT,
                audit_result VARCHAR(50),
                audit_note TEXT,
                audit_time FLOAT,
                consistency_score FLOAT,
                sampled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                audited_at TIMESTAMP NULL,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                INDEX idx_sample_type (sample_type),
                INDEX idx_is_audited (is_audited),
                INDEX idx_sampled_at (sampled_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS sanitized_path VARCHAR(500) NULL,
            ADD COLUMN IF NOT EXISTS is_sanitized TINYINT(1) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS is_quality_sample TINYINT(1) DEFAULT 0,
            ADD INDEX IF NOT EXISTS idx_is_quality_sample (is_quality_sample)
        """)

        cursor.execute("""
            ALTER TABLE violations ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'medium',
            ADD COLUMN IF NOT EXISTS sensitive_word VARCHAR(100) NULL,
            ADD INDEX IF NOT EXISTS idx_severity (severity)
        """)

        cursor.execute("""
            INSERT IGNORE INTO sensitive_words (word, category, severity) VALUES
            ('违禁词1', 'politics', 'high'),
            ('违禁词2', 'politics', 'high'),
            ('违禁词3', 'porn', 'high'),
            ('违禁词4', 'violence', 'medium')
        """)

        cursor.execute("""
            INSERT IGNORE INTO audit_rules (rule_name, rule_type, violation_type, threshold, description) VALUES
            ('政治敏感检测', 'vision', 'politics', 0.7, '检测视频画面中的政治敏感内容'),
            ('色情内容检测', 'vision', 'porn', 0.6, '检测视频画面中的色情内容'),
            ('暴力内容检测', 'vision', 'violence', 0.7, '检测视频画面中的暴力内容'),
            ('敏感词检测', 'ocr', 'sensitive_text', 0.9, '检测字幕中的敏感词'),
            ('OCR文本检测', 'ocr', 'ocr_text', 0.5, 'OCR文本识别置信度阈值')
        """)

    conn.commit()
    return True
