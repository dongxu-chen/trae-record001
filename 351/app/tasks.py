from celery_app import celery
from app.redis_store import RedisStore
from app.classifier import SpamClassifier
from app.rule_engine import RuleEngine
from app.text_cleaner import TextCleaner
from app.phishing_detector import PhishingDetector
from app.email_clustering import EmailClustering
from app.bounce_analyzer import BounceAnalyzer
from config import Config
import uuid
import json


@celery.task(name='tasks.classify_email', bind=True)
def classify_email_task(self, email_data: dict) -> dict:
    redis_store = RedisStore()
    classifier = SpamClassifier()
    rule_engine = RuleEngine(redis_store)
    phishing_detector = PhishingDetector(redis_store)
    email_clustering = EmailClustering(redis_store)
    
    email_id = email_data.get('email_id', str(uuid.uuid4()))
    
    redis_store.save_email(email_id, email_data)
    
    ip_count = redis_store.increment_ip_count(email_data.get('sender_ip', 'unknown'))
    
    sender = email_data.get('sender', '')
    sender_reputation = redis_store.get_sender_reputation(sender)
    
    model_result = classifier.classify_email(email_data)
    
    rule_result = rule_engine.evaluate(email_data)
    rule_based_prob = rule_engine.get_spam_probability_from_rules(rule_result['total_score'])
    
    phishing_result = None
    if Config.PHISHING_DETECTION_ENABLED:
        phishing_result = phishing_detector.detect_phishing(email_data)
    
    similar_patterns = []
    pattern_signature = None
    if Config.CLUSTERING_ENABLED:
        similar_patterns = email_clustering.get_similar_patterns(email_data)
    
    model_weight = 0.5
    rule_weight = 0.25
    reputation_weight = 0.1
    phishing_weight = Config.PHISHING_SCORE_WEIGHT if phishing_result else 0.0
    
    total_weight = model_weight + rule_weight + reputation_weight + phishing_weight
    if total_weight > 0:
        model_weight /= total_weight
        rule_weight /= total_weight
        reputation_weight /= total_weight
        phishing_weight /= total_weight
    
    reputation_factor = (100 - sender_reputation) / 100
    phishing_factor = phishing_result.get('phishing_score', 0) / 10 if phishing_result else 0
    
    final_spam_prob = (
        model_result['spam_probability'] * model_weight +
        rule_based_prob * rule_weight +
        reputation_factor * reputation_weight +
        phishing_factor * phishing_weight
    )
    
    final_spam_prob = max(0.0, min(1.0, final_spam_prob))
    is_spam = final_spam_prob >= Config.SPAM_THRESHOLD
    
    is_phishing = False
    if phishing_result:
        is_phishing = phishing_result.get('is_phishing', False)
        if phishing_result.get('phishing_score', 0) >= Config.PHISHING_AUTO_BLOCK_THRESHOLD:
            is_spam = True
    
    rate_limit_exceeded = ip_count > Config.MAX_EMAILS_PER_WINDOW
    
    if Config.CLUSTERING_ENABLED and is_spam:
        pattern_signature = email_clustering.add_email_to_pattern_analysis(email_data, True)
    
    final_result = {
        'email_id': email_id,
        'is_spam': is_spam,
        'is_phishing': is_phishing,
        'spam_probability': float(final_spam_prob),
        'ham_probability': float(1 - final_spam_prob),
        'threshold': Config.SPAM_THRESHOLD,
        'model_result': model_result,
        'rule_result': rule_result,
        'phishing_result': phishing_result,
        'similar_spam_patterns': similar_patterns,
        'pattern_signature': pattern_signature,
        'sender_reputation': sender_reputation,
        'sender_ip_count': ip_count,
        'rate_limit_exceeded': rate_limit_exceeded,
        'score_breakdown': {
            'model_score': model_result['spam_probability'],
            'rule_score': rule_based_prob,
            'reputation_score': reputation_factor,
            'phishing_score': phishing_factor,
            'model_weight': model_weight,
            'rule_weight': rule_weight,
            'reputation_weight': reputation_weight,
            'phishing_weight': phishing_weight
        }
    }
    
    redis_store.save_classification_result(email_id, final_result)
    
    return final_result


@celery.task(name='tasks.train_model')
def train_model_task(training_data: list) -> dict:
    classifier = SpamClassifier()
    
    texts = [item['text'] for item in training_data]
    labels = [item['label'] for item in training_data]
    
    metrics = classifier.train(texts, labels)
    
    return metrics


@celery.task(name='tasks.update_reputation')
def update_reputation_task(sender: str, feedback_type: str) -> dict:
    redis_store = RedisStore()
    
    if feedback_type == 'correct_spam' or feedback_type == 'correct_ham':
        delta = Config.FEEDBACK_REPUTATION_BONUS
    else:
        delta = Config.FEEDBACK_REPUTATION_PENALTY
    
    new_reputation = redis_store.update_sender_reputation(sender, delta)
    
    return {
        'sender': sender,
        'feedback_type': feedback_type,
        'delta': delta,
        'new_reputation': new_reputation
    }


