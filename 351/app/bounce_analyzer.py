import re
import time
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class BounceAnalyzer:
    def __init__(self, redis_store=None):
        self.redis_store = redis_store
        self.bounce_patterns = self._init_bounce_patterns()
    
    def _init_bounce_patterns(self) -> Dict[str, List[str]]:
        return {
            'hard_bounce': [
                r'user unknown',
                r'invalid recipient',
                r'no such user',
                r'address rejected',
                r'mailbox not found',
                r'does not exist',
                r'account disabled',
                r'user not found'
            ],
            'soft_bounce': [
                r'mailbox full',
                r'over quota',
                r'temporarily deferred',
                r'try again later',
                r'service unavailable',
                r'connection timed out',
                r'dns failure'
            ],
            'spam_rejection': [
                r'spam detected',
                r'content rejected',
                r'blacklisted',
                r'spamhaus',
                r'spam score',
                r'message rejected as spam',
                r'unsolicited bulk email'
            ],
            'virus_rejection': [
                r'virus detected',
                r'malware detected',
                r'infected',
                r'trojan detected',
                r'malicious content'
            ]
        }
    
    def analyze_bounce(self, bounce_email: Dict[str, Any]) -> Dict[str, Any]:
        subject = bounce_email.get('subject', '')
        body = bounce_email.get('body', '')
        combined_text = f"{subject} {body}".lower()
        
        result = {
            'is_bounce': False,
            'bounce_type': 'unknown',
            'original_sender': None,
            'original_recipient': None,
            'original_message_id': None,
            'bounce_reason': None,
            'risk_score': 0.0,
            'indicators': []
        }
        
        if 'mail delivery failed' in subject.lower() or 'returned mail' in subject.lower():
            result['is_bounce'] = True
        
        bounce_type, reason = self._classify_bounce_type(combined_text)
        if bounce_type != 'unknown':
            result['is_bounce'] = True
            result['bounce_type'] = bounce_type
            result['bounce_reason'] = reason
        
        original_sender = self._extract_original_sender(body)
        if original_sender:
            result['original_sender'] = original_sender
        
        original_recipient = self._extract_original_recipient(combined_text)
        if original_recipient:
            result['original_recipient'] = original_recipient
        
        message_id = self._extract_message_id(body)
        if message_id:
            result['original_message_id'] = message_id
        
        if result['is_bounce']:
            risk_score = self._calculate_bounce_risk(result)
            result['risk_score'] = risk_score
            
            if risk_score >= 7.0:
                result['indicators'].append('high_bounce_rate')
            elif risk_score >= 4.0:
                result['indicators'].append('moderate_bounce_rate')
            
            if bounce_type == 'spam_rejection':
                result['indicators'].append('spam_reported')
                result['risk_score'] += 3.0
            elif bounce_type == 'virus_rejection':
                result['indicators'].append('virus_detected')
                result['risk_score'] += 5.0
        
        if self.redis_store and result['original_sender']:
            self._record_bounce(result['original_sender'], result)
        
        return result
    
    def _classify_bounce_type(self, text: str) -> tuple:
        for bounce_type, patterns in self.bounce_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return bounce_type, pattern
        return 'unknown', None
    
    def _extract_original_sender(self, body: str) -> Optional[str]:
        patterns = [
            r'From:\s*([\w\.-]+@[\w\.-]+\.\w+)',
            r'Original-Sender:\s*([\w\.-]+@[\w\.-]+\.\w+)',
            r'X-Original-Sender:\s*([\w\.-]+@[\w\.-]+\.\w+)',
            r'Return-Path:\s*<([\w\.-]+@[\w\.-]+\.\w+)>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        
        return None
    
    def _extract_original_recipient(self, text: str) -> Optional[str]:
        patterns = [
            r'RCPT TO:\s*<?([\w\.-]+@[\w\.-]+\.\w+)>?',
            r'Final-Recipient:\s*rfc822;\s*([\w\.-]+@[\w\.-]+\.\w+)',
            r'Original-Recipient:\s*rfc822;\s*([\w\.-]+@[\w\.-]+\.\w+)',
            r'unknown recipient:\s*([\w\.-]+@[\w\.-]+\.\w+)',
            r'no such user:\s*([\w\.-]+@[\w\.-]+\.\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        
        return None
    
    def _extract_message_id(self, body: str) -> Optional[str]:
        pattern = r'Message-ID:\s*<([^>]+)>'
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _calculate_bounce_risk(self, bounce_result: Dict[str, Any]) -> float:
        if not self.redis_store or not bounce_result['original_sender']:
            return 0.0
        
        sender = bounce_result['original_sender']
        key = f"bounce_stats:{sender}"
        
        stats = self.redis_store.client.hgetall(key)
        if not stats:
            return 0.0
        
        total_sent = int(stats.get('total_sent', 1))
        total_bounces = int(stats.get('total_bounces', 0))
        
        bounce_rate = total_bounces / total_sent if total_sent > 0 else 0
        
        risk_score = bounce_rate * 10
        
        if bounce_rate > 0.5:
            risk_score += 3.0
        elif bounce_rate > 0.3:
            risk_score += 1.0
        
        return min(risk_score, 10.0)
    
    def _record_bounce(self, sender: str, bounce_result: Dict[str, Any]) -> None:
        key = f"bounce_stats:{sender}"
        
        pipe = self.redis_store.client.pipeline()
        pipe.hincrby(key, 'total_bounces', 1)
        pipe.hincrby(key, f"{bounce_result['bounce_type']}_count", 1)
        pipe.hset(key, 'last_bounce', str(time.time()))
        pipe.expire(key, 86400 * 30)
        pipe.execute()
    
    def record_successful_delivery(self, sender: str) -> None:
        if not self.redis_store:
            return
        
        key = f"bounce_stats:{sender}"
        self.redis_store.client.hincrby(key, 'total_sent', 1)
        self.redis_store.client.expire(key, 86400 * 30)
    
    def detect_hijacked_account(self, sender: str) -> Dict[str, Any]:
        if not self.redis_store:
            return {'is_hijacked': False}
        
        result = {
            'sender': sender,
            'is_hijacked': False,
            'confidence': 0.0,
            'indicators': [],
            'bounce_stats': {},
            'sending_pattern_anomaly': False
        }
        
        bounce_key = f"bounce_stats:{sender}"
        bounce_stats = self.redis_store.client.hgetall(bounce_key)
        
        if bounce_stats:
            total_sent = int(bounce_stats.get('total_sent', 0))
            total_bounces = int(bounce_stats.get('total_bounces', 0))
            spam_rejections = int(bounce_stats.get('spam_rejection_count', 0))
            virus_rejections = int(bounce_stats.get('virus_rejection_count', 0))
            
            result['bounce_stats'] = {
                'total_sent': total_sent,
                'total_bounces': total_bounces,
                'spam_rejections': spam_rejections,
                'virus_rejections': virus_rejections
            }
            
            bounce_rate = total_bounces / total_sent if total_sent > 0 else 0
            
            if bounce_rate > 0.4:
                result['indicators'].append('high_bounce_rate')
                result['confidence'] += 0.3
            
            if spam_rejections > 5:
                result['indicators'].append('multiple_spam_rejections')
                result['confidence'] += 0.4
            
            if virus_rejections > 0:
                result['indicators'].append('virus_detected_in_outgoing')
                result['confidence'] += 0.5
        
        pattern_anomaly = self._detect_sending_pattern_anomaly(sender)
        if pattern_anomaly['is_anomalous']:
            result['sending_pattern_anomaly'] = True
            result['indicators'].extend(pattern_anomaly['reasons'])
            result['confidence'] += pattern_anomaly['confidence_boost']
        
        reputation_key = f"reputation:{sender}"
        reputation_data = self.redis_store.client.hgetall(reputation_key)
        if reputation_data:
            current_reputation = float(reputation_data.get('score', 50.0))
            reputation_drop = 50.0 - current_reputation
            
            if reputation_drop > 30:
                result['indicators'].append('rapid_reputation_decline')
                result['confidence'] += 0.3
        
        similar_patterns = self._check_known_spam_patterns(sender)
        if similar_patterns:
            result['indicators'].append('matches_known_spam_patterns')
            result['confidence'] += 0.2
        
        result['is_hijacked'] = result['confidence'] >= 0.6
        
        return result
    
    def _detect_sending_pattern_anomaly(self, sender: str) -> Dict[str, Any]:
        result = {
            'is_anomalous': False,
            'reasons': [],
            'confidence_boost': 0.0
        }
        
        if not self.redis_store:
            return result
        
        rate_key = f"rate_limit:sender:{sender}"
        recent_count = self.redis_store.client.get(rate_key)
        
        if recent_count and int(recent_count) > 100:
            result['is_anomalous'] = True
            result['reasons'].append('unusual_sending_volume')
            result['confidence_boost'] += 0.3
        
        return result
    
    def _check_known_spam_patterns(self, sender: str) -> bool:
        if not self.redis_store:
            return False
        
        spam_patterns = self.redis_store.client.smembers('spam_patterns')
        return len(spam_patterns) > 0
    
    def get_hijacked_accounts(self, threshold: float = 0.6) -> List[Dict[str, Any]]:
        if not self.redis_store:
            return []
        
        hijacked_accounts = []
        bounce_keys = self.redis_store.client.keys('bounce_stats:*')
        
        for key in bounce_keys[:50]:
            sender = key.replace('bounce_stats:', '')
            detection = self.detect_hijacked_account(sender)
            
            if detection['confidence'] >= threshold:
                hijacked_accounts.append(detection)
        
        hijacked_accounts.sort(key=lambda x: x['confidence'], reverse=True)
        
        return hijacked_accounts
    
    def get_bounce_statistics(self, sender: str = None) -> Dict[str, Any]:
        if not self.redis_store:
            return {}
        
        if sender:
            key = f"bounce_stats:{sender}"
            stats = self.redis_store.client.hgetall(key)
            return {sender: stats} if stats else {}
        
        stats = {}
        bounce_keys = self.redis_store.client.keys('bounce_stats:*')
        
        for key in bounce_keys[:20]:
            sender = key.replace('bounce_stats:', '')
            sender_stats = self.redis_store.client.hgetall(key)
            stats[sender] = sender_stats
        
        return stats
