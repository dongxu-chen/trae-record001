import os
import sys
import pickle
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
from src.data.preprocess import preprocess_video_features, preprocess_user_features
from src.models.deepfm import predict_multi_target, rank_videos
from src.api.model_router import get_model_router
from src.data.cold_start import handle_cold_start_for_prediction
from src.models.online_learning import get_online_manager


app = Flask(__name__)

model_router = None
online_managers = {}


def init_router():
    global model_router, online_managers
    model_router = get_model_router()
    print("Model router initialized")
    
    if config.ONLINE_LEARNING_ENABLED:
        for version, model_version in model_router.models.items():
            if model_version.loaded and model_version.processors:
                try:
                    online_manager = get_online_manager(
                        model_version.model,
                        model_version.processors
                    )
                    online_managers[version] = online_manager
                    print(f"Online learning manager initialized for version {version}")
                except Exception as e:
                    print(f"Failed to initialize online manager for {version}: {e}")


def preprocess_single_sample_with_version(sample, model_version):
    df = pd.DataFrame([sample])
    
    processors = model_version.processors
    title_processor = processors['title_processor']
    tag_processor = processors['tag_processor']
    user_processor = processors['user_processor']
    
    video_features = preprocess_video_features(df, title_processor, tag_processor)
    user_features, _ = preprocess_user_features(df, user_processor)
    
    features = {}
    features.update(video_features)
    features.update(user_features)
    
    return features


def get_history_count(user_history):
    if isinstance(user_history, str):
        return len(user_history.split(','))
    elif isinstance(user_history, list):
        return len(user_history)
    return 0


@app.route('/health', methods=['GET'])
def health_check():
    stats = model_router.get_routing_stats() if model_router else {}
    return jsonify({
        'status': 'ok',
        'router_initialized': model_router is not None,
        'online_learning_enabled': config.ONLINE_LEARNING_ENABLED,
        'model_stats': stats
    })


@app.route('/predict', methods=['POST'])
def predict():
    if model_router is None:
        return jsonify({
            'error': 'Model router not initialized'
        }), 500
    
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'title', 'tags', 'category', 'duration', 'user_history']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        requested_version = data.get('model_version')
        user_id = data.get('user_id')
        category = data.get('category')
        user_history = data.get('user_history', '')
        history_count = get_history_count(user_history)
        
        model_version = model_router.route(user_id, requested_version)
        
        if model_version is None:
            return jsonify({'error': 'No available model version'}), 500
        
        features = preprocess_single_sample_with_version(data, model_version)
        predictions = predict_multi_target(model_version.model, features)
        
        cold_start_info = None
        if model_version.cold_start_handler:
            click_prob = predictions.get('click', [0])[0]
            result = handle_cold_start_for_prediction(
                model_version.cold_start_handler,
                user_id,
                category,
                click_prob,
                history_count
            )
            predictions['click'] = np.array([result['final_ctr']])
            cold_start_info = result['cold_start_info']
        
        response = {
            'user_id': user_id,
            'video_id': data.get('video_id', 'unknown'),
            'title': data.get('title'),
            'model_version': model_version.version,
            'predictions': {},
            'cold_start_info': cold_start_info
        }
        
        for target, probs in predictions.items():
            response['predictions'][target] = {
                'probability': float(probs[0]),
                'percentage': f'{probs[0] * 100:.2f}%'
            }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/rank', methods=['POST'])
