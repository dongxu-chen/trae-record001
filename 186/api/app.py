import os
import sys
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import init_database
from modules.audit_service import DramaAuditService
from modules import format_time

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

audit_service = DramaAuditService()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'Drama Content Audit System',
        'version': '2.0.0'
    })

@app.route('/api/videos/upload', methods=['POST'])
def upload_video():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未找到上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        original_filename = secure_filename(file.filename)
        result = audit_service.upload_video(file, original_filename)
        
        return jsonify({
            'code': 0,
            'message': '上传成功',
            'data': result
        })
        
    except ValueError as e:
        return jsonify({'code': 400, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'code': 500, 'message': f'上传失败: {str(e)}'}), 500

@app.route('/api/videos/<int:video_id>/audit', methods=['POST'])
def start_audit(video_id):
    try:
        data = request.json if request.is_json else {}
        frame_interval = data.get('frame_interval')
        min_interval = data.get('min_interval', 0.5)
        max_interval = data.get('max_interval', 5.0)
        scene_threshold = data.get('scene_threshold', 0.3)
        enable_ocr_preprocessing = data.get('enable_ocr_preprocessing', True)
        
        result = audit_service.audit_video(
            video_id=video_id,
            frame_interval=frame_interval,
            min_interval=min_interval,
            max_interval=max_interval,
            scene_threshold=scene_threshold,
            enable_ocr_preprocessing=enable_ocr_preprocessing
        )
        
        return jsonify({
            'code': 0,
            'message': '审核完成',
            'data': result
        })
        
    except ValueError as e:
        return jsonify({'code': 404, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'code': 500, 'message': f'审核失败: {str(e)}'}), 500

