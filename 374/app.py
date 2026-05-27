import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model.lstm_attention import LoadPredictor
from data.data_processor import load_or_create_data, prepare_prediction_input, analyze_influences

app = Flask(__name__)

predictor = None
df_data = None


def initialize_model():
    global predictor, df_data
    print("正在加载数据...")
    df_data = load_or_create_data()
    print(f"数据加载完成，共 {len(df_data)} 条记录")

    print("正在初始化模型...")
    predictor = LoadPredictor(seq_length=168, pred_length=168)

    print("正在训练模型...")
    history = predictor.train(df_data, epochs=30, batch_size=32)
    print("模型训练完成！")
    return history


def get_prediction_data():
    global df_data, predictor
    predict_start = df_data['timestamp'].max() + timedelta(hours=1)
    predict_start = predict_start.replace(minute=0, second=0, microsecond=0)

    df_future, pv_info = prepare_prediction_input(df_data, predict_start)
    predictions = predictor.predict(df_data, df_future)
    analysis = analyze_influences(predictions, df_data, df_future, pv_info)

    timestamps = [str(t) for t in df_future['timestamp']]
    history_data = df_data.tail(168)
    history_timestamps = [str(t) for t in history_data['timestamp']]
    history_values = history_data['load'].tolist()

    result = {
        'timestamps': timestamps,
        'predictions': predictions.tolist(),
        'history_timestamps': history_timestamps,
        'history_values': history_values,
        'analysis': analysis
    }

    if 'pv_output' in df_data.columns:
        result['historical_pv'] = df_data['pv_output'].tail(168).tolist()
        result['gross_load'] = df_data['gross_load'].tail(168).tolist() if 'gross_load' in df_data.columns else None

    return result


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/predict', methods=['GET'])
def predict():
    try:
        result = get_prediction_data()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/retrain', methods=['POST'])
def retrain():
    try:
        global predictor
        data = request.json
        epochs = data.get('epochs', 30)
        batch_size = data.get('batch_size', 32)

        history = predictor.train(df_data, epochs=epochs, batch_size=batch_size)

        return jsonify({
            'success': True,
            'history': {
                'loss': [float(x) for x in history['loss']],
                'val_loss': [float(x) for x in history['val_loss']]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/attention', methods=['GET'])
def get_attention():
    try:
        global df_data, predictor
        predict_start = df_data['timestamp'].max() + timedelta(hours=1)
        predict_start = predict_start.replace(minute=0, second=0, microsecond=0)

        df_future, _ = prepare_prediction_input(df_data, predict_start)
        weights = predictor.get_attention_weights(df_data, df_future)

        avg_weights = np.mean(weights, axis=0)
        top_indices = np.argsort(avg_weights)[-20:][::-1]

        timestamps = [str(df_data.iloc[-(168 - i)]['timestamp']) for i in top_indices]

        return jsonify({
            'success': True,
            'data': {
                'timestamps': timestamps,
                'weights': [float(avg_weights[i]) for i in top_indices]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/load_breakdown', methods=['GET'])
def get_load_breakdown():
    try:
        global df_data
        from model.lstm_attention import decompose_load

        recent_hist = df_data.tail(336)
        total_hist = recent_hist['load']
        temp_hist = recent_hist['temperature'].values
        hour_hist = recent_hist['timestamp'].dt.hour.values
        dow_hist = recent_hist['timestamp'].dt.dayofweek.values
        ts_hist = recent_hist['timestamp'].values

        components, breakdown, hourly_profile = decompose_load(
            total_hist.values, temp_hist, hour_hist, dow_hist, ts_hist
        )

        return jsonify({
            'success': True,
            'data': {
                'breakdown': breakdown,
                'hourly_profile': hourly_profile,
                'timestamps': [str(t) for t in components['timestamp']],
                'components': {
                    'hvac': components['hvac'].tolist(),
                    'lighting': components['lighting'].tolist(),
                    'industrial_motor': components['industrial_motor'].tolist(),
                    'ev_charging': components['ev_charging'].tolist(),
                    'home_appliance': components['home_appliance'].tolist(),
                    'other': components['other'].tolist()
                }
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/demand_response', methods=['GET'])
def get_demand_response():
    try:
        global df_data, predictor
        predict_start = df_data['timestamp'].max() + timedelta(hours=1)
        predict_start = predict_start.replace(minute=0, second=0, microsecond=0)

        df_future, pv_info = prepare_prediction_input(df_data, predict_start)
        predictions = predictor.predict(df_data, df_future)

        recent_hist = df_data.tail(336)
        temp_hist = recent_hist['temperature'].values
        hour_hist = recent_hist['timestamp'].dt.hour.values
        dow_hist = recent_hist['timestamp'].dt.dayofweek.values
        ts_hist = recent_hist['timestamp'].values

        _, _, hourly_profile = decompose_load(
            recent_hist['load'].values, temp_hist, hour_hist, dow_hist, ts_hist
        )

        pv_forecast = np.array(pv_info['forecast'])

        from model.lstm_attention import evaluate_demand_response
        dr_analysis = evaluate_demand_response(
            predictions, df_data, df_future, pv_forecast, hourly_profile
        )

        return jsonify({
            'success': True,
            'data': dr_analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/pv_output', methods=['GET'])
def get_pv_output():
    try:
        global df_data, predictor
        predict_start = df_data['timestamp'].max() + timedelta(hours=1)
        predict_start = predict_start.replace(minute=0, second=0, microsecond=0)

        df_future, pv_info = prepare_prediction_input(df_data, predict_start)

        historical_pv = None
        historical_gross = None
        if 'pv_output' in df_data.columns:
            historical_pv = df_data['pv_output'].tail(168).tolist()
            if 'gross_load' in df_data.columns:
                historical_gross = df_data['gross_load'].tail(168).tolist()

        return jsonify({
            'success': True,
            'data': {
                'pv_info': pv_info,
                'future_pv': pv_info['forecast'],
                'historical_pv': historical_pv,
                'historical_gross_load': historical_gross,
                'timestamps': [str(t) for t in df_future['timestamp']]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/industry_data', methods=['GET'])
def get_industry_data():
    try:
        global df_data
        recent = df_data.tail(168)
        return jsonify({
            'success': True,
            'data': {
                'timestamps': [str(t) for t in recent['timestamp']],
                'residential': recent['industry_residential'].tolist(),
                'commercial': recent['industry_commercial'].tolist(),
                'industrial': recent['industry_industrial'].tolist()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("电力负荷预测平台启动中...")
    print("=" * 60)
    initialize_model()
    print("=" * 60)
    print("服务已启动: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)