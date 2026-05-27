import re
import hashlib
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Any
from difflib import SequenceMatcher


class PhishingDetector:
    def __init__(self, redis_store=None):
        self.redis_store = redis_store
        self.legitimate_domains = set()
        self._init_common_legitimate_domains()
    
    def _init_common_legitimate_domains(self):
        self.legitimate_domains = {
            'google.com', 'gmail.com', 'microsoft.com', 'outlook.com',
            'apple.com', 'amazon.com', 'paypal.com', 'facebook.com',
            'twitter.com', 'linkedin.com', 'github.com', 'yahoo.com',
            'bankofamerica.com', 'chase.com', 'wellsfargo.com',
            'citibank.com', 'hsbc.com', 'barclays.com', 'santander.com'
        }
    
    def detect_phishing(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        results = {
            'is_phishing': False,
            'phishing_score': 0.0,
            'url_analysis': {},
            'sender_analysis': {},
            'content_analysis': {},
            'suspicious_indicators': []
        }
        
        url_analysis = self.analyze_urls(email_data)
        results['url_analysis'] = url_analysis
        results['phishing_score'] += url_analysis.get('risk_score', 0)
        
        sender_analysis = self.analyze_sender(email_data)
        results['sender_analysis'] = sender_analysis
        results['phishing_score'] += sender_analysis.get('risk_score', 0)
        
        content_analysis = self.analyze_phishing_content(email_data)
        results['content_analysis'] = content_analysis
        results['phishing_score'] += content_analysis.get('risk_score', 0)
        
        results['suspicious_indicators'] = (
            url_analysis.get('suspicious_urls', []) +
            sender_analysis.get('suspicious_senders', []) +
            content_analysis.get('suspicious_patterns', [])
        )
        
        results['is_phishing'] = results['phishing_score'] >= 5.0
        results['risk_level'] = self._get_risk_level(results['phishing_score'])
        
        return results
    
    def analyze_urls(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        combined_text = f"{subject} {body}"
        
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, combined_text)
        
        result = {
            'total_urls': len(urls),
            'suspicious_urls': [],
            'unique_domains': set(),
            'ip_urls': [],
            'homoglyph_urls': [],
            'redirect_urls': [],
            'risk_score': 0.0
        }
        
        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            if ':' in domain:
                domain = domain.split(':')[0]
            
            result['unique_domains'].add(domain)
            
            if self._is_ip_address(domain):
                result['ip_urls'].append(url)
                result['suspicious_urls'].append({
                    'url': url,
                    'type': 'ip_address',
                    'risk': 'high'
                })
                result['risk_score'] += 2.0
            
            if self._detect_homoglyph(domain):
                result['homoglyph_urls'].append(url)
                result['suspicious_urls'].append({
                    'url': url,
                    'type': 'homoglyph',
                    'domain': domain,
                    'risk': 'high'
                })
                result['risk_score'] += 3.0
            
            if self._detect_brand_spoofing(domain):
                result['suspicious_urls'].append({
                    'url': url,
                    'type': 'brand_spoofing',
                    'domain': domain,
                    'risk': 'critical'
                })
                result['risk_score'] += 4.0
            
            if 'login' in parsed.path.lower() or 'signin' in parsed.path.lower() or 'verify' in parsed.path.lower():
                result['redirect_urls'].append(url)
                result['risk_score'] += 1.0
        
        result['unique_domains'] = list(result['unique_domains'])
        result['domain_count'] = len(result['unique_domains'])
        
        if result['domain_count'] > 5:
            result['risk_score'] += 1.0
        
        return result
    
    def _is_ip_address(self, domain: str) -> bool:
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        return bool(re.match(ip_pattern, domain))
    
    def _detect_homoglyph(self, domain: str) -> bool:
        homoglyph_chars = {
            'о': 'o', 'а': 'a', 'е': 'e', 'р': 'p',
            'с': 'c', 'һ': 'h', 'і': 'i', 'ј': 'j',
            'ԛ': 'q', 'ѕ': 's', 'ԁ': 'd', 'Ԍ': 'g'
        }
        
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in domain)
        if has_cyrillic:
            return True
        
        suspicious_patterns = [
            r'0[0o]', r'[o0]0', r'[il]1', r'1[il]',
            r'[sz]5', r'5[sz]', r'[ou]8', r'8[ou]'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, domain):
                return True
        
        return False
    
    def _detect_brand_spoofing(self, domain: str) -> bool:
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return False
        
        main_domain = '.'.join(domain_parts[-2:])
        
        for legit_domain in self.legitimate_domains:
            if main_domain == legit_domain:
                return False
            
            similarity = SequenceMatcher(None, main_domain, legit_domain).ratio()
            if 0.7 < similarity < 1.0:
                return True
            
            if legit_domain.replace('.', '') in main_domain.replace('.', ''):
                if main_domain != legit_domain:
                    return True
        
        return False
    
    def analyze_sender(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        sender = email_data.get('sender', '')
        display_name = email_data.get('sender_name', '')
        reply_to = email_data.get('reply_to', '')
        recipients = email_data.get('recipients', [])
        
        result = {
            'sender': sender,
            'display_name': display_name,
            'suspicious_senders': [],
            'is_spoofed': False,
            'reply_to_mismatch': False,
            'unusual_recipients': False,
            'risk_score': 0.0
        }
        
        if not sender:
            return result
        
        sender_domain = sender.split('@')[-1].lower() if '@' in sender else ''
        
        if display_name and '@' in display_name:
            display_email = re.search(r'[\w\.-]+@[\w\.-]+', display_name)
            if display_email:
                display_domain = display_email.group().split('@')[-1].lower()
                if display_domain != sender_domain and display_domain:
                    result['is_spoofed'] = True
                    result['suspicious_senders'].append({
                        'type': 'display_name_spoof',
                        'display_domain': display_domain,
                        'sender_domain': sender_domain,
                        'risk': 'high'
                    })
                    result['risk_score'] += 4.0
        
        if reply_to and reply_to != sender:
            reply_to_domain = reply_to.split('@')[-1].lower() if '@' in reply_to else ''
            if reply_to_domain != sender_domain and reply_to_domain:
                result['reply_to_mismatch'] = True
                result['suspicious_senders'].append({
                    'type': 'reply_to_mismatch',
                    'reply_to': reply_to,
                    'sender': sender,
                    'risk': 'medium'
                })
                result['risk_score'] += 2.0
        
        if len(recipients) > 20:
            result['unusual_recipients'] = True
            result['risk_score'] += 1.0
        
        if self._detect_sender_domain_spoof(sender_domain):
            result['is_spoofed'] = True
            result['suspicious_senders'].append({
                'type': 'domain_spoof',
                'domain': sender_domain,
                'risk': 'critical'
            })
            result['risk_score'] += 5.0
        
        if self.redis_store:
            reputation = self.redis_store.get_sender_reputation(sender)
            if reputation < 30:
                result['risk_score'] += 2.0
        
        return result
    
    def _detect_sender_domain_spoof(self, domain: str) -> bool:
        return self._detect_brand_spoofing(domain)
    
    def analyze_phishing_content(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        combined_text = f"{subject} {body}".lower()
        
        result = {
            'suspicious_patterns': [],
            'urgency_count': 0,
            'threat_count': 0,
            'action_count': 0,
            'risk_score': 0.0
        }
        
        urgency_keywords = [
            'urgent', 'immediately', 'asap', 'right now', 'only today',
            'last chance', 'final notice', 'expires', 'deadline',
            'suspend', 'limited time', 'act now', 'hurry'
        ]
        
        threat_keywords = [
            'suspended', 'locked', 'blocked', 'disabled', 'terminated',
            'compromised', 'hacked', 'stolen', 'unauthorized',
            'security alert', 'verify account', 'confirm account'
        ]
        
        action_keywords = [
            'click here', 'click now', 'verify now', 'confirm now',
            'update now', 'login now', 'sign in now', 'download now',
            'open attachment', 'run attachment', 'enable macros'
        ]
        
        for keyword in urgency_keywords:
            if keyword in combined_text:
                result['urgency_count'] += combined_text.count(keyword)
        
        for keyword in threat_keywords:
            if keyword in combined_text:
                result['threat_count'] += combined_text.count(keyword)
                result['suspicious_patterns'].append({
                    'type': 'threat_language',
                    'keyword': keyword,
                    'risk': 'medium'
                })
        
        for keyword in action_keywords:
            if keyword in combined_text:
                result['action_count'] += combined_text.count(keyword)
        
        if result['urgency_count'] >= 3:
            result['risk_score'] += 2.0
        
        if result['threat_count'] >= 2:
            result['risk_score'] += 3.0
        
        if result['action_count'] >= 2:
            result['risk_score'] += 2.0
        
        if 'verify' in combined_text and 'account' in combined_text:
            result['risk_score'] += 2.0
            result['suspicious_patterns'].append({
                'type': 'verify_account',
                'risk': 'high'
            })
        
        if 'update' in combined_text and 'payment' in combined_text:
            result['risk_score'] += 2.0
        
        return result
    
    def _get_risk_level(self, score: float) -> str:
        if score >= 10:
            return 'critical'
        elif score >= 5:
            return 'high'
        elif score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def get_url_hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
