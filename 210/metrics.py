import numpy as np
import pandas as pd


def calculate_mae(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.mean(np.abs(y_true - y_pred))


def calculate_rmse(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.sqrt(np.mean((y_true - y_pred) ** 2))


def calculate_mape(y_true, y_pred, epsilon=1e-10):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_true = np.where(y_true == 0, epsilon, y_true)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100


def calculate_metrics(y_true, y_pred):
    mae = calculate_mae(y_true, y_pred)
    rmse = calculate_rmse(y_true, y_pred)
    mape = calculate_mape(y_true, y_pred)
    
    return {
        'MAE': round(mae, 4),
        'RMSE': round(rmse, 4),
        'MAPE': round(mape, 4)
    }


def evaluate_model(predictions, actual_values):
    if len(predictions) != len(actual_values):
        min_len = min(len(predictions), len(actual_values))
        predictions = predictions[:min_len]
        actual_values = actual_values[:min_len]
    
    y_pred = predictions['Predicted_Close'].values
    y_true = actual_values['Close'].values
    
    metrics = calculate_metrics(y_true, y_pred)
    
    return metrics
