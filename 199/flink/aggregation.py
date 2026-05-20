import time
import math
from collections import deque, defaultdict
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from config import FLINK_CONFIG


@dataclass
class EventTimeWindow:
    start: float
    end: float
    data: List[Dict] = field(default_factory=list)
    total_amount: float = 0.0
    count: int = 0
    is_closed: bool = False

    def contains(self, timestamp: float) -> bool:
        return self.start <= timestamp < self.end

    def add(self, data: Dict, timestamp: float) -> bool:
        if self.contains(timestamp) and not self.is_closed:
            self.data.append(data)
            self.total_amount += data.get('amount', 0.0)
            self.count += 1
            return True
        return False


class EventTimeAggregator:
    @staticmethod
    def align_window_start(timestamp: float, window_size: int) -> float:
        return math.floor(timestamp / window_size) * window_size

    @staticmethod
    def align_window_end(timestamp: float, window_size: int) -> float:
        return EventTimeAggregator.align_window_start(timestamp, window_size) + window_size

    def __init__(self, window_size: int = None, slide_size: int = None, watermark_delay: int = None):
        self.window_size = window_size or FLINK_CONFIG['window_size']
        self.window_slide = slide_size or FLINK_CONFIG['window_slide']
        self.watermark_delay = watermark_delay or FLINK_CONFIG.get('watermark_delay', 3)

        self._max_event_time = 0.0
        self._watermark = 0.0
        self._first_event_time: Optional[float] = None

        self._windows: Dict[float, EventTimeWindow] = {}
        self._expired_windows: deque = deque(maxlen=100)

        self._total_viewers = 0
        self._current_online = 0
        self._total_likes = 0
        self._total_transactions = 0
        self._total_amount = 0.0
        self._total_product_clicks = 0

        self._viewer_events: deque = deque(maxlen=10000)
        self._like_events: deque = deque(maxlen=10000)
        self._transaction_events: deque = deque(maxlen=10000)
        self._product_click_events: deque = deque(maxlen=10000)

        self._second_stats: deque = deque(maxlen=60)
        self._product_stats = defaultdict(lambda: {'clicks': 0, 'orders': 0, 'amount': 0.0})

        self._late_events: List[Dict] = []
        self._late_event_count = 0

    def update_watermark(self, event_time: Optional[float] = None) -> float:
        if event_time is not None:
            if event_time > self._max_event_time:
                self._max_event_time = event_time
            if self._first_event_time is None:
                self._first_event_time = event_time

        event_based_watermark = self._max_event_time - self.watermark_delay
        process_based_watermark = time.time() - self.watermark_delay * 2

        self._watermark = min(event_based_watermark, process_based_watermark)
        return self._watermark

    def _get_or_create_window(self, event_time: float) -> EventTimeWindow:
        window_start = self.align_window_start(event_time, self.window_slide)

        if window_start not in self._windows:
            window_end = window_start + self.window_size
            self._windows[window_start] = EventTimeWindow(
                start=window_start,
                end=window_end
            )

        return self._windows[window_start]

    def _clean_expired_windows(self) -> int:
        expired_count = 0
        windows_to_remove = []

        for window_start, window in self._windows.items():
            if window.end <= self._watermark:
                window.is_closed = True
                self._expired_windows.append(window)
                windows_to_remove.append(window_start)
                expired_count += 1

        for window_start in windows_to_remove:
            del self._windows[window_start]

        return expired_count

    def add_viewer(self, data: Dict):
        try:
            action = data.get('action', 'enter')
            event_time = data.get('event_timestamp', data.get('timestamp', time.time()))

            self.update_watermark(event_time)

            if event_time < self._watermark:
                self._late_event_count += 1
                self._late_events.append({'type': 'viewer', 'data': data, 'event_time': event_time})
                return

            if action == 'enter':
                self._total_viewers += 1
            self._viewer_events.append({'event_time': event_time, 'action': action, 'delta': 1 if action == 'enter' else -1})

        except Exception as e:
            print(f"聚合观众数据错误: {e}")

    def add_online(self, data: Dict):
        try:
            event_time = data.get('event_timestamp', data.get('timestamp', time.time()))
            self.update_watermark(event_time)
            self._current_online = data.get('online_count', self._current_online)
        except Exception as e:
            print(f"聚合在线数据错误: {e}")

    def add_like(self, data: Dict):
        try:
            count = data.get('count', 1)
            event_time = data.get('event_timestamp', data.get('timestamp', time.time()))

            self.update_watermark(event_time)

            if event_time < self._watermark:
                self._late_event_count += 1
                self._late_events.append({'type': 'like', 'data': data, 'event_time': event_time})
                return

            self._total_likes += count
            self._like_events.append({'event_time': event_time, 'count': count})

        except Exception as e:
            print(f"聚合点赞数据错误: {e}")

    def add_transaction(self, data: Dict):
        try:
            amount = data.get('amount', 0.0)
            product_id = data.get('product_id', '')
            event_time = data.get('event_timestamp', data.get('timestamp', time.time()))

            self.update_watermark(event_time)

            if event_time < self._watermark:
                self._late_event_count += 1
                self._late_events.append({'type': 'transaction', 'data': data, 'event_time': event_time})
                return

            self._total_transactions += 1
            self._total_amount += amount

            window = self._get_or_create_window(event_time)
            window.add(data, event_time)

            self._transaction_events.append({
                'event_time': event_time,
                'amount': amount,
                'product_id': product_id,
                'window_start': window.start
            })

            self._product_stats[product_id]['orders'] += 1
            self._product_stats[product_id]['amount'] += amount

            self._clean_expired_windows()

        except Exception as e:
            print(f"聚合交易数据错误: {e}")

    def add_product_click(self, data: Dict):
        try:
            product_id = data.get('product_id', '')
            event_time = data.get('event_timestamp', data.get('timestamp', time.time()))

            self.update_watermark(event_time)

            if event_time < self._watermark:
                self._late_event_count += 1
                self._late_events.append({'type': 'product_click', 'data': data, 'event_time': event_time})
                return

            self._total_product_clicks += 1
            self._product_click_events.append({
                'event_time': event_time,
                'product_id': product_id
            })

            self._product_stats[product_id]['clicks'] += 1

        except Exception as e:
            print(f"聚合商品点击数据错误: {e}")

    def _get_event_count_in_range(self, events: deque, start_time: float, end_time: float) -> int:
        count = 0
        for event in events:
            et = event.get('event_time', event.get('timestamp', 0))
            if start_time <= et < end_time:
                count += event.get('count', event.get('delta', 1))
        return count

    def _get_event_amount_in_range(self, events: deque, start_time: float, end_time: float) -> float:
        amount = 0.0
        for event in events:
            et = event.get('event_time', event.get('timestamp', 0))
            if start_time <= et < end_time:
                amount += event.get('amount', 0.0)
        return amount

    def get_conversion_rate(self, use_event_time: bool = True) -> float:
        if use_event_time:
            current = self._watermark
            start = current - 60
        else:
            current = time.time()
            start = current - 60

        clicks = sum(
            1 for event in self._product_click_events
            if start <= event.get('event_time', 0) < current
        )
        orders = sum(
            1 for event in self._transaction_events
            if start <= event.get('event_time', 0) < current
        )

        if clicks == 0:
            return 0.0
        return round(orders / clicks, 4)

    def get_top_products(self, top_n: int = 5) -> List[Dict]:
        sorted_products = sorted(
            self._product_stats.items(),
            key=lambda x: x[1]['amount'],
            reverse=True
        )[:top_n]

        result = []
        for product_id, stats in sorted_products:
            clicks = stats['clicks']
            orders = stats['orders']
            result.append({
                'product_id': product_id,
                'clicks': clicks,
                'orders': orders,
                'amount': round(stats['amount'], 2),
                'conversion_rate': round(orders / clicks, 4) if clicks > 0 else 0.0,
            })
        return result

    def get_metrics(self, use_event_time: bool = True) -> Dict:
        if use_event_time:
            current_time = self._watermark
            window_end = self.align_window_end(self._max_event_time, self.window_slide)
            window_start = window_end - self.window_slide
        else:
            current_time = time.time()
            window_end = self.align_window_end(current_time, self.window_slide)
            window_start = window_end - self.window_slide

        second_data = {
            'event_time': self._max_event_time,
            'watermark': self._watermark,
            'window_start': window_start,
            'window_end': window_end,
            'viewers_per_second': self._get_event_count_in_range(
                self._viewer_events, window_start, window_end
            ),
            'likes_per_second': self._get_event_count_in_range(
                self._like_events, window_start, window_end
            ),
            'transactions_per_second': sum(
                1 for e in self._transaction_events
                if window_start <= e.get('event_time', 0) < window_end
            ),
            'amount_per_second': self._get_event_amount_in_range(
                self._transaction_events, window_start, window_end
            ),
        }
        self._second_stats.append(second_data)

        one_minute_ago = current_time - 60

        return {
            'total_viewers': self._total_viewers,
            'current_online': self._current_online,
            'total_likes': self._total_likes,
            'total_transactions': self._total_transactions,
            'total_amount': round(self._total_amount, 2),
            'total_product_clicks': self._total_product_clicks,
            'conversion_rate': self.get_conversion_rate(use_event_time),
            'viewers_per_minute': self._get_event_count_in_range(
                self._viewer_events, one_minute_ago, current_time
            ),
            'likes_per_minute': self._get_event_count_in_range(
                self._like_events, one_minute_ago, current_time
            ),
            'transactions_per_minute': sum(
                1 for e in self._transaction_events
                if one_minute_ago <= e.get('event_time', 0) < current_time
            ),
            'amount_per_minute': round(self._get_event_amount_in_range(
                self._transaction_events, one_minute_ago, current_time
            ), 2),
            'viewers_per_second': second_data['viewers_per_second'],
            'likes_per_second': second_data['likes_per_second'],
            'transactions_per_second': second_data['transactions_per_second'],
            'amount_per_second': round(second_data['amount_per_second'], 2),
            'event_time': self._max_event_time,
            'watermark': self._watermark,
            'late_event_count': self._late_event_count,
            'active_window_count': len(self._windows),
            'timestamp': time.time(),
        }

    def get_watermark_info(self) -> Dict:
        current_process_time = time.time()
        lag = current_process_time - self._max_event_time if self._max_event_time > 0 else 0.0

        return {
            'max_event_time': self._max_event_time,
            'current_watermark': self._watermark,
            'current_process_time': current_process_time,
            'lag': round(lag, 2),
            'watermark_delay': self.watermark_delay,
            'active_windows': len(self._windows),
            'expired_windows': len(self._expired_windows),
            'late_events': self._late_event_count,
        }

    def get_trend_data(self, points: int = 30, use_event_time: bool = True) -> Dict:
        if not self._second_stats:
            return {
                'timestamps': [],
                'viewers': [],
                'likes': [],
                'transactions': [],
                'amount': [],
                'event_timestamps': [],
                'watermarks': [],
            }

        stats = list(self._second_stats)[-points:]
        return {
            'timestamps': [s.get('event_time', s.get('timestamp', 0)) for s in stats],
            'viewers': [s['viewers_per_second'] for s in stats],
            'likes': [s['likes_per_second'] for s in stats],
            'transactions': [s['transactions_per_second'] for s in stats],
            'amount': [s['amount_per_second'] for s in stats],
            'event_timestamps': [s.get('event_time', 0) for s in stats],
            'watermarks': [s.get('watermark', 0) for s in stats],
        }

    def get_window_metrics(self, window_start: Optional[float] = None) -> Dict:
        if window_start is None:
            if self._windows:
                window_start = max(self._windows.keys())
            else:
                return {}

        window = self._windows.get(window_start)
        if not window:
            return {}

        return {
            'window_start': window.start,
            'window_end': window.end,
            'is_closed': window.is_closed,
            'total_amount': round(window.total_amount, 2),
            'transaction_count': window.count,
            'event_count': len(window.data),
        }

    def get_all_windows(self) -> List[Dict]:
        return [
            self.get_window_metrics(ws)
            for ws in sorted(self._windows.keys())
        ]


class MetricsAggregator(EventTimeAggregator):
    def __init__(self):
        super().__init__()
