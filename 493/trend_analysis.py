import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field

from git import Repo, Commit

from git_scanner import GitHistoryScanner, LargeFileInfo
from bfg_advisor import format_size, SizeEstimator


@dataclass
class TrendPoint:
    timestamp: datetime
    commit_count: int
    large_file_count: int
    total_large_size: int
    new_files: List[str] = field(default_factory=list)
    removed_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)


class TrendAnalyzer:
    def __init__(self, scanner: GitHistoryScanner):
        self.scanner = scanner
        self.repo = scanner.repo
        self.trend_data: List[TrendPoint] = []

    def analyze_by_commit(self, max_points: int = 50) -> List[TrendPoint]:
        all_commits = self._get_ordered_commits()
        if not all_commits:
            return []

        stride = max(1, len(all_commits) // max_points)
        sampled_commits = all_commits[::stride][-max_points:]

        self.trend_data = self._build_trend_data(sampled_commits)
        return self.trend_data

    def analyze_by_time(self, interval_days: int = 7, max_points: int = 20) -> List[TrendPoint]:
        all_commits = self._get_ordered_commits()
        if not all_commits:
            return []

        earliest = datetime.fromtimestamp(all_commits[0].committed_date)
        latest = datetime.fromtimestamp(all_commits[-1].committed_date)

        buckets = []
        current = latest.replace(hour=0, minute=0, second=0, microsecond=0)
        while current >= earliest:
            bucket_start = current - timedelta(days=interval_days)
            buckets.append((bucket_start, current))
            current = bucket_start

        buckets = list(reversed(buckets))
        if len(buckets) > max_points:
            stride = len(buckets) // max_points
            buckets = buckets[::stride][-max_points:]

        self.trend_data = self._build_trend_by_time(all_commits, buckets)
        return self.trend_data

    def _get_ordered_commits(self) -> List[Commit]:
        try:
            refs = []
            try:
                refs.extend(self.repo.remotes.origin.refs)
            except (AttributeError, ValueError):
                pass
            try:
                refs.extend(self.repo.branches)
            except AttributeError:
                pass
            if not refs:
                refs = [self.repo.head.ref]

            all_commits = set()
            for ref in refs:
                try:
                    for commit in self.repo.iter_commits(ref.name):
                        all_commits.add((commit.committed_date, commit))
                except Exception:
                    continue

            sorted_commits = sorted(all_commits, key=lambda x: x[0])
            return [c[1] for c in sorted_commits]
        except Exception:
            return []

    def _build_trend_data(self, commits: List[Commit]) -> List[TrendPoint]:
        large_files = self.scanner.large_files
        file_first_seen: Dict[str, datetime] = {}
        file_last_seen: Dict[str, datetime] = {}
        file_versions: Dict[str, set] = defaultdict(set)

        for info in large_files.values():
            file_first_seen[info.file_path] = info.first_introduced
            file_last_seen[info.file_path] = info.last_modified
            file_versions[info.file_path] = info.blob_ids

        trend_points = []
        active_files: set = set()

        for commit in commits:
            commit_time = datetime.fromtimestamp(commit.committed_date)
            new_files = []
            removed_files = []
            modified_files = []

            try:
                for blob in commit.tree.traverse():
                    if blob.type != 'blob':
                        continue
                    file_path = blob.path
                    if file_path in large_files:
                        if file_path not in active_files:
                            if file_path not in active_files:
                                active_files.add(file_path)
                                if file_path in file_first_seen and file_first_seen[file_path] <= commit_time:
                                    new_files.append(file_path)
                        blob_id = blob.hexsha
                        if blob_id in file_versions.get(file_path, set()):
                            pass
            except Exception:
                pass

            current_large = set()
            for path, info in large_files.items():
                if info.first_introduced <= commit_time <= info.last_modified:
                    current_large.add(path)

            total_size = sum(large_files[p].max_size for p in current_large if p in large_files)

            trend_points.append(TrendPoint(
                timestamp=commit_time,
                commit_count=1,
                large_file_count=len(current_large),
                total_large_size=total_size,
                new_files=new_files,
                removed_files=removed_files,
                modified_files=modified_files
            ))

        return trend_points

    def _build_trend_by_time(self, all_commits: List[Commit], buckets: List[Tuple[datetime, datetime]]) -> List[TrendPoint]:
        large_files = self.scanner.large_files

        trend_points = []
        for start, end in buckets:
            bucket_commits = [
                c for c in all_commits
                if start <= datetime.fromtimestamp(c.committed_date) <= end
            ]

            if not bucket_commits:
                continue

            current_large = set()
            total_size = 0
            new_files = []

            for path, info in large_files.items():
                if start <= info.first_introduced <= end:
                    current_large.add(path)
                    total_size += info.max_size
                    new_files.append(path)
                elif info.first_introduced <= end and info.last_modified >= start:
                    current_large.add(path)
                    total_size += info.max_size

            trend_points.append(TrendPoint(
                timestamp=end,
                commit_count=len(bucket_commits),
                large_file_count=len(current_large),
                total_large_size=total_size,
                new_files=new_files
            ))

        return trend_points

    def get_summary(self) -> dict:
        if not self.trend_data:
            return {}

        first = self.trend_data[0]
        last = self.trend_data[-1]

        return {
            'start_date': first.timestamp,
            'end_date': last.timestamp,
            'initial_count': first.large_file_count,
            'final_count': last.large_file_count,
            'count_growth': last.large_file_count - first.large_file_count,
            'initial_size': first.total_large_size,
            'final_size': last.total_large_size,
            'size_growth': last.total_large_size - first.total_large_size,
            'peak_count': max(p.large_file_count for p in self.trend_data),
            'peak_size': max(p.total_large_size for p in self.trend_data),
            'data_points': len(self.trend_data)
        }


class ChartGenerator:
    @staticmethod
    def generate_bar_chart(
        data: List[Tuple[str, int]],
        title: str = '',
        max_width: int = 50,
        label_width: int = 20
    ) -> List[str]:
        if not data:
            return [f"{title} - No data"]

        lines = [title, ''] if title else []

        max_val = max(v for _, v in data)
        if max_val == 0:
            max_val = 1

        for label, value in data:
            bar_length = int((value / max_val) * max_width)
            bar = '█' * bar_length
            lines.append(f"{label[:label_width]:<{label_width}} | {bar} {format_size(value)}")

        return lines

    @staticmethod
    def generate_size_chart(
        before: int,
        after: int,
        title: str = 'Cleanup Impact'
    ) -> List[str]:
        lines = [
            '',
            f"  === {title} ===",
            ''
        ]

        max_val = max(before, after)
        bar_width = 40

        before_bar = '█' * int((before / max_val) * bar_width)
        after_bar = '█' * int((after / max_val) * bar_width)

        reduction = before - after
        reduction_pct = (reduction / before * 100) if before > 0 else 0

        lines.extend([
            f"  Before: {before_bar} {format_size(before)}",
            f"  After:  {after_bar} {format_size(after)}",
            '',
            f"  Savings: {format_size(reduction)} ({reduction_pct:.1f}%)",
            ''
        ])

        return lines

    @staticmethod
    def generate_trend_chart(
        trend_data: List[TrendPoint],
        title: str = 'Large Files Trend',
        height: int = 10
    ) -> List[str]:
        if not trend_data:
            return [f"{title} - No trend data"]

        lines = ['', f"  === {title} ===", '']

        if len(trend_data) < 2:
            lines.append("  Not enough data points for trend chart")
            return lines

        values = [p.large_file_count for p in trend_data]
        max_val = max(values)
        min_val = min(values)
        if max_val == min_val:
            max_val = min_val + 1

        width = min(len(trend_data), 60)
        stride = max(1, len(trend_data) // width)
        sampled = trend_data[::stride][-width:]

        chart = []
        for row in range(height, 0, -1):
            line = f"  {row:2d} | "
            for point in sampled:
                normalized = (point.large_file_count - min_val) / (max_val - min_val)
                if normalized >= (row - 1) / height:
                    line += '█'
                else:
                    line += ' '
            chart.append(line)

        chart.append(f"     +{'-' * len(sampled)}")

        labels = ''
        for p in [sampled[0], sampled[len(sampled) // 2], sampled[-1]]:
            labels += p.timestamp.strftime('%Y-%m') + ' '
        chart.append(f"       {labels}")

        lines.extend(chart)
        lines.extend([
            '',
            f"  Count: {min_val} → {max_val}",
            f"  Period: {sampled[0].timestamp.strftime('%Y-%m-%d')} to {sampled[-1].timestamp.strftime('%Y-%m-%d')}",
            ''
        ])

        return lines


class CleanupComparison:
    def __init__(self, scanner: GitHistoryScanner):
        self.scanner = scanner
        self.estimator = SizeEstimator(scanner)

    def get_current_state(self) -> dict:
        savings = self.estimator.estimate_savings()
        return {
            'total_repo_size': savings['total_repo_size'],
            'large_files_count': len(self.scanner.large_files),
            'large_files_size': savings['total_large_files_size'],
            'unique_blobs': savings['unique_large_blobs'],
            'unique_blobs_size': savings['unique_blobs_size']
        }

    def get_estimated_after(self) -> dict:
        savings = self.estimator.estimate_savings()
        return {
            'estimated_repo_size': savings['total_repo_size'] - savings['estimated_savings'],
            'estimated_savings': savings['estimated_savings'],
            'reduction_percent': savings['estimated_reduction_percent'],
            'savings_low': savings['estimated_savings_low'],
            'savings_high': savings['estimated_savings_high']
        }

    def generate_comparison_report(self) -> List[str]:
        current = self.get_current_state()
        after = self.get_estimated_after()

        lines = []
        lines.extend(ChartGenerator.generate_size_chart(
            current['total_repo_size'],
            after['estimated_repo_size'],
            'Repository Size Comparison'
        ))

        data_points = [
            ('Before cleanup', current['total_repo_size']),
            ('After cleanup', after['estimated_repo_size']),
        ]
        lines.extend(ChartGenerator.generate_bar_chart(
            data_points,
            'Detailed Size Breakdown'
        ))

        lines.extend([
            '',
            '  === Details ===',
            '',
            f"  Large files removed:   {current['large_files_count']} files",
            f"  Unique blobs removed:  {current['unique_blobs']} blobs",
            f"  Uncompressed size:     {format_size(current['unique_blobs_size'])}",
            '',
            f"  Expected savings:      {format_size(after['estimated_savings'])}",
            f"  Range (conservative):  {format_size(after['savings_low'])} ~ {format_size(after['savings_high'])}",
            f"  Reduction:             {after['reduction_percent']:.1f}%",
            ''
        ])

        return lines
