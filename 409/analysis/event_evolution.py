import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)

try:
    from gensim import corpora, models
    from gensim.models.coherencemodel import CoherenceModel
    GENSIM_AVAILABLE = True
except ImportError:
    GENSIM_AVAILABLE = False
    logger.warning("Gensim not available. Event evolution will use fallback methods.")

from .text_processor import TextProcessor


class EventEvolutionAnalyzer:
    def __init__(self):
        self.text_processor = TextProcessor()
        self.event_clusters = {}
        self.time_windows = []
        self.topic_evolution = []
    
    def _group_by_time_window(self, posts: List[Dict], window_hours: int = 1) -> Dict[str, List[Dict]]:
        windows = defaultdict(list)
        
        for post in posts:
            timestamp = post.get('timestamp')
            if not timestamp:
                continue
            
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except:
                    continue
            
            window_key = timestamp.strftime('%Y-%m-%d %H:00:00')
            windows[window_key].append(post)
        
        return dict(sorted(windows.items()))
    
    def _extract_keywords_from_posts(self, posts: List[Dict], top_k: int = 20) -> List[Tuple[str, int]]:
        all_tokens = []
        for post in posts:
            content = post.get('content', '')
            tokens = self.text_processor.tokenize(content)
            all_tokens.extend(tokens)
        
        word_freq = Counter(all_tokens)
        return word_freq.most_common(top_k)
    
    def _calculate_keyword_trend(self, keyword: str, time_windows: Dict[str, List[Dict]]) -> List[Dict]:
        trend = []
        for window_key, posts in sorted(time_windows.items()):
            count = 0
            total_posts = len(posts)
            
            for post in posts:
                content = post.get('content', '').lower()
                if keyword.lower() in content:
                    count += 1
            
            trend.append({
                'time_window': window_key,
                'count': count,
                'frequency': count / total_posts if total_posts > 0 else 0,
                'total_posts': total_posts
            })
        
        return trend
    
    def detect_events(self, posts: List[Dict], min_posts: int = 5) -> List[Dict]:
        if not posts:
            return []
        
        time_windows = self._group_by_time_window(posts)
        events = []
        
        all_keywords = set()
        for window_posts in time_windows.values():
            keywords = self._extract_keywords_from_posts(window_posts, top_k=30)
            for kw, _ in keywords:
                all_keywords.add(kw)
        
        for keyword in all_keywords:
            trend = self._calculate_keyword_trend(keyword, time_windows)
            
            if not trend:
                continue
            
            counts = [t['count'] for t in trend]
            max_count = max(counts) if counts else 0
            
            if max_count >= min_posts:
                peak_index = counts.index(max_count)
                peak_time = trend[peak_index]['time_window']
                
                growth_rate = 0
                if peak_index > 0:
                    prev_count = trend[peak_index - 1]['count']
                    if prev_count > 0:
                        growth_rate = (max_count - prev_count) / prev_count
                
                events.append({
                    'event_keyword': keyword,
                    'peak_time': peak_time,
                    'peak_count': max_count,
                    'growth_rate': round(growth_rate, 4),
                    'trend_data': trend,
                    'total_mentions': sum(counts),
                    'duration_windows': len([t for t in trend if t['count'] > 0])
                })
        
        events.sort(key=lambda x: x['peak_count'], reverse=True)
        return events
    
    def analyze_subtopic_evolution(self, posts: List[Dict], main_keyword: str, 
                                     time_window_hours: int = 1) -> Dict:
        if not posts:
            return {}
        
        filtered_posts = [
            p for p in posts 
            if main_keyword.lower() in p.get('content', '').lower()
        ]
        
        if not filtered_posts:
            return {'main_keyword': main_keyword, 'subtopics': []}
        
        time_windows = self._group_by_time_window(filtered_posts, window_hours=time_window_hours)
        
        subtopic_evolution = []
        
        for window_key, window_posts in sorted(time_windows.items()):
            keywords = self._extract_keywords_from_posts(window_posts, top_k=15)
            
            subtopics = []
            for kw, freq in keywords:
                if kw.lower() != main_keyword.lower():
                    subtopics.append({
                        'keyword': kw,
                        'frequency': freq,
                        'relative_freq': freq / len(window_posts) if len(window_posts) > 0 else 0
                    })
            
            subtopic_evolution.append({
                'time_window': window_key,
                'post_count': len(window_posts),
                'top_subtopics': subtopics[:10],
                'all_keywords': [k for k, _ in keywords]
            })
        
        emerging_subtopics = self._detect_emerging_subtopics(subtopic_evolution)
        declining_subtopics = self._detect_declining_subtopics(subtopic_evolution)
        
        return {
            'main_keyword': main_keyword,
            'total_posts': len(filtered_posts),
            'time_windows': len(time_windows),
            'subtopic_evolution': subtopic_evolution,
            'emerging_subtopics': emerging_subtopics,
            'declining_subtopics': declining_subtopics
        }
    
    def _detect_emerging_subtopics(self, subtopic_evolution: List[Dict], 
                                     threshold: float = 0.5) -> List[Dict]:
        if len(subtopic_evolution) < 2:
            return []
        
        all_subtopics = defaultdict(list)
        
        for window_data in subtopic_evolution:
            for subtopic in window_data['top_subtopics']:
                all_subtopics[subtopic['keyword']].append({
                    'time_window': window_data['time_window'],
                    'frequency': subtopic['frequency'],
                    'relative_freq': subtopic['relative_freq']
                })
        
        emerging = []
        for keyword, history in all_subtopics.items():
            if len(history) >= 2:
                recent = history[-3:] if len(history) >= 3 else history
                
                if len(recent) >= 2:
                    first_freq = recent[0]['relative_freq']
                    last_freq = recent[-1]['relative_freq']
                    
                    if first_freq > 0:
                        growth = (last_freq - first_freq) / first_freq
                        if growth >= threshold and last_freq > 0.05:
                            emerging.append({
                                'keyword': keyword,
                                'growth_rate': round(growth, 4),
                                'first_freq': round(first_freq, 4),
                                'last_freq': round(last_freq, 4),
                                'history': history
                            })
        
        emerging.sort(key=lambda x: x['growth_rate'], reverse=True)
        return emerging[:10]
    
    def _detect_declining_subtopics(self, subtopic_evolution: List[Dict],
                                      threshold: float = -0.3) -> List[Dict]:
        if len(subtopic_evolution) < 2:
            return []
        
        all_subtopics = defaultdict(list)
        
        for window_data in subtopic_evolution:
            for subtopic in window_data['top_subtopics']:
                all_subtopics[subtopic['keyword']].append({
                    'time_window': window_data['time_window'],
                    'frequency': subtopic['frequency'],
                    'relative_freq': subtopic['relative_freq']
                })
        
        declining = []
        for keyword, history in all_subtopics.items():
            if len(history) >= 2:
                recent = history[-3:] if len(history) >= 3 else history
                
                if len(recent) >= 2:
                    first_freq = recent[0]['relative_freq']
                    last_freq = recent[-1]['relative_freq']
                    
                    if first_freq > 0:
                        decline = (last_freq - first_freq) / first_freq
                        if decline <= threshold and first_freq > 0.05:
                            declining.append({
                                'keyword': keyword,
                                'decline_rate': round(decline, 4),
                                'first_freq': round(first_freq, 4),
                                'last_freq': round(last_freq, 4),
                                'history': history
                            })
        
        declining.sort(key=lambda x: x['decline_rate'])
        return declining[:10]
    
    def track_event_lifecycle(self, posts: List[Dict], event_keyword: str) -> Dict:
        filtered_posts = [
            p for p in posts 
            if event_keyword.lower() in p.get('content', '').lower()
        ]
        
        if not filtered_posts:
            return {'event_keyword': event_keyword, 'lifecycle': {}}
        
        timestamps = []
        for post in filtered_posts:
            ts = post.get('timestamp')
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except:
                    continue
            if ts:
                timestamps.append(ts)
        
        if not timestamps:
            return {'event_keyword': event_keyword, 'lifecycle': {}}
        
        start_time = min(timestamps)
        end_time = max(timestamps)
        duration_hours = (end_time - start_time).total_seconds() / 3600
        
        sorted_posts = sorted(filtered_posts, key=lambda x: x.get('timestamp', datetime.min))
        
        time_windows = self._group_by_time_window(filtered_posts, window_hours=1)
        window_counts = [len(posts) for posts in time_windows.values()]
        
        if window_counts:
            peak_count = max(window_counts)
            peak_index = window_counts.index(peak_count)
            peak_time = list(time_windows.keys())[peak_index]
            
            first_half = window_counts[:peak_index + 1]
            second_half = window_counts[peak_index:]
            
            growth_phase = sum(first_half) > 0
            decline_phase = len(second_half) > 1 and second_half[-1] < peak_count
        else:
            peak_count = 0
            peak_time = None
            growth_phase = False
            decline_phase = False
        
        lifecycle_stage = 'emerging'
        if peak_time and decline_phase:
            lifecycle_stage = 'declining'
        elif peak_time and not decline_phase:
            lifecycle_stage = 'peak'
        elif growth_phase:
            lifecycle_stage = 'growing'
        
        sentiment_counts = Counter()
        for post in filtered_posts:
            sentiment = post.get('sentiment', {}).get('sentiment', 'neutral')
            sentiment_counts[sentiment] += 1
        
        return {
            'event_keyword': event_keyword,
            'total_posts': len(filtered_posts),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_hours': round(duration_hours, 2),
            'peak_time': peak_time,
            'peak_count': peak_count,
            'lifecycle_stage': lifecycle_stage,
            'sentiment_distribution': dict(sentiment_counts),
            'time_series': [
                {'time': k, 'count': len(v)} 
                for k, v in sorted(time_windows.items())
            ]
        }
    
    def generate_event_summary(self, events: List[Dict], top_n: int = 5) -> Dict:
        if not events:
            return {}
        
        top_events = events[:top_n]
        
        total_mentions = sum(e['total_mentions'] for e in top_events)
        
        categories = defaultdict(list)
        for event in top_events:
            if event['growth_rate'] > 1.0:
                categories['explosive'].append(event)
            elif event['growth_rate'] > 0.3:
                categories['growing'].append(event)
            elif event['growth_rate'] < -0.3:
                categories['declining'].append(event)
            else:
                categories['stable'].append(event)
        
        return {
            'total_events': len(events),
            'top_events': top_events,
            'total_mentions': total_mentions,
            'categories': {k: len(v) for k, v in categories.items()},
            'top_growing': [e for e in top_events if e['growth_rate'] > 0.3][:3],
            'top_declining': [e for e in top_events if e['growth_rate'] < -0.3][:3]
        }
