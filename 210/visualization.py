import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def plot_predictions(historical_data, arima_preds=None, prophet_preds=None, 
                     lstm_preds=None, actual_values=None, ticker='Stock', save_path=None):
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.plot(historical_data.index, historical_data['Close'], 
            label='历史数据', color='blue', linewidth=2)
    
    if arima_preds is not None:
        ax.plot(arima_preds.index, arima_preds['Predicted_Close'], 
                label='ARIMA预测', color='red', linestyle='--', linewidth=2)
        ax.fill_between(arima_preds.index, 
                        arima_preds['Lower_CI'], 
                        arima_preds['Upper_CI'], 
                        color='red', alpha=0.15, label='ARIMA 95%置信区间')
    
    if prophet_preds is not None:
        ax.plot(prophet_preds.index, prophet_preds['Predicted_Close'], 
                label='Prophet预测', color='green', linestyle='--', linewidth=2)
        ax.fill_between(prophet_preds.index, 
                        prophet_preds['Lower_CI'], 
                        prophet_preds['Upper_CI'], 
                        color='green', alpha=0.15, label='Prophet 95%置信区间')
    
    if lstm_preds is not None:
        ax.plot(lstm_preds.index, lstm_preds['Predicted_Close'], 
                label='LSTM预测', color='purple', linestyle='--', linewidth=2)
        ax.fill_between(lstm_preds.index, 
                        lstm_preds['Lower_CI'], 
                        lstm_preds['Upper_CI'], 
                        color='purple', alpha=0.15, label='LSTM 95%置信区间')
    
    if actual_values is not None:
        ax.plot(actual_values.index, actual_values['Close'], 
                label='实际值', color='orange', linewidth=2, marker='o', markersize=4)
    
    ax.set_title(f'{ticker} 股票收盘价预测', fontsize=16, fontweight='bold')
    ax.set_xlabel('日期', fontsize=12)
    ax.set_ylabel('收盘价', fontsize=12)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def plot_metrics_comparison(arima_metrics, prophet_metrics, lstm_metrics=None, 
                            ticker='Stock', save_path=None):
    metrics_names = ['MAE', 'RMSE', 'MAPE']
    
    models = []
    model_names = []
    colors = []
    
    if arima_metrics:
        models.append(arima_metrics)
        model_names.append('ARIMA')
        colors.append('#FF6B6B')
    
    if prophet_metrics:
        models.append(prophet_metrics)
        model_names.append('Prophet')
        colors.append('#4ECDC4')
    
    if lstm_metrics:
        models.append(lstm_metrics)
        model_names.append('LSTM')
        colors.append('#9B59B6')
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    for i, metric in enumerate(metrics_names):
        ax = axes[i]
        values = [m[metric] for m in models]
        bars = ax.bar(model_names, values, color=colors, width=0.6)
        ax.set_title(f'{metric} 对比', fontsize=12, fontweight='bold')
        ax.set_ylabel(metric, fontsize=10)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.4f}',
                    ha='center', va='bottom', fontsize=10)
    
    fig.suptitle(f'{ticker} 模型评估指标对比', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def plot_multiple_stocks_predictions(results_dict, save_path=None):
    n_stocks = len(results_dict)
    n_cols = min(2, n_stocks)
    n_rows = (n_stocks + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 5 * n_rows))
    if n_stocks == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for idx, (ticker, result) in enumerate(results_dict.items()):
        ax = axes[idx]
        historical = result['historical_data']
        arima_preds = result.get('arima_predictions')
        prophet_preds = result.get('prophet_predictions')
        lstm_preds = result.get('lstm_predictions')
        
        ax.plot(historical.index, historical['Close'], 
                label='历史数据', color='blue', linewidth=1.5)
        
        if arima_preds is not None:
            ax.plot(arima_preds.index, arima_preds['Predicted_Close'], 
                    label='ARIMA', color='red', linestyle='--', linewidth=1.5)
        
        if prophet_preds is not None:
            ax.plot(prophet_preds.index, prophet_preds['Predicted_Close'], 
                    label='Prophet', color='green', linestyle='--', linewidth=1.5)
        
        if lstm_preds is not None:
            ax.plot(lstm_preds.index, lstm_preds['Predicted_Close'], 
                    label='LSTM', color='purple', linestyle='--', linewidth=1.5)
        
        ax.set_title(f'{ticker}', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.get_xticklabels(), rotation=45)
        
        if idx == 0:
            ax.legend(loc='best', fontsize=8)
    
    for idx in range(len(results_dict), len(axes)):
        axes[idx].axis('off')
    
    fig.suptitle('多只股票收盘价预测对比', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()
