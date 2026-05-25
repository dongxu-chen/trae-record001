import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional


def plot_training_curves(
    rewards: List[float],
    losses: List[float],
    output_path: str,
    window: int = 10
):
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    if len(rewards) >= window:
        smoothed_rewards = np.convolve(
            rewards,
            np.ones(window) / window,
            mode='valid'
        )
        axes[0].plot(range(window - 1, len(rewards)), smoothed_rewards, label=f'Smoothed ({window})')
    axes[0].plot(rewards, alpha=0.3, label='Raw')
    axes[0].set_xlabel('Episode')
    axes[0].set_ylabel('Reward')
    axes[0].set_title('Training Rewards')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    if len(losses) >= window:
        smoothed_losses = np.convolve(
            losses,
            np.ones(window) / window,
            mode='valid'
        )
        axes[1].plot(range(window - 1, len(losses)), smoothed_losses, label=f'Smoothed ({window})')
    axes[1].plot(losses, alpha=0.3, label='Raw')
    axes[1].set_xlabel('Episode')
    axes[1].set_ylabel('Loss')
    axes[1].set_title('Training Losses')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_index_recommendations(
    recommendations: List[dict],
    output_path: str,
    top_k: int = 10
):
    if not recommendations:
        return
    
    recs = recommendations[:top_k]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    labels = [f"{r['table']}\n({', '.join(r['columns'])})" for r in recs]
    q_values = [r['q_value'] for r in recs]
    sizes = [r.get('estimated_size_mb', 0) for r in recs]
    
    x = np.arange(len(recs))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, q_values, width, label='Q-Value', color='steelblue', alpha=0.8)
    ax2 = ax.twinx()
    bars2 = ax2.bar(x + width/2, sizes, width, label='Size (MB)', color='coral', alpha=0.8)
    
    ax.set_xlabel('Index Recommendation')
    ax.set_ylabel('Q-Value', color='steelblue')
    ax2.set_ylabel('Estimated Size (MB)', color='coral')
    ax.set_title('Top Index Recommendations')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_query_improvement(
    query_names: List[str],
    baseline_costs: List[float],
    optimized_costs: List[float],
    output_path: str
):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(query_names))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, baseline_costs, width, label='Baseline', color='lightcoral', alpha=0.8)
    bars2 = ax.bar(x + width/2, optimized_costs, width, label='Optimized', color='lightgreen', alpha=0.8)
    
    ax.set_xlabel('Query')
    ax.set_ylabel('Cost')
    ax.set_title('Query Cost Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(query_names, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    for i, (b, o) in enumerate(zip(baseline_costs, optimized_costs)):
        if b > 0:
            improvement = (b - o) / b * 100
            ax.text(i, max(b, o) * 1.02, f'{improvement:.1f}%', ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_column_importance(
    column_scores: Dict[str, Dict[str, float]],
    output_path: str,
    top_n: int = 15
):
    all_cols = []
    all_scores = []
    all_tables = []
    
    for table, cols in column_scores.items():
        sorted_cols = sorted(cols.items(), key=lambda x: x[1], reverse=True)[:top_n//len(column_scores)]
        for col, score in sorted_cols:
            all_cols.append(f"{table}.{col}")
            all_scores.append(score)
            all_tables.append(table)
    
    sorted_idx = np.argsort(all_scores)[::-1]
    all_cols = [all_cols[i] for i in sorted_idx]
    all_scores = [all_scores[i] for i in sorted_idx]
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(set(all_tables))))
    color_map = {table: colors[i] for i, table in enumerate(set(all_tables))}
    bar_colors = [color_map[t] for t in [all_tables[sorted_idx[i]] for i in range(len(all_cols))]]
    
    bars = ax.barh(all_cols[::-1], all_scores[::-1], color=bar_colors, alpha=0.8)
    
    ax.set_xlabel('Importance Score')
    ax.set_title('Column Importance from Query Workload')
    ax.grid(True, alpha=0.3, axis='x')
    
    for i, (table, color) in enumerate(color_map.items()):
        ax.text(0.98, 0.98 - i*0.03, table, transform=ax.transAxes, 
                ha='right', va='top', fontsize=10,
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
