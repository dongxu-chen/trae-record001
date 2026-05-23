import numpy as np
import pandas as pd
from prophet import Prophet
from data_loader import prepare_prophet_data
from china_holidays import get_prophet_holidays


class ProphetPredictor:
    def __init__(self, yearly_seasonality=False, weekly_seasonality=True, 
                 daily_seasonality=False, seasonality_mode='additive', 
                 changepoint_prior_scale=0.05,
                 use_china_holidays=True, holiday_start_year=2020, holiday_end_year=2030):
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.seasonality_mode = seasonality_mode
        self.changepoint_prior_scale = changepoint_prior_scale
        self.use_china_holidays = use_china_holidays
        self.holiday_start_year = holiday_start_year
        self.holiday_end_year = holiday_end_year
        self.model = None
        self.holidays = None
    
    def fit(self, train_data):
        prophet_df = prepare_prophet_data(train_data)
        
        holidays = None
        if self.use_china_holidays:
            self.holidays = get_prophet_holidays(
                start_year=self.holiday_start_year,
                end_year=self.holiday_end_year
            )
            holidays = self.holidays
        
        self.model = Prophet(
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            seasonality_mode=self.seasonality_mode,
            changepoint_prior_scale=self.changepoint_prior_scale,
            holidays=holidays
        )
        
        self.model.fit(prophet_df)
        
        return self
    
    def predict(self, steps=30):
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        future = self.model.make_future_dataframe(periods=steps, freq='B')
        forecast = self.model.predict(future)
        
        predictions = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(steps)
        predictions.columns = ['Date', 'Predicted_Close', 'Lower_CI', 'Upper_CI']
        predictions.set_index('Date', inplace=True)
        
        return predictions
    
    def get_model_summary(self):
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        return {
            'yearly_seasonality': self.yearly_seasonality,
            'weekly_seasonality': self.weekly_seasonality,
            'daily_seasonality': self.daily_seasonality,
            'seasonality_mode': self.seasonality_mode,
            'changepoint_prior_scale': self.changepoint_prior_scale,
            'use_china_holidays': self.use_china_holidays,
            'n_changepoints': len(self.model.changepoints),
            'n_holidays': len(self.holidays) if self.holidays is not None else 0
        }
