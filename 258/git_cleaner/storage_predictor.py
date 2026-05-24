"""存储空间预测模块"""
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional
from git import Repo, Commit
from collections import defaultdict
import statistics

class StoragePredictor:
    """基于历史增长趋势预测仓库存储空间"""
    
    def __init__(self, repo: Repo):
        self.repo = repo
    
    def get_repo_size(self) -> int:
        """获取当前仓库大小（字节）"""
        total_size = 0
        git_dir = self.repo.git_dir
        
        for dirpath, dirnames, filenames in os.walk(git_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except (OSError, PermissionError):
                    continue
        
        return total_size
    
    def get_commit_size_history(self, max_commits: int = 1000) -> List[Dict]:
        """获取提交大小历史"""
        commits = list(self.repo.iter_commits(max_count=max_commits))
        history = []
        
        cumulative_size = 0
        for i, commit in enumerate(reversed(commits)):
            try:
                commit_size = self._get_commit_size(commit)
                cumulative_size += commit_size
                history.append({
                    'commit': commit.hexsha,
                    'date': commit.committed_datetime,
                    'commit_size': commit_size,
                    'cumulative_size': cumulative_size,
                    'message': commit.message.strip()[:50],
                })
            except Exception:
                continue
        
        return history
    
    def _get_commit_size(self, commit: Commit) -> int:
        """估算单个提交的大小"""
        try:
            parents = commit.parents
            if not parents:
                return sum(blob.size for blob in commit.tree.traverse() if hasattr(blob, 'size'))
            
            total_added = 0
            for parent in parents:
                try:
                    diff = commit.diff(parent, create_patch=False)
                    for d in diff:
                        if d.b_blob:
                            total_added += d.b_blob.size
                except Exception:
                    continue
            
            return total_added if total_added > 0 else 0
        except Exception:
            return 0
    
    def analyze_growth_trend(self, history: List[Dict]) -> Dict:
        """分析增长趋势"""
        if len(history) < 2:
            return {
                'error': '历史数据不足，无法分析趋势',
                'total_commits': len(history)
            }
        
        daily_growth = defaultdict(int)
        for entry in history:
            day = entry['date'].date()
            daily_growth[day] += entry['commit_size']
        
        daily_sizes = list(daily_growth.values())
        if not daily_sizes:
            return {'error': '无法计算日增长率'}
        
        avg_daily_growth = statistics.mean(daily_sizes)
        median_daily_growth = statistics.median(daily_sizes)
        
        if len(daily_sizes) > 1:
            std_dev = statistics.stdev(daily_sizes)
        else:
            std_dev = 0
        
        earliest = history[0]['date']
        latest = history[-1]['date']
        days_span = (latest - earliest).days + 1
        
        total_growth = sum(e['commit_size'] for e in history)
        
        return {
            'total_commits': len(history),
            'days_span': days_span,
            'total_growth_bytes': total_growth,
            'avg_daily_growth_bytes': avg_daily_growth,
            'median_daily_growth_bytes': median_daily_growth,
            'std_dev_bytes': std_dev,
            'avg_monthly_growth_mb': (avg_daily_growth * 30) / (1024 * 1024),
            'daily_growth_data': dict(daily_growth),
        }
    
    def predict_growth(self, trend: Dict, months_ahead: int = 12) -> Dict:
        """预测未来增长"""
        if 'error' in trend:
            return {'error': trend['error']}
        
        current_size = self.get_repo_size()
        avg_monthly_growth = trend.get('avg_monthly_growth_mb', 0) * 1024 * 1024
        
        predictions = []
        for month in range(1, months_ahead + 1):
            predicted_size = current_size + (avg_monthly_growth * month)
            predictions.append({
                'month': month,
                'predicted_size_bytes': predicted_size,
                'predicted_size_mb': predicted_size / (1024 * 1024),
                'predicted_size_gb': predicted_size / (1024 * 1024 * 1024),
                'date': (datetime.now(timezone.utc) + timedelta(days=30 * month)).strftime('%Y-%m'),
            })
        
        size_thresholds = [
            {'size_gb': 1, 'label': '1GB'},
            {'size_gb': 5, 'label': '5GB'},
            {'size_gb': 10, 'label': '10GB'},
            {'size_gb': 50, 'label': '50GB'},
            {'size_gb': 100, 'label': '100GB'},
        ]
        
        time_to_thresholds = []
        if avg_monthly_growth > 0:
            for threshold in size_thresholds:
                threshold_bytes = threshold['size_gb'] * 1024 * 1024 * 1024
                if current_size < threshold_bytes:
                    bytes_needed = threshold_bytes - current_size
                    months_needed = bytes_needed / avg_monthly_growth
                    if months_needed > 0 and months_needed < 120:
                        time_to_thresholds.append({
                            'threshold': threshold['label'],
                            'months_needed': round(months_needed, 1),
                            'estimated_date': (datetime.now(timezone.utc) + timedelta(days=30 * months_needed)).strftime('%Y-%m'),
                        })
        
        return {
            'current_size_bytes': current_size,
            'current_size_mb': current_size / (1024 * 1024),
            'current_size_gb': current_size / (1024 * 1024 * 1024),
            'avg_monthly_growth_mb': avg_monthly_growth / (1024 * 1024),
            'predictions': predictions,
            'time_to_thresholds': time_to_thresholds,
        }
    
    def get_full_analysis(self, max_commits: int = 1000) -> Dict:
        """获取完整的存储分析报告"""
        history = self.get_commit_size_history(max_commits)
        trend = self.analyze_growth_trend(history)
        prediction = self.predict_growth(trend)
        
        return {
            'history': history,
            'trend': trend,
            'prediction': prediction,
        }
