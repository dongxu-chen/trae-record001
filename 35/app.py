import os
import logging
import re
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from celery.result import AsyncResult
from celery.exceptions import CeleryError, TimeoutError
from kombu.exceptions import KombuError
from dotenv import load_dotenv

from celery_app import make_celery, get_queue_for_priority
from tasks import process_thumbnail, process_filter, batch_process, get_available_filters
from rate_limit import rate_limit

load_dotenv()

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

celery = make_celery(app)

CELERY_RESULT_TIMEOUT = 5
CELERY_RETRY_TIMES = 2

WEBHOOK_URL_PATTERN = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
    r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_file():
    if 'image' not in request.files:
        return None, {'error': 'No image file provided'}, 400
    
    file = request.files['image']
    if file.filename == '':
        return None, {'error': 'No image file selected'}, 400
    
    if not allowed_file(file.filename):
        return None, {'error': 'File type not allowed'}, 400
    
    return file, None, None

def validate_webhook_url(url):
    if not url:
        return None
    
    url = url.strip()
    
    if not WEBHOOK_URL_PATTERN.match(url):
        raise ValueError('Invalid webhook URL format')
    
    parsed = __import__('urllib.parse', fromlist=['urlparse']).urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('Webhook URL must use http or https scheme')
    
    return url

def validate_priority(priority):
    if priority is None:
        return None
    
    try:
        priority = int(priority)
    except (TypeError, ValueError):
        raise ValueError('Priority must be an integer between 1 and 9')
    
    if priority < 1 or priority > 9:
        raise ValueError('Priority must be between 1 and 9')
    
    return priority

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'image-processor'
    })

@app.route('/api/filters', methods=['GET'])
@rate_limit(rate=10, capacity=50)
def list_filters():
    return jsonify({
        'filters': get_available_filters()
    })

