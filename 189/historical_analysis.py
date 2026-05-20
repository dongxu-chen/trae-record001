import numpy as np
import pandas as pd
from datetime import timedelta
from config import Config


class HistoricalAnalysis:
    def __init__(self):
        self.config = Config()

    def get_same_period_history(self, df, target_date, years_back=1, days_window=7):
        target_date = pd.to_datetime(target_date)
        history_data = []

        for year_offset in range(1, years_back + 1):
            compare_year = target_date.year - year_offset
            try:
                compare_date = target_date.replace(year=compare_year)
            except ValueError:
                continue

            start_date = compare_date - timedelta(days=days_window)
            end_date = compare_date + timedelta(days=days_window)

            mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
            period_data = df[mask].copy()

            if len(period_data) > 0:
                period_data['year_offset'] = year_offset
                period_data['compare_type'] = f'同期第{year_offset}年'
                history_data.append(period_data)

        if len(history_data) > 0:
            return pd.concat(history_data, ignore_index=True)
        return pd.DataFrame()

    def get_weekday_comparison(self, df, target_date, weeks_back=4):
        target_date = pd.to_datetime(target_date)
        target_weekday = target_date.weekday()

        history_data = []
        for week_offset in range(1, weeks_back + 1):
            compare_date = target_date - timedelta(weeks=week_offset)
            start_date = compare_date - timedelta(days=1)
            end_date = compare_date + timedelta(days=1)

            mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
            period_data = df[mask].copy()

            if len(period_data) > 0:
                period_data['week_offset'] = week_offset
                period_data['compare_type'] = f'前第{week_offset}周'
                history_data.append(period_data)

        if len(history_data) > 0:
            return pd.concat(history_data, ignore_index=True)
        return pd.DataFrame()

    def get_monthly_comparison(self, df, target_date, months_back=12):
        target_date = pd.to_datetime(target_date)
        history_data = []

        for month_offset in range(1, months_back + 1):
            compare_date = target_date - timedelta(days=30 * month_offset)
            start_date = compare_date - timedelta(days=15)
            end_date = compare_date + timedelta(days=15)

            mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
            period_data = df[mask].copy()

            if len(period_data) > 0:
                period_data['month_offset'] = month_offset
                period_data['compare_type'] = f'前第{month_offset}月'
                history_data.append(period_data)

        if len(history_data) > 0:
            return pd.concat(history_data, ignore_index=True)
        return pd.DataFrame()

    def calculate_statistics(self, data, pollutants=None):
        if pollutants is None:
            pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'AQI']

        stats = {}
        for pollutant in pollutants:
            if pollutant in data.columns:
                values = data[pollutant].dropna()
                if len(values) > 0:
                    stats[pollutant] = {
                        'mean': values.mean(),
                        'median': values.median(),
                        'std': values.std(),
                        'min': values.min(),
                        'max': values.max(),
                        'p25': values.quantile(0.25),
                        'p75': values.quantile(0.75),
                        'count': len(values)
                    }
        return stats

    def compare_with_history(self, df, target_period_start, target_period_hours=24, years_back=3):
        target_start = pd.to_datetime(target_period_start)
        target_end = target_start + timedelta(hours=target_period_hours)

        target_mask = (df['timestamp'] >= target_start) & (df['timestamp'] < target_end)
        target_data = df[target_mask].copy()

        if len(target_data) == 0:
            return None

        target_stats = self.calculate_statistics(target_data)

        history_comparisons = []
        for year_offset in range(1, years_back + 1):
            hist_start = target_start.replace(year=target_start.year - year_offset)
            hist_end = hist_start + timedelta(hours=target_period_hours)

            hist_mask = (df['timestamp'] >= hist_start) & (df['timestamp'] < hist_end)
            hist_data = df[hist_mask].copy()

            if len(hist_data) > 0:
                hist_stats = self.calculate_statistics(hist_data)
                comparison = self._compare_stats(target_stats, hist_stats)
                history_comparisons.append({
                    'year_offset': year_offset,
                    'period': f'{hist_start.date()} ~ {hist_end.date()}',
                    'stats': hist_stats,
                    'comparison': comparison
                })

        return {
            'target_period': {
                'start': target_start,
                'end': target_end,
                'stats': target_stats,
                'data': target_data
            },
            'history_comparisons': history_comparisons
        }

    def _compare_stats(self, target_stats, hist_stats):
        comparison = {}
        for pollutant in target_stats:
            if pollutant in hist_stats:
                target_mean = target_stats[pollutant]['mean']
                hist_mean = hist_stats[pollutant]['mean']
                if hist_mean > 0:
                    change_pct = (target_mean - hist_mean) / hist_mean * 100
                else:
                    change_pct = 0 if target_mean == 0 else 100

                comparison[pollutant] = {
                    'target_mean': target_mean,
                    'history_mean': hist_mean,
                    'absolute_change': target_mean - hist_mean,
                    'percentage_change': change_pct,
                    'trend': '改善' if change_pct < -5 else '恶化' if change_pct > 5 else '持平'
                }
        return comparison

    def detect_anomalies(self, df, window=24, threshold=2):
        df = df.copy()
        pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'AQI']
        anomalies = []

        for pollutant in pollutants:
            if pollutant in df.columns:
                rolling_mean = df[pollutant].rolling(window=window).mean()
                rolling_std = df[pollutant].rolling(window=window).std()

                upper_bound = rolling_mean + threshold * rolling_std
                lower_bound = rolling_mean - threshold * rolling_std

                anomaly_mask = (df[pollutant] > upper_bound) | (df[pollutant] < lower_bound)
                anomaly_rows = df[anomaly_mask].copy()

                for idx, row in anomaly_rows.iterrows():
                    anomalies.append({
                        'timestamp': row['timestamp'],
                        'pollutant': pollutant,
                        'value': row[pollutant],
                        'expected': rolling_mean.loc[idx],
                        'deviation': row[pollutant] - rolling_mean.loc[idx],
                        'severity': abs(row[pollutant] - rolling_mean.loc[idx]) / rolling_std.loc[idx] if rolling_std.loc[idx] > 0 else 0
                    })

        return pd.DataFrame(anomalies)

    def analyze_trend(self, df, period='W'):
        df = df.copy()
        df = df.set_index('timestamp')
        pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'AQI']

        trend_data = df[pollutants].resample(period).mean()
        trend_data = trend_data.reset_index()

        trends = {}
        for pollutant in pollutants:
            if pollutant in trend_data.columns:
                values = trend_data[pollutant].dropna().values
                if len(values) >= 2:
                    x = np.arange(len(values))
                    slope, intercept = np.polyfit(x, values, 1)
                    trends[pollutant] = {
                        'slope': slope,
                        'direction': '下降' if slope < -0.1 else '上升' if slope > 0.1 else '稳定',
                        'change_per_period': slope,
                        'values': values.tolist()
                    }

        return trend_data, trends

    def print_historical_report(self, comparison_result):
        if comparison_result is None:
            print("未找到目标时段数据")
            return

        target = comparison_result['target_period']
        print("\n" + "=" * 80)
        print(" " * 25 + "历史重演分析报告")
        print("=" * 80)

        print(f"\n📅 目标时段: {target['start']} ~ {target['end']}")

        print("\n📊 目标时段统计:")
        for pollutant, stats in target['stats'].items():
            print(f"  {pollutant:<6}: 均值 {stats['mean']:>6.1f}, 范围 [{stats['min']:.1f}, {stats['max']:.1f}]")

        print("\n📈 历史同期对比:")
        print("-" * 80)
        print(f"{'对比年份':<12} {'指标':<8} {'目标均值':<10} {'历史均值':<10} {'变化率':<10} {'趋势':<8}")
        print("-" * 80)

        for comp in comparison_result['history_comparisons']:
            for pollutant, data in comp['comparison'].items():
                change_str = f"{data['percentage_change']:+.1f}%"
                print(f"{comp['period']:<12} {pollutant:<8} {data['target_mean']:<10.1f} {data['history_mean']:<10.1f} {change_str:<10} {data['trend']:<8}")
            print()

        print("-" * 80)

        overall_changes = {}
        for comp in comparison_result['history_comparisons']:
            for pollutant, data in comp['comparison'].items():
                if pollutant not in overall_changes:
                    overall_changes[pollutant] = []
                overall_changes[pollutant].append(data['percentage_change'])

        print("\n🏆 总体变化趋势总结:")
        for pollutant, changes in overall_changes.items():
            avg_change = np.mean(changes)
            trend = '显著改善' if avg_change < -10 else '改善' if avg_change < -5 else '持平' if abs(avg_change) <= 5 else '恶化' if avg_change > 5 else '显著恶化'
            print(f"  {pollutant:<6}: 平均变化 {avg_change:+.1f}% → {trend}")

        print("\n" + "=" * 80)

    def print_trend_report(self, trend_data, trends):
        print("\n" + "=" * 80)
        print(" " * 28 + "长期趋势分析报告")
        print("=" * 80)

        print("\n📈 各污染物长期趋势:")
        for pollutant, trend_info in trends.items():
            direction_emoji = '📉' if trend_info['direction'] == '下降' else '📈' if trend_info['direction'] == '上升' else '➡️'
            print(f"  {direction_emoji} {pollutant:<6}: {trend_info['direction']}, 变化率 {trend_info['change_per_period']:+.2f}/周期")

        print("\n" + "=" * 80)
