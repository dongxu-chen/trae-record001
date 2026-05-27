import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', f'redis://{REDIS_HOST}:{REDIS_PORT}/2')
    
    MODEL_PATH = os.getenv('MODEL_PATH', './models/spam_classifier.pkl')
    VECTORIZER_PATH = os.getenv('VECTORIZER_PATH', './models/vectorizer.pkl')
    
    SPAM_THRESHOLD = float(os.getenv('SPAM_THRESHOLD', 0.5))
    
    MAX_EMAIL_SIZE = int(os.getenv('MAX_EMAIL_SIZE', 10 * 1024 * 1024))
    
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 3600))
    MAX_EMAILS_PER_WINDOW = int(os.getenv('MAX_EMAILS_PER_WINDOW', 100))
    
    REPUTATION_DECAY_DAYS = int(os.getenv('REPUTATION_DECAY_DAYS', 30))
    INITIAL_REPUTATION = float(os.getenv('INITIAL_REPUTATION', 50.0))
    MIN_REPUTATION = float(os.getenv('MIN_REPUTATION', 0.0))
    MAX_REPUTATION = float(os.getenv('MAX_REPUTATION', 100.0))
    
    FEEDBACK_REPUTATION_BONUS = float(os.getenv('FEEDBACK_REPUTATION_BONUS', 5.0))
    FEEDBACK_REPUTATION_PENALTY = float(os.getenv('FEEDBACK_REPUTATION_PENALTY', -10.0))

    ONLINE_LEARNING_ENABLED = os.getenv('ONLINE_LEARNING_ENABLED', 'true').lower() == 'true'
    ONLINE_LEARNING_BATCH_SIZE = int(os.getenv('ONLINE_LEARNING_BATCH_SIZE', 5))
    MODEL_UPDATE_INTERVAL_HOURS = int(os.getenv('MODEL_UPDATE_INTERVAL_HOURS', 1))

    RULE_WEIGHTS = {
        'blacklist_keyword': 3.0,
        'blacklist_sender': 5.0,
        'blacklist_ip': 5.0,
        'suspicious_attachment': 2.5,
        'too_many_links': 2.0,
        'all_caps_subject': 1.5,
        'excessive_special_chars': 2.0,
        'short_body': 1.0,
    }

    RULE_PRIORITIES = {
        'blacklist_ip': 100,
        'blacklist_sender': 90,
        'blacklist_keyword': 80,
        'suspicious_attachment': 70,
        'too_many_links': 60,
        'excessive_special_chars': 50,
        'all_caps_subject': 40,
        'short_body': 30,
    }

    HIGH_PRIORITY_THRESHOLD = 80
    AUTO_BLOCK_THRESHOLD = 10.0

    PHISHING_DETECTION_ENABLED = os.getenv('PHISHING_DETECTION_ENABLED', 'true').lower() == 'true'
    PHISHING_SCORE_WEIGHT = float(os.getenv('PHISHING_SCORE_WEIGHT', 0.3))
    PHISHING_AUTO_BLOCK_THRESHOLD = float(os.getenv('PHISHING_AUTO_BLOCK_THRESHOLD', 8.0))

    CLUSTERING_ENABLED = os.getenv('CLUSTERING_ENABLED', 'true').lower() == 'true'
    CLUSTERING_SIMILARITY_THRESHOLD = float(os.getenv('CLUSTERING_SIMILARITY_THRESHOLD', 0.7))

    BOUNCE_ANALYSIS_ENABLED = os.getenv('BOUNCE_ANALYSIS_ENABLED', 'true').lower() == 'true'
    BOUNCE_HIJACK_THRESHOLD = float(os.getenv('BOUNCE_HIJACK_THRESHOLD', 0.6))
    BOUNCE_RATE_ALERT_THRESHOLD = float(os.getenv('BOUNCE_RATE_ALERT_THRESHOLD', 0.4))
