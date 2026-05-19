from typing import List, Dict, Optional
from .database import Database


class SensitiveWordModel:
    @staticmethod
    def get_all_words(category: str = None, is_active: bool = None) -> List[Dict]:
        db = Database()
        query = "SELECT * FROM sensitive_words WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        if is_active is not None:
            query += " AND is_active = %s"
            params.append(1 if is_active else 0)
        
        query += " ORDER BY category, severity DESC"
        
        return db.execute_query(query, params)

    @staticmethod
    def get_active_words(category: str = None) -> List[str]:
        words = SensitiveWordModel.get_all_words(category=category, is_active=True)
        return [w['word'] for w in words]

    @staticmethod
    def add_word(word: str, category: str, severity: str = 'medium', 
                match_mode: str = 'exact') -> int:
        db = Database()
        query = """
            INSERT INTO sensitive_words (word, category, severity, match_mode, is_active)
            VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE 
                category = VALUES(category),
                severity = VALUES(severity),
                match_mode = VALUES(match_mode),
                is_active = 1
        """
        return db.execute_update(query, (word, category, severity, match_mode))

    @staticmethod
    def add_words_batch(words: List[Dict]) -> int:
        db = Database()
        count = 0
        for word_data in words:
            count += SensitiveWordModel.add_word(
                word_data.get('word', ''),
                word_data.get('category', 'other'),
                word_data.get('severity', 'medium'),
                word_data.get('match_mode', 'exact')
            )
        return count

    @staticmethod
    def update_word(word_id: int, **kwargs) -> int:
        db = Database()
        allowed_fields = ['word', 'category', 'severity', 'match_mode', 'is_active']
        fields = [f for f in kwargs.keys() if f in allowed_fields]
        
        if not fields:
            return 0
        
        set_clause = ", ".join([f"{f} = %s" for f in fields])
        params = [kwargs[f] for f in fields]
        params.append(word_id)
        
        query = f"UPDATE sensitive_words SET {set_clause} WHERE id = %s"
        return db.execute_update(query, params)

    @staticmethod
    def delete_word(word_id: int) -> int:
        db = Database()
        query = "DELETE FROM sensitive_words WHERE id = %s"
        return db.execute_update(query, (word_id,))

    @staticmethod
    def toggle_word(word_id: int, is_active: bool) -> int:
        db = Database()
        query = "UPDATE sensitive_words SET is_active = %s WHERE id = %s"
        return db.execute_update(query, (1 if is_active else 0, word_id))

    @staticmethod
    def get_word_categories() -> List[Dict]:
        db = Database()
        query = """
            SELECT category, COUNT(*) as word_count, 
                   SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
            FROM sensitive_words 
            GROUP BY category
        """
        return db.execute_query(query)


class AuditRuleModel:
    @staticmethod
    def get_all_rules(rule_type: str = None, is_active: bool = None) -> List[Dict]:
        db = Database()
        query = "SELECT * FROM audit_rules WHERE 1=1"
        params = []
        
        if rule_type:
            query += " AND rule_type = %s"
            params.append(rule_type)
        
        if is_active is not None:
            query += " AND is_active = %s"
            params.append(1 if is_active else 0)
        
        query += " ORDER BY rule_type, threshold DESC"
        
        return db.execute_query(query, params)

    @staticmethod
    def get_active_rules(rule_type: str = None) -> List[Dict]:
        return AuditRuleModel.get_all_rules(rule_type=rule_type, is_active=True)

    @staticmethod
    def get_threshold(rule_type: str, violation_type: str) -> float:
        db = Database()
        query = """
            SELECT threshold FROM audit_rules 
            WHERE rule_type = %s AND violation_type = %s AND is_active = 1
            LIMIT 1
        """
        result = db.execute_query(query, (rule_type, violation_type))
        return result[0]['threshold'] if result else 0.7

    @staticmethod
    def add_rule(rule_name: str, rule_type: str, violation_type: str, 
                 threshold: float = 0.7, config_json: str = None, 
                 description: str = None) -> int:
        db = Database()
        query = """
            INSERT INTO audit_rules (rule_name, rule_type, violation_type, threshold, 
                                   config_json, description, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
        """
        return db.execute_update(query, (rule_name, rule_type, violation_type, 
                                       threshold, config_json, description))

    @staticmethod
    def update_rule(rule_id: int, **kwargs) -> int:
        db = Database()
        allowed_fields = ['rule_name', 'rule_type', 'violation_type', 
                         'threshold', 'config_json', 'description', 'is_active']
        fields = [f for f in kwargs.keys() if f in allowed_fields]
        
        if not fields:
            return 0
        
        set_clause = ", ".join([f"{f} = %s" for f in fields])
        params = [kwargs[f] for f in fields]
        params.append(rule_id)
        
        query = f"UPDATE audit_rules SET {set_clause} WHERE id = %s"
        return db.execute_update(query, params)

    @staticmethod
    def delete_rule(rule_id: int) -> int:
        db = Database()
        query = "DELETE FROM audit_rules WHERE id = %s"
        return db.execute_update(query, (rule_id,))

    @staticmethod
    def toggle_rule(rule_id: int, is_active: bool) -> int:
        db = Database()
        query = "UPDATE audit_rules SET is_active = %s WHERE id = %s"
        return db.execute_update(query, (1 if is_active else 0, rule_id))
