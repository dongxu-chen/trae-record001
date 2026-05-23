import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from arima_model import ARIMAPredictor
from prophet_model import ProphetPredictor
from lstm_model import LSTMPredictor
from metrics import evaluate_model
from data_loader import split_train_test


class ModelSelector:
    def __init__(self, use_arima=True, use_prophet=True, use_lstm=True,
                 forecast_days=30, validation_ratio=0.2):
        self.use_arima = use_arima
        self.use_prophet = use_prophet
        self.use_lstm = use_lstm
        self.forecast_days = forecast_days
        self.validation_ratio = validation_ratio
        self.models = {}
        self.model_metrics = {}
        self.best_model = None
        self.best_model_name = None
    
    def _fit_and_evaluate_model(self, model_name, model, train_data, val_data):
        try:
            model.fit(train_data)
            
            if hasattr(model, 'predict'):
                if model_name == 'ARIMA':
                    last_date = train_data.index[-1]
                    predictions = model.predict(steps=self.forecast_days, last_date=last_date)
                else:
                    predictions = model.predict(steps=self.forecast_days)
                
                metrics = evaluate_model(predictions, val_data)
                return predictions, metrics, model
        except Exception as e:
            print(f"{model_name} 模型评估失败: {e}")
        return None, None, None
    
    def fit_evaluate(self, data):
        total_days = len(data)
        val_days = int(total_days * self.validation_ratio)
        val_days = max(val_days, self.forecast_days)
        
        train_data, val_data = split_train_test(data, test_size=val_days)
        
        print(f"训练集: {len(train_data)} 天, 验证集: {len(val_data)} 天")
        
        if self.use_arima:
            print("正在评估 ARIMA 模型...")
            arima = ARIMAPredictor()
            arima_preds, arima_metrics, arima_model = self._fit_and_evaluate_model(
                'ARIMA', arima, train_data, val_data
            )
            if arima_metrics is not None:
                self.models['ARIMA'] = arima_model
                self.model_metrics['ARIMA'] = arima_metrics
                print(f"ARIMA - MAPE: {arima_metrics['MAPE']:.2f}%")
        
        if self.use_prophet:
            print("正在评估 Prophet 模型...")
            prophet = ProphetPredictor()
            prophet_preds, prophet_metrics, prophet_model = self._fit_and_evaluate_model(
                'Prophet', prophet, train_data, val_data
            )
            if prophet_metrics is not None:
                self.models['Prophet'] = prophet_model
                self.model_metrics['Prophet'] = prophet_metrics
                print(f"Prophet - MAPE: {prophet_metrics['MAPE']:.2f}%")
        
        if self.use_lstm:
            print("正在评估 LSTM 模型...")
            lstm = LSTMPredictor()
            lstm_preds, lstm_metrics, lstm_model = self._fit_and_evaluate_model(
                'LSTM', lstm, train_data, val_data
            )
            if lstm_metrics is not None:
                self.models['LSTM'] = lstm_model
                self.model_metrics['LSTM'] = lstm_metrics
                print(f"LSTM - MAPE: {lstm_metrics['MAPE']:.2f}%")
        
        self._select_best_model()
        
        return self.model_metrics
    
    def _select_best_model(self):
        if not self.model_metrics:
            print("没有成功训练的模型")
            return
        
        best_mape = float('inf')
        for model_name, metrics in self.model_metrics.items():
            if metrics['MAPE'] < best_mape:
                best_mape = metrics['MAPE']
                self.best_model_name = model_name
                self.best_model = self.models[model_name]
        
        print(f"\n最优模型: {self.best_model_name}, MAPE: {best_mape:.2f}%")
    
    def predict_with_best_model(self, full_data, steps=30):
        if self.best_model is None:
            raise ValueError("未选择最优模型，请先调用 fit_evaluate()")
        
        print(f"使用 {self.best_model_name} 模型进行预测...")
        
        self.best_model.fit(full_data)
        
        if self.best_model_name == 'ARIMA':
            last_date = full_data.index[-1]
            predictions = self.best_model.predict(steps=steps, last_date=last_date)
        elif self.best_model_name == 'LSTM':
            last_date = full_data.index[-1]
            predictions = self.best_model.predict(steps=steps, last_date=last_date)
        else:
            predictions = self.best_model.predict(steps=steps)
        
        return predictions
    
    def get_all_metrics(self):
        metrics_df = pd.DataFrame(self.model_metrics).T
        metrics_df.index.name = 'Model'
        return metrics_df
    
    def get_best_model_info(self):
        if self.best_model_name is None:
            return None
        
        return {
            'best_model': self.best_model_name,
            'metrics': self.model_metrics.get(self.best_model_name),
            'all_metrics': self.model_metrics
        }
