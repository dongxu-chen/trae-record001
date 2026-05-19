import os
import sys
import json
import traceback
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory, render_template_string, Response, stream_with_context
from flask_cors import CORS

from license_plate_recognition import LicensePlateRecognition
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
CORS(app, supports_credentials=True)

lpr = None


def get_lpr():
    global lpr
    if lpr is None:
        try:
            lpr = LicensePlateRecognition()
        except Exception as e:
            print(f"Failed to initialize LPR: {e}")
            traceback.print_exc()
            lpr = None
    return lpr


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def make_response(success, data=None, message='', code=200):
    return jsonify({
        'success': success,
        'code': code,
        'message': message,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }), code


@app.route('/')
def index():
    html = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>车牌识别系统 API</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #555; margin-top: 30px; }
        .endpoint { margin: 15px 0; padding: 15px; background: #f5f5f5; border-radius: 8px; }
        .method { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; }
        .get { background: #28a745; }
        .post { background: #007bff; }
        .delete { background: #dc3545; }
        .put { background: #ffc107; color: #333; }
        code { background: #e9ecef; padding: 2px 6px; border-radius: 4px; }
        pre { background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 8px; overflow-x: auto; }
        .section { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>🚗 车牌识别系统 API</h1>
    <p>基于 Python + OpenCV + PaddleOCR 的车牌识别后端服务</p>
    
    <div class="section">
        <h2>📊 基础接口</h2>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/health</h3>
            <p>健康检查接口</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/info</h3>
            <p>获取系统信息和支持的功能</p>
        </div>
    </div>
    
    <div class="section">
        <h2>🖼️ 图片识别接口</h2>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/recognize</h3>
            <p>上传图片进行车牌识别</p>
            <p><strong>请求参数:</strong></p>
            <ul>
                <li><code>image</code> - 图片文件 (multipart/form-data)</li>
                <li><code>save_images</code> - 是否保存处理图片 (可选, 默认 true)</li>
                <li><code>generate_heatmap</code> - 是否生成置信度热力图 (可选, 默认 false)</li>
                <li><code>check_blacklist</code> - 是否检查黑白名单 (可选, 默认 false)</li>
            </ul>
        </div>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/recognize_batch</h3>
            <p>批量识别多张图片</p>
        </div>
    </div>
    
    <div class="section">
        <h2>🎥 视频流接口</h2>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/video/process</h3>
            <p>处理视频文件或RTSP流</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/video/statistics</h3>
            <p>获取视频处理统计信息</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/video/records</h3>
            <p>获取进出场记录</p>
        </div>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/video/stop</h3>
            <p>停止视频处理</p>
        </div>
    </div>
    
    <div class="section">
        <h2>📋 黑白名单接口</h2>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/whitelist/add</h3>
            <p>添加车牌到白名单</p>
        </div>
        <div class="endpoint">
            <h3><span class="method delete">DELETE</span> /api/whitelist/remove</h3>
            <p>从白名单移除车牌</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/whitelist</h3>
            <p>获取白名单列表</p>
        </div>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/blacklist/add</h3>
            <p>添加车牌到黑名单</p>
        </div>
        <div class="endpoint">
            <h3><span class="method delete">DELETE</span> /api/blacklist/remove</h3>
            <p>从黑名单移除车牌</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/blacklist</h3>
            <p>获取黑名单列表</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/lists/statistics</h3>
            <p>获取黑白名单统计信息</p>
        </div>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/lists/check</h3>
            <p>检查车牌是否在黑白名单中</p>
        </div>
    </div>
    
    <div class="section">
        <h2>🔔 告警接口</h2>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/alerts</h3>
            <p>获取告警历史记录</p>
        </div>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/alerts/acknowledge</h3>
            <p>确认告警</p>
        </div>
    </div>
    
    <div class="section">
        <h2>🔥 热力图接口</h2>
        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/heatmap/generate</h3>
            <p>生成置信度热力图</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/heatmap/legend</h3>
            <p>获取热力图图例</p>
        </div>
    </div>
    
    <div class="section">
        <h2>📁 文件访问</h2>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/output/&lt;filename&gt;</h3>
            <p>获取处理后的图片</p>
        </div>
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/uploads/&lt;filename&gt;</h3>
            <p>获取上传的图片</p>
        </div>
    </div>
</body>
</html>
    '''
    return render_template_string(html)


@app.route('/api/health', methods=['GET'])
def health():
    lpr_instance = get_lpr()
    return make_response(
        success=True,
        data={
            'status': 'running',
            'lpr_initialized': lpr_instance is not None,
            'uptime': 'unknown'
        },
        message='服务运行正常'
    )


@app.route('/api/info', methods=['GET'])
def info():
    lpr_instance = get_lpr()
    if lpr_instance:
        info_data = lpr_instance.get_system_info()
    else:
        info_data = {
            'modules': {},
            'supported_plate_types': [],
            'features': [],
            'error': 'LPR not initialized'
        }
    
    return make_response(
        success=True,
        data=info_data,
        message='获取系统信息成功'
    )


@app.route('/api/recognize', methods=['POST'])
def recognize():
    try:
        if 'image' not in request.files:
            return make_response(
                success=False,
                message='未找到图片文件',
                code=400
            )
        
        file = request.files['image']
        if file.filename == '':
            return make_response(
                success=False,
                message='文件名不能为空',
                code=400
            )
        
        if not allowed_file(file.filename):
            return make_response(
                success=False,
                message=f'不支持的文件格式，支持: {", ".join(ALLOWED_EXTENSIONS)}',
                code=400
            )
        
        save_images = request.form.get('save_images', 'true').lower() == 'true'
        generate_heatmap = request.form.get('generate_heatmap', 'false').lower() == 'true'
        check_blacklist = request.form.get('check_blacklist', 'false').lower() == 'true'
        
        image_data = file.read()
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.recognize(
            image_data=image_data,
            save_images=save_images,
            generate_heatmap=generate_heatmap,
            check_blacklist=check_blacklist
        )
        
        if 'error' in result:
            return make_response(
                success=False,
                message=result['error'],
                code=400
            )
        
        return make_response(
            success=result['success'],
            data=result,
            message='识别成功' if result['success'] else '未检测到车牌'
        )
        
    except Exception as e:
        print(f"Recognition error: {e}")
        traceback.print_exc()
        return make_response(
            success=False,
            message=f'识别失败: {str(e)}',
            code=500
        )


@app.route('/api/recognize_batch', methods=['POST'])
def recognize_batch():
    try:
        if 'images' not in request.files:
            return make_response(
                success=False,
                message='未找到图片文件',
                code=400
            )
        
        files = request.files.getlist('images')
        if not files:
            return make_response(
                success=False,
                message='没有上传任何图片',
                code=400
            )
        
        save_images = request.form.get('save_images', 'true').lower() == 'true'
        generate_heatmap = request.form.get('generate_heatmap', 'false').lower() == 'true'
        check_blacklist = request.form.get('check_blacklist', 'false').lower() == 'true'
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        results = []
        for file in files:
            if file.filename == '' or not allowed_file(file.filename):
                continue
            
            image_data = file.read()
            result = lpr_instance.recognize(
                image_data=image_data,
                save_images=save_images,
                generate_heatmap=generate_heatmap,
                check_blacklist=check_blacklist
            )
            results.append({
                'filename': file.filename,
                'result': result
            })
        
        return make_response(
            success=True,
            data={
                'total': len(results),
                'results': results
            },
            message='批量识别完成'
        )
        
    except Exception as e:
        print(f"Batch recognition error: {e}")
        traceback.print_exc()
        return make_response(
            success=False,
            message=f'批量识别失败: {str(e)}',
            code=500
        )


@app.route('/api/video/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json() or {}
        video_source = data.get('video_source')
        output_path = data.get('output_path')
        max_frames = data.get('max_frames')
        entry_zone = data.get('entry_zone')
        exit_zone = data.get('exit_zone')
        check_blacklist = data.get('check_blacklist', False)
        
        if not video_source:
            return make_response(
                success=False,
                message='请提供视频源地址或文件路径',
                code=400
            )
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        def generate():
            for frame_count, frame, tracks in lpr_instance.process_video(
                video_source=video_source,
                output_path=output_path,
                max_frames=max_frames,
                entry_zone=entry_zone,
                exit_zone=exit_zone,
                check_blacklist=check_blacklist
            ):
                track_info = []
                for track in tracks:
                    track_info.append({
                        'track_id': track.track_id,
                        'plate_text': track.plate_text,
                        'bbox': track.bbox,
                        'confidence': track.confidence,
                        'direction': track.direction,
                        'entry_recorded': track.entry_recorded,
                        'exit_recorded': track.exit_recorded
                    })
                
                yield f"data: {json.dumps({'frame': frame_count, 'tracks': track_info})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )
        
    except Exception as e:
        print(f"Video processing error: {e}")
        traceback.print_exc()
        return make_response(
            success=False,
            message=f'视频处理失败: {str(e)}',
            code=500
        )


@app.route('/api/video/statistics', methods=['GET'])
def video_statistics():
    try:
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        stats = lpr_instance.get_video_statistics()
        return make_response(
            success=True,
            data=stats,
            message='获取视频统计信息成功'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'获取统计信息失败: {str(e)}',
            code=500
        )


@app.route('/api/video/records', methods=['GET'])
def video_records():
    try:
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        records = lpr_instance.get_entry_exit_records()
        return make_response(
            success=True,
            data={
                'total': len(records),
                'records': records
            },
            message='获取进出场记录成功'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'获取进出场记录失败: {str(e)}',
            code=500
        )


@app.route('/api/video/stop', methods=['POST'])
def stop_video():
    try:
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        lpr_instance.stop_video_processing()
        return make_response(
            success=True,
            message='视频处理已停止'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'停止视频处理失败: {str(e)}',
            code=500
        )


@app.route('/api/whitelist/add', methods=['POST'])
def add_whitelist():
    try:
        data = request.get_json() or {}
        plate_number = data.get('plate_number')
        
        if not plate_number:
            return make_response(
                success=False,
                message='请提供车牌号码',
                code=400
            )
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.add_to_whitelist(
            plate_number=plate_number,
            owner=data.get('owner'),
            vehicle_type=data.get('vehicle_type'),
            description=data.get('description'),
            valid_from=data.get('valid_from'),
            valid_to=data.get('valid_to')
        )
        
        return make_response(
            success=result['success'],
            data=result.get('data'),
            message=result['message']
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'添加白名单失败: {str(e)}',
            code=500
        )


@app.route('/api/whitelist/remove', methods=['DELETE'])
def remove_whitelist():
    try:
        data = request.get_json() or {}
        plate_number = data.get('plate_number')
        
        if not plate_number:
            return make_response(
                success=False,
                message='请提供车牌号码',
                code=400
            )
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.remove_from_whitelist(plate_number)
        
        return make_response(
            success=result['success'],
            message=result['message']
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'移除白名单失败: {str(e)}',
            code=500
        )


@app.route('/api/whitelist', methods=['GET'])
def get_whitelist():
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.get_whitelist(page=page, page_size=page_size)
        
        return make_response(
            success=True,
            data=result,
            message='获取白名单成功'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'获取白名单失败: {str(e)}',
            code=500
        )


@app.route('/api/blacklist/add', methods=['POST'])
def add_blacklist():
    try:
        data = request.get_json() or {}
        plate_number = data.get('plate_number')
        
        if not plate_number:
            return make_response(
                success=False,
                message='请提供车牌号码',
                code=400
            )
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.add_to_blacklist(
            plate_number=plate_number,
            reason=data.get('reason'),
            level=data.get('level', 'medium'),
            description=data.get('description'),
            valid_from=data.get('valid_from'),
            valid_to=data.get('valid_to')
        )
        
        return make_response(
            success=result['success'],
            data=result.get('data'),
            message=result['message']
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'添加黑名单失败: {str(e)}',
            code=500
        )


@app.route('/api/blacklist/remove', methods=['DELETE'])
def remove_blacklist():
    try:
        data = request.get_json() or {}
        plate_number = data.get('plate_number')
        
        if not plate_number:
            return make_response(
                success=False,
                message='请提供车牌号码',
                code=400
            )
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.remove_from_blacklist(plate_number)
        
        return make_response(
            success=result['success'],
            message=result['message']
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'移除黑名单失败: {str(e)}',
            code=500
        )


@app.route('/api/blacklist', methods=['GET'])
def get_blacklist():
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.get_blacklist(page=page, page_size=page_size)
        
        return make_response(
            success=True,
            data=result,
            message='获取黑名单成功'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'获取黑名单失败: {str(e)}',
            code=500
        )


@app.route('/api/lists/statistics', methods=['GET'])
def get_list_statistics():
    try:
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        stats = lpr_instance.get_list_statistics()
        
        return make_response(
            success=True,
            data=stats,
            message='获取黑白名单统计成功'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'获取统计信息失败: {str(e)}',
            code=500
        )


@app.route('/api/lists/check', methods=['POST'])
def check_plate():
    try:
        data = request.get_json() or {}
        plate_number = data.get('plate_number')
        
        if not plate_number:
            return make_response(
                success=False,
                message='请提供车牌号码',
                code=400
            )
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.check_plate(plate_number)
        
        return make_response(
            success=True,
            data=result,
            message='检查完成'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'检查失败: {str(e)}',
            code=500
        )


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        acknowledged = request.args.get('acknowledged')
        level = request.args.get('level')
        
        if acknowledged is not None:
            acknowledged = acknowledged.lower() == 'true'
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.get_alert_history(
            page=page,
            page_size=page_size,
            acknowledged=acknowledged,
            level=level
        )
        
        return make_response(
            success=True,
            data=result,
            message='获取告警记录成功'
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'获取告警记录失败: {str(e)}',
            code=500
        )


@app.route('/api/alerts/acknowledge', methods=['POST'])
def acknowledge_alert():
    try:
        data = request.get_json() or {}
        alert_id = data.get('alert_id')
        acknowledged_by = data.get('acknowledged_by')
        
        if not alert_id:
            return make_response(
                success=False,
                message='请提供告警ID',
                code=400
            )
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.acknowledge_alert(alert_id, acknowledged_by=acknowledged_by)
        
        return make_response(
            success=result['success'],
            data=result.get('data'),
            message=result['message']
        )
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'确认告警失败: {str(e)}',
            code=500
        )


@app.route('/api/heatmap/generate', methods=['POST'])
def generate_heatmap():
    try:
        if 'image' not in request.files:
            return make_response(
                success=False,
                message='未找到图片文件',
                code=400
            )
        
        file = request.files['image']
        image_data = file.read()
        
        lpr_instance = get_lpr()
        if lpr_instance is None:
            return make_response(
                success=False,
                message='车牌识别系统未初始化',
                code=500
            )
        
        result = lpr_instance.recognize(
            image_data=image_data,
            save_images=True,
            generate_heatmap=True
        )
        
        if 'error' in result:
            return make_response(
                success=False,
                message=result['error'],
                code=400
            )
        
        return make_response(
            success=result['success'],
            data={
                'heatmap_image_path': result.get('heatmap_image_path'),
                'heatmap_report': result.get('heatmap_report'),
                'results': result.get('results', [])
            },
            message='热力图生成成功' if result['success'] else '未检测到车牌'
        )
        
    except Exception as e:
        print(f"Heatmap generation error: {e}")
        traceback.print_exc()
        return make_response(
            success=False,
            message=f'热力图生成失败: {str(e)}',
            code=500
        )


@app.route('/api/heatmap/legend', methods=['GET'])
def heatmap_legend():
    try:
        import cv2
        import numpy as np
        from confidence_heatmap import ConfidenceHeatmap
        
        heatmap_gen = ConfidenceHeatmap()
        legend = heatmap_gen.create_heatmap_legend()
        
        output_path = os.path.join(OUTPUT_FOLDER, 'heatmap_legend.png')
        cv2.imwrite(output_path, legend)
        
        return send_from_directory(OUTPUT_FOLDER, 'heatmap_legend.png')
        
    except Exception as e:
        return make_response(
            success=False,
            message=f'生成图例失败: {str(e)}',
            code=500
        )


@app.route('/api/output/<path:filename>', methods=['GET'])
def get_output_file(filename):
    try:
        return send_from_directory(OUTPUT_FOLDER, filename)
    except Exception as e:
        return make_response(
            success=False,
            message=f'文件不存在: {str(e)}',
            code=404
        )


@app.route('/api/uploads/<path:filename>', methods=['GET'])
def get_upload_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return make_response(
            success=False,
            message=f'文件不存在: {str(e)}',
            code=404
        )


@app.errorhandler(413)
def too_large(e):
    return make_response(
        success=False,
        message=f'文件过大，最大支持 {MAX_CONTENT_LENGTH // (1024 * 1024)} MB',
        code=413
    )


@app.errorhandler(404)
def not_found(e):
    return make_response(
        success=False,
        message='接口不存在',
        code=404
    )


@app.errorhandler(500)
def internal_error(e):
    return make_response(
        success=False,
        message='服务器内部错误',
        code=500
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"🚀 车牌识别系统启动中...")
    print(f"📡 服务地址: http://{host}:{port}")
    print(f"📂 上传目录: {UPLOAD_FOLDER}")
    print(f"📂 输出目录: {OUTPUT_FOLDER}")
    print(f"📂 临时目录: {TEMP_FOLDER}")
    
    app.run(
        host=host,
        port=port,
        debug=os.environ.get('DEBUG', 'False').lower() == 'true',
        threaded=True
    )
