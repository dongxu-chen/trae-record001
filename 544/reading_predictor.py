import numpy as np
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from data_store import DataStore
from models import ReadingProgress, ReadingPrediction


class ReadingPredictor:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.default_pages_per_day = 30.0
        self.book_type_reading_speed = {
            '科幻': 35,
            '悬疑': 45,
            '推理': 45,
            '经典': 25,
            '哲学': 15,
            '历史': 20,
            '社科': 20,
            '童话': 40,
            '奇幻': 35,
            '冒险': 40,
            '治愈': 30,
            '温情': 30,
        }

    def _get_genre_based_speed(self, book_id: int) -> float:
        book = self.data_store.get_book(book_id)
        if not book:
            return self.default_pages_per_day

        speeds = []
        for genre in book.genres:
            if genre in self.book_type_reading_speed:
                speeds.append(self.book_type_reading_speed[genre])

        if speeds:
            return np.mean(speeds)
        return self.default_pages_per_day

    def _get_user_historical_speed(self, user_id: int) -> float:
        user_progress = self.data_store.get_user_reading_progress(user_id)
        speeds = []

        for progress in user_progress:
            if progress.status == 'finished' and progress.pages_per_day_avg > 0:
                speeds.append(progress.pages_per_day_avg)

        if speeds:
            return np.mean(speeds)
        return 0.0

    def predict_finish_time(self, user_id: int, book_id: int) -> Optional[ReadingPrediction]:
        progress = self.data_store.get_reading_progress(user_id, book_id)
        book = self.data_store.get_book(book_id)

        if not book:
            return None

        total_pages = progress.total_pages if progress and progress.total_pages else book.total_pages
        if not total_pages or total_pages <= 0:
            total_pages = 300

        current_page = 0
        user_speed = self._get_user_historical_speed(user_id)
        genre_speed = self._get_genre_based_speed(book_id)

        if progress:
            current_page = progress.current_page
            if progress.pages_per_day_avg > 0:
                pages_per_day = progress.pages_per_day_avg
            elif user_speed > 0:
                pages_per_day = user_speed * 0.6 + genre_speed * 0.4
            else:
                pages_per_day = genre_speed
        else:
            if user_speed > 0:
                pages_per_day = user_speed * 0.5 + genre_speed * 0.5
            else:
                pages_per_day = genre_speed

        pages_left = max(0, total_pages - current_page)
        progress_percent = (current_page / total_pages) * 100 if total_pages > 0 else 0

        if pages_per_day <= 0:
            pages_per_day = self.default_pages_per_day

        estimated_days_left = pages_left / pages_per_day

        now = datetime.now()
        estimated_finish_date = now + timedelta(days=estimated_days_left)

        return ReadingPrediction(
            book_id=book_id,
            current_page=current_page,
            total_pages=total_pages,
            pages_per_day=round(pages_per_day, 1),
            estimated_days_left=round(estimated_days_left, 1),
            estimated_finish_date=estimated_finish_date,
            progress_percent=round(progress_percent, 1)
        )

    def update_progress(self, user_id: int, book_id: int, current_page: int,
                        total_pages: Optional[int] = None) -> ReadingProgress:
        book = self.data_store.get_book(book_id)
        if not book:
            raise ValueError(f"书籍 {book_id} 不存在")

        actual_total = total_pages or book.total_pages or 300
        current_page = min(max(0, current_page), actual_total)

        status = 'reading'
        if current_page >= actual_total:
            status = 'finished'

        existing = self.data_store.get_reading_progress(user_id, book_id)
        today = datetime.now().date()

        if existing:
            reading_days = existing.reading_days.copy()
            last_date = existing.last_read_date.date() if existing.last_read_date else None
            if last_date != today:
                reading_days.append(datetime.now())
        else:
            reading_days = [datetime.now()]

        progress = ReadingProgress(
            user_id=user_id,
            book_id=book_id,
            current_page=current_page,
            total_pages=actual_total,
            start_date=existing.start_date if existing else datetime.now(),
            last_read_date=datetime.now(),
            reading_days=reading_days,
            status=status
        )

        self.data_store.update_reading_progress(progress)
        return progress

    def get_user_reading_stats(self, user_id: int) -> Dict:
        user_progress = self.data_store.get_user_reading_progress(user_id)
        user_ratings = self.data_store.get_user_ratings(user_id)

        total_books_read = len(user_ratings)
        total_pages_read = 0
        total_reading_days = 0
        finished_books = 0
        currently_reading = []

        for progress in user_progress:
            total_pages_read += progress.current_page
            total_reading_days += len(progress.reading_days)
            if progress.status == 'finished':
                finished_books += 1
            elif progress.status == 'reading':
                currently_reading.append(progress)

        avg_pages_per_day = total_pages_read / total_reading_days if total_reading_days > 0 else 0
        reading_predictions = []
        for progress in currently_reading:
            pred = self.predict_finish_time(user_id, progress.book_id)
            if pred:
                reading_predictions.append(pred)

        return {
            'user_id': user_id,
            'total_books_read': total_books_read,
            'finished_books': finished_books,
            'currently_reading_count': len(currently_reading),
            'total_pages_read': total_pages_read,
            'total_reading_days': total_reading_days,
            'avg_pages_per_day': round(avg_pages_per_day, 1),
            'current_books': currently_reading,
            'predictions': reading_predictions
        }

    def recommend_reading_schedule(self, user_id: int, daily_goal_pages: int = 30) -> Dict:
        user_progress = self.data_store.get_user_reading_progress(user_id)
        currently_reading = [p for p in user_progress if p.status == 'reading']

        schedules = []
        for progress in currently_reading:
            book = self.data_store.get_book(progress.book_id)
            if not book:
                continue

            total_pages = progress.total_pages or book.total_pages or 300
            pages_left = total_pages - progress.current_page

            days_at_goal = pages_left / daily_goal_pages if daily_goal_pages > 0 else 0
            daily_pages = daily_goal_pages
            finish_date = datetime.now() + timedelta(days=days_at_goal)

            schedules.append({
                'book_id': progress.book_id,
                'title': book.title,
                'current_page': progress.current_page,
                'total_pages': total_pages,
                'pages_left': pages_left,
                'daily_goal_pages': daily_pages,
                'estimated_days': round(days_at_goal, 1),
                'estimated_finish': finish_date,
                'next_milestone': {
                    '25%': total_pages * 0.25,
                    '50%': total_pages * 0.5,
                    '75%': total_pages * 0.75,
                    '100%': total_pages
                }
            })

        return {
            'user_id': user_id,
            'daily_goal_pages': daily_goal_pages,
            'schedules': schedules
        }
