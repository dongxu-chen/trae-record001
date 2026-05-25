import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from config import RANDOM_SEED

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

def generate_season_dates(start_date=None, num_episodes=40, days_per_episode=1):
    if start_date is None:
        start_date = datetime(2024, 1, 1)
    dates = []
    for i in range(num_episodes):
        dates.append(start_date + timedelta(days=i * days_per_episode))
    return dates

def get_season(date):
    month = date.month
    if month in [3, 4, 5]:
        return '春季'
    elif month in [6, 7, 8]:
        return '夏季'
    elif month in [9, 10, 11]:
        return '秋季'
    else:
        return '冬季'

def calculate_rmse(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.sqrt(np.mean((y_true - y_pred) ** 2))

def calculate_mape(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def smooth_curve(data, window_size=3):
    if len(data) < window_size:
        return data
    return pd.Series(data).rolling(window=window_size, center=True).mean().bfill().ffill().values

def detect_peaks(data, threshold=0.1, min_distance=2):
    peaks = []
    n = len(data)
    for i in range(1, n - 1):
        if data[i] > data[i-1] and data[i] > data[i+1]:
            if data[i] > np.mean(data) * (1 + threshold):
                if not peaks or (i - peaks[-1]) >= min_distance:
                    peaks.append(i)
    return peaks

def calculate_trend(data):
    if len(data) < 2:
        return 0
    x = np.arange(len(data))
    slope, _ = np.polyfit(x, data, 1)
    return slope

def normalize(data):
    data = np.array(data)
    if np.std(data) == 0:
        return np.zeros_like(data)
    return (data - np.min(data)) / (np.max(data) - np.min(data))

def create_time_sequences(data, seq_length):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:(i + seq_length)])
        y.append(data[i + seq_length])
    return np.array(X), np.array(y)
