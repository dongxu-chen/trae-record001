import time
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from collections import deque, defaultdict

from config import ADVISOR_CONFIG


@dataclass
class Suggestion:
    level: str
    category: str
    message: str
    action: str
    priority: int
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            'level': self.level,
            'category': self.category,
            'message': self.message,
            'action': self.action,
            'priority': self.priority,
            'timestamp': self.timestamp,
        }


@dataclass
class IncrementalState:
    _last_processed_danmu_id: int = 0
    _danmu_count: int = 0
    _positive_count: int = 0
    _negative_count: int = 0
    _neutral_count: int = 0
    _total_score: float = 0.0
    _window_positive_count: int = 0
    _window_negative_count: int = 0
    _window_neutral_count: int = 0
    _window_total_score: float = 0.0
    _window_start_time: float = field(default_factory=time.time)
    _concern_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _window_concern_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _max_window_seconds: int = 300

    @property
    def last_processed_danmu_id(self) -> int:
        return self._last_processed_danmu_id

    @property
    def danmu_count(self) -> int:
        return self._danmu_count

    def increment_danmu_id(self, new_id: int, count_as_processed: bool = True):
        if count_as_processed:
            self._danmu_count += 1
        if new_id > self._last_processed_danmu_id:
            self._last_processed_danmu_id = new_id

    def add_sentiment(self, label: str, score: float, concerns: List[str]):
        self._total_score += score
        if label == 'positive':
            self._positive_count += 1
            self._window_positive_count += 1
        elif label == 'negative':
            self._negative_count += 1
            self._window_negative_count += 1
        else:
            self._neutral_count += 1
            self._window_neutral_count += 1

        self._window_total_score += score

        for concern in concerns:
            self._concern_counts[concern] += 1
            self._window_concern_counts[concern] += 1

    def get_sentiment_stats(self, use_window: bool = False) -> Dict:
        if use_window:
            total = self._window_positive_count + self._window_negative_count + self._window_neutral_count
            if total == 0:
                return {
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0,
                    'total_count': 0,
                    'avg_score': 0.5,
                    'positive_rate': 0.0,
                    'negative_rate': 0.0,
                }
            return {
                'positive_count': self._window_positive_count,
                'negative_count': self._window_negative_count,
                'neutral_count': self._window_neutral_count,
                'total_count': total,
                'avg_score': round(self._window_total_score / total, 4),
                'positive_rate': round(self._window_positive_count / total, 4),
                'negative_rate': round(self._window_negative_count / total, 4),
            }
        else:
            total = self._positive_count + self._negative_count + self._neutral_count
            if total == 0:
                return {
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0,
                    'total_count': 0,
                    'avg_score': 0.5,
                    'positive_rate': 0.0,
                    'negative_rate': 0.0,
                }
            return {
                'positive_count': self._positive_count,
                'negative_count': self._negative_count,
                'neutral_count': self._neutral_count,
                'total_count': total,
                'avg_score': round(self._total_score / total, 4),
                'positive_rate': round(self._positive_count / total, 4),
                'negative_rate': round(self._negative_count / total, 4),
            }

    def get_top_concerns(self, top_n: int = 5, use_window: bool = False) -> List[Dict]:
        counts = self._window_concern_counts if use_window else self._concern_counts
        sorted_concerns = sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        return [{'concern': c, 'count': cnt} for c, cnt in sorted_concerns]

    def reset_window(self):
        self._window_positive_count = 0
        self._window_negative_count = 0
        self._window_neutral_count = 0
        self._window_total_score = 0.0
        self._window_start_time = time.time()
        self._window_concern_counts.clear()

    def check_and_reset_window(self) -> bool:
        if time.time() - self._window_start_time > self._max_window_seconds:
            self.reset_window()
            return True
        return False

    def get_window_age(self) -> float:
        return time.time() - self._window_start_time

    def to_dict(self) -> Dict:
        return {
            'last_processed_danmu_id': self._last_processed_danmu_id,
            'total_danmu': self._danmu_count,
            'window_age': round(self.get_window_age(), 2),
            'max_window_seconds': self._max_window_seconds,
        }


