import numpy as np
from typing import Dict, List, Tuple
from data_store import DataStore


class MatrixFactorization:
    def __init__(self, data_store: DataStore, n_factors: int = 20, 
                 learning_rate: float = 0.01, reg_param: float = 0.02,
                 n_epochs: int = 50):
        self.data_store = data_store
        self.n_factors = n_factors
        self.learning_rate = learning_rate
        self.reg_param = reg_param
        self.n_epochs = n_epochs
        self.user_factors = None
        self.book_factors = None
        self.user_bias = None
        self.book_bias = None
        self.global_bias = 0
        self.user_idx = {}
        self.book_idx = {}
        self.is_trained = False

    def train(self):
        matrix, users, books, user_idx, book_idx = self.data_store.build_rating_matrix()
        
        self.user_idx = user_idx
        self.book_idx = book_idx
        n_users, n_books = matrix.shape
        
        np.random.seed(42)
        self.user_factors = np.random.normal(0, 0.1, (n_users, self.n_factors))
        self.book_factors = np.random.normal(0, 0.1, (n_books, self.n_factors))
        self.user_bias = np.zeros(n_users)
        self.book_bias = np.zeros(n_books)
        
        non_zero_mask = matrix > 0
        non_zero_indices = np.where(non_zero_mask)
        
        if len(non_zero_indices[0]) == 0:
            self.is_trained = False
            return
        
        self.global_bias = np.mean(matrix[non_zero_mask])
        
        for epoch in range(self.n_epochs):
            total_loss = 0
            n_samples = 0
            
            for u, i in zip(non_zero_indices[0], non_zero_indices[1]):
                rating = matrix[u, i]
                
                prediction = self._predict_single(u, i)
                error = rating - prediction
                
                total_loss += error ** 2
                n_samples += 1
                
                self.user_bias[u] += self.learning_rate * (error - self.reg_param * self.user_bias[u])
                self.book_bias[i] += self.learning_rate * (error - self.reg_param * self.book_bias[i])
                
                uf = self.user_factors[u].copy()
                bf = self.book_factors[i].copy()
                
                self.user_factors[u] += self.learning_rate * (error * bf - self.reg_param * uf)
                self.book_factors[i] += self.learning_rate * (error * uf - self.reg_param * bf)
            
            rmse = np.sqrt(total_loss / n_samples) if n_samples > 0 else 0
            
        self.is_trained = True

    def _predict_single(self, user_idx: int, book_idx: int) -> float:
        prediction = self.global_bias
        prediction += self.user_bias[user_idx]
        prediction += self.book_bias[book_idx]
        prediction += np.dot(self.user_factors[user_idx], self.book_factors[book_idx])
        return prediction

    def predict(self, user_id: int, book_id: int) -> float:
        if not self.is_trained:
            return 0.0
        
        if user_id not in self.user_idx or book_id not in self.book_idx:
            return 0.0
        
        u = self.user_idx[user_id]
        i = self.book_idx[book_id]
        return self._predict_single(u, i)

    def recommend(self, user_id: int, top_n: int = 10) -> List[Tuple[int, float, str]]:
        if not self.is_trained:
            return []
        
        if user_id not in self.user_idx:
            return []
        
        user_ratings = self.data_store.get_user_ratings(user_id)
        u = self.user_idx[user_id]
        
        predictions = []
        for book_id in self.data_store.get_all_books():
            if book_id not in user_ratings and book_id in self.book_idx:
                i = self.book_idx[book_id]
                score = self._predict_single(u, i)
                predictions.append((book_id, score, "矩阵分解推荐"))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:top_n]

    def get_similar_books(self, book_id: int, top_n: int = 10) -> List[Tuple[int, float]]:
        if not self.is_trained or book_id not in self.book_idx:
            return []
        
        book_idx = self.book_idx[book_id]
        book_vector = self.book_factors[book_idx]
        
        similarities = []
        for other_book_id, other_idx in self.book_idx.items():
            if other_book_id != book_id:
                other_vector = self.book_factors[other_idx]
                sim = np.dot(book_vector, other_vector) / (
                    np.linalg.norm(book_vector) * np.linalg.norm(other_vector) + 1e-10
                )
                similarities.append((other_book_id, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]
