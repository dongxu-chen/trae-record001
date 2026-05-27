import io
import time
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Any
import numpy as np


class SpamVisualizer:
    def __init__(self):
        plt.style.use('seaborn-v0_8-darkgrid')
    
    def generate_score_distribution_chart(self, classifications: List[Dict[str, Any]]) -> str:
        spam_scores = []
        ham_scores = []
        
        for item in classifications:
            result = item.get('result', {})
            if result.get('is_spam'):
                spam_scores.append(result.get('spam_probability', 0))
            else:
                ham_scores.append(result.get('spam_probability', 0))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bins = np.linspace(0, 1, 20)
        ax.hist(spam_scores, bins=bins, alpha=0.7, label='垃圾邮件', color='#e74c3c')
        ax.hist(ham_scores, bins=bins, alpha=0.7, label='正常邮件', color='#27ae60')
        
        ax.set_xlabel('垃圾邮件评分', fontsize=12)
        ax.set_ylabel('邮件数量', fontsize=12)
        ax.set_title('垃圾邮件评分分布', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        return self._fig_to_base64(fig)
    
    def generate_spam_trend_chart(self, classifications: List[Dict[str, Any]]) -> str:
        from collections import defaultdict
        from datetime import datetime
        
        daily_stats = defaultdict(lambda: {'spam': 0, 'ham': 0, 'total': 0})
        
        for item in classifications:
            result = item.get('result', {})
            timestamp = result.get('classified_at', time.time())
            date_key = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            if result.get('is_spam'):
                daily_stats[date_key]['spam'] += 1
            else:
                daily_stats[date_key]['ham'] += 1
            daily_stats[date_key]['total'] += 1
        
        dates = sorted(daily_stats.keys())
        spam_counts = [daily_stats[d]['spam'] for d in dates]
        ham_counts = [daily_stats[d]['ham'] for d in dates]
        spam_rates = [daily_stats[d]['spam'] / daily_stats[d]['total'] if daily_stats[d]['total'] > 0 else 0 for d in dates]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        x = range(len(dates))
        width = 0.35
        
        ax1.bar([i - width/2 for i in x], spam_counts, width, label='垃圾邮件', color='#e74c3c')
        ax1.bar([i + width/2 for i in x], ham_counts, width, label='正常邮件', color='#27ae60')
        ax1.set_ylabel('邮件数量', fontsize=11)
        ax1.set_title('每日邮件分类统计', fontsize=13, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(x, spam_rates, marker='o', color='#f39c12', linewidth=2, markersize=6)
        ax2.set_xlabel('日期', fontsize=11)
        ax2.set_ylabel('垃圾率', fontsize=11)
        ax2.set_title('每日垃圾率趋势', fontsize=13, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels([d[-5:] for d in dates], rotation=45)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_reputation_distribution_chart(self, reputations: List[float]) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bins = [0, 20, 40, 60, 80, 100]
        labels = ['极差', '较差', '一般', '良好', '优秀']
        colors = ['#e74c3c', '#e67e22', '#f1c40f', '#3498db', '#27ae60']
        
        counts, _ = np.histogram(reputations, bins=bins)
        
        bars = ax.bar(labels, counts, color=colors, alpha=0.8)
        
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{count}', ha='center', va='bottom', fontsize=10)
        
        ax.set_xlabel('声誉等级', fontsize=12)
        ax.set_ylabel('发件人数量', fontsize=12)
        ax.set_title('发件人声誉分布', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        return self._fig_to_base64(fig)
    
    def generate_score_breakdown_chart(self, score_breakdown: Dict[str, float]) -> str:
        labels = ['模型评分', '规则评分', '声誉评分']
        weights = [score_breakdown.get('model_weight', 0.6),
                   score_breakdown.get('rule_weight', 0.3),
                   score_breakdown.get('reputation_weight', 0.1)]
        scores = [score_breakdown.get('model_score', 0),
                  score_breakdown.get('rule_score', 0),
                  score_breakdown.get('reputation_score', 0)]
        
        weighted_scores = [s * w for s, w in zip(scores, weights)]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        colors = ['#3498db', '#9b59b6', '#e67e22']
        
        wedges, texts, autotexts = ax1.pie(weighted_scores, labels=labels, colors=colors,
                                            autopct='%1.1f%%', startangle=90)
        ax1.set_title('垃圾评分权重分布', fontsize=13, fontweight='bold')
        
        x = range(len(labels))
        ax2.bar(x, scores, color=colors, alpha=0.8, label='原始评分')
        ax2.bar([i + 0.3 for i in x], weighted_scores, color=colors, alpha=0.5, width=0.5, label='加权后')
        ax2.set_xlabel('评分来源', fontsize=11)
        ax2.set_ylabel('评分值', fontsize=11)
        ax2.set_title('评分明细对比', fontsize=13, fontweight='bold')
        ax2.set_xticks([i + 0.15 for i in x])
        ax2.set_xticklabels(labels)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_top_words_chart(self, top_words: List[tuple]) -> str:
        words = [word for word, _ in top_words[:15]]
        scores = [score for _, score in top_words[:15]]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        y_pos = range(len(words))
        bars = ax.barh(y_pos, scores, color='#3498db', alpha=0.8)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(words, fontsize=10)
        ax.invert_yaxis()
        ax.set_xlabel('重要性', fontsize=12)
        ax.set_title('Top 15 垃圾关键词', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        
        for bar, score in zip(bars, scores):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2,
                    f'{score:.3f}', ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        return f'data:image/png;base64,{image_base64}'