@app.route('/api/videos/<int:video_id>/result', methods=['GET'])
def get_audit_result(video_id):
    try:
        result = audit_service.get_audit_result(video_id)
        
        violations_formatted = []
        for v in result['violations']:
            violations_formatted.append({
                'id': v['id'],
                'violation_type': v['violation_type'],
                'violation_type_name': v['violation_type_name'],
                'timestamp': v['timestamp'],
                'timestamp_formatted': format_time(v['timestamp']),
                'confidence': v['confidence'],
                'description': v['description'],
                'ocr_text': v.get('ocr_text'),
                'image_path': v.get('image_path'),
                'review_status': v.get('review_status', 'pending'),
                'is_false_positive': v.get('is_false_positive', 0),
                'created_at': v['created_at'].isoformat() if v.get('created_at') else None
            })
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'video': {
                    'id': result['video']['id'],
                    'original_name': result['video']['original_name'],
                    'duration': result['video']['duration'],
                    'status': result['video']['status'],
                    'audit_result': result['video']['audit_result'],
                    'violation_count': result['video']['violation_count'],
                    'review_status': result['video'].get('review_status', 'pending'),
                    'created_at': result['video']['created_at'].isoformat() if result['video'].get('created_at') else None
                },
                'violations': violations_formatted,
                'violation_count': result['violation_count']
            }
        })
        
    except ValueError as e:
        return jsonify({'code': 404, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取结果失败: {str(e)}'}), 500

@app.route('/api/videos', methods=['GET'])
def list_videos():
    try:
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        result = audit_service.list_videos(status=status, page=page, page_size=page_size)
        
        videos_formatted = []
        for v in result['videos']:
            videos_formatted.append({
                'id': v['id'],
                'original_name': v['original_name'],
                'file_size': v['file_size'],
                'duration': v['duration'],
                'width': v['width'],
                'height': v['height'],
                'status': v['status'],
                'audit_result': v['audit_result'],
                'violation_count': v['violation_count'],
                'review_status': v.get('review_status', 'pending'),
                'created_at': v['created_at'].isoformat() if v.get('created_at') else None
            })
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'videos': videos_formatted,
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
                'total_pages': result['total_pages']
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取列表失败: {str(e)}'}), 500

@app.route('/api/videos/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    try:
        audit_service.delete_video(video_id)
        return jsonify({
            'code': 0,
            'message': '删除成功'
        })
        
    except ValueError as e:
        return jsonify({'code': 404, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'code': 500, 'message': f'删除失败: {str(e)}'}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        stats = audit_service.get_statistics()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取统计失败: {str(e)}'}), 500

@app.route('/api/reviews/pending', methods=['GET'])
def get_pending_reviews():
    try:
        video_id = request.args.get('video_id', type=int)
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        result = audit_service.get_pending_reviews(video_id=video_id, page=page, page_size=page_size)
        
        violations_formatted = []
        for v in result['violations']:
            violations_formatted.append({
                'id': v['id'],
                'video_id': v['video_id'],
                'video_name': v.get('video_name', ''),
                'violation_type': v['violation_type'],
                'violation_type_name': v['violation_type_name'],
                'timestamp': v['timestamp'],
                'timestamp_formatted': format_time(v['timestamp']),
                'confidence': v['confidence'],
                'description': v['description'],
                'image_path': v.get('image_path'),
                'created_at': v['created_at'].isoformat() if v.get('created_at') else None
            })
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'violations': violations_formatted,
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
                'total_pages': result['total_pages']
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取待审核列表失败: {str(e)}'}), 500

@app.route('/api/reviews/<int:violation_id>', methods=['POST'])
def review_violation(violation_id):
    try:
        data = request.json
        reviewer_id = data.get('reviewer_id')
        reviewer_name = data.get('reviewer_name', '未知用户')
        is_false_positive = data.get('is_false_positive', False)
        review_note = data.get('review_note', '')
        review_time = data.get('review_time')
        
        if not reviewer_id:
            return jsonify({'code': 400, 'message': '缺少reviewer_id参数'}), 400
        
        result = audit_service.review_violation(
            violation_id=violation_id,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            is_false_positive=is_false_positive,
            review_note=review_note,
            review_time=review_time
        )
        
        return jsonify({
            'code': 0,
            'message': '审核完成',
            'data': result
        })
        
    except ValueError as e:
        return jsonify({'code': 404, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'code': 500, 'message': f'审核失败: {str(e)}'}), 500

@app.route('/api/statistics/quality', methods=['GET'])
def get_quality_statistics():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        stats = audit_service.get_quality_metrics(start_date=start_date, end_date=end_date)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取质量统计失败: {str(e)}'}), 500

@app.route('/api/videos/<int:video_id>/sanitize', methods=['POST'])
def sanitize_video(video_id):
    try:
        data = request.json or {}
        blur_strength = data.get('blur_strength', 30)
        
        result = audit_service.sanitize_video(video_id, blur_strength=blur_strength)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except ValueError as e:
        return jsonify({'code': 404, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'code': 500, 'message': f'视频脱敏失败: {str(e)}'}), 500

@app.route('/api/sensitive-words', methods=['GET'])
def get_sensitive_words():
    try:
        category = request.args.get('category')
        is_active = request.args.get('is_active')
        is_active_bool = None if is_active is None else (is_active.lower() == 'true')
        
        result = audit_service.get_sensitive_words(category=category, is_active=is_active_bool)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取敏感词失败: {str(e)}'}), 500

@app.route('/api/sensitive-words', methods=['POST'])
def add_sensitive_word():
    try:
        data = request.json
        word = data.get('word', '').strip()
        category = data.get('category', 'other')
        severity = data.get('severity', 'medium')
        match_mode = data.get('match_mode', 'exact')
        
        if not word:
            return jsonify({'code': 400, 'message': '缺少word参数'}), 400
        
        result = audit_service.add_sensitive_word(
            word=word,
            category=category,
            severity=severity,
            match_mode=match_mode
        )
        
        return jsonify({
            'code': 0,
            'message': '添加成功',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'添加敏感词失败: {str(e)}'}), 500

@app.route('/api/sensitive-words/batch', methods=['POST'])
def add_sensitive_words_batch():
    try:
        data = request.json
        words = data.get('words', [])
        
        if not words:
            return jsonify({'code': 400, 'message': '缺少words参数'}), 400
        
        from models.rule_model import SensitiveWordModel
        count = SensitiveWordModel.add_words_batch(words)
        
        return jsonify({
            'code': 0,
            'message': f'成功添加{count}个敏感词',
            'data': {'added_count': count}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'批量添加敏感词失败: {str(e)}'}), 500

@app.route('/api/sensitive-words/<int:word_id>', methods=['PUT'])
def update_sensitive_word(word_id):
    try:
        data = request.json
        result = audit_service.update_sensitive_word(word_id, **data)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'更新敏感词失败: {str(e)}'}), 500

@app.route('/api/sensitive-words/<int:word_id>', methods=['DELETE'])
def delete_sensitive_word(word_id):
    try:
        result = audit_service.delete_sensitive_word(word_id)
        
        return jsonify({
            'code': 0,
            'message': '删除成功',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'删除敏感词失败: {str(e)}'}), 500

@app.route('/api/text/mask', methods=['POST'])
def mask_text():
    try:
        data = request.json
        text = data.get('text', '')
        category = data.get('category')
        mask_mode = data.get('mask_mode', 'full')
        mask_char = data.get('mask_char', '*')
        
        result = audit_service.mask_sensitive_text(
            text=text,
            category=category,
            mask_mode=mask_mode,
            mask_char=mask_char
        )
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'文本脱敏失败: {str(e)}'}), 500

