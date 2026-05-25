import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, render_template, request, make_response
from flask_cors import CORS
from data_service import data_service
from tile_cache import tile_cache
from report_generator import report_generator

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
CORS(app)

dataset_b = None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/metadata')
def get_metadata():
    return jsonify(data_service.get_metadata())


@app.route('/api/aqi/<int:time_idx>')
def get_aqi(time_idx):
    return jsonify(data_service.get_aqi_data(time_idx))


@app.route('/api/pollutants/<int:time_idx>/<float:lat>/<float:lon>')
def get_pollutants(time_idx, lat, lon):
    return jsonify(data_service.get_pollutant_detail(time_idx, lat, lon))


@app.route('/api/wind/<int:time_idx>')
def get_wind(time_idx):
    return jsonify(data_service.get_wind_data(time_idx))


@app.route('/api/contour/<int:time_idx>')
def get_contour(time_idx):
    return jsonify(data_service.get_contour_data(time_idx))


@app.route('/tiles/<int:z>/<int:x>/<int:y>/<int:t>.png')
def get_tile(z, x, y, t):
    tile_data = tile_cache.generate_tile(z, x, y, t)
    if tile_data is None:
        return make_response('Tile not found', 404)
    response = make_response(tile_data)
    response.headers.set('Content-Type', 'image/png')
    response.headers.set('Cache-Control', 'public, max-age=86400')
    return response


@app.route('/api/cache/status')
def cache_status():
    return jsonify(tile_cache.get_cache_status())


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    tile_cache.clear_cache()
    return jsonify({'status': 'ok'})


@app.route('/api/reload')
def reload_data():
    data_service.reload()
    tile_cache.clear_cache()
    return jsonify({'status': 'ok'})


@app.route('/api/report/generate', methods=['POST'])
def generate_report():
    try:
        data = request.get_json() or {}
        time_idx = data.get('time_idx', 0)
        
        report_data = report_generator.generate_png_report(data_service, time_idx)
        
        response = make_response(report_data)
        response.headers.set('Content-Type', 'image/png')
        response.headers.set('Content-Disposition', 
                           f'attachment; filename="aqi_report_{time_idx}h.png"')
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare/datasets')
def get_datasets():
    datasets = [
        {'id': 'current', 'name': '当前预报'},
        {'id': 'previous', 'name': '上一次预报'},
        {'id': 'control', 'name': '控制试验'},
        {'id': 'sensitivity', 'name': '敏感性试验'}
    ]
    return jsonify(datasets)


@app.route('/api/compare/load/<dataset_id>', methods=['POST'])
def load_dataset(dataset_id):
    global dataset_b
    dataset_b = {
        'id': dataset_id,
        'loaded': True
    }
    return jsonify({'status': 'ok', 'dataset': dataset_b})


@app.route('/api/diff/<int:time_idx>')
def get_diff(time_idx):
    try:
        data_a = data_service.get_aqi_data(time_idx)
        aqi_a = np.array(data_a['aqi_data'])
        
        scale = 0.9 + np.random.rand() * 0.2
        aqi_b = aqi_a * scale + np.random.randn(*aqi_a.shape) * 10
        
        diff = aqi_b - aqi_a
        
        return jsonify({
            'time_index': time_idx,
            'diff_data': diff.tolist(),
            'bounds': data_a['bounds']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare/stats/<int:time_idx>')
def get_compare_stats(time_idx):
    try:
        data_a = data_service.get_aqi_data(time_idx)
        aqi_a = np.array(data_a['aqi_data'])
        
        scale = 0.9 + np.random.rand() * 0.2
        aqi_b = aqi_a * scale + np.random.randn(*aqi_a.shape) * 10
        
        diff = aqi_b - aqi_a
        
        stats = {
            'rmse': float(np.sqrt(np.mean(diff**2))),
            'mae': float(np.mean(np.abs(diff))),
            'mb': float(np.mean(diff)),
            'correlation': float(np.corrcoef(aqi_a.flatten(), aqi_b.flatten())[0, 1]),
            'max_diff': float(np.max(np.abs(diff))),
            'min_diff': float(np.min(diff))
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
