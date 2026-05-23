import os
import gc
import pandas as pd
import numpy as np
import multiprocessing as mp
from multiprocessing import Pool, cpu_count
import warnings
warnings.filterwarnings('ignore')

from data_loader import fetch_stock_data, preprocess_data, split_train_test
from arima_model import ARIMAPredictor
from prophet_model import ProphetPredictor
from lstm_model import LSTMPredictor
from metrics import evaluate_model
from visualization import plot_predictions, plot_metrics_comparison


def _predict_single_stock_worker(args):
    ticker, historical_days, forecast_days, use_arima, use_prophet, use_lstm, evaluate = args
    
    try:
        raw_data = fetch_stock_data(ticker, days=historical_days)
        data = preprocess_data(raw_data)
        
        if len(data) < historical_days * 0.8:
            return None
        
        historical_data_json = data.reset_index().to_json(orient='split', date_format='iso')
        
        arima_preds_json = None
        prophet_preds_json = None
        lstm_preds_json = None
        arima_metrics = None
        prophet_metrics = None
        lstm_metrics = None
        arima_summary = None
        prophet_summary = None
        lstm_summary = None
        
        if evaluate:
            train_data, test_data = split_train_test(data, test_size=forecast_days)
        else:
            train_data = data
            test_data = None
        
        if use_arima:
            try:
                arima = ARIMAPredictor()
                arima.fit(train_data)
                last_date = train_data.index[-1]
                arima_preds = arima.predict(steps=forecast_days, last_date=last_date)
                arima_preds_json = arima_preds.reset_index().to_json(orient='split', date_format='iso')
                arima_summary = arima.get_model_summary()
                
                if evaluate and test_data is not None:
                    arima_metrics = evaluate_model(arima_preds, test_data)
                
                del arima, arima_preds
                gc.collect()
            except Exception as e:
                print(f"ARIMA 模型处理 {ticker} 时出错: {e}")
        
        if use_prophet:
            try:
                prophet = ProphetPredictor()
                prophet.fit(train_data)
                prophet_preds = prophet.predict(steps=forecast_days)
                prophet_preds_json = prophet_preds.reset_index().to_json(orient='split', date_format='iso')
                prophet_summary = prophet.get_model_summary()
                
                if evaluate and test_data is not None:
                    prophet_metrics = evaluate_model(prophet_preds, test_data)
                
                del prophet, prophet_preds
                gc.collect()
            except Exception as e:
                print(f"Prophet 模型处理 {ticker} 时出错: {e}")
        
        if use_lstm:
            try:
                lstm = LSTMPredictor()
                lstm.fit(train_data)
                last_date = train_data.index[-1]
                lstm_preds = lstm.predict(steps=forecast_days, last_date=last_date)
                lstm_preds_json = lstm_preds.reset_index().to_json(orient='split', date_format='iso')
                lstm_summary = lstm.get_model_summary()
                
                if evaluate and test_data is not None:
                    lstm_metrics = evaluate_model(lstm_preds, test_data)
                
                del lstm, lstm_preds
                gc.collect()
            except Exception as e:
                print(f"LSTM 模型处理 {ticker} 时出错: {e}")
        
        result = {
            'ticker': ticker,
            'historical_data_json': historical_data_json,
            'arima_preds_json': arima_preds_json,
            'prophet_preds_json': prophet_preds_json,
            'lstm_preds_json': lstm_preds_json,
            'arima_metrics': arima_metrics,
            'prophet_metrics': prophet_metrics,
            'lstm_metrics': lstm_metrics,
            'arima_summary': arima_summary,
            'prophet_summary': prophet_summary,
            'lstm_summary': lstm_summary
        }
        
        del raw_data, data, train_data, test_data
        gc.collect()
        
        return result
        
    except Exception as e:
        print(f"处理 {ticker} 时发生错误: {e}")
        return None


def _json_to_df(json_str):
    if json_str is None:
        return None
    df = pd.read_json(json_str, orient='split')
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
    return df


def predict_single_stock(ticker, historical_days=180, forecast_days=30, 
                         use_arima=True, use_prophet=True, use_lstm=True, evaluate=True):
    print(f"正在处理 {ticker}...")
    
    args = (ticker, historical_days, forecast_days, use_arima, use_prophet, use_lstm, evaluate)
    result = _predict_single_stock_worker(args)
    
    if result is None:
        return None
    
    final_result = {
        'ticker': result['ticker'],
        'historical_data': _json_to_df(result['historical_data_json']),
        'arima_predictions': _json_to_df(result['arima_preds_json']),
        'prophet_predictions': _json_to_df(result['prophet_preds_json']),
        'lstm_predictions': _json_to_df(result['lstm_preds_json']),
        'arima_metrics': result['arima_metrics'],
        'prophet_metrics': result['prophet_metrics'],
        'lstm_metrics': result['lstm_metrics'],
        'arima_summary': result['arima_summary'],
        'prophet_summary': result['prophet_summary'],
        'lstm_summary': result['lstm_summary']
    }
    
    print(f"{ticker} 处理完成")
    return final_result


