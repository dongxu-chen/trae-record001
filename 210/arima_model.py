import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from ts_utils import auto_arima_order_selection
from data_loader import generate_future_dates


class ARIMAPredictor:
    def __init__(self, order=None, auto_select=True, max_p=5, max_d=3, max_q=5,
                 remove_seasonality=True, stl_period=5):
        self.order = order
        self.auto_select = auto_select
        self.max_p = max_p
        self.max_d = max_d
        self.max_q = max_q
        self.remove_seasonality = remove_seasonality
        self.stl_period = stl_period
        self.model = None
        self.model_fit = None
        self.selected_order = None
    
    def fit(self, train_data):
        series = train_data['Close']
        
        if self.auto_select or self.order is None:
            order_info = auto_arima_order_selection(
                series, 
                max_p=self.max_p, 
                max_d=self.max_d, 
                max_q=self.max_q,
                remove_seasonality=self.remove_seasonality,
                stl_period=self.stl_period
            )
            self.selected_order = order_info['order']
        else:
            self.selected_order = self.order
        
        self.model = ARIMA(series, order=self.selected_order)
        self.model_fit = self.model.fit()
        
        return self
    
    def predict(self, steps=30, last_date=None):
        if self.model_fit is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        forecast = self.model_fit.get_forecast(steps=steps)
        forecast_mean = forecast.predicted_mean
        forecast_ci = forecast.conf_int(alpha=0.05)
        
        if last_date is None:
            last_date = self.model_fit.fittedvalues.index[-1]
        
        future_dates = generate_future_dates(last_date, periods=steps)
        
        predictions = pd.DataFrame({
            'Date': future_dates,
            'Predicted_Close': forecast_mean.values,
            'Lower_CI': forecast_ci.iloc[:, 0].values,
            'Upper_CI': forecast_ci.iloc[:, 1].values
        })
        predictions.set_index('Date', inplace=True)
        
        return predictions
    
    def get_model_summary(self):
        if self.model_fit is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        return {
            'order': self.selected_order,
            'aic': self.model_fit.aic,
            'bic': self.model_fit.bic,
            'log_likelihood': self.model_fit.llf
        }
