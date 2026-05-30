import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import random
from scipy import signal
from scipy.fft import fft, fftfreq
from enum import Enum


class SeasonalityType(Enum):
    NONE = "无季节性"
    SPRING = "春季商品"
    SUMMER = "夏季商品"
    AUTUMN = "秋季商品"
    WINTER = "冬季商品"
    HOLIDAY = "节日商品"
    WEEKEND = "周末高峰"
    MONTH_END = "月末高峰"


@dataclass
class SeasonalPattern:
    product_id: str
    seasonality_type: SeasonalityType
    peak_seasons: List[int]
    seasonality_strength: float
    trend_slope: float
    cyclic_period: int
    confidence_score: float


@dataclass
class Product:
    id: str
    name: str
    width: float
    depth: float
    height: float
    weight: float
    turnover_rate: float
    category: str
    volume: float = field(init=False)
    seasonal_pattern: Optional[SeasonalPattern] = None
    current_season_weight: float = 1.0

    def __post_init__(self):
        self.volume = self.width * self.depth * self.height

    def get_effective_turnover(self, season: int = 0) -> float:
        if self.seasonal_pattern and season in self.seasonal_pattern.peak_seasons:
            return self.turnover_rate * (1 + self.seasonal_pattern.seasonality_strength)
        return self.turnover_rate * self.current_season_weight


