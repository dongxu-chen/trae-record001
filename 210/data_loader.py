import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def fetch_stock_data(ticker, days=180):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 50)
    
    data = yf.download(ticker, start=start_date, end=end_date)
    data = data[['Close']].copy()
    data = data.dropna()
    
    if len(data) > days:
        data = data.tail(days)
    
    return data


def preprocess_data(data):
    data = data.copy()
    data.index = pd.to_datetime(data.index)
    data = data.asfreq('B')
    data = data.interpolate(method='time')
    return data


def prepare_prophet_data(data):
    df = data.reset_index()
    df.columns = ['ds', 'y']
    return df


def split_train_test(data, test_size=30):
    train = data[:-test_size]
    test = data[-test_size:]
    return train, test


def generate_future_dates(last_date, periods=30):
    future_dates = pd.bdate_range(start=last_date + timedelta(days=1), periods=periods)
    return future_dates