def predict_multiple_stocks(tickers, historical_days=180, forecast_days=30, 
                            use_arima=True, use_prophet=True, use_lstm=True, 
                            evaluate=True, n_jobs=None, maxtasksperchild=1):
    if n_jobs is None or n_jobs <= 0:
        n_jobs = max(1, cpu_count() - 1)
    
    n_jobs = min(n_jobs, len(tickers))
    
    print(f"使用 {n_jobs} 个进程并行处理 {len(tickers)} 只股票")
    
    args_list = [
        (ticker, historical_days, forecast_days, use_arima, use_prophet, use_lstm, evaluate)
        for ticker in tickers
    ]
    
    with Pool(processes=n_jobs, maxtasksperchild=maxtasksperchild) as pool:
        results = pool.map(_predict_single_stock_worker, args_list)
    
    results_dict = {}
    for result in results:
        if result is not None:
            ticker = result['ticker']
            results_dict[ticker] = {
                'ticker': result['ticker'],
                'historical_data': _json_to_df(result['historical_data_json']),
                'arima_predictions': _json_to_df(result['arima_preds_json']),
                'prophet_predictions': _json_to_df(result['prophet_preds_json']),
                'lstm_predictions': _json_to_df(result['lstm_preds_json']),
                'arima_metrics': result['arima_metrics'],
                'prophet_metrics': result['prophet_metrics'],
                'lstm_metrics': result['lstm_metrics'],
                'arima_summary': result['arima_summary'],
                'prophet_summary': result['prophet_summary'],
                'lstm_summary': result['lstm_summary']
            }
    
    gc.collect()
    return results_dict


def save_results_to_csv(results_dict, output_dir='output'):
    os.makedirs(output_dir, exist_ok=True)
    
    all_predictions = []
    all_metrics = []
    
    for ticker, result in results_dict.items():
        if result['arima_predictions'] is not None:
            arima_df = result['arima_predictions'].copy()
            arima_df['Ticker'] = ticker
            arima_df['Model'] = 'ARIMA'
            arima_df.reset_index(inplace=True)
            all_predictions.append(arima_df)
        
        if result['prophet_predictions'] is not None:
            prophet_df = result['prophet_predictions'].copy()
            prophet_df['Ticker'] = ticker
            prophet_df['Model'] = 'Prophet'
            prophet_df.reset_index(inplace=True)
            all_predictions.append(prophet_df)
        
        if result['lstm_predictions'] is not None:
            lstm_df = result['lstm_predictions'].copy()
            lstm_df['Ticker'] = ticker
            lstm_df['Model'] = 'LSTM'
            lstm_df.reset_index(inplace=True)
            all_predictions.append(lstm_df)
        
        metrics_row = {'Ticker': ticker}
        if result['arima_metrics']:
            for k, v in result['arima_metrics'].items():
                metrics_row[f'ARIMA_{k}'] = v
        if result['prophet_metrics']:
            for k, v in result['prophet_metrics'].items():
                metrics_row[f'Prophet_{k}'] = v
        if result['lstm_metrics']:
            for k, v in result['lstm_metrics'].items():
                metrics_row[f'LSTM_{k}'] = v
        all_metrics.append(metrics_row)
    
    if all_predictions:
        predictions_df = pd.concat(all_predictions, ignore_index=True)
        predictions_df.to_csv(os.path.join(output_dir, 'predictions.csv'), 
                              index=False, encoding='utf-8-sig')
        print(f"预测结果已保存到 {output_dir}/predictions.csv")
    
    if all_metrics:
        metrics_df = pd.DataFrame(all_metrics)
        metrics_df.to_csv(os.path.join(output_dir, 'metrics.csv'), 
                          index=False, encoding='utf-8-sig')
        print(f"评估指标已保存到 {output_dir}/metrics.csv")
    
    summary_data = []
    for ticker, result in results_dict.items():
        if result['arima_summary']:
            row = {'Ticker': ticker, 'Model': 'ARIMA'}
            row.update(result['arima_summary'])
            summary_data.append(row)
        if result['prophet_summary']:
            row = {'Ticker': ticker, 'Model': 'Prophet'}
            row.update(result['prophet_summary'])
            summary_data.append(row)
        if result['lstm_summary']:
            row = {'Ticker': ticker, 'Model': 'LSTM'}
            row.update(result['lstm_summary'])
            summary_data.append(row)
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(os.path.join(output_dir, 'model_summary.csv'), 
                          index=False, encoding='utf-8-sig')
        print(f"模型摘要已保存到 {output_dir}/model_summary.csv")


def save_visualizations(results_dict, output_dir='output'):
    os.makedirs(output_dir, exist_ok=True)
    
    for ticker, result in results_dict.items():
        historical = result['historical_data']
        arima_preds = result['arima_predictions']
        prophet_preds = result['prophet_predictions']
        lstm_preds = result.get('lstm_predictions')
        
        plot_path = os.path.join(output_dir, f'{ticker}_prediction.png')
        plot_predictions(
            historical, 
            arima_preds=arima_preds, 
            prophet_preds=prophet_preds,
            ticker=ticker,
            save_path=plot_path
        )
        
        if result['arima_metrics'] and result['prophet_metrics'] and result.get('lstm_metrics'):
            metrics_path = os.path.join(output_dir, f'{ticker}_metrics.png')
            plot_metrics_comparison(
                result['arima_metrics'],
                result['prophet_metrics'],
                ticker=ticker,
                save_path=metrics_path
            )
    
    print(f"可视化结果已保存到 {output_dir}/")