@app.route('/api/audit-rules', methods=['GET'])
def get_audit_rules():
    try:
        rule_type = request.args.get('rule_type')
        is_active = request.args.get('is_active')
        is_active_bool = None if is_active is None else (is_active.lower() == 'true')
        
        result = audit_service.get_audit_rules(rule_type=rule_type, is_active=is_active_bool)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取审核规则失败: {str(e)}'}), 500

@app.route('/api/audit-rules', methods=['POST'])
def add_audit_rule():
    try:
        data = request.json
        rule_name = data.get('rule_name', '')
        rule_type = data.get('rule_type', '')
        violation_type = data.get('violation_type', '')
        threshold = data.get('threshold', 0.7)
        config_json = data.get('config_json')
        description = data.get('description')
        
        if not rule_name or not rule_type or not violation_type:
            return jsonify({'code': 400, 'message': '缺少必填参数'}), 400
        
        result = audit_service.add_audit_rule(
            rule_name=rule_name,
            rule_type=rule_type,
            violation_type=violation_type,
            threshold=threshold,
            config_json=config_json,
            description=description
        )
        
        return jsonify({
            'code': 0,
            'message': '添加成功',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'添加审核规则失败: {str(e)}'}), 500

@app.route('/api/audit-rules/<int:rule_id>', methods=['PUT'])
def update_audit_rule(rule_id):
    try:
        data = request.json
        result = audit_service.update_audit_rule(rule_id, **data)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'更新审核规则失败: {str(e)}'}), 500

@app.route('/api/audit-rules/<int:rule_id>', methods=['DELETE'])
def delete_audit_rule(rule_id):
    try:
        result = audit_service.delete_audit_rule(rule_id)
        
        return jsonify({
            'code': 0,
            'message': '删除成功',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'删除审核规则失败: {str(e)}'}), 500

@app.route('/api/quality-samples/run', methods=['POST'])
def run_quality_sampling():
    try:
        data = request.json or {}
        sample_rate = data.get('sample_rate', 0.05)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        sample_type = data.get('sample_type', 'manual')
        
        result = audit_service.run_quality_sampling(
            sample_rate=sample_rate,
            start_date=start_date,
            end_date=end_date,
            sample_type=sample_type
        )
        
        return jsonify({
            'code': 0,
            'message': '抽检完成',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'质量抽检失败: {str(e)}'}), 500

@app.route('/api/quality-samples/pending', methods=['GET'])
def get_pending_quality_samples():
    try:
        sample_type = request.args.get('sample_type')
        
        result = audit_service.get_pending_quality_samples(sample_type=sample_type)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取待抽检列表失败: {str(e)}'}), 500

@app.route('/api/quality-samples/<int:sample_id>/audit', methods=['POST'])
def audit_quality_sample(sample_id):
    try:
        data = request.json
        auditor_id = data.get('auditor_id')
        audit_result = data.get('audit_result')
        audit_note = data.get('audit_note')
        audit_time = data.get('audit_time')
        
        if not auditor_id or not audit_result:
            return jsonify({'code': 400, 'message': '缺少必填参数'}), 400
        
        result = audit_service.audit_quality_sample(
            sample_id=sample_id,
            auditor_id=auditor_id,
            audit_result=audit_result,
            audit_note=audit_note,
            audit_time=audit_time
        )
        
        return jsonify({
            'code': 0,
            'message': '审核完成',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'抽检审核失败: {str(e)}'}), 500

@app.route('/api/statistics/consistency', methods=['GET'])
def get_consistency_statistics():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        stats = audit_service.get_quality_consistency_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取一致性统计失败: {str(e)}'}), 500

@app.route('/api/statistics/samples', methods=['GET'])
def get_sample_statistics():
    try:
        stats = audit_service.get_quality_sample_stats()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取抽检统计失败: {str(e)}'}), 500

@app.route('/api/quality-samples/<int:sample_id>/detail', methods=['GET'])
def get_sample_consistency_detail(sample_id):
    try:
        detail = audit_service.get_sample_consistency_detail(sample_id)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': detail
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取抽检详情失败: {str(e)}'}), 500

@app.route('/api/videos/<int:video_id>/frames/<path:filename>', methods=['GET'])
def get_frame_image(video_id, filename):
    from config.config import FRAMES_DIR
    frame_path = os.path.join(FRAMES_DIR, str(video_id), filename)
    
    if os.path.exists(frame_path):
        return send_file(frame_path, mimetype='image/jpeg')
    else:
        return jsonify({'error': '图片不存在'}), 404

@app.errorhandler(413)
def too_large(e):
    return jsonify({'code': 413, 'message': '文件过大，最大支持500MB'}), 413

def create_app():
    init_database()
    return app

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=True)
