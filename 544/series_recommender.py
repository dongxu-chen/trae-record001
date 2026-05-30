from typing import List, Tuple, Optional, Dict
import numpy as np
from data_store import DataStore
from models import Book, BookSeries
from collections import defaultdict


class SeriesRecommender:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    def detect_series(self) -> List[BookSeries]:
        author_series = defaultdict(lambda: defaultdict(list))
        
        for book in self.data_store.books.values():
            if book.series_id is None:
                author_series[book.author][book.title[:2]].append(book)
        
        auto_series = []
        series_counter = max(self.data_store.book_series.keys()) + 1 if self.data_store.book_series else 100
        
        for author, title_groups in author_series.items():
            for prefix, books in title_groups.items():
                if len(books) >= 2:
                    series_name = f"{author} - {prefix}系列"
                    series = BookSeries(
                        series_id=series_counter,
                        series_name=series_name,
                        author=author,
                        description=f"自动检测的{author}系列丛书",
                        total_books=len(books)
                    )
                    auto_series.append(series)
                    series_counter += 1
        
        return auto_series

    def get_user_series_progress(self, user_id: int) -> Dict[int, Dict]:
        user_ratings = self.data_store.get_user_ratings(user_id)
        series_progress = {}

        for series_id, series in self.data_store.book_series.items():
            series_books = self.data_store.get_series_books(series_id)
            if not series_books:
                continue

            read_books = []
            unread_books = []
            next_book = None

            for book in series_books:
                if book.book_id in user_ratings:
                    read_books.append(book)
                else:
                    if next_book is None:
                        next_book = book
                    unread_books.append(book)

            if read_books or unread_books:
                series_progress[series_id] = {
                    'series': series,
                    'total_books': len(series_books),
                    'read_count': len(read_books),
                    'read_books': read_books,
                    'unread_books': unread_books,
                    'next_book': next_book,
                    'completion_percent': len(read_books) / len(series_books) * 100
                }

        return series_progress

    def recommend_next_in_series(self, user_id: int, top_n: int = 5) -> List[Tuple[int, float, str]]:
        series_progress = self.get_user_series_progress(user_id)
        recommendations = []

        for series_id, progress in series_progress.items():
            if progress['next_book'] and progress['read_count'] > 0:
                completion = progress['completion_percent']
                series = progress['series']
                next_book = progress['next_book']

                base_score = 4.0 + (completion / 100.0)
                if next_book.avg_rating > 0:
                    base_score = base_score * 0.7 + next_book.avg_rating * 0.3

                reason = f"《{series.series_name}》系列第{next_book.series_order}本，已读{progress['read_count']}/{progress['total_books']}"
                recommendations.append((next_book.book_id, base_score, reason))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]

    def recommend_complete_series(self, user_id: int, top_n: int = 5) -> List[Tuple[int, float, str]]:
        user_ratings = self.data_store.get_user_ratings(user_id)
        user_genres = set()
        
        for book_id, rating in user_ratings.items():
            if rating >= 4.0:
                book = self.data_store.get_book(book_id)
                if book:
                    user_genres.update(book.genres)

        recommendations = []
        for series_id, series in self.data_store.book_series.items():
            series_books = self.data_store.get_series_books(series_id)
            if not series_books:
                continue

            read_any = any(b.book_id in user_ratings for b in series_books)
            if read_any:
                continue

            genre_overlap = 0
            for book in series_books:
                genre_overlap += len(set(book.genres) & user_genres)

            if genre_overlap == 0 and user_genres:
                continue

            avg_rating = np.mean([b.avg_rating for b in series_books if b.avg_rating > 0])
            score = avg_rating * (1 + 0.1 * min(genre_overlap, 5))
            reason = f"完整系列推荐: 《{series.series_name}》({series.total_books}本)"
            recommendations.append((series_books[0].book_id, score, reason))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_n]

    def get_series_reading_order(self, book_id: int) -> List[Book]:
        book = self.data_store.get_book(book_id)
        if not book or not book.series_id:
            return []
        
        return self.data_store.get_series_books(book.series_id)
