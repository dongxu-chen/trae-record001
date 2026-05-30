import numpy as np
import networkx as nx
from typing import Dict, List, Tuple
from data_store import DataStore
from collections import defaultdict


class SocialRecommender:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.social_graph = nx.Graph()
        self._build_social_graph()

    def _build_social_graph(self):
        self.social_graph.clear()
        for user_id in self.data_store.get_all_users():
            self.social_graph.add_node(user_id)
            friends = self.data_store.get_user_friends(user_id)
            for friend_id in friends:
                self.social_graph.add_edge(user_id, friend_id, weight=1.0)

    def add_connection(self, user_id: int, friend_id: int):
        self.social_graph.add_edge(user_id, friend_id, weight=1.0)

    def get_trust_score(self, user1_id: int, user2_id: int) -> float:
        if not self.social_graph.has_node(user1_id) or not self.social_graph.has_node(user2_id):
            return 0.0
        
        if user1_id == user2_id:
            return 1.0
        
        try:
            path_length = nx.shortest_path_length(self.social_graph, user1_id, user2_id)
            return 1.0 / (path_length + 1)
        except nx.NetworkXNoPath:
            return 0.0

    def get_social_neighbors(self, user_id: int, max_depth: int = 2) -> List[Tuple[int, float]]:
        if not self.social_graph.has_node(user_id):
            return []
        
        neighbors = []
        visited = {user_id}
        queue = [(user_id, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            if depth > max_depth:
                continue
            
            for neighbor in self.social_graph.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    trust = self.get_trust_score(user_id, neighbor)
                    if trust > 0:
                        neighbors.append((neighbor, trust))
                    queue.append((neighbor, depth + 1))
        
        return sorted(neighbors, key=lambda x: x[1], reverse=True)

    def recommend_based_on_friends(self, user_id: int, top_n: int = 10) -> List[Tuple[int, float, str]]:
        user_ratings = self.data_store.get_user_ratings(user_id)
        friends = self.data_store.get_user_friends(user_id)
        
        if not friends:
            return []
        
        book_scores = defaultdict(float)
        book_counts = defaultdict(int)
        book_reasons = defaultdict(list)
        
        for friend_id in friends:
            friend_ratings = self.data_store.get_user_ratings(friend_id)
            trust = self.get_trust_score(user_id, friend_id)
            
            for book_id, rating in friend_ratings.items():
                if book_id not in user_ratings:
                    if rating >= 4.0:
                        book_scores[book_id] += trust * rating
                        book_counts[book_id] += 1
                        friend_user = self.data_store.get_user(friend_id)
                        if friend_user:
                            book_reasons[book_id].append(friend_user.username)
        
        recommendations = []
        for book_id in book_scores:
            avg_score = book_scores[book_id] / book_counts[book_id]
            friends_list = book_reasons[book_id]
            if friends_list:
                reason = f"好友推荐: {', '.join(friends_list[:3])}"
                if len(friends_list) > 3:
                    reason += f" 等{len(friends_list)}位好友"
            else:
                reason = "好友推荐"
            recommendations.append((book_id, avg_score, reason))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]

    def recommend_based_on_social_influence(self, user_id: int, top_n: int = 10, max_depth: int = 2) -> List[Tuple[int, float, str]]:
        user_ratings = self.data_store.get_user_ratings(user_id)
        social_neighbors = self.get_social_neighbors(user_id, max_depth)
        
        if not social_neighbors:
            return []
        
        book_scores = defaultdict(float)
        book_counts = defaultdict(int)
        
        for neighbor_id, trust in social_neighbors:
            neighbor_ratings = self.data_store.get_user_ratings(neighbor_id)
            
            for book_id, rating in neighbor_ratings.items():
                if book_id not in user_ratings:
                    if rating >= 4.0:
                        book_scores[book_id] += trust * rating
                        book_counts[book_id] += 1
        
        recommendations = []
        for book_id in book_scores:
            avg_score = book_scores[book_id] / book_counts[book_id]
            recommendations.append((book_id, avg_score, "社交圈推荐"))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]

    def recommend(self, user_id: int, top_n: int = 10) -> List[Tuple[int, float, str]]:
        friend_recs = self.recommend_based_on_friends(user_id, top_n * 2)
        social_recs = self.recommend_based_on_social_influence(user_id, top_n * 2)
        
        combined = {}
        
        for book_id, score, reason in friend_recs:
            if book_id not in combined:
                combined[book_id] = {'score': 0, 'count': 0, 'reasons': []}
            combined[book_id]['score'] += score * 0.6
            combined[book_id]['count'] += 1
            combined[book_id]['reasons'].append(reason)
        
        for book_id, score, reason in social_recs:
            if book_id not in combined:
                combined[book_id] = {'score': 0, 'count': 0, 'reasons': []}
            combined[book_id]['score'] += score * 0.4
            combined[book_id]['count'] += 1
            combined[book_id]['reasons'].append(reason)
        
        recommendations = []
        for book_id, data in combined.items():
            avg_score = data['score'] / data['count'] if data['count'] > 0 else 0
            final_reason = " + ".join(set(data['reasons']))[:50]
            recommendations.append((book_id, avg_score, final_reason))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]