class LiveAdvisor:
    def __init__(self):
        self.check_interval = ADVISOR_CONFIG['check_interval']
        self.low_interaction_threshold = ADVISOR_CONFIG['low_interaction_threshold']
        self.high_conversion_threshold = ADVISOR_CONFIG['high_conversion_threshold']

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_data: Optional[Dict] = None
        self._suggestion_history = deque(maxlen=20)
        self._last_suggestion_time = 0
        self._min_suggestion_interval = 15

        self._state = IncrementalState()
        self._last_incremental_stats: Dict = {}

        self._interaction_baseline = None
        self._conversion_baseline = None

    def _process_incremental_danmu(self, latest_danmu: List[Dict]) -> int:
        if not latest_danmu:
            return 0

        processed_count = 0
        last_id = self._state.last_processed_danmu_id

        for danmu in latest_danmu:
            danmu_id = danmu.get('danmu_id', 0)
            if danmu_id > last_id:
                self._state.increment_danmu_id(danmu_id)
                sentiment = danmu.get('sentiment', {})
                label = sentiment.get('label', 'neutral')
                score = sentiment.get('score', 0.5)
                concerns = sentiment.get('concerns', [])
                self._state.add_sentiment(label, score, concerns)
                processed_count += 1

        if processed_count > 0:
            self._state.check_and_reset_window()

        return processed_count

    def _calculate_interaction_score(self, metrics: Dict) -> float:
        online = metrics.get('current_online', 1)
        likes_per_min = metrics.get('likes_per_minute', 0)
        viewers_per_min = metrics.get('viewers_per_minute', 0)

        full_stats = self._state.get_sentiment_stats(use_window=False)
        window_stats = self._state.get_sentiment_stats(use_window=True)

        danmu_rate = (full_stats['total_count'] / max(self._state.get_window_age() / 60, 1)) if self._state.get_window_age() > 0 else 0

        score = (
            (likes_per_min / max(online, 1) * 0.4) +
            (viewers_per_min / max(online, 1) * 0.3) +
            (danmu_rate / max(online, 1) * 0.3)
        )
        return min(score, 1.0)

    def _check_low_interaction(self, metrics: Dict) -> Optional[Suggestion]:
        score = self._calculate_interaction_score(metrics)
        online = metrics.get('current_online', 0)

        if score < self.low_interaction_threshold and online > 1000:
            return Suggestion(
                level='warning',
                category='interaction',
                message=f'当前互动指数偏低（{score:.2%}），观众参与度不高',
                action='建议发起互动活动：抽奖、问答、红包等引导观众参与',
                priority=2,
                timestamp=time.time(),
            )
        return None

    def _check_sentiment(self, full_stats: Dict, window_stats: Dict) -> Optional[Suggestion]:
        negative_rate = full_stats.get('negative_rate', 0)
        window_negative_rate = window_stats.get('negative_rate', 0)
        avg_score = full_stats.get('avg_score', 0.5)

        if window_negative_rate > 0.15:
            return Suggestion(
                level='danger',
                category='sentiment',
                message=f'近期负面评价占比过高（{window_negative_rate:.1%}），平均情感分{avg_score:.2f}',
                action='建议关注负面评论，及时回应用户顾虑，优化产品介绍',
                priority=3,
                timestamp=time.time(),
            )
        elif negative_rate > 0.08:
            return Suggestion(
                level='info',
                category='sentiment',
                message=f'负面评价有所上升（{negative_rate:.1%}），请注意引导',
                action='建议增加正向互动，强调产品优势和售后保障',
                priority=1,
                timestamp=time.time(),
            )
        return None

    def _check_conversion(self, metrics: Dict, top_products: List[Dict]) -> Optional[Suggestion]:
        conversion_rate = metrics.get('conversion_rate', 0)
        online = metrics.get('current_online', 0)

        if conversion_rate > self.high_conversion_threshold:
            return Suggestion(
                level='success',
                category='conversion',
                message=f'转化率表现优秀（{conversion_rate:.2%}），购买意愿强烈',
                action='建议趁热打铁，增加库存、推出组合套餐或限时优惠',
                priority=1,
                timestamp=time.time(),
            )
        elif conversion_rate < 0.05 and online > 2000:
            hot_product = top_products[0] if top_products else None
            product_name = hot_product.get('product_id', '爆款商品') if hot_product else '爆款商品'
            return Suggestion(
                level='warning',
                category='conversion',
                message=f'转化率偏低（{conversion_rate:.2%}），点击未转化',
                action=f'建议重点讲解{product_name}，强调性价比、展示用户评价、推出限时优惠',
                priority=2,
                timestamp=time.time(),
            )
        return None

    def _check_hotwords(self, hotwords: List[Dict], top_concerns: List[Dict]) -> Optional[Suggestion]:
        all_concerns = []

        for hw in hotwords[:10]:
            word = hw.get('word', '')
            concern_patterns = ['价格', '便宜', '优惠', '贵', '多少钱', '质量', '发货', '售后', '运费']
            for concern in concern_patterns:
                if concern in word or word in concern:
                    all_concerns.append(word)
                    break

        for tc in top_concerns[:3]:
            all_concerns.append(tc.get('concern', ''))

        all_concerns = list(set(all_concerns))

        if all_concerns:
            concerns_str = '、'.join(all_concerns[:5])
            return Suggestion(
                level='info',
                category='hotwords',
                message=f'观众高频关注：{concerns_str}',
                action=f'建议针对「{concerns_str}」进行重点讲解和答疑',
                priority=1,
                timestamp=time.time(),
            )
        return None

    def _check_online_trend(self, metrics: Dict) -> Optional[Suggestion]:
        online = metrics.get('current_online', 0)
        viewers_per_min = metrics.get('viewers_per_minute', 0)

        if viewers_per_min < 0 and online > 5000:
            return Suggestion(
                level='warning',
                category='online',
                message=f'观众正在流失，每分钟离开{abs(viewers_per_min)}人',
                action='建议提升直播节奏，推出爆点活动或发放福利留住观众',
                priority=2,
                timestamp=time.time(),
            )
        elif viewers_per_min > 100:
            return Suggestion(
                level='success',
                category='online',
                message=f'流量快速增长，每分钟新增{viewers_per_min}位观众',
                action='建议做好新观众承接：欢迎新人、介绍直播主题和福利',
                priority=1,
                timestamp=time.time(),
            )
        return None

    def _check_top_products(self, top_products: List[Dict]) -> Optional[Suggestion]:
        if not top_products:
            return None

        top_product = top_products[0]
        conversion = top_product.get('conversion_rate', 0)
        amount = top_product.get('amount', 0)

        if conversion > 0.2:
            return Suggestion(
                level='success',
                category='products',
                message=f'{top_product["product_id"]} 爆款预警！转化率{conversion:.1%}，销售额¥{amount:,.0f}',
                action='建议延长讲解时间，增加库存，推出多件优惠套餐',
                priority=2,
                timestamp=time.time(),
            )
        return None

    def _check_sentiment_trend(self, full_stats: Dict, window_stats: Dict) -> Optional[Suggestion]:
        full_positive = full_stats.get('positive_rate', 0)
        window_positive = window_stats.get('positive_rate', 0)
        window_total = window_stats.get('total_count', 0)

        if window_total >= 10 and window_positive - full_positive > 0.15:
            return Suggestion(
                level='success',
                category='sentiment_trend',
                message=f'观众情绪明显好转！近期正面率{window_positive:.1%}，整体{full_positive:.1%}',
                action='建议保持当前节奏，继续强化产品优势介绍',
                priority=1,
                timestamp=time.time(),
            )
        elif window_total >= 10 and full_positive - window_positive > 0.15:
            return Suggestion(
                level='warning',
                category='sentiment_trend',
                message=f'观众情绪有所下降！近期正面率{window_positive:.1%}，整体{full_positive:.1%}',
                action='建议调整讲解策略，增加互动和福利环节',
                priority=2,
                timestamp=time.time(),
            )
        return None

    def analyze(self, data: Dict) -> Optional[Dict]:
        self._latest_data = data

        latest_danmu = data.get('latest_danmu', [])
        incremental_info = data.get('incremental_info', {})

        processed_count = self._process_incremental_danmu(latest_danmu)

        external_last_id = incremental_info.get('last_processed_danmu_id', 0)
        if external_last_id > self._state.last_processed_danmu_id:
            self._state.increment_danmu_id(external_last_id, count_as_processed=False)

        full_stats = self._state.get_sentiment_stats(use_window=False)
        window_stats = self._state.get_sentiment_stats(use_window=True)
        top_concerns = self._state.get_top_concerns(use_window=True)

        self._last_incremental_stats = {
            'processed_danmu_count': processed_count,
            'total_danmu_processed': self._state.danmu_count,
            'last_processed_danmu_id': self._state.last_processed_danmu_id,
            'window_age': round(self._state.get_window_age(), 2),
            'full_stats': full_stats,
            'window_stats': window_stats,
            'top_concerns': top_concerns,
        }

        current_time = time.time()
        if current_time - self._last_suggestion_time < self._min_suggestion_interval:
            return {
                'incremental': self._last_incremental_stats,
                'state': self._state.to_dict(),
                'current': None,
                'history': [s.to_dict() for s in list(self._suggestion_history)[-5:]],
            }

        metrics = data.get('metrics', {})
        hotwords = data.get('hotwords', [])
        top_products = data.get('top_products', [])

        suggestions: List[Suggestion] = []

        checkers = [
            self._check_low_interaction(metrics),
            self._check_sentiment(full_stats, window_stats),
            self._check_conversion(metrics, top_products),
            self._check_hotwords(hotwords, top_concerns),
            self._check_online_trend(metrics),
            self._check_top_products(top_products),
            self._check_sentiment_trend(full_stats, window_stats),
        ]

        for s in checkers:
            if s:
                suggestions.append(s)

        if not suggestions:
            return {
                'incremental': self._last_incremental_stats,
                'state': self._state.to_dict(),
                'current': None,
                'history': [s.to_dict() for s in list(self._suggestion_history)[-5:]],
            }

        suggestions.sort(key=lambda x: -x.priority)
        top_suggestion = suggestions[0]

        recent = any(
            s.category == top_suggestion.category
            for s in list(self._suggestion_history)[-3:]
        )
        if recent:
            return {
                'incremental': self._last_incremental_stats,
                'state': self._state.to_dict(),
                'current': None,
                'history': [s.to_dict() for s in list(self._suggestion_history)[-5:]],
            }

        self._suggestion_history.append(top_suggestion)
        self._last_suggestion_time = current_time

        return {
            'incremental': self._last_incremental_stats,
            'state': self._state.to_dict(),
            'current': top_suggestion.to_dict(),
            'history': [s.to_dict() for s in list(self._suggestion_history)[-5:]],
        }

    def get_incremental_state(self) -> Dict:
        return self._state.to_dict()

    def get_incremental_stats(self) -> Dict:
        return self._last_incremental_stats

    def reset_state(self):
        self._state = IncrementalState()
        self._last_incremental_stats = {}

    def start(self):
        self._running = True
        print("主播话术建议模块已启动（增量计算模式）")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("主播话术建议模块已停止")
