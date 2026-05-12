import sys
import json
import numpy as np
from collections import defaultdict

class CollaborativeFilteringRecommender:
    def __init__(self):
        self.user_item_matrix = defaultdict(lambda: defaultdict(int))
        self.item_users = defaultdict(set)
        self.user_items = defaultdict(set)
        self.song_features = {}
        
    def add_play_history(self, user_id, song_id, weight=1):
        self.user_item_matrix[user_id][song_id] += weight
        self.item_users[song_id].add(user_id)
        self.user_items[user_id].add(song_id)
        
    def add_song_features(self, song_id, features):
        self.song_features[song_id] = features
        
    def calculate_jaccard_similarity(self, song1, song2):
        users1 = self.item_users.get(song1, set())
        users2 = self.item_users.get(song2, set())
        
        if not users1 or not users2:
            return 0.0
            
        intersection = len(users1 & users2)
        union = len(users1 | users2)
        
        if union == 0:
            return 0.0
            
        return intersection / union
        
    def calculate_cosine_similarity(self, song1, song2):
        feat1 = self.song_features.get(song1, {})
        feat2 = self.song_features.get(song2, {})
        
        if not feat1 or not feat2:
            return self.calculate_jaccard_similarity(song1, song2)
            
        all_keys = set(feat1.keys()) | set(feat2.keys())
        
        vec1 = np.array([feat1.get(k, 0) for k in all_keys])
        vec2 = np.array([feat2.get(k, 0) for k in all_keys])
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return np.dot(vec1, vec2) / (norm1 * norm2)
        
    def get_similar_songs(self, song_id, top_n=10, exclude_songs=None):
        exclude = set(exclude_songs) if exclude_songs else set()
        exclude.add(song_id)
        
        all_songs = set(self.item_users.keys()) | set(self.song_features.keys())
        similar_songs = []
        
        for other_song in all_songs:
            if other_song in exclude:
                continue
                
            similarity = self.calculate_cosine_similarity(song_id, other_song)
            if similarity > 0:
                similar_songs.append((other_song, similarity))
                
        similar_songs.sort(key=lambda x: x[1], reverse=True)
        
        return [song[0] for song in similar_songs[:top_n]]
        
    def get_user_recommendations(self, user_id, top_n=10, exclude_songs=None):
        exclude = set(exclude_songs) if exclude_songs else set()
        user_played = self.user_items.get(user_id, set())
        exclude.update(user_played)
        
        if not user_played:
            popular = self.get_popular_songs(top_n * 2)
            return [s for s in popular if s not in exclude][:top_n]
            
        scores = defaultdict(float)
        total_weight = 0
        
        for played_song in user_played:
            play_count = self.user_item_matrix[user_id][played_song]
            similar = self.get_similar_songs(played_song, top_n=20, exclude_songs=exclude)
            
            weight = min(play_count, 5)
            total_weight += weight
            
            for idx, sim_song in enumerate(similar):
                if sim_song in exclude:
                    continue
                position_weight = 1.0 / (idx + 1)
                scores[sim_song] += weight * position_weight
                
        if total_weight > 0:
            for song in scores:
                scores[song] /= total_weight
                
        recommendations = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return [song[0] for song in recommendations[:top_n]]
        
    def get_popular_songs(self, top_n=10):
        song_plays = defaultdict(int)
        
        for user, songs in self.user_item_matrix.items():
            for song, count in songs.items():
                song_plays[song] += count
                
        popular = sorted(song_plays.items(), key=lambda x: x[1], reverse=True)
        
        return [song[0] for song in popular[:top_n]]
        
    def export_state(self):
        return {
            'user_item_matrix': {k: dict(v) for k, v in self.user_item_matrix.items()},
            'item_users': {k: list(v) for k, v in self.item_users.items()},
            'user_items': {k: list(v) for k, v in self.user_items.items()},
            'song_features': self.song_features
        }
        
    def import_state(self, state):
        self.user_item_matrix = defaultdict(lambda: defaultdict(int))
        for k, v in state.get('user_item_matrix', {}).items():
            self.user_item_matrix[k] = defaultdict(int, v)
            
        self.item_users = defaultdict(set)
        for k, v in state.get('item_users', {}).items():
            self.item_users[k] = set(v)
            
        self.user_items = defaultdict(set)
        for k, v in state.get('user_items', {}).items():
            self.user_items[k] = set(v)
            
        self.song_features = state.get('song_features', {})

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No command provided'}))
        return
        
    command = sys.argv[1]
    recommender = CollaborativeFilteringRecommender()
    
    try:
        if command == 'recommend':
            if len(sys.argv) < 3:
                print(json.dumps({'error': 'Missing user_id'}))
                return
            user_id = sys.argv[2]
            top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            
            if len(sys.argv) > 4:
                state = json.loads(sys.argv[4])
                recommender.import_state(state)
                
            recommendations = recommender.get_user_recommendations(user_id, top_n)
            print(json.dumps({'recommendations': recommendations}))
            
        elif command == 'similar':
            if len(sys.argv) < 3:
                print(json.dumps({'error': 'Missing song_id'}))
                return
            song_id = sys.argv[2]
            top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            
            if len(sys.argv) > 4:
                state = json.loads(sys.argv[4])
                recommender.import_state(state)
                
            similar = recommender.get_similar_songs(song_id, top_n)
            print(json.dumps({'similar': similar}))
            
        elif command == 'popular':
            top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            
            if len(sys.argv) > 3:
                state = json.loads(sys.argv[3])
                recommender.import_state(state)
                
            popular = recommender.get_popular_songs(top_n)
            print(json.dumps({'popular': popular}))
            
        elif command == 'add_play':
            if len(sys.argv) < 4:
                print(json.dumps({'error': 'Missing parameters'}))
                return
            user_id = sys.argv[2]
            song_id = sys.argv[3]
            
            if len(sys.argv) > 4:
                state = json.loads(sys.argv[4])
                recommender.import_state(state)
                
            recommender.add_play_history(user_id, song_id)
            print(json.dumps({'success': True, 'state': recommender.export_state()}))
            
        elif command == 'add_features':
            if len(sys.argv) < 4:
                print(json.dumps({'error': 'Missing parameters'}))
                return
            song_id = sys.argv[2]
            features = json.loads(sys.argv[3])
            
            if len(sys.argv) > 4:
                state = json.loads(sys.argv[4])
                recommender.import_state(state)
                
            recommender.add_song_features(song_id, features)
            print(json.dumps({'success': True, 'state': recommender.export_state()}))
            
        else:
            print(json.dumps({'error': f'Unknown command: {command}'}))
            
    except Exception as e:
        print(json.dumps({'error': str(e)}))

if __name__ == '__main__':
    main()
