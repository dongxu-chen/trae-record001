import os
import json
from collections import defaultdict

class UserFeedback:
    def __init__(self, feedback_path):
        self.feedback_path = feedback_path
        self.feedback_data = defaultdict(lambda: {'clicks': defaultdict(int), 'skips': defaultdict(int)})
        self.learned_weights = defaultdict(int)
        self.load_feedback()
    
    def load_feedback(self):
        if os.path.exists(self.feedback_path):
            with open(self.feedback_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for query, info in data.get('feedback', {}).items():
                    self.feedback_data[query] = {
                        'clicks': defaultdict(int, info.get('clicks', {})),
                        'skips': defaultdict(int, info.get('skips', {}))
                    }
                self.learned_weights = defaultdict(int, data.get('learned_weights', {}))
    
    def save_feedback(self):
        data = {
            'feedback': {
                query: {
                    'clicks': dict(info['clicks']),
                    'skips': dict(info['skips'])
                } for query, info in self.feedback_data.items()
            },
            'learned_weights': dict(self.learned_weights)
        }
        os.makedirs(os.path.dirname(self.feedback_path), exist_ok=True)
        with open(self.feedback_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def record_click(self, original_query, corrected_query, suggestion):
        self.feedback_data[original_query]['clicks'][suggestion] += 1
        self.learned_weights[suggestion] += 1
        self.save_feedback()
    
    def record_skip(self, original_query, suggestion):
        self.feedback_data[original_query]['skips'][suggestion] += 1
        self.save_feedback()
    
    def get_feedback_score(self, original_query, suggestion):
        clicks = self.feedback_data[original_query]['clicks'].get(suggestion, 0)
        skips = self.feedback_data[original_query]['skips'].get(suggestion, 0)
        total = clicks + skips
        if total == 0:
            return 0.5
        return clicks / total
    
    def get_learned_weight(self, word):
        return self.learned_weights.get(word, 0)
    
    def get_popular_corrections(self, query, limit=5):
        if query not in self.feedback_data:
            return []
        clicks = self.feedback_data[query]['clicks']
        sorted_clicks = sorted(clicks.items(), key=lambda x: -x[1])
        return sorted_clicks[:limit]
