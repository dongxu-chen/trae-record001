import os
import json
from collections import defaultdict
from datetime import datetime, timedelta

class UserPreference:
    def __init__(self, preference_path):
        self.preference_path = preference_path
        self.user_data = defaultdict(lambda: {
            'correction_history': [],
            'category_preferences': defaultdict(int),
            'word_preferences': defaultdict(int),
            'acceptance_rate': 0.0,
            'total_interactions': 0,
            'accepted_corrections': 0,
            'last_active': None
        })
        self.load_preferences()
    
    def load_preferences(self):
        if os.path.exists(self.preference_path):
            try:
                with open(self.preference_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, info in data.items():
                        self.user_data[user_id] = {
                            'correction_history': info.get('correction_history', []),
                            'category_preferences': defaultdict(int, info.get('category_preferences', {})),
                            'word_preferences': defaultdict(int, info.get('word_preferences', {})),
                            'acceptance_rate': info.get('acceptance_rate', 0.0),
                            'total_interactions': info.get('total_interactions', 0),
                            'accepted_corrections': info.get('accepted_corrections', 0),
                            'last_active': info.get('last_active')
                        }
            except Exception as e:
                print(f"Error loading preferences: {e}")
    
    def save_preferences(self):
        data = {}
        for user_id, info in self.user_data.items():
            data[user_id] = {
                'correction_history': info['correction_history'][-100:],
                'category_preferences': dict(info['category_preferences']),
                'word_preferences': dict(info['word_preferences']),
                'acceptance_rate': info['acceptance_rate'],
                'total_interactions': info['total_interactions'],
                'accepted_corrections': info['accepted_corrections'],
                'last_active': info['last_active']
            }
        
        os.makedirs(os.path.dirname(self.preference_path), exist_ok=True)
        with open(self.preference_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_user(self, user_id):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'correction_history': [],
                'category_preferences': defaultdict(int),
                'word_preferences': defaultdict(int),
                'acceptance_rate': 0.0,
                'total_interactions': 0,
                'accepted_corrections': 0,
                'last_active': None
            }
        return self.user_data[user_id]
    
    def record_correction(self, user_id, original_query, corrected_query, accepted, category=None):
        user = self._get_user(user_id)
        
        user['correction_history'].append({
            'original': original_query,
            'corrected': corrected_query,
            'accepted': accepted,
            'category': category,
            'timestamp': datetime.now().isoformat()
        })
        
        user['total_interactions'] += 1
        if accepted:
            user['accepted_corrections'] += 1
            user['word_preferences'][corrected_query] += 1
            if category:
                user['category_preferences'][category] += 1
        
        if user['total_interactions'] > 0:
            user['acceptance_rate'] = user['accepted_corrections'] / user['total_interactions']
        
        user['last_active'] = datetime.now().isoformat()
        self.save_preferences()
    
    def get_word_preference_score(self, user_id, word):
        user = self._get_user(user_id)
        total = sum(user['word_preferences'].values())
        if total == 0:
            return 0.5
        return user['word_preferences'].get(word, 0) / total
    
    def get_user_threshold_adjustment(self, user_id):
        user = self._get_user(user_id)
        acceptance_rate = user['acceptance_rate']
        
        if acceptance_rate == 0:
            return 0.0
        
        if acceptance_rate > 0.8:
            return -0.05
        elif acceptance_rate > 0.6:
            return 0.0
        elif acceptance_rate > 0.4:
            return 0.05
        else:
            return 0.1
    
    def get_personalized_candidates(self, user_id, candidates, max_count=5):
        if user_id not in self.user_data:
            return candidates
        
        user = self._get_user(user_id)
        word_prefs = user['word_preferences']
        
        scored = []
        for cand in candidates:
            if isinstance(cand, str):
                word = cand
            elif isinstance(cand, dict):
                word = cand.get('word', '')
            elif isinstance(cand, (list, tuple)):
                word = cand[0]
            else:
                word = str(cand)
            
            pref_score = self.get_word_preference_score(user_id, word)
            
            if isinstance(cand, dict):
                cand['personalization_score'] = max(cand.get('personalization_score', 0), pref_score)
                cand['final_score'] = cand.get('final_score', 0) + pref_score * 0.1
            
            scored.append((cand, pref_score))
        
        scored.sort(key=lambda x: -x[1])
        return [cand for cand, score in scored[:max_count]]
    
    def get_user_profile(self, user_id):
        user = self._get_user(user_id)
        return {
            'user_id': user_id,
            'total_interactions': user['total_interactions'],
            'accepted_corrections': user['accepted_corrections'],
            'acceptance_rate': user['acceptance_rate'],
            'threshold_adjustment': self.get_user_threshold_adjustment(user_id),
            'top_words': sorted(user['word_preferences'].items(), key=lambda x: -x[1])[:10],
            'last_active': user['last_active']
        }
    
    def get_similar_users(self, user_id, top_n=5):
        if user_id not in self.user_data:
            return []
        
        target_user = self._get_user(user_id)
        target_words = set(target_user['word_preferences'].keys())
        
        similarities = []
        for other_id, other_user in self.user_data.items():
            if other_id == user_id:
                continue
            
            other_words = set(other_user['word_preferences'].keys())
            if not target_words or not other_words:
                continue
            
            intersection = target_words & other_words
            union = target_words | other_words
            
            if len(union) > 0:
                similarity = len(intersection) / len(union)
                similarities.append((other_id, similarity))
        
        similarities.sort(key=lambda x: -x[1])
        return similarities[:top_n]
