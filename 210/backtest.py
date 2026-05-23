import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

from data_loader import fetch_stock_data, preprocess_data
from arima_model import ARIMAPredictor
from prophet_model import ProphetPredictor
from lstm_model import LSTMPredictor
from metrics import calculate_metrics
from visualization import plot_predictions


class BacktestEngine:
    def __init__(self, ticker, total_days=360, forecast_days=30, 
                 train_window=180, step_size=15,
                 use_arima=True, use_prophet=True, use_lstm=True):
        self.ticker = ticker
        self.total_days = total_days
        self.forecast_days = forecast_days
        self.train_window = train_window
        self.step_size = step_size
        self.use_arima = use_arima
        self.use_prophet = use_prophet
        self.use_lstm = use_lstm
        self.data = None
        self.backtest_results = []
        self.summary = None
    
    def load_data(self):
        print(f"正在加载 {self.ticker} 数据...")
        raw_data = fetch_stock_data(self.ticker, days=self.total_days + 50)
        self.data = preprocess_data(raw_data)
        print(f"数据加载完成，共 {len(self.data)} 条记录")
        return self.data
    
    def _run_single_backtest(self, train_data, test_data, backtest_date):
        result = {
            'backtest_date': backtest_date,
            'train_start': train_data.index[0],
            'train_end': train_data.index[-1],
            'test_start': test_data.index[0],
            'test_end': test_data.index[-1],
            'actual_values': test_data['Close'].values,
            'arima_predictions': None,
            'prophet_predictions': None,
            'lstm_predictions': None,
            'arima_metrics': None,
            'prophet_metrics': None,
            'lstm_metrics': None
        }
        
        if self.use_arima:
            try:
                arima = ARIMAPredictor()
                arima.fit(train_data)
                last_date = train_data.index[-1]
                preds = arima.predict(steps=len(test_data), last_date=last_date)
                result['arima_predictions'] = preds['Predicted_Close'].values
                result['arima_metrics'] = calculate_metrics(
                    test_data['Close'].values[:len(preds)],
                    preds['Predicted_Close'].values
                )
            except Exception as e:
                print(f"ARIMA 回测失败 ({backtest_date}): {e}")
        
        if self.use_prophet:
            try:
                prophet = ProphetPredictor()
                prophet.fit(train_data)
                preds = prophet.predict(steps=len(test_data))
                result['prophet_predictions'] = preds['Predicted_Close'].values
                result['prophet_metrics'] = calculate_metrics(
                    test_data['Close'].values[:len(preds)],
                    preds['Predicted_Close'].values
                )
            except Exception as e:
                print(f"Prophet 回测失败 ({backtest_date}): {e}")
        
        if self.use_lstm:
            try:
                lstm = LSTMPredictor()
                lstm.fit(train_data)
                last_date = train_data.index[-1]
                preds = lstm.predict(steps=len(test_data), last_date=last_date)
                result['lstm_predictions'] = preds['Predicted_Close'].values
                result['lstm_metrics'] = calculate_metrics(
                    test_data['Close'].values[:len(preds)],
                    preds['Predicted_Close'].values
                )
            except Exception as e:
                print(f"LSTM 回测失败 ({backtest_date}): {e}")
        
        return result
    
    def run_backtest(self):
        if self.data is None:
            self.load_data()
        
        n = len(self.data)
        min_required = self.train_window + self.forecast_days
        
        if n < min_required:
            raise ValueError(f"数据不足，需要至少 {min_required} 天数据")
        
        self.backtest_results = []
        
        start_idx = 0
        backtest_num = 1
        
        while start_idx + self.train_window + self.forecast_days <= n:
            train_end = start_idx + self.train_window
            test_end = min(train_end + self.forecast_days, n)
            
            train_data = self.data.iloc[start_idx:train_end].copy()
            test_data = self.data.iloc[train_end:test_end].copy()
            
            backtest_date = train_data.index[-1].strftime('%Y-%m-%d')
            print(f"回测 #{backtest_num} - 训练截止: {backtest_date}")
            
            result = self._run_single_backtest(train_data, test_data, backtest_date)
            self.backtest_results.append(result)
            
            start_idx += self.step_size
            backtest_num += 1
        
        print(f"\n回测完成，共执行 {len(self.backtest_results)} 次滚动预测")
        self._calculate_summary()
        
        return self.backtest_results
    
    def _calculate_summary(self):
        if not self.backtest_results:
            return None
        
        models = []
        if self.use_arima:
            models.append('arima')
        if self.use_prophet:
            models.append('prophet')
        if self.use_lstm:
            models.append('lstm')
        
        self.summary = {}
        
        for model in models:
            metrics_key = f'{model}_metrics'
            all_metrics = [r[metrics_key] for r in self.backtest_results if r[metrics_key] is not None]
            
            if all_metrics:
                self.summary[model.upper()] = {
                    'avg_MAE': np.mean([m['MAE'] for m in all_metrics]),
                    'std_MAE': np.std([m['MAE'] for m in all_metrics]),
                    'avg_RMSE': np.mean([m['RMSE'] for m in all_metrics]),
                    'std_RMSE': np.std([m['RMSE'] for m in all_metrics]),
                    'avg_MAPE': np.mean([m['MAPE'] for m in all_metrics]),
                    'std_MAPE': np.std([m['MAPE'] for m in all_metrics]),
                    'success_rate': len(all_metrics) / len(self.backtest_results),
                    'n_backtests': len(all_metrics)
                }
        
        return self.summary
    
    def get_summary_report(self):
        if self.summary is None:
            self._calculate_summary()
        
        report_data = []
        for model, metrics in self.summary.items():
            report_data.append({
                'Model': model,
                'Avg MAE': f"{metrics['avg_MAE']:.4f} ± {metrics['std_MAE']:.4f}",
                'Avg RMSE': f"{metrics['avg_RMSE']:.4f} ± {metrics['std_RMSE']:.4f}",
                'Avg MAPE': f"{metrics['avg_MAPE']:.2f}% ± {metrics['std_MAPE']:.2f}%",
                'Success Rate': f"{metrics['success_rate']*100:.1f}%",
                'Backtests': metrics['n_backtests']
            })
        
        report_df = pd.DataFrame(report_data)
        return report_df
    
    def plot_backtest_results(self, save_path=None):
        if not self.backtest_results:
            print("没有回测结果可绘制")
            return
        
        n_backtests = len(self.backtest_results)
        n_cols = min(3, n_backtests)
        n_rows = (n_backtests + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5 * n_rows))
        if n_backtests == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for idx, result in enumerate(self.backtest_results):
            ax = axes[idx]
            
            train_dates = pd.date_range(start=result['train_start'], 
                                        end=result['train_end'], freq='B')
            train_values = self.data.loc[train_dates, 'Close'].values
            
            test_dates = pd.date_range(start=result['test_start'], 
                                       end=result['test_end'], freq='B')
            
            ax.plot(train_dates[-30:], train_values[-30:], 
                    label='训练数据', color='blue', linewidth=1.5)
            ax.plot(test_dates, result['actual_values'], 
                    label='实际值', color='orange', linewidth=2, marker='o', markersize=3)
            
            if result['arima_predictions'] is not None:
                ax.plot(test_dates[:len(result['arima_predictions'])], 
                        result['arima_predictions'], 
                        label='ARIMA', color='red', linestyle='--', linewidth=1.5)
            
            if result['prophet_predictions'] is not None:
                ax.plot(test_dates[:len(result['prophet_predictions'])], 
                        result['prophet_predictions'], 
                        label='Prophet', color='green', linestyle='--', linewidth=1.5)
            
            if result['lstm_predictions'] is not None:
                ax.plot(test_dates[:len(result['lstm_predictions'])], 
                        result['lstm_predictions'], 
                        label='LSTM', color='purple', linestyle='--', linewidth=1.5)
            
            ax.set_title(f"回测 #{idx+1} ({result['backtest_date']})", fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.setp(ax.get_xticklabels(), rotation=45, fontsize=8)
            
            if idx == 0:
                ax.legend(loc='best', fontsize=8)
        
        for idx in range(len(self.backtest_results), len(axes)):
            axes[idx].axis('off')
        
        fig.suptitle(f'{self.ticker} 回测结果 - 滚动预测', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    
    def plot_metrics_evolution(self, save_path=None):
        if not self.backtest_results:
            print("没有回测结果可绘制")
            return
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        
        backtest_dates = [r['backtest_date'] for r in self.backtest_results]
        x = range(len(backtest_dates))
        
        models = []
        colors = {'arima': 'red', 'prophet': 'green', 'lstm': 'purple'}
        
        if self.use_arima:
            models.append('arima')
        if self.use_prophet:
            models.append('prophet')
        if self.use_lstm:
            models.append('lstm')
        
        metrics_names = ['MAE', 'RMSE', 'MAPE']
        
        for ax_idx, metric in enumerate(metrics_names):
            ax = axes[ax_idx]
            
            for model in models:
                metrics_key = f'{model}_metrics'
                values = []
                for r in self.backtest_results:
                    if r[metrics_key] is not None:
                        values.append(r[metrics_key][metric])
                    else:
                        values.append(None)
                
                valid_x = [i for i, v in enumerate(values) if v is not None]
                valid_v = [v for v in values if v is not None]
                
                if valid_v:
                    ax.plot(valid_x, valid_v, marker='o', label=model.upper(), 
                            color=colors[model], linewidth=1.5, markersize=4)
            
            ax.set_title(f'{metric} 变化趋势', fontsize=12, fontweight='bold')
            ax.set_xlabel('回测次数', fontsize=10)
            ax.set_ylabel(metric, fontsize=10)
            ax.set_xticks(x)
            ax.set_xticklabels(backtest_dates, rotation=45, fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    
    def save_backtest_report(self, output_dir='backtest_report'):
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        summary_df = self.get_summary_report()
        summary_path = os.path.join(output_dir, f'{self.ticker}_summary.csv')
        summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
        print(f"回测摘要已保存到 {summary_path}")
        
        detailed_data = []
        for idx, result in enumerate(self.backtest_results):
            row = {
                'backtest_id': idx + 1,
                'backtest_date': result['backtest_date'],
                'train_start': result['train_start'],
                'train_end': result['train_end'],
                'test_start': result['test_start'],
                'test_end': result['test_end']
            }
            
            for model in ['arima', 'prophet', 'lstm']:
                metrics = result[f'{model}_metrics']
                if metrics:
                    for k, v in metrics.items():
                        row[f'{model}_{k}'] = v
            
            detailed_data.append(row)
        
        detailed_df = pd.DataFrame(detailed_data)
        detailed_path = os.path.join(output_dir, f'{self.ticker}_detailed.csv')
        detailed_df.to_csv(detailed_path, index=False, encoding='utf-8-sig')
        print(f"详细回测数据已保存到 {detailed_path}")
        
        try:
            self.plot_backtest_results(
                save_path=os.path.join(output_dir, f'{self.ticker}_backtest_results.png')
            )
            self.plot_metrics_evolution(
                save_path=os.path.join(output_dir, f'{self.ticker}_metrics_evolution.png')
            )
            print(f"回测图表已保存到 {output_dir}/")
        except Exception as e:
            print(f"生成图表时出错: {e}")
        
        return summary_df


def run_backtest(ticker, total_days=360, forecast_days=30, 
                 train_window=180, step_size=15,
                 use_arima=True, use_prophet=True, use_lstm=True,
                 output_dir='backtest_report'):
    
    engine = BacktestEngine(
        ticker=ticker,
        total_days=total_days,
        forecast_days=forecast_days,
        train_window=train_window,
        step_size=step_size,
        use_arima=use_arima,
        use_prophet=use_prophet,
        use_lstm=use_lstm
    )
    
    engine.load_data()
    engine.run_backtest()
    
    summary = engine.save_backtest_report(output_dir=output_dir)
    
    print("\n" + "=" * 60)
    print(f"{ticker} 回测摘要:")
    print("=" * 60)
    print(summary.to_string(index=False))
    print("=" * 60)
    
    return engine, summary