class TimeSeriesDecomposer:
    def __init__(self, period_days: int = 365):
        self.period_days = period_days

    def decompose(self, time_series: pd.Series) -> Dict:
        if len(time_series) < 30:
            return {
                'trend': np.zeros(len(time_series)),
                'seasonal': np.zeros(len(time_series)),
                'residual': time_series.values,
                'seasonality_strength': 0.0
            }

        try:
            ts = pd.Series(time_series.values, index=pd.date_range(
                start='2024-01-01', periods=len(time_series), freq='D'))

            decomposition = signal.seasonal_decompose(
                ts, model='additive', period=min(30, len(ts) // 2), extrapolate_trend='freq')

            trend = decomposition.trend.values
            seasonal = decomposition.seasonal.values
            residual = decomposition.resid.values

            seasonal_var = np.var(seasonal)
            total_var = np.var(ts.values)
            seasonality_strength = seasonal_var / total_var if total_var > 0 else 0

            return {
                'trend': trend,
                'seasonal': seasonal,
                'residual': residual,
                'seasonality_strength': min(seasonality_strength, 1.0)
            }
        except:
            return {
                'trend': np.zeros(len(time_series)),
                'seasonal': np.zeros(len(time_series)),
                'residual': time_series.values,
                'seasonality_strength': 0.0
            }

    def detect_peak_periods(self, seasonal_component: np.ndarray,
                            num_peaks: int = 2) -> List[int]:
        peaks, _ = signal.find_peaks(seasonal_component, distance=len(seasonal_component) // 12)
        peak_indices = sorted(peaks, key=lambda x: seasonal_component[x], reverse=True)[:num_peaks]
        return sorted([int(p * 12 / len(seasonal_component)) % 12 for p in peak_indices])

    def fft_analysis(self, time_series: np.ndarray) -> Dict:
        n = len(time_series)
        if n < 32:
            return {'dominant_period': 7, 'frequency_strength': 0.0}

        yf = fft(time_series - np.mean(time_series))
        xf = fftfreq(n, 1)[:n // 2]

        positive_freqs = xf[1:n // 2]
        magnitudes = 2.0 / n * np.abs(yf[1:n // 2])

        if len(magnitudes) > 0:
            dominant_idx = np.argmax(magnitudes)
            dominant_freq = positive_freqs[dominant_idx]
            dominant_period = int(1 / dominant_freq) if dominant_freq > 0 else 7
            frequency_strength = magnitudes[dominant_idx] / np.sum(magnitudes) if np.sum(magnitudes) > 0 else 0
        else:
            dominant_period = 7
            frequency_strength = 0.0

        return {
            'dominant_period': max(1, min(dominant_period, 365)),
            'frequency_strength': frequency_strength
        }


class SeasonalityAnalyzer:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.decomposer = TimeSeriesDecomposer()
        self.product_seasonality: Dict[str, SeasonalPattern] = {}

    def analyze_product_history(self, product_id: str,
                                daily_sales: Optional[pd.Series] = None,
                                num_days: int = 365) -> SeasonalPattern:
        if daily_sales is None:
            daily_sales = self._generate_synthetic_sales(product_id, num_days)

        decomposition = self.decomposer.decompose(daily_sales)
        fft_result = self.decomposer.fft_analysis(daily_sales.values)
        peak_periods = self.decomposer.detect_peak_periods(decomposition['seasonal'])

        seasonality_type = self._classify_seasonality(peak_periods, decomposition['seasonality_strength'])
        trend_slope = np.polyfit(range(len(decomposition['trend'])), decomposition['trend'], 1)[0]
        confidence_score = min(decomposition['seasonality_strength'] * 0.7 + fft_result['frequency_strength'] * 0.3, 1.0)

        pattern = SeasonalPattern(
            product_id=product_id,
            seasonality_type=seasonality_type,
            peak_seasons=peak_periods,
            seasonality_strength=decomposition['seasonality_strength'],
            trend_slope=trend_slope,
            cyclic_period=fft_result['dominant_period'],
            confidence_score=confidence_score
        )

        self.product_seasonality[product_id] = pattern
        return pattern

    def _generate_synthetic_sales(self, product_id: str, num_days: int) -> pd.Series:
        product = self.warehouse.products.get(product_id)
        if not product:
            return pd.Series(np.zeros(num_days))

        base_demand = product.turnover_rate * 10
        category_patterns = {
            '电子产品': {'seasonal_amp': 0.2, 'peak_month': 11},
            '服装': {'seasonal_amp': 0.5, 'peak_month': random.choice([1, 7])},
            '食品': {'seasonal_amp': 0.15, 'peak_month': 12},
            '日用品': {'seasonal_amp': 0.1, 'peak_month': 6},
            '工具': {'seasonal_amp': 0.25, 'peak_month': 4},
            '玩具': {'seasonal_amp': 0.6, 'peak_month': 12}
        }

        pattern = category_patterns.get(product.category, {'seasonal_amp': 0.2, 'peak_month': 6})
        seasonal_amp = pattern['seasonal_amp']
        peak_month = pattern['peak_month']

        days = np.arange(num_days)
        seasonal_component = seasonal_amp * np.sin(2 * np.pi * (days - peak_month * 30) / 365)
        weekend_effect = 0.3 * np.array([1 if d % 7 in [5, 6] else 0 for d in days])
        noise = np.random.normal(0, 0.1, num_days)

        sales = base_demand * (1 + seasonal_component + weekend_effect + noise)
        sales = np.maximum(sales, 0)

        return pd.Series(sales)

    def _classify_seasonality(self, peak_months: List[int], strength: float) -> SeasonalityType:
        if strength < 0.1:
            return SeasonalityType.NONE

        if not peak_months:
            return SeasonalityType.NONE

        avg_peak = np.mean(peak_months)

        if 2 <= avg_peak <= 4:
            return SeasonalityType.SPRING
        elif 5 <= avg_peak <= 7:
            return SeasonalityType.SUMMER
        elif 8 <= avg_peak <= 10:
            return SeasonalityType.AUTUMN
        else:
            if strength > 0.4:
                return SeasonalityType.HOLIDAY
            return SeasonalityType.WINTER

    def get_seasonal_weight(self, product_id: str, current_month: int) -> float:
        pattern = self.product_seasonality.get(product_id)
        if not pattern:
            return 1.0

        if current_month in pattern.peak_seasons:
            return 1.0 + pattern.seasonality_strength
        else:
            return max(0.3, 1.0 - pattern.seasonality_strength * 0.5)

    def analyze_all_products(self, num_days: int = 365) -> Dict[str, SeasonalPattern]:
        for product_id in self.warehouse.products.keys():
            self.analyze_product_history(product_id, num_days=num_days)
            pattern = self.product_seasonality[product_id]
            self.warehouse.products[product_id].seasonal_pattern = pattern

        return self.product_seasonality

    def get_seasonal_recommendations(self, current_month: int) -> List[Tuple[str, str, float]]:
        recommendations = []
        depot_pos = np.array([-1.0, -1.0, 0.0])

        for product_id, pattern in self.product_seasonality.items():
            product = self.warehouse.products[product_id]
            weight = self.get_seasonal_weight(product_id, current_month)

            if weight > 1.2 and pattern.confidence_score > 0.3:
                action = "建议移至靠近出库台位置"
            elif weight < 0.7 and pattern.confidence_score > 0.3:
                action = "建议移至仓库深处"
            else:
                continue

            recommendations.append((product_id, action, weight))

        return sorted(recommendations, key=lambda x: abs(x[2] - 1.0), reverse=True)


class ZoneType(Enum):
    GOLD = "黄金区"
    SILVER = "白银区"
    BRONZE = "青铜区"
    STORAGE = "存储区"


class ABCClass(Enum):
    A = "A类 (高周转)"
    B = "B类 (中周转)"
    C = "C类 (低周转)"


@dataclass
class Location:
    id: str
    aisle: int
    bay: int
    level: int
    max_width: float
    max_depth: float
    max_height: float
    max_weight: float
    x: float
    y: float
    z: float
    zone: ZoneType = ZoneType.STORAGE
    is_occupied: bool = False
    product_id: Optional[str] = None
    allowed_abc_classes: List[ABCClass] = field(default_factory=lambda: [ABCClass.A, ABCClass.B, ABCClass.C])

    @property
    def coordinates(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class ABCAnalysisResult:
    product_id: str
    abc_class: ABCClass
    turnover_rate: float
    cumulative_percent: float
    annual_demand: float
    annual_value: float


class ABCAnalyzer:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.abc_results: Dict[str, ABCAnalysisResult] = {}
        self.threshold_a = 0.8
        self.threshold_b = 0.95

    def perform_abc_analysis(self, use_value: bool = False) -> Dict[str, ABCAnalysisResult]:
        products_data = []
        for prod_id, product in self.warehouse.products.items():
            annual_demand = product.turnover_rate * 365
            annual_value = annual_demand * (product.weight * 0.1 + product.volume * 0.05)
            products_data.append({
                'product_id': prod_id,
                'turnover_rate': product.turnover_rate,
                'annual_demand': annual_demand,
                'annual_value': annual_value if use_value else annual_demand
            })

        df = pd.DataFrame(products_data)
        df = df.sort_values('annual_value', ascending=False)
        df['cumulative_value'] = df['annual_value'].cumsum()
        total_value = df['annual_value'].sum()
        df['cumulative_percent'] = df['cumulative_value'] / total_value * 100

        for _, row in df.iterrows():
            if row['cumulative_percent'] <= self.threshold_a * 100:
                abc_class = ABCClass.A
            elif row['cumulative_percent'] <= self.threshold_b * 100:
                abc_class = ABCClass.B
            else:
                abc_class = ABCClass.C

            self.abc_results[row['product_id']] = ABCAnalysisResult(
                product_id=row['product_id'],
                abc_class=abc_class,
                turnover_rate=row['turnover_rate'],
                cumulative_percent=row['cumulative_percent'],
                annual_demand=row['annual_demand'],
                annual_value=row['annual_value']
            )

        return self.abc_results

    def get_products_by_class(self, abc_class: ABCClass) -> List[str]:
        return [pid for pid, res in self.abc_results.items() if res.abc_class == abc_class]

    def get_class_stats(self) -> Dict:
        stats = {}
        for cls in ABCClass:
            products = self.get_products_by_class(cls)
            stats[cls.value] = {
                'count': len(products),
                'percent': len(products) / len(self.abc_results) * 100 if self.abc_results else 0,
                'avg_turnover': np.mean([self.abc_results[p].turnover_rate for p in products]) if products else 0
            }
        return stats


class DynamicAdjustmentManager:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.current_mode = "normal"
        self.mode_history = []
        self.reoptimization_triggers = []
        self.last_optimization_time = None
        self.mode_thresholds = {
            'peak_intensity': 2.0,
            'seasonal_change': 0.3,
            'order_pattern_change': 0.25
        }

    def detect_mode_change(self, current_intensity: float,
                          current_month: int,
                          order_pattern_similarity: float) -> Tuple[bool, str]:
        triggers = []

        if current_intensity >= self.mode_thresholds['peak_intensity']:
            triggers.append("peak_demand")

        if len(self.mode_history) > 0:
            last_month = self.mode_history[-1].get('month', current_month)
            if last_month != current_month:
                triggers.append("seasonal_change")

        if order_pattern_similarity < (1 - self.mode_thresholds['order_pattern_change']):
            triggers.append("pattern_shift")

        self.mode_history.append({
            'time': pd.Timestamp.now(),
            'intensity': current_intensity,
            'month': current_month,
            'triggers': triggers
        })

        if len(self.mode_history) > 100:
            self.mode_history = self.mode_history[-100:]

        return len(triggers) > 0, triggers

    def should_reoptimize(self, hours_since_last: float = 24) -> bool:
        if self.last_optimization_time is None:
            return True

        time_diff = (pd.Timestamp.now() - self.last_optimization_time).total_seconds() / 3600
        if time_diff >= hours_since_last:
            return True

        recent_triggers = [t for entry in self.mode_history[-5:] for t in entry.get('triggers', [])]
        if 'peak_demand' in recent_triggers or 'seasonal_change' in recent_triggers:
            return True

        return False

    def record_optimization(self):
        self.last_optimization_time = pd.Timestamp.now()


class Warehouse:
    def __init__(self, num_aisles: int = 4, bays_per_aisle: int = 10, levels: int = 3):
        self.num_aisles = num_aisles
        self.bays_per_aisle = bays_per_aisle
        self.levels = levels
        self.locations: Dict[str, Location] = {}
        self.products: Dict[str, Product] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.abc_analyzer = ABCAnalyzer(self)
        self.dynamic_manager = DynamicAdjustmentManager(self)
        self._generate_locations()
        self._assign_zones()

    def _generate_locations(self):
        aisle_spacing = 5.0
        bay_width = 2.0
        level_height = 1.5

        for aisle in range(1, self.num_aisles + 1):
            for bay in range(1, self.bays_per_aisle + 1):
                for level in range(1, self.levels + 1):
                    loc_id = f"A{aisle:02d}B{bay:02d}L{level:02d}"
                    x = (aisle - 1) * aisle_spacing
                    y = (bay - 1) * bay_width
                    z = (level - 1) * level_height

                    self.locations[loc_id] = Location(
                        id=loc_id,
                        aisle=aisle,
                        bay=bay,
                        level=level,
                        max_width=2.0,
                        max_depth=1.0,
                        max_height=1.5,
                        max_weight=100.0,
                        x=x,
                        y=y,
                        z=z
                    )

    def _assign_zones(self):
        depot_x, depot_y, depot_z = -1.0, -1.0, 0.0

        for loc_id, loc in self.locations.items():
            distance = np.sqrt(
                (loc.x - depot_x) ** 2 +
                (loc.y - depot_y) ** 2 +
                (loc.z - depot_z) ** 2
            )

            is_middle_level = (loc.level == 2 and self.levels >= 3) or (loc.level == 1 and self.levels == 2)
            is_near_front = loc.bay <= self.bays_per_aisle // 3
            is_center_aisle = 1 <= loc.aisle <= 2

            if distance < 8.0 and is_middle_level and is_near_front:
                loc.zone = ZoneType.GOLD
                loc.allowed_abc_classes = [ABCClass.A]
            elif distance < 15.0 and (is_middle_level or is_near_front):
                loc.zone = ZoneType.SILVER
                loc.allowed_abc_classes = [ABCClass.A, ABCClass.B]
            elif distance < 25.0:
                loc.zone = ZoneType.BRONZE
                loc.allowed_abc_classes = [ABCClass.A, ABCClass.B, ABCClass.C]
            else:
                loc.zone = ZoneType.STORAGE
                loc.allowed_abc_classes = [ABCClass.B, ABCClass.C]

    def get_locations_by_zone(self, zone: ZoneType) -> List[Location]:
        return [loc for loc in self.locations.values() if loc.zone == zone]

    def get_golden_locations(self) -> List[Location]:
        return self.get_locations_by_zone(ZoneType.GOLD)

    def add_product(self, product: Product):
        self.products[product.id] = product

    def add_products_from_dataframe(self, df: pd.DataFrame):
        for _, row in df.iterrows():
            product = Product(
                id=str(row['product_id']),
                name=row['product_name'],
                width=row['width'],
                depth=row['depth'],
                height=row['height'],
                weight=row['weight'],
                turnover_rate=row['turnover_rate'],
                category=row['category']
            )
            self.add_product(product)

    def generate_correlation_matrix(self, orders_data: Optional[pd.DataFrame] = None):
        product_ids = list(self.products.keys())
        n = len(product_ids)

        if orders_data is not None:
            for i, p1 in enumerate(product_ids):
                self.correlation_matrix[p1] = {}
                for j, p2 in enumerate(product_ids):
                    if i == j:
                        self.correlation_matrix[p1][p2] = 1.0
                    else:
                        corr = self._calculate_order_correlation(p1, p2, orders_data)
                        self.correlation_matrix[p1][p2] = corr
        else:
            for i, p1 in enumerate(product_ids):
                self.correlation_matrix[p1] = {}
                for j, p2 in enumerate(product_ids):
                    if i == j:
                        self.correlation_matrix[p1][p2] = 1.0
                    else:
                        cat1 = self.products[p1].category
                        cat2 = self.products[p2].category
                        if cat1 == cat2:
                            self.correlation_matrix[p1][p2] = random.uniform(0.5, 0.9)
                        else:
                            self.correlation_matrix[p1][p2] = random.uniform(0.0, 0.3)

    def _calculate_order_correlation(self, p1: str, p2: str, orders: pd.DataFrame) -> float:
        p1_orders = set(orders[orders['product_id'] == p1]['order_id'])
        p2_orders = set(orders[orders['product_id'] == p2]['order_id'])

        if not p1_orders or not p2_orders:
            return 0.0

        intersection = len(p1_orders & p2_orders)
        union = len(p1_orders | p2_orders)

        return intersection / union if union > 0 else 0.0

    def get_location_distance(self, loc1_id: str, loc2_id: str) -> float:
        loc1 = self.locations[loc1_id]
        loc2 = self.locations[loc2_id]
        return np.sqrt(
            (loc1.x - loc2.x) ** 2 +
            (loc1.y - loc2.y) ** 2 +
            (loc1.z - loc2.z) ** 2
        )

    def get_aisle_distance(self, loc1_id: str, loc2_id: str) -> float:
        loc1 = self.locations[loc1_id]
        loc2 = self.locations[loc2_id]
        return abs(loc1.x - loc2.x) + abs(loc1.y - loc2.y) + abs(loc1.z - loc2.z)

    def reset_assignments(self):
        for loc in self.locations.values():
            loc.is_occupied = False
            loc.product_id = None

    def assign_product(self, product_id: str, location_id: str) -> bool:
        if location_id not in self.locations:
            return False
        if product_id not in self.products:
            return False

        loc = self.locations[location_id]
        prod = self.products[product_id]

        if (prod.width <= loc.max_width and
            prod.depth <= loc.max_depth and
            prod.height <= loc.max_height and
            prod.weight <= loc.max_weight):
            loc.is_occupied = True
            loc.product_id = product_id
            return True
        return False

    def get_product_assignment(self) -> Dict[str, str]:
        return {loc.product_id: loc_id
                for loc_id, loc in self.locations.items()
                if loc.product_id is not None}

    def get_location_assignment(self) -> Dict[str, Optional[str]]:
        return {loc_id: loc.product_id
                for loc_id, loc in self.locations.items()}

    def get_assigned_locations(self) -> List[Location]:
        return [loc for loc in self.locations.values() if loc.product_id is not None]

    def get_empty_locations(self) -> List[Location]:
        return [loc for loc in self.locations.values() if loc.product_id is None]


def generate_sample_products(num_products: int = 50) -> pd.DataFrame:
    categories = ['电子产品', '日用品', '食品', '服装', '工具', '玩具']
    products = []

    for i in range(1, num_products + 1):
        products.append({
            'product_id': f'P{i:03d}',
            'product_name': f'商品_{i}',
            'width': random.uniform(0.2, 0.8),
            'depth': random.uniform(0.2, 0.6),
            'height': random.uniform(0.1, 0.5),
            'weight': random.uniform(0.5, 20.0),
            'turnover_rate': random.uniform(0.1, 5.0),
            'category': random.choice(categories)
        })

    return pd.DataFrame(products)


def generate_sample_orders(num_orders: int = 200, product_ids: List[str] = None) -> pd.DataFrame:
    if product_ids is None:
        product_ids = [f'P{i:03d}' for i in range(1, 51)]

    orders = []
    for order_id in range(1, num_orders + 1):
        num_items = random.randint(1, 8)
        items = random.sample(product_ids, min(num_items, len(product_ids)))
        for item in items:
            orders.append({
                'order_id': f'O{order_id:04d}',
                'product_id': item,
                'quantity': random.randint(1, 5)
            })

    return pd.DataFrame(orders)