@celery.task(name='tasks.process_feedback')
def process_feedback_task(email_id: str, feedback_data: dict) -> dict:
    redis_store = RedisStore()
    classifier = SpamClassifier()
    
    email = redis_store.get_email(email_id)
    original_result = redis_store.get_classification_result(email_id)
    
    if not email or not original_result:
        return {'error': 'Email or classification result not found'}
    
    redis_store.save_feedback(email_id, feedback_data)
    
    is_correct = feedback_data.get('is_correct', False)
    sender = email.get('sender', '')
    
    if is_correct:
        feedback_type = 'correct_spam' if original_result.get('is_spam') else 'correct_ham'
        corrected_label = 1 if original_result.get('is_spam') else 0
    else:
        feedback_type = 'wrong_spam' if original_result.get('is_spam') else 'wrong_ham'
        corrected_label = 0 if original_result.get('is_spam') else 1
    
    update_reputation_task.delay(sender, feedback_type)
    
    online_learning_result = None
    if Config.ONLINE_LEARNING_ENABLED:
        cleaned_result = TextCleaner.extract_plain_text(email)
        cleaned_text = cleaned_result['cleaned_text']
        
        if cleaned_text and len(cleaned_text) > 10:
            online_learning_result = classifier.online_learn_single(cleaned_text, corrected_label)
            
            pending_feedback = redis_store.client.incr('pending_feedback_count')
            if pending_feedback >= Config.ONLINE_LEARNING_BATCH_SIZE:
                incremental_model_update.delay()
                redis_store.client.set('pending_feedback_count', 0)
    
    return {
        'email_id': email_id,
        'feedback_type': feedback_type,
        'sender': sender,
        'is_correct': is_correct,
        'corrected_label': corrected_label,
        'online_learning': online_learning_result
    }


@celery.task(name='tasks.online_learn_single')
def online_learn_single_task(text: str, label: int) -> dict:
    classifier = SpamClassifier()
    
    result = classifier.online_learn_single(text, label)
    
    return result


@celery.task(name='tasks.incremental_model_update')
def incremental_model_update() -> dict:
    redis_store = RedisStore()
    classifier = SpamClassifier()
    
    feedback_keys = redis_store.client.keys('feedback:*')
    
    if len(feedback_keys) < 1:
        return {'error': 'No feedback data available for incremental update'}
    
    texts = []
    labels = []
    
    for key in feedback_keys[-100:]:
        feedback_data = json.loads(redis_store.client.get(key) or '{}')
        email_id = key.replace('feedback:', '')
        email = redis_store.get_email(email_id)
        original_result = redis_store.get_classification_result(email_id)
        
        if email and original_result:
            is_correct = feedback_data.get('is_correct', True)
            
            cleaned_result = TextCleaner.extract_plain_text(email)
            cleaned_text = cleaned_result['cleaned_text']
            
            if cleaned_text and len(cleaned_text) > 10:
                if is_correct:
                    label = 1 if original_result.get('is_spam') else 0
                else:
                    label = 0 if original_result.get('is_spam') else 1
                
                texts.append(cleaned_text)
                labels.append(label)
    
    if len(texts) < Config.ONLINE_LEARNING_BATCH_SIZE:
        return {
            'error': 'Not enough feedback data',
            'available_samples': len(texts),
            'required_samples': Config.ONLINE_LEARNING_BATCH_SIZE
        }
    
    result = classifier.partial_fit(texts, labels)
    
    return {
        **result,
        'samples_used': len(texts),
        'timestamp': __import__('time').time()
    }


@celery.task(name='tasks.scheduled_hourly_update')
def scheduled_hourly_update() -> dict:
    result = incremental_model_update()
    
    return {
        'task': 'hourly_model_update',
        'result': result,
        'timestamp': __import__('time').time()
    }


@celery.task(name='tasks.batch_classify')
def batch_classify_task(emails: list) -> list:
    results = []
    
    for email_data in emails:
        result = classify_email_task(email_data)
        results.append(result)
    
    return results


@celery.task(name='tasks.analyze_phishing')
def analyze_phishing_task(email_data: dict) -> dict:
    redis_store = RedisStore()
    phishing_detector = PhishingDetector(redis_store)
    
    result = phishing_detector.detect_phishing(email_data)
    
    return result


@celery.task(name='tasks.cluster_emails')
def cluster_emails_task(emails: list, method: str = 'dbscan') -> dict:
    redis_store = RedisStore()
    email_clustering = EmailClustering(redis_store)
    
    result = email_clustering.cluster_emails(emails, method)
    
    return result


@celery.task(name='tasks.detect_spam_campaign')
def detect_spam_campaign_task(recent_emails: list) -> dict:
    redis_store = RedisStore()
    email_clustering = EmailClustering(redis_store)
    
    result = email_clustering.detect_spam_campaign(recent_emails)
    
    return result


@celery.task(name='tasks.analyze_bounce')
def analyze_bounce_task(bounce_email: dict) -> dict:
    redis_store = RedisStore()
    bounce_analyzer = BounceAnalyzer(redis_store)
    
    result = bounce_analyzer.analyze_bounce(bounce_email)
    
    return result


@celery.task(name='tasks.detect_hijacked_accounts')
def detect_hijacked_accounts_task(threshold: float = None) -> dict:
    redis_store = RedisStore()
    bounce_analyzer = BounceAnalyzer(redis_store)
    
    if threshold is None:
        threshold = Config.BOUNCE_HIJACK_THRESHOLD
    
    hijacked_accounts = bounce_analyzer.get_hijacked_accounts(threshold)
    
    return {
        'total_detected': len(hijacked_accounts),
        'threshold': threshold,
        'hijacked_accounts': hijacked_accounts
    }


@celery.task(name='tasks.get_bounce_stats')
def get_bounce_stats_task(sender: str = None) -> dict:
    redis_store = RedisStore()
    bounce_analyzer = BounceAnalyzer(redis_store)
    
    stats = bounce_analyzer.get_bounce_statistics(sender)
    
    return stats