def rank():
    if model_router is None:
        return jsonify({
            'error': 'Model router not initialized'
        }), 500
    
    try:
        data = request.get_json()
        
        if 'user_id' not in data:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        if 'videos' not in data or not isinstance(data['videos'], list):
            return jsonify({'error': 'Missing or invalid field: videos (must be a list)'}), 400
        if 'user_history' not in data:
            return jsonify({'error': 'Missing required field: user_history'}), 400
        
        requested_version = data.get('model_version')
        user_id = data['user_id']
        user_history = data['user_history']
        videos = data['videos']
        target = data.get('rank_by', 'click')
        history_count = get_history_count(user_history)
        
        model_version = model_router.route(user_id, requested_version)
        
        if model_version is None:
            return jsonify({'error': 'No available model version'}), 500
        
        video_features_list = []
        video_predictions = []
        
        for video in videos:
            video_sample = {
                'user_id': user_id,
                'title': video.get('title', ''),
                'tags': video.get('tags', ''),
                'category': video.get('category', ''),
                'duration': video.get('duration', 0),
                'user_history': user_history
            }
            
            features = preprocess_single_sample_with_version(video_sample, model_version)
            predictions = predict_multi_target(model_version.model, features)
            
            if model_version.cold_start_handler:
                category = video.get('category')
                click_prob = predictions.get('click', [0])[0]
                result = handle_cold_start_for_prediction(
                    model_version.cold_start_handler,
                    user_id,
                    category,
                    click_prob,
                    history_count
                )
                predictions['click'] = np.array([result['final_ctr']])
            
            video_features_list.append(features)
            video_predictions.append(predictions)
        
        scores = [pred.get(target, pred.get('click', [0]))[0] for pred in video_predictions]
        ranked_indices = np.argsort(scores)[::-1]
        
        ranked_videos = []
        for rank, idx in enumerate(ranked_indices):
            video = videos[idx].copy()
            predictions = video_predictions[idx]
            
            video['rank'] = rank + 1
            video['score'] = float(scores[idx])
            video['predictions'] = {
                t: float(p[0]) for t, p in predictions.items()
            }
            ranked_videos.append(video)
        
        return jsonify({
            'user_id': user_id,
            'model_version': model_version.version,
            'ranked_by': target,
            'total_videos': len(videos),
            'ranked_videos': ranked_videos
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/batch_predict', methods=['POST'])
def batch_predict():
    if model_router is None:
        return jsonify({
            'error': 'Model router not initialized'
        }), 500
    
    try:
        data = request.get_json()
        
        if 'samples' not in data or not isinstance(data['samples'], list):
            return jsonify({'error': 'Missing or invalid field: samples (must be a list)'}), 400
        
        requested_version = data.get('model_version')
        
        results = []
        for sample in data['samples']:
            try:
                user_id = sample.get('user_id')
                category = sample.get('category')
                user_history = sample.get('user_history', '')
                history_count = get_history_count(user_history)
                
                model_version = model_router.route(user_id, requested_version)
                
                if model_version is None:
                    results.append({'error': 'No available model version'})
                    continue
                
                features = preprocess_single_sample_with_version(sample, model_version)
                predictions = predict_multi_target(model_version.model, features)
                
                if model_version.cold_start_handler:
                    click_prob = predictions.get('click', [0])[0]
                    result = handle_cold_start_for_prediction(
                        model_version.cold_start_handler,
                        user_id,
                        category,
                        click_prob,
                        history_count
                    )
                    predictions['click'] = np.array([result['final_ctr']])
                
                results.append({
                    'user_id': user_id,
                    'video_id': sample.get('video_id', 'unknown'),
                    'model_version': model_version.version,
                    'predictions': {t: float(p[0]) for t, p in predictions.items()}
                })
            except Exception as e:
                results.append({
                    'error': str(e),
                    'sample': sample
                })
        
        return jsonify({
            'total_samples': len(data['samples']),
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/feedback', methods=['POST'])
def feedback():
    if not config.ONLINE_LEARNING_ENABLED:
        return jsonify({'error': 'Online learning is disabled'}), 400
    
    if model_router is None:
        return jsonify({'error': 'Model router not initialized'}), 500
    
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'title', 'tags', 'category', 'duration', 'user_history']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        if 'feedback' not in data:
            return jsonify({'error': 'Missing feedback data'}), 400
        
        feedback_data = data['feedback']
        user_id = data.get('user_id')
        requested_version = data.get('model_version')
        
        model_version = model_router.route(user_id, requested_version)
        
        if model_version is None:
            return jsonify({'error': 'No available model version'}), 500
        
        version = model_version.version
        if version not in online_managers:
            return jsonify({'error': f'Online manager not available for version {version}'}), 500
        
        online_manager = online_managers[version]
        
        sample_dict = {
            'user_id': user_id,
            'title': data.get('title'),
            'tags': data.get('tags'),
            'category': data.get('category'),
            'duration': data.get('duration'),
            'user_history': data.get('user_history')
        }
        
        success = online_manager.add_feedback_from_dict(sample_dict, feedback_data)
        
        stats = online_manager.get_stats()
        
        return jsonify({
            'success': success,
            'model_version': version,
            'message': 'Feedback added to online learning buffer',
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/online_learning/stats', methods=['GET'])
def online_learning_stats():
    if not config.ONLINE_LEARNING_ENABLED:
        return jsonify({'error': 'Online learning is disabled'}), 400
    
    try:
        version = request.args.get('version')
        stats = {}
        
        if version:
            if version in online_managers:
                stats[version] = online_managers[version].get_stats()
            else:
                return jsonify({'error': f'Version {version} not found'}), 404
        else:
            for v, manager in online_managers.items():
                stats[v] = manager.get_stats()
        
        return jsonify({
            'online_learning_enabled': True,
            'versions': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/online_learning/update', methods=['POST'])
def trigger_online_update():
    if not config.ONLINE_LEARNING_ENABLED:
        return jsonify({'error': 'Online learning is disabled'}), 400
    
    try:
        data = request.get_json() or {}
        version = data.get('version')
        batch_size = data.get('batch_size', config.ONLINE_BATCH_SIZE)
        
        results = {}
        
        if version:
            if version in online_managers:
                result = online_managers[version].process_batch(batch_size)
                results[version] = result
            else:
                return jsonify({'error': f'Version {version} not found'}), 404
        else:
            for v, manager in online_managers.items():
                result = manager.process_batch(batch_size)
                results[v] = result
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/feature_importance', methods=['GET'])
def feature_importance():
    if model_router is None:
        return jsonify({'error': 'Model router not initialized'}), 500
    
    try:
        version = request.args.get('version')
        target = request.args.get('target', 'click')
        top_n = int(request.args.get('top_n', config.FEATURE_IMPORTANCE_TOP_N))
        
        if version:
            model_version = model_router.get_model_by_version(version)
        else:
            model_version = model_router.get_default_model()
        
        if model_version is None:
            return jsonify({'error': 'No available model version'}), 500
        
        report_path = os.path.join(model_version.path, 'feature_importance.npy')
        
        if not os.path.exists(report_path):
            return jsonify({
                'warning': 'Feature importance report not found',
                'hint': 'Report is generated during training'
            }), 404
        
        report = np.load(report_path, allow_pickle=True).item()
        
        combined_key = f'combined_{target}'
        if combined_key in report:
            importance = report[combined_key]
        elif 'combined' in report:
            importance = report['combined']
        else:
            importance = report.get('linear_importance', {})
        
        top_features = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
        )
        
        return jsonify({
            'model_version': model_version.version,
            'target': target,
            'top_n': top_n,
            'feature_importance': top_features,
            'methods_available': list(report.keys())
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/router/stats', methods=['GET'])
def router_stats():
    if model_router is None:
        return jsonify({
            'error': 'Model router not initialized'
        }), 500
    
    stats = model_router.get_routing_stats()
    return jsonify(stats)


@app.route('/router/update_ratio', methods=['POST'])
def update_traffic_ratio():
    if model_router is None:
        return jsonify({
            'error': 'Model router not initialized'
        }), 500
    
    try:
        data = request.get_json()
        version = data.get('version')
        new_ratio = data.get('traffic_ratio')
        
        if not version or new_ratio is None:
            return jsonify({'error': 'Missing version or traffic_ratio'}), 400
        
        success = model_router.update_traffic_ratio(version, new_ratio)
        
        if success:
            return jsonify({
                'success': True,
                'version': version,
                'new_traffic_ratio': new_ratio
            })
        else:
            return jsonify({'error': f'Version {version} not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/router/add_version', methods=['POST'])
def add_model_version():
    if model_router is None:
        return jsonify({
            'error': 'Model router not initialized'
        }), 500
    
    try:
        data = request.get_json()
        version = data.get('version')
        path = data.get('path')
        traffic_ratio = data.get('traffic_ratio', 0.0)
        default = data.get('default', False)
        
        if not version or not path:
            return jsonify({'error': 'Missing version or path'}), 400
        
        model_version = model_router.add_model_version(
            version, path, traffic_ratio, default
        )
        
        if model_version.loaded and config.ONLINE_LEARNING_ENABLED:
            online_manager = get_online_manager(
                model_version.model,
                model_version.processors
            )
            online_managers[version] = online_manager
        
        return jsonify({
            'success': True,
            'version': version,
            'path': path,
            'loaded': model_version.loaded
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'name': 'Video CTR Prediction API v3.0',
        'version': '3.0',
        'model': 'DeepFM with Multi-Target Learning',
        'features': [
            'Multi-target prediction (click, like, share)',
            'Two-stage training (FM pretraining + DeepFM joint training)',
            'Cold start handling with global/category fallback',
            'Model version routing',
            'Grayscale release by traffic ratio',
            'Feature importance analysis',
            'Real-time online learning',
            'User-based consistent routing'
        ],
        'endpoints': {
            '/health': 'GET - Health check',
            '/predict': 'POST - Single sample multi-target prediction',
            '/batch_predict': 'POST - Batch prediction',
            '/rank': 'POST - Rank videos for a user',
            '/feedback': 'POST - Submit user feedback for online learning',
            '/online_learning/stats': 'GET - Online learning statistics',
            '/online_learning/update': 'POST - Trigger online model update',
            '/feature_importance': 'GET - Feature importance analysis',
            '/router/stats': 'GET - Get routing statistics',
            '/router/update_ratio': 'POST - Update traffic ratio',
            '/router/add_version': 'POST - Add new model version'
        }
    })


if __name__ == '__main__':
    print("Starting Video CTR Prediction API Server v3.0...")
    print("=" * 70)
    print("New Features in v3.0:")
    print("  ✅ Multi-target prediction (click, like, share)")
    print("  ✅ Feature importance analysis")
    print("  ✅ Real-time online learning")
    print("=" * 70)
    
    init_router()
    
    print(f"\nFlask server starting on http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)