@app.route('/api/thumbnail', methods=['POST'])
@rate_limit(rate=2, capacity=10)
def create_thumbnail():
    file, error_response, status_code = validate_image_file()
    if error_response:
        return jsonify(error_response), status_code
    
    try:
        width = request.form.get('width', type=int)
        height = request.form.get('height', type=int)
        quality = request.form.get('quality', default=85, type=int)
        maintain_aspect = request.form.get('maintain_aspect_ratio', default='true').lower() == 'true'
        webhook_url = validate_webhook_url(request.form.get('webhook_url'))
        priority = validate_priority(request.form.get('priority'))
        
        if not width and not height:
            return jsonify({'error': 'At least one of width or height is required'}), 400
        
        if quality < 1 or quality > 100:
            return jsonify({'error': 'Quality must be between 1 and 100'}), 400
        
        image_bytes = file.read()
        
        queue, actual_priority = get_queue_for_priority(priority)
        
        task = process_thumbnail.apply_async(
            kwargs={
                'image_bytes': image_bytes,
                'width': width,
                'height': height,
                'quality': quality,
                'maintain_aspect_ratio': maintain_aspect,
                'webhook_url': webhook_url
            },
            queue=queue,
            priority=actual_priority
        )
        
        response = {
            'task_id': task.id,
            'status': 'queued',
            'queue': queue,
            'priority': actual_priority,
            'message': 'Thumbnail processing task has been queued'
        }
        
        if webhook_url:
            response['webhook_enabled'] = True
        
        return jsonify(response), 202
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception('Error in create_thumbnail')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/filter', methods=['POST'])
@rate_limit(rate=2, capacity=10)
def apply_filter():
    file, error_response, status_code = validate_image_file()
    if error_response:
        return jsonify(error_response), status_code
    
    try:
        filter_name = request.form.get('filter')
        quality = request.form.get('quality', default=85, type=int)
        webhook_url = validate_webhook_url(request.form.get('webhook_url'))
        priority = validate_priority(request.form.get('priority'))
        
        if not filter_name:
            return jsonify({'error': 'Filter name is required'}), 400
        
        if filter_name not in get_available_filters():
            return jsonify({'error': f'Unknown filter: {filter_name}'}), 400
        
        if quality < 1 or quality > 100:
            return jsonify({'error': 'Quality must be between 1 and 100'}), 400
        
        image_bytes = file.read()
        
        queue, actual_priority = get_queue_for_priority(priority)
        
        task = process_filter.apply_async(
            kwargs={
                'image_bytes': image_bytes,
                'filter_name': filter_name,
                'quality': quality,
                'webhook_url': webhook_url
            },
            queue=queue,
            priority=actual_priority
        )
        
        response = {
            'task_id': task.id,
            'status': 'queued',
            'queue': queue,
            'priority': actual_priority,
            'message': f'Filter processing task has been queued'
        }
        
        if webhook_url:
            response['webhook_enabled'] = True
        
        return jsonify(response), 202
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception('Error in apply_filter')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/batch', methods=['POST'])
@rate_limit(rate=1, capacity=5)
def batch_process_images():
    file, error_response, status_code = validate_image_file()
    if error_response:
        return jsonify(error_response), status_code
    
    try:
        import json
        operations_str = request.form.get('operations', '[]')
        operations = json.loads(operations_str)
        quality = request.form.get('quality', default=85, type=int)
        webhook_url = validate_webhook_url(request.form.get('webhook_url'))
        priority = validate_priority(request.form.get('priority'))
        
        if not operations or not isinstance(operations, list):
            return jsonify({'error': 'Operations array is required'}), 400
        
        if len(operations) == 0:
            return jsonify({'error': 'At least one operation is required'}), 400
        
        if quality < 1 or quality > 100:
            return jsonify({'error': 'Quality must be between 1 and 100'}), 400
        
        available_filters = get_available_filters()
        for op in operations:
            op_type = op.get('type')
            if op_type not in ['resize', 'filter']:
                return jsonify({'error': f'Unknown operation type: {op_type}'}), 400
            
            if op_type == 'filter':
                if 'filter' not in op:
                    return jsonify({'error': 'Filter name is required for filter operation'}), 400
                if op['filter'] not in available_filters:
                    return jsonify({'error': f'Unknown filter: {op["filter"]}'}), 400
            
            if op_type == 'resize':
                if 'width' not in op and 'height' not in op:
                    return jsonify({'error': 'At least one of width or height is required for resize operation'}), 400
        
        image_bytes = file.read()
        
        queue, actual_priority = get_queue_for_priority(priority)
        
        task = batch_process.apply_async(
            kwargs={
                'image_bytes': image_bytes,
                'operations': operations,
                'quality': quality,
                'webhook_url': webhook_url
            },
            queue=queue,
            priority=actual_priority
        )
        
        response = {
            'task_id': task.id,
            'status': 'queued',
            'queue': queue,
            'priority': actual_priority,
            'message': 'Batch processing task has been queued'
        }
        
        if webhook_url:
            response['webhook_enabled'] = True
        
        return jsonify(response), 202
        
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in operations field'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception('Error in batch_process_images')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
@rate_limit(rate=5, capacity=30)
def get_task_status(task_id):
    last_error = None
    
    for attempt in range(CELERY_RETRY_TIMES + 1):
        try:
            task = AsyncResult(task_id, app=celery)
            
            response = {
                'task_id': task_id,
                'status': task.status
            }
            
            if task.state == 'PENDING':
                response['message'] = 'Task is pending'
            elif task.state == 'STARTED':
                response['message'] = 'Task is running'
                try:
                    info = task.info
                    if isinstance(info, dict) and 'error' not in info:
                        response['meta'] = info
                except Exception:
                    pass
            elif task.state == 'SUCCESS':
                try:
                    response['result'] = task.result
                    response['message'] = 'Task completed successfully'
                except Exception as e:
                    logger.warning(f'Failed to retrieve task result for {task_id}: {str(e)}')
                    response['message'] = 'Task completed but result unavailable'
            elif task.state == 'FAILURE':
                response['message'] = 'Task failed'
                try:
                    error_info = task.result
                    if isinstance(error_info, Exception):
                        response['error'] = str(error_info)
                    elif isinstance(error_info, dict) and 'error' in error_info:
                        response['error'] = str(error_info['error'])
                    else:
                        response['error'] = str(error_info)
                except Exception:
                    response['error'] = 'Unknown failure'
            elif task.state == 'RETRY':
                response['message'] = 'Task is retrying'
            elif task.state == 'REVOKED':
                response['message'] = 'Task was revoked'
            
            return jsonify(response)
            
        except TimeoutError as e:
            last_error = f'Connection timeout while fetching task status: {str(e)}'
            logger.warning(f'Attempt {attempt + 1}/{CELERY_RETRY_TIMES + 1}: {last_error}')
            if attempt == CELERY_RETRY_TIMES:
                return jsonify({
                    'task_id': task_id,
                    'status': 'unknown',
                    'error': 'Backend timeout. Please retry later.'
                }), 504
        except (CeleryError, KombuError) as e:
            last_error = f'Celery/Kombu error: {str(e)}'
            logger.error(f'{last_error} (task_id: {task_id})')
            return jsonify({
                'task_id': task_id,
                'status': 'error',
                'error': 'Failed to communicate with task backend'
            }), 503
        except ConnectionError as e:
            last_error = f'Connection error: {str(e)}'
            logger.warning(f'Attempt {attempt + 1}/{CELERY_RETRY_TIMES + 1}: {last_error}')
            if attempt == CELERY_RETRY_TIMES:
                return jsonify({
                    'task_id': task_id,
                    'status': 'unknown',
                    'error': 'Cannot connect to task backend. Please retry later.'
                }), 503
        except Exception as e:
            last_error = f'Unexpected error: {str(e)}'
            logger.exception(f'Unhandled exception in get_task_status for {task_id}')
            return jsonify({
                'task_id': task_id,
                'status': 'error',
                'error': 'Internal server error while fetching task status'
            }), 500
    
    return jsonify({
        'task_id': task_id,
        'status': 'unknown',
        'error': last_error or 'Failed to retrieve task status'
    }), 503

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@rate_limit(rate=3, capacity=20)
def cancel_task(task_id):
    last_error = None
    
    for attempt in range(CELERY_RETRY_TIMES + 1):
        try:
            task = AsyncResult(task_id, app=celery)
            state = task.state
            
            if state in ['PENDING', 'STARTED', 'RETRY']:
                task.revoke(terminate=True)
                return jsonify({
                    'task_id': task_id,
                    'status': 'cancelled',
                    'message': 'Task has been cancelled'
                })
            elif state == 'REVOKED':
                return jsonify({
                    'task_id': task_id,
                    'status': 'cancelled',
                    'message': 'Task was already cancelled'
                })
            else:
                return jsonify({
                    'task_id': task_id,
                    'status': state,
                    'message': 'Task is not cancellable in its current state'
                })
            
        except TimeoutError as e:
            last_error = f'Connection timeout while revoking task: {str(e)}'
            logger.warning(f'Attempt {attempt + 1}/{CELERY_RETRY_TIMES + 1}: {last_error}')
            if attempt == CELERY_RETRY_TIMES:
                return jsonify({
                    'task_id': task_id,
                    'status': 'error',
                    'error': 'Backend timeout while cancelling task'
                }), 504
        except (CeleryError, KombuError) as e:
            last_error = f'Celery/Kombu error: {str(e)}'
            logger.error(f'{last_error} (task_id: {task_id})')
            return jsonify({
                'task_id': task_id,
                'status': 'error',
                'error': 'Failed to communicate with task backend'
            }), 503
        except ConnectionError as e:
            last_error = f'Connection error: {str(e)}'
            logger.warning(f'Attempt {attempt + 1}/{CELERY_RETRY_TIMES + 1}: {last_error}')
            if attempt == CELERY_RETRY_TIMES:
                return jsonify({
                    'task_id': task_id,
                    'status': 'error',
                    'error': 'Cannot connect to task backend'
                }), 503
        except Exception as e:
            logger.exception(f'Unhandled exception in cancel_task for {task_id}')
            return jsonify({
                'task_id': task_id,
                'status': 'error',
                'error': 'Internal server error'
            }), 500
    
    return jsonify({
        'task_id': task_id,
        'status': 'error',
        'error': last_error or 'Failed to cancel task'
    }), 503

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
