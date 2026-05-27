import re
import hashlib
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from difflib import SequenceMatcher


class EmailClustering:
    def __init__(self, redis_store=None):
        self.redis_store = redis_store
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words='english'
        )
        self.email_patterns = defaultdict(list)
        self.sender_patterns = defaultdict(lambda: {'count': 0, 'templates': []})
    
    def cluster_emails(self, emails: List[Dict[str, Any]], method: str = 'dbscan') -> Dict[str, Any]:
        if len(emails) < 2:
            return {'clusters': [], 'total_emails': len(emails), 'method': method}
        
        texts = []
        for email in emails:
            subject = email.get('subject', '')
            body = email.get('body', '')
            cleaned_text = self._clean_text(f"{subject} {body}")
            texts.append(cleaned_text)
        
        try:
            X = self.vectorizer.fit_transform(texts)
            
            if method == 'dbscan':
                clusters = self._cluster_dbscan(X)
            elif method == 'kmeans':
                n_clusters = min(5, len(emails) // 2)
                clusters = self._cluster_kmeans(X, n_clusters)
            else:
                clusters = self._cluster_similarity(texts)
            
            cluster_results = []
            for cluster_id, email_indices in clusters.items():
                cluster_emails = [emails[i] for i in email_indices]
                cluster_info = self._analyze_cluster(cluster_emails, texts, email_indices)
                cluster_results.append({
                    'cluster_id': cluster_id,
                    'size': len(email_indices),
                    'email_indices': email_indices,
                    **cluster_info
                })
            
            return {
                'clusters': cluster_results,
                'total_emails': len(emails),
                'num_clusters': len(cluster_results),
                'method': method
            }
        
        except Exception as e:
            return {'error': str(e), 'clusters': [], 'total_emails': len(emails)}
    
    def _clean_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'http\S+', 'URL', text)
        text = re.sub(r'\S+@\S+', 'EMAIL', text)
        text = re.sub(r'\d+', 'NUM', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _cluster_dbscan(self, X, eps: float = 0.5, min_samples: int = 2) -> Dict[int, List[int]]:
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
        labels = clustering.fit_predict(X)
        
        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:
                clusters[label].append(idx)
        
        return dict(clusters)
    
    def _cluster_kmeans(self, X, n_clusters: int = 3) -> Dict[int, List[int]]:
        if n_clusters < 1:
            n_clusters = 1
        
        clustering = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = clustering.fit_predict(X)
        
        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters[label].append(idx)
        
        return dict(clusters)
    
    def _cluster_similarity(self, texts: List[str], threshold: float = 0.7) -> Dict[int, List[int]]:
        clusters = {}
        cluster_id = 0
        
        for i, text1 in enumerate(texts):
            assigned = False
            for cid, indices in clusters.items():
                text2 = texts[indices[0]]
                similarity = SequenceMatcher(None, text1, text2).ratio()
                if similarity >= threshold:
                    clusters[cid].append(i)
                    assigned = True
                    break
            
            if not assigned:
                clusters[cluster_id] = [i]
                cluster_id += 1
        
        return clusters
    
    def _analyze_cluster(self, emails: List[Dict[str, Any]], texts: List[str], indices: List[int]) -> Dict[str, Any]:
        subjects = [e.get('subject', '') for e in emails]
        senders = [e.get('sender', '') for e in emails]
        bodies = [texts[i] for i in indices]
        
        common_subject_pattern = self._find_common_pattern(subjects)
        common_body_pattern = self._extract_common_phrases(bodies)
        
        sender_domains = []
        for sender in senders:
            if '@' in sender:
                domain = sender.split('@')[-1].lower()
                sender_domains.append(domain)
        
        domain_counter = Counter(sender_domains)
        top_domains = domain_counter.most_common(3)
        
        subject_similarity = self._calculate_group_similarity(subjects)
        body_similarity = self._calculate_group_similarity(bodies)
        
        is_spam_pattern = (
            subject_similarity > 0.7 or
            body_similarity > 0.6 or
            len(top_domains) == 1
        )
        
        return {
            'common_subject_pattern': common_subject_pattern,
            'common_phrases': common_body_pattern[:5],
            'sender_domains': top_domains,
            'unique_senders': len(set(senders)),
            'subject_similarity': subject_similarity,
            'body_similarity': body_similarity,
            'is_likely_spam_campaign': is_spam_pattern,
            'pattern_signature': self._generate_pattern_signature(common_subject_pattern, common_body_pattern)
        }
    
    def _find_common_pattern(self, texts: List[str]) -> str:
        if not texts:
            return ''
        
        words_list = [t.lower().split() for t in texts]
        if not words_list:
            return ''
        
        common_words = set(words_list[0])
        for words in words_list[1:]:
            common_words.intersection_update(words)
        
        return ' '.join(sorted(common_words)[:10])
    
    def _extract_common_phrases(self, texts: List[str], min_length: int = 3) -> List[Tuple[str, int]]:
        phrase_counter = Counter()
        
        for text in texts:
            words = text.split()
            for i in range(len(words) - min_length + 1):
                phrase = ' '.join(words[i:i + min_length])
                phrase_counter[phrase] += 1
        
        return [(phrase, count) for phrase, count in phrase_counter.most_common(10) if count >= 2]
    
    def _calculate_group_similarity(self, texts: List[str]) -> float:
        if len(texts) < 2:
            return 1.0
        
        total_similarity = 0.0
        comparisons = 0
        
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                similarity = SequenceMatcher(None, texts[i], texts[j]).ratio()
                total_similarity += similarity
                comparisons += 1
        
        return total_similarity / comparisons if comparisons > 0 else 0.0
    
    def _generate_pattern_signature(self, subject_pattern: str, phrases: List[Tuple[str, int]]) -> str:
        signature_text = f"{subject_pattern}|{'|'.join([p[0] for p in phrases[:3]])}"
        return hashlib.md5(signature_text.encode()).hexdigest()[:16]
    
    def detect_spam_campaign(self, recent_emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        cluster_result = self.cluster_emails(recent_emails, method='dbscan')
        
        campaigns = []
        for cluster in cluster_result.get('clusters', []):
            if cluster.get('is_likely_spam_campaign') and cluster['size'] >= 3:
                campaigns.append({
                    'campaign_id': cluster['cluster_id'],
                    'pattern_signature': cluster.get('pattern_signature'),
                    'size': cluster['size'],
                    'sender_domains': cluster.get('sender_domains', []),
                    'common_pattern': cluster.get('common_subject_pattern', ''),
                    'risk_level': 'high' if cluster['size'] >= 10 else 'medium'
                })
        
        return {
            'total_emails_analyzed': cluster_result.get('total_emails', 0),
            'detected_campaigns': len(campaigns),
            'campaigns': campaigns
        }
    
    def add_email_to_pattern_analysis(self, email_data: Dict[str, Any], is_spam: bool) -> str:
        sender = email_data.get('sender', 'unknown')
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        pattern_sig = self._generate_pattern_signature(subject, [(body[:50], 1)])
        
        sender_key = f"sender_pattern:{sender}"
        pattern_key = f"pattern:{pattern_sig}"
        
        if self.redis_store:
            self.redis_store.client.hincrby(sender_key, 'total_sent', 1)
            if is_spam:
                self.redis_store.client.hincrby(sender_key, 'spam_count', 1)
            
            self.redis_store.client.hincrby(pattern_key, 'occurrences', 1)
            self.redis_store.client.hset(pattern_key, 'last_seen', str(__import__('time').time()))
            
            if is_spam:
                self.redis_store.client.sadd(f"spam_patterns", pattern_sig)
        
        return pattern_sig
    
    def get_similar_patterns(self, email_data: Dict[str, Any], threshold: float = 0.7) -> List[Dict[str, Any]]:
        if not self.redis_store:
            return []
        
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        current_text = self._clean_text(f"{subject} {body}")
        
        similar_patterns = []
        spam_patterns = self.redis_store.client.smembers('spam_patterns')
        
        for pattern_sig in list(spam_patterns)[:20]:
            pattern_key = f"pattern:{pattern_sig}"
            pattern_data = self.redis_store.client.hgetall(pattern_key)
            
            if pattern_data:
                similar_patterns.append({
                    'pattern_signature': pattern_sig,
                    'occurrences': int(pattern_data.get('occurrences', 0)),
                    'last_seen': pattern_data.get('last_seen', '')
                })
        
        return similar_patterns
