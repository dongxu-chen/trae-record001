import re
from typing import Dict, List, Any, Callable, Tuple
from config import Config


class RuleEngine:
    def __init__(self, redis_store):
        self.redis_store = redis_store
        self.default_rules = self._init_default_rules()
        self.custom_rules = []
    
    def _init_default_rules(self) -> Dict[str, Dict[str, Any]]:
        return {
            'blacklist_ip': {
                'func': self._check_blacklist_ip,
                'priority': Config.RULE_PRIORITIES['blacklist_ip'],
                'weight': Config.RULE_WEIGHTS['blacklist_ip']
            },
            'blacklist_sender': {
                'func': self._check_blacklist_sender,
                'priority': Config.RULE_PRIORITIES['blacklist_sender'],
                'weight': Config.RULE_WEIGHTS['blacklist_sender']
            },
            'blacklist_keyword': {
                'func': self._check_blacklist_keywords,
                'priority': Config.RULE_PRIORITIES['blacklist_keyword'],
                'weight': Config.RULE_WEIGHTS['blacklist_keyword']
            },
            'suspicious_attachment': {
                'func': self._check_suspicious_attachment,
                'priority': Config.RULE_PRIORITIES['suspicious_attachment'],
                'weight': Config.RULE_WEIGHTS['suspicious_attachment']
            },
            'too_many_links': {
                'func': self._check_too_many_links,
                'priority': Config.RULE_PRIORITIES['too_many_links'],
                'weight': Config.RULE_WEIGHTS['too_many_links']
            },
            'excessive_special_chars': {
                'func': self._check_excessive_special_chars,
                'priority': Config.RULE_PRIORITIES['excessive_special_chars'],
                'weight': Config.RULE_WEIGHTS['excessive_special_chars']
            },
            'all_caps_subject': {
                'func': self._check_all_caps_subject,
                'priority': Config.RULE_PRIORITIES['all_caps_subject'],
                'weight': Config.RULE_WEIGHTS['all_caps_subject']
            },
            'short_body': {
                'func': self._check_short_body,
                'priority': Config.RULE_PRIORITIES['short_body'],
                'weight': Config.RULE_WEIGHTS['short_body']
            }
        }
    
    def _check_blacklist_keywords(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        keywords = self.redis_store.get_blacklist('keywords')
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        combined_text = f"{subject} {body}"
        
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in combined_text:
                matched_keywords.append(keyword)
        
        return {
            'matched': len(matched_keywords) > 0,
            'matched_keywords': matched_keywords
        }
    
    def _check_blacklist_sender(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        sender = email_data.get('sender', '').lower()
        is_blacklisted = self.redis_store.is_blacklisted('senders', sender)
        
        return {
            'matched': is_blacklisted,
            'sender': sender
        }
    
    def _check_blacklist_ip(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        ip = email_data.get('sender_ip', '')
        is_blacklisted = self.redis_store.is_blacklisted('ips', ip)
        
        return {
            'matched': is_blacklisted,
            'ip': ip
        }
    
    def _check_suspicious_attachment(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        attachments = email_data.get('attachments', [])
        suspicious_extensions = {'exe', 'scr', 'bat', 'com', 'pif', 'vbs', 'js', 'jar', 'msi'}
        matched_attachments = []
        
        for attachment in attachments:
            ext = attachment.split('.')[-1].lower() if '.' in attachment else ''
            if ext in suspicious_extensions:
                matched_attachments.append(attachment)
        
        return {
            'matched': len(matched_attachments) > 0,
            'matched_attachments': matched_attachments
        }
    
    def _check_too_many_links(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        combined_text = f"{subject} {body}"
        
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        links = re.findall(url_pattern, combined_text)
        
        too_many = len(links) > 5
        
        return {
            'matched': too_many,
            'link_count': len(links)
        }
    
    def _check_all_caps_subject(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        subject = email_data.get('subject', '')
        
        if len(subject) < 5:
            return {'matched': False}
        
        all_caps = subject.isupper()
        
        return {
            'matched': all_caps,
            'subject': subject
        }
    
    def _check_excessive_special_chars(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        combined_text = f"{subject} {body}"
        
        special_chars = set('!$%&*@#?')
        count = sum(1 for c in combined_text if c in special_chars)
        
        excessive = count > 15
        
        return {
            'matched': excessive,
            'special_char_count': count
        }
    
    def _check_short_body(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        body = email_data.get('body', '')
        
        too_short = len(body.strip()) < 20 and len(body.strip()) > 0
        
        return {
            'matched': too_short,
            'body_length': len(body.strip())
        }
    
    def _evaluate_custom_rule(self, rule: Dict[str, Any], email_data: Dict[str, Any]) -> Dict[str, Any]:
        rule_type = rule.get('type')
        condition = rule.get('condition', {})
        matched = False
        
        if rule_type == 'keyword_match':
            field = condition.get('field', 'body')
            keywords = condition.get('keywords', [])
            text = email_data.get(field, '').lower()
            
            matched = any(kw.lower() in text for kw in keywords)
        
        elif rule_type == 'regex_match':
            field = condition.get('field', 'body')
            pattern = condition.get('pattern', '')
            text = email_data.get(field, '')
            
            try:
                matched = bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                matched = False
        
        elif rule_type == 'sender_domain':
            sender = email_data.get('sender', '')
            domains = condition.get('domains', [])
            
            matched = any(sender.lower().endswith(f"@{d.lower()}") for d in domains)
        
        elif rule_type == 'attachment_name':
            attachments = email_data.get('attachments', [])
            pattern = condition.get('pattern', '')
            
            try:
                matched = any(re.search(pattern, a, re.IGNORECASE) for a in attachments)
            except re.error:
                matched = False
        
        return {
            'matched': matched,
            'rule_id': rule.get('id'),
            'rule_name': rule.get('name')
        }
    
    def _get_sorted_default_rules(self) -> List[Tuple[str, Dict[str, Any]]]:
        sorted_rules = sorted(
            self.default_rules.items(),
            key=lambda x: x[1]['priority'],
            reverse=True
        )
        return sorted_rules
    
    def evaluate(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        results = {
            'default_rules': {},
            'custom_rules': [],
            'total_score': 0.0,
            'risk_level': 'low',
            'high_priority_triggered': [],
            'early_block': False,
            'execution_order': []
        }
        
        sorted_rules = self._get_sorted_default_rules()
        
        for rule_name, rule_info in sorted_rules:
            priority = rule_info['priority']
            weight = rule_info['weight']
            
            result = rule_info['func'](email_data)
            result['priority'] = priority
            result['weight'] = weight
            
            if result['matched']:
                result['score'] = weight
                results['total_score'] += weight
                
                if priority >= Config.HIGH_PRIORITY_THRESHOLD:
                    results['high_priority_triggered'].append({
                        'rule': rule_name,
                        'priority': priority
                    })
            else:
                result['score'] = 0
            
            results['default_rules'][rule_name] = result
            results['execution_order'].append({
                'rule': rule_name,
                'priority': priority,
                'matched': result['matched']
            })
            
            if results['total_score'] >= Config.AUTO_BLOCK_THRESHOLD:
                results['early_block'] = True
                results['early_block_reason'] = f"Rule {rule_name} triggered, score exceeded auto-block threshold"
                break
        
        if not results['early_block']:
            custom_rules = self.redis_store.get_all_rules()
            custom_rules_with_priority = []
            
            for rule in custom_rules:
                if rule.get('enabled', True):
                    priority = rule.get('priority', 50)
                    custom_rules_with_priority.append((priority, rule))
            
            custom_rules_with_priority.sort(key=lambda x: x[0], reverse=True)
            
            for priority, rule in custom_rules_with_priority:
                result = self._evaluate_custom_rule(rule, email_data)
                result['priority'] = priority
                result['weight'] = rule.get('weight', 1.0)
                
                if result['matched']:
                    result['score'] = result['weight']
                    results['total_score'] += result['weight']
                    
                    if priority >= Config.HIGH_PRIORITY_THRESHOLD:
                        results['high_priority_triggered'].append({
                            'rule': rule.get('name'),
                            'priority': priority
                        })
                else:
                    result['score'] = 0
                
                results['custom_rules'].append(result)
                results['execution_order'].append({
                    'rule': rule.get('name'),
                    'priority': priority,
                    'matched': result['matched']
                })
                
                if results['total_score'] >= Config.AUTO_BLOCK_THRESHOLD:
                    results['early_block'] = True
                    results['early_block_reason'] = f"Custom rule {rule.get('name')} triggered, score exceeded auto-block threshold"
                    break
        
        if results['total_score'] >= 10:
            results['risk_level'] = 'critical'
        elif results['total_score'] >= 5:
            results['risk_level'] = 'high'
        elif results['total_score'] >= 2:
            results['risk_level'] = 'medium'
        
        return results
    
    def get_spam_probability_from_rules(self, rule_score: float) -> float:
        max_score = sum(Config.RULE_WEIGHTS.values()) + 10
        normalized_score = min(rule_score / max_score, 1.0)
        return normalized_score
