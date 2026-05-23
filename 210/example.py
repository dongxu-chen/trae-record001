import warnings
warnings.filterwarnings('ignore')

from stock_predictor import predict_single_stock, save_results_to_csv, save_visualizations
from visualization import plot_predictions, plot_metrics_comparison


def example_single_stock():
    print("示例1: 单只股票预测")
    print("-" * 50)
    
    result = predict_single_stock(
        ticker='AAPL',
        historical_days=180,
        forecast_days=30,
        use_arima=True,
        use_prophet=True,
        evaluate=True
    )
    
    if result:
        print(f"\n股票: {result['ticker']}")
        print(f"历史数据点数: {len(result['historical_data'])}")
        
        if result['arima_metrics']:
            print(f"\nARIMA模型评估:")
            print(f"  MAE: {result['arima_metrics']['MAE']}")
            print(f"  RMSE: {result['arima_metrics']['RMSE']}")
            print(f"  MAPE: {result['arima_metrics']['MAPE']}%")
        
        if result['prophet_metrics']:
            print(f"\nProphet模型评估:")
            print(f"  MAE: {result['prophet_metrics']['MAE']}")
            print(f"  RMSE: {result['prophet_metrics']['RMSE']}")
            print(f"  MAPE: {result['prophet_metrics']['MAPE']}%")
        
        if result['arima_predictions'] is not None:
            print(f"\nARIMA前5天预测:")
            print(result['arima_predictions'].head())
        
        if result['prophet_predictions'] is not None:
            print(f"\nProphet前5天预测:")
            print(result['prophet_predictions'].head())


def example_with_visualization():
    print("\n\n示例2: 预测并生成可视化")
    print("-" * 50)
    
    result = predict_single_stock(
        ticker='GOOGL',
        historical_days=180,
        forecast_days=30,
        use_arima=True,
        use_prophet=True,
        evaluate=True
    )
    
    if result:
        import os
        os.makedirs('output_example', exist_ok=True)
        
        plot_predictions(
            historical_data=result['historical_data'],
            arima_preds=result['arima_predictions'],
            prophet_preds=result['prophet_predictions'],
            ticker='GOOGL',
            save_path='output_example/GOOGL_prediction.png'
        )
        print("预测图已保存到 output_example/GOOGL_prediction.png")
        
        if result['arima_metrics'] and result['prophet_metrics']:
            plot_metrics_comparison(
                result['arima_metrics'],
                result['prophet_metrics'],
                ticker='GOOGL',
                save_path='output_example/GOOGL_metrics.png'
            )
            print("指标对比图已保存到 output_example/GOOGL_metrics.png")


def example_save_to_csv():
    print("\n\n示例3: 多只股票预测并保存到CSV")
    print("-" * 50)
    
    from stock_predictor import predict_multiple_stocks
    
    tickers = ['MSFT', 'AMZN']
    results = predict_multiple_stocks(
        tickers=tickers,
        historical_days=180,
        forecast_days=30,
        use_arima=True,
        use_prophet=True,
        evaluate=True,
        n_jobs=2
    )
    
    if results:
        save_results_to_csv(results, output_dir='output_example')
        print("结果已保存到 output_example/ 目录")


if __name__ == "__main__":
    print("=" * 60)
    print("金融时间序列预测 - 使用示例")
    print("=" * 60)
    
    example_single_stock()
    example_with_visualization()
    example_save_to_csv()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
