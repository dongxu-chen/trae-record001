import os
import io
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
from config import Config
from core import SaliencyInferencer, BatchProcessor
from core.post_processing import (
    segment_salient_object,
    overlay_saliency,
    apply_mask,
    get_saliency_stats
)
from utils.helpers import allowed_file, save_image, generate_output_filename

_inferencer = None
_batch_processor = None


def get_inferencer():
    global _inferencer
    if _inferencer is None:
        _inferencer = SaliencyInferencer(pretrained=False)
    return _inferencer


def get_batch_processor():
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor(get_inferencer())
    return _batch_processor


def image_to_base64(image, is_gray=False):
    if is_gray:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    
    _, buffer = cv2.imencode('.png', image)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


def base64_to_image(base64_string):
    if base64_string.startswith('data:image'):
        base64_string = base64_string.split(',')[1]
    
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def create_app():
    Config.ensure_dirs()
    
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
    
    @app.route('/')
    def index():
        return render_template_string('''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>显著性目标检测 API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { display: inline-block; background: #4CAF50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; margin-right: 10px; }
                .url { font-family: monospace; color: #666; }
                .description { margin-top: 5px; color: #555; }
            </style>
        </head>
        <body>
            <h1>显著性目标检测 API</h1>
            <p>基于 BASNet 和 PoolNet 的深度学习显著性目标检测服务</p>
            
            <div class="endpoint">
                <span class="method">GET</span><span class="url">/api/health</span>
                <div class="description">健康检查接口</div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span><span class="url">/api/models</span>
                <div class="description">获取可用模型列表</div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span><span class="url">/api/predict</span>
                <div class="description">单图显著性检测，支持上传文件或Base64编码</div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span><span class="url">/api/predict/batch</span>
                <div class="description">批量图像显著性检测</div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span><span class="url">/api/segment</span>
                <div class="description">显著目标分割，返回带Alpha通道的图像</div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span><span class="url">/api/switch-model</span>
                <div class="description">切换检测模型 (basnet/poolnet)</div>
            </div>
        </body>
        </html>
        ''')
    
    @app.route('/api/health', methods=['GET'])
    def health():
        inferencer = get_inferencer()
        model_info = inferencer.get_model_info()
        return jsonify({
            'status': 'ok',
            'model': model_info,
            'device': Config.get_device(),
            'allowed_extensions': list(Config.ALLOWED_EXTENSIONS)
        })
    
    @app.route('/api/models', methods=['GET'])
    def get_models():
        inferencer = get_inferencer()
        return jsonify(inferencer.get_model_info())
    
    @app.route('/api/switch-model', methods=['POST'])
    def switch_model():
        data = request.get_json() or request.form
        model_name = data.get('model_name', '').lower()
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        try:
            inferencer = get_inferencer()
            info = inferencer.switch_model(model_name, pretrained=False)
            return jsonify({
                'success': True,
                'message': f'Switched to model: {model_name}',
                'model_info': info
            })
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/predict', methods=['POST'])
    def predict():
        try:
            threshold = float(request.form.get('threshold', Config.THRESHOLD))
            edge_refinement = request.form.get('edge_refinement', 'true').lower() == 'true'
            return_base64 = request.form.get('return_base64', 'true').lower() == 'true'
            
            image = None
            
            if 'image' in request.files:
                file = request.files['image']
                if file.filename == '':
                    return jsonify({'error': 'No selected file'}), 400
                if file and allowed_file(file.filename):
                    file_bytes = file.read()
                    nparr = np.frombuffer(file_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    filename = secure_filename(file.filename)
                else:
                    return jsonify({'error': 'Invalid file type'}), 400
            elif 'image_base64' in request.form:
                image = base64_to_image(request.form['image_base64'])
                filename = generate_output_filename()
            elif 'image_url' in request.form:
                return jsonify({'error': 'image_url not implemented yet'}), 501
            else:
                return jsonify({'error': 'No image provided'}), 400
            
            inferencer = get_inferencer()
            result = inferencer.predict(
                image,
                threshold=threshold,
                edge_refinement=edge_refinement
            )
            
            stats = get_saliency_stats(result['saliency_map'], result['binary_mask'])
            
            response = {
                'success': True,
                'filename': filename,
                'original_size': {
                    'height': result['original_size'][0],
                    'width': result['original_size'][1]
                },
                'threshold': threshold,
                'edge_refinement': edge_refinement,
                'stats': stats
            }
            
            if return_base64:
                response['saliency_map'] = image_to_base64(
                    (result['saliency_map'] * 255).astype(np.uint8),
                    is_gray=True
                )
                response['binary_mask'] = image_to_base64(
                    (result['binary_mask'] * 255).astype(np.uint8),
                    is_gray=True
                )
                response['overlay'] = image_to_base64(
                    overlay_saliency(result['original_image'], result['saliency_map'])
                )
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/predict/batch', methods=['POST'])
    def predict_batch():
        try:
            threshold = float(request.form.get('threshold', Config.THRESHOLD))
            edge_refinement = request.form.get('edge_refinement', 'true').lower() == 'true'
            return_base64 = request.form.get('return_base64', 'false').lower() == 'true'
            
            files = request.files.getlist('images')
            if not files:
                return jsonify({'error': 'No images provided'}), 400
            
            images = []
            filenames = []
            
            for file in files:
                if file and allowed_file(file.filename):
                    file_bytes = file.read()
                    nparr = np.frombuffer(file_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    images.append(img)
                    filenames.append(secure_filename(file.filename))
            
            if not images:
                return jsonify({'error': 'No valid images provided'}), 400
            
            inferencer = get_inferencer()
            results = inferencer.predict_batch(
                images,
                threshold=threshold,
                edge_refinement=edge_refinement
            )
            
            batch_results = []
            for i, result in enumerate(results):
                stats = get_saliency_stats(result['saliency_map'], result['binary_mask'])
                item = {
                    'filename': filenames[i],
                    'original_size': {
                        'height': result['original_size'][0],
                        'width': result['original_size'][1]
                    },
                    'stats': stats
                }
                
                if return_base64:
                    item['saliency_map'] = image_to_base64(
                        (result['saliency_map'] * 255).astype(np.uint8),
                        is_gray=True
                    )
                    item['binary_mask'] = image_to_base64(
                        (result['binary_mask'] * 255).astype(np.uint8),
                        is_gray=True
                    )
                
                batch_results.append(item)
            
            return jsonify({
                'success': True,
                'total_images': len(batch_results),
                'threshold': threshold,
                'edge_refinement': edge_refinement,
                'results': batch_results
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/segment', methods=['POST'])
    def segment():
        try:
            threshold = float(request.form.get('threshold', Config.THRESHOLD))
            edge_refinement = request.form.get('edge_refinement', 'true').lower() == 'true'
            apply_type = request.form.get('apply_type', 'segment')
            
            image = None
            filename = None
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    file_bytes = file.read()
                    nparr = np.frombuffer(file_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    filename = secure_filename(file.filename)
            elif 'image_base64' in request.form:
                image = base64_to_image(request.form['image_base64'])
                filename = generate_output_filename()
            
            if image is None:
                return jsonify({'error': 'No image provided'}), 400
            
            inferencer = get_inferencer()
            result = inferencer.predict(
                image,
                threshold=threshold,
                edge_refinement=edge_refinement
            )
            
            seg_result = segment_salient_object(
                result['original_image'],
                result['saliency_map'],
                result['binary_mask']
            )
            
            if apply_type == 'segment':
                output_image = seg_result['segmented_rgb']
            elif apply_type == 'blur_background':
                output_image = apply_mask(image, result['binary_mask'], 'blur_background')
            elif apply_type == 'color_background':
                bg_color_str = request.form.get('bg_color', '0,0,0')
                bg_color = tuple(map(int, bg_color_str.split(',')))
                output_image = apply_mask(image, result['binary_mask'], 'color_background', bg_color)
            else:
                output_image = seg_result['segmented_rgb']
            
            response = {
                'success': True,
                'filename': filename,
                'num_objects': seg_result['num_objects'],
                'bounding_boxes': seg_result['bounding_boxes'],
                'segmented_image': image_to_base64(output_image),
                'alpha_mask': image_to_base64(seg_result['alpha_mask'], is_gray=True)
            }
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/download/<path:filename>', methods=['GET'])
    def download_file(filename):
        filepath = os.path.join(Config.OUTPUT_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        return send_file(filepath, as_attachment=True)
    
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'error': 'File too large. Maximum 100MB'}), 413
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.DEBUG)
