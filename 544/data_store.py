from typing import Dict, List, Optional, Tuple
from datetime import datetime
from models import User, Book, Rating, SocialConnection, BookSeries, ReadingProgress, BookReviewSummary
import numpy as np
from collections import defaultdict


class DataStore:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.books: Dict[int, Book] = {}
        self.ratings: List[Rating] = []
        self.social_connections: Dict[int, List[SocialConnection]] = defaultdict(list)
        self.user_ratings: Dict[int, Dict[int, float]] = defaultdict(dict)
        self.book_ratings: Dict[int, Dict[int, float]] = defaultdict(dict)
        self.user_friends: Dict[int, List[int]] = defaultdict(list)
        self.book_series: Dict[int, BookSeries] = {}
        self.series_books: Dict[int, List[int]] = defaultdict(list)
        self.reading_progress: Dict[Tuple[int, int], ReadingProgress] = {}
        self.review_summaries: Dict[int, BookReviewSummary] = {}

    def add_user(self, user: User):
        self.users[user.user_id] = user

    def add_book(self, book: Book):
        self.books[book.book_id] = book

    def add_rating(self, rating: Rating):
        self.ratings.append(rating)
        self.user_ratings[rating.user_id][rating.book_id] = rating.rating
        self.book_ratings[rating.book_id][rating.user_id] = rating.rating
        self._update_book_stats(rating.book_id)

    def add_social_connection(self, conn: SocialConnection):
        self.social_connections[conn.user_id].append(conn)
        self.user_friends[conn.user_id].append(conn.friend_id)
        if conn.friend_id not in self.user_friends:
            self.user_friends[conn.friend_id] = []
        if conn.user_id not in self.user_friends[conn.friend_id]:
            self.user_friends[conn.friend_id].append(conn.user_id)

    def _update_book_stats(self, book_id: int):
        if book_id in self.books and book_id in self.book_ratings:
            ratings = list(self.book_ratings[book_id].values())
            self.books[book_id].avg_rating = np.mean(ratings)
            self.books[book_id].total_ratings = len(ratings)

    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    def get_book(self, book_id: int) -> Optional[Book]:
        return self.books.get(book_id)

    def get_user_ratings(self, user_id: int) -> Dict[int, float]:
        return self.user_ratings.get(user_id, {})

    def get_book_ratings(self, book_id: int) -> Dict[int, float]:
        return self.book_ratings.get(book_id, {})

    def get_user_friends(self, user_id: int) -> List[int]:
        return self.user_friends.get(user_id, [])

    def get_all_users(self) -> List[int]:
        return list(self.users.keys())

    def get_all_books(self) -> List[int]:
        return list(self.books.keys())

    def is_new_user(self, user_id: int) -> bool:
        return len(self.user_ratings.get(user_id, {})) < 3

    def get_popular_books(self, top_n: int = 10) -> List[int]:
        sorted_books = sorted(
            self.books.values(),
            key=lambda b: (b.avg_rating * np.log(b.total_ratings + 1)),
            reverse=True
        )
        return [b.book_id for b in sorted_books[:top_n]]

    def get_books_by_genre(self, genres: List[str], top_n: int = 10) -> List[int]:
        genre_books = []
        for book in self.books.values():
            overlap = len(set(book.genres) & set(genres))
            if overlap > 0:
                genre_books.append((book.book_id, overlap, book.avg_rating))
        genre_books.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return [b[0] for b in genre_books[:top_n]]

    def get_hot_genres(self, top_n: int = 5) -> List[Tuple[str, float]]:
        genre_scores = defaultdict(float)
        for book in self.books.values():
            if book.total_ratings > 0:
                popularity = book.avg_rating * np.log1p(book.total_ratings)
                for genre in book.genres:
                    genre_scores[genre] += popularity
        sorted_genres = sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_genres[:top_n]

    def get_books_by_popularity(self, top_n: int = 10) -> List[Tuple[int, float]]:
        scored = []
        for book in self.books.values():
            popularity = book.avg_rating * np.log1p(book.total_ratings)
            scored.append((book.book_id, popularity))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def build_rating_matrix(self):
        users = list(self.users.keys())
        books = list(self.books.keys())
        user_idx = {u: i for i, u in enumerate(users)}
        book_idx = {b: i for i, b in enumerate(books)}
        
        matrix = np.zeros((len(users), len(books)))
        for user_id, ratings in self.user_ratings.items():
            for book_id, rating in ratings.items():
                if user_id in user_idx and book_id in book_idx:
                    matrix[user_idx[user_id], book_idx[book_id]] = rating
        
        return matrix, users, books, user_idx, book_idx

    def add_book_series(self, series: BookSeries):
        self.book_series[series.series_id] = series

    def get_book_series(self, series_id: int) -> Optional[BookSeries]:
        return self.book_series.get(series_id)

    def add_book_to_series(self, book_id: int, series_id: int, series_order: int):
        if book_id in self.books:
            self.books[book_id].series_id = series_id
            self.books[book_id].series_order = series_order
            self.series_books[series_id].append(book_id)
            self.series_books[series_id].sort(
                key=lambda bid: self.books[bid].series_order or 0
            )
            if series_id in self.book_series:
                self.book_series[series_id].total_books = len(self.series_books[series_id])

    def get_series_books(self, series_id: int) -> List[Book]:
        book_ids = self.series_books.get(series_id, [])
        return [self.books[bid] for bid in book_ids if bid in self.books]

    def get_book_series_by_book(self, book_id: int) -> Optional[BookSeries]:
        book = self.books.get(book_id)
        if book and book.series_id:
            return self.book_series.get(book.series_id)
        return None

    def get_all_series(self) -> List[BookSeries]:
        return list(self.book_series.values())

    def update_reading_progress(self, progress: ReadingProgress):
        key = (progress.user_id, progress.book_id)
        existing = self.reading_progress.get(key)
        
        if existing:
            if progress.current_page > existing.current_page:
                existing.current_page = progress.current_page
            existing.last_read_date = progress.last_read_date or datetime.now()
            if progress.reading_days:
                existing.reading_days.extend(progress.reading_days)
            existing.status = progress.status
            existing.pages_per_day_avg = self._calculate_pages_per_day(existing)
            self.reading_progress[key] = existing
        else:
            if not progress.start_date:
                progress.start_date = datetime.now()
            if not progress.last_read_date:
                progress.last_read_date = datetime.now()
            progress.pages_per_day_avg = self._calculate_pages_per_day(progress)
            self.reading_progress[key] = progress

    def _calculate_pages_per_day(self, progress: ReadingProgress) -> float:
        if not progress.start_date or progress.current_page == 0:
            return 0.0
        
        end_date = progress.last_read_date or datetime.now()
        days_elapsed = (end_date.date() - progress.start_date.date()).days + 1
        days_read = max(len(progress.reading_days), days_elapsed)
        if days_read <= 0:
            days_read = 1
        
        return progress.current_page / days_read

    def get_reading_progress(self, user_id: int, book_id: int) -> Optional[ReadingProgress]:
        return self.reading_progress.get((user_id, book_id))

    def get_user_reading_progress(self, user_id: int) -> List[ReadingProgress]:
        return [
            progress for (uid, bid), progress in self.reading_progress.items()
            if uid == user_id
        ]

    def save_review_summary(self, summary: BookReviewSummary):
        self.review_summaries[summary.book_id] = summary

    def get_review_summary(self, book_id: int) -> Optional[BookReviewSummary]:
        return self.review_summaries.get(book_id)
