import argparse
import os
import warnings
warnings.filterwarnings('ignore')

from stock_predictor import predict_multiple_stocks, save_results_to_csv, save_visualizations
from visualization import plot_multiple_stocks_predictions
from model_selector import ModelSelector
from data_loader import fetch_stock_data, preprocess_data
from backtest import run_backtest


def run_prediction_mode(args):
    print("=" * 60)
    print("金融时间序列预测系统 - ARIMA, Prophet & LSTM")
    print("=" * 60)
    print(f"股票代码: {', '.join(args.tickers)}")
    print(f"历史数据天数: {args.historical_days}")
    print(f"预测天数: {args.forecast_days}")
    print(f"使用ARIMA: {not args.no_arima}")
    print(f"使用Prophet: {not args.no_prophet}")
    print(f"使用LSTM: {not args.no_lstm}")
    print(f"模型评估: {not args.no_evaluate}")
    print(f"自动选择最优模型: {args.auto_select}")
    print(f"输出目录: {args.output_dir}")
    print("=" * 60)
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    results = predict_multiple_stocks(
        tickers=args.tickers,
        historical_days=args.historical_days,
        forecast_days=args.forecast_days,
        use_arima=not args.no_arima,
        use_prophet=not args.no_prophet,
        use_lstm=not args.no_lstm,
        evaluate=not args.no_evaluate,
        n_jobs=args.n_jobs
    )
    
    if not results:
        print("没有成功处理的股票")
        return
    
    print("\n" + "=" * 60)
    print("处理完成的股票:", ", ".join(results.keys()))
    print("=" * 60)
    
    save_results_to_csv(results, output_dir=args.output_dir)
    
    if not args.no_visualize:
        save_visualizations(results, output_dir=args.output_dir)
        
        multi_plot_path = os.path.join(args.output_dir, 'all_stocks_prediction.png')
        plot_multiple_stocks_predictions(results, save_path=multi_plot_path)
    
    print("\n" + "=" * 60)
    print("模型评估结果:")
    print("-" * 60)
    
    for ticker, result in results.items():
        print(f"\n{ticker}:")
        if result['arima_metrics']:
            print(f"  ARIMA  - MAE: {result['arima_metrics']['MAE']:.4f}, "
                  f"RMSE: {result['arima_metrics']['RMSE']:.4f}, "
                  f"MAPE: {result['arima_metrics']['MAPE']:.2f}%")
        if result['prophet_metrics']:
            print(f"  Prophet - MAE: {result['prophet_metrics']['MAE']:.4f}, "
                  f"RMSE: {result['prophet_metrics']['RMSE']:.4f}, "
                  f"MAPE: {result['prophet_metrics']['MAPE']:.2f}%")
        if result.get('lstm_metrics'):
            print(f"  LSTM   - MAE: {result['lstm_metrics']['MAE']:.4f}, "
                  f"RMSE: {result['lstm_metrics']['RMSE']:.4f}, "
                  f"MAPE: {result['lstm_metrics']['MAPE']:.2f}%")
    
    print("\n" + "=" * 60)
    print(f"所有结果已保存到 {args.output_dir}/ 目录")
    print("=" * 60)


def run_model_selection_mode(args):
    print("=" * 60)
    print("模型自动选择模式")
    print("=" * 60)
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    for ticker in args.tickers:
        print(f"\n正在处理 {ticker}...")
        try:
            raw_data = fetch_stock_data(ticker, days=args.historical_days)
            data = preprocess_data(raw_data)
            
            selector = ModelSelector(
                use_arima=not args.no_arima,
                use_prophet=not args.no_prophet,
                use_lstm=not args.no_lstm,
                forecast_days=args.forecast_days,
                validation_ratio=0.2
            )
            
            metrics = selector.fit_evaluate(data)
            
            best_info = selector.get_best_model_info()
            
            if best_info:
                print(f"\n{ticker} 模型对比:")
                for model_name, m in metrics.items():
                    print(f"  {model_name}: MAPE={m['MAPE']:.2f}%")
                print(f"最优模型: {best_info['best_model']}")
                
                best_predictions = selector.predict_with_best_model(data, steps=args.forecast_days)
                
                result_dir = os.path.join(args.output_dir, f'{ticker}_auto_select')
                os.makedirs(result_dir, exist_ok=True)
                
                best_predictions.to_csv(
                    os.path.join(result_dir, f'{ticker}_best_model_predictions.csv'),
                    encoding='utf-8-sig'
                )
                
                metrics_df = selector.get_all_metrics()
                metrics_df.to_csv(
                    os.path.join(result_dir, f'{ticker}_model_comparison.csv'),
                    encoding='utf-8-sig'
                )
                
                print(f"结果已保存到 {result_dir}/")
        except Exception as e:
            print(f"处理 {ticker} 时出错: {e}")


def run_backtest_mode(args):
    print("=" * 60)
    print("回测模式 - 验证过去12个月预测效果")
    print("=" * 60)
    
    backtest_dir = os.path.join(args.output_dir, 'backtest_results')
    os.makedirs(backtest_dir, exist_ok=True)
    
    for ticker in args.tickers:
        print(f"\n开始 {ticker} 回测...")
        try:
            engine, summary = run_backtest(
                ticker=ticker,
                total_days=360,
                forecast_days=args.forecast_days,
                train_window=args.historical_days,
                step_size=15,
                use_arima=not args.no_arima,
                use_prophet=not args.no_prophet,
                use_lstm=not args.no_lstm,
                output_dir=backtest_dir
            )
        except Exception as e:
            print(f"{ticker} 回测失败: {e}")
    
    print(f"\n回测报告已保存到 {backtest_dir}/")


def main():
    parser = argparse.ArgumentParser(description='金融时间序列预测 - ARIMA, Prophet & LSTM')
    parser.add_argument('--mode', type=str, default='predict',
                        choices=['predict', 'auto_select', 'backtest'],
                        help='运行模式: predict(预测), auto_select(自动选模型), backtest(回测)')
    parser.add_argument('--tickers', type=str, nargs='+', 
                        default=['AAPL', 'GOOGL', 'MSFT', 'AMZN'],
                        help='股票代码列表 (默认: AAPL GOOGL MSFT AMZN)')
    parser.add_argument('--historical-days', type=int, default=180,
                        help='历史数据天数 (默认: 180)')
    parser.add_argument('--forecast-days', type=int, default=30,
                        help='预测天数 (默认: 30)')
    parser.add_argument('--no-arima', action='store_true',
                        help='不使用ARIMA模型')
    parser.add_argument('--no-prophet', action='store_true',
                        help='不使用Prophet模型')
    parser.add_argument('--no-lstm', action='store_true',
                        help='不使用LSTM模型')
    parser.add_argument('--no-evaluate', action='store_true',
                        help='不进行模型评估')
    parser.add_argument('--auto-select', action='store_true',
                        help='自动选择最优模型进行预测')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='输出目录 (默认: output)')
    parser.add_argument('--no-visualize', action='store_true',
                        help='不生成可视化图表')
    parser.add_argument('--n-jobs', type=int, default=-1,
                        help='并行工作进程数 (默认: -1，使用所有CPU)')
    
    args = parser.parse_args()
    
    if args.mode == 'backtest':
        run_backtest_mode(args)
    elif args.mode == 'auto_select' or args.auto_select:
        run_model_selection_mode(args)
    else:
        run_prediction_mode(args)


if __name__ == "__main__":
    main()
