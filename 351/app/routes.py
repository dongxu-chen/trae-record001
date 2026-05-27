from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import uuid
from app.redis_store import RedisStore
from app.classifier import SpamClassifier
from app.rule_engine import RuleEngine
from app.text_cleaner import TextCleaner
from app.tasks import classify_email_task, process_feedback_task, train_model_task, incremental_model_update
from config import Config


def create_app():
    app = Flask(__name__)
    CORS(app)
    
    redis_store = RedisStore()
    classifier = SpamClassifier()
    rule_engine = RuleEngine(redis_store)
    phishing_detector = PhishingDetector(redis_store)
    email_clustering = EmailClustering(redis_store)
    bounce_analyzer = BounceAnalyzer(redis_store)
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'spam-filter-api',
            'version': '1.0.0'
        })
    
    @app.route('/api/email/classify', methods=['POST'])
    def classify_email():
        try:
            data = request.get_json()
            
            required_fields = ['sender', 'subject', 'body']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            email_id = str(uuid.uuid4())
            email_data = {
                'email_id': email_id,
                'sender': data.get('sender'),
                'sender_name': data.get('sender_name', ''),
                'reply_to': data.get('reply_to', ''),
                'subject': data.get('subject'),
                'body': data.get('body'),
                'attachments': data.get('attachments', []),
                'sender_ip': data.get('sender_ip', request.remote_addr),
                'recipients': data.get('recipients', []),
                'is_html': data.get('is_html', False)
            }
            
            async_process = data.get('async', False)
            
            if async_process:
                task = classify_email_task.delay(email_data)
                return jsonify({
                    'email_id': email_id,
                    'task_id': task.id,
                    'status': 'processing'
                }), 202
            else:
                result = classify_email_task(email_data)
                return jsonify(result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/email/<email_id>', methods=['GET'])
    def get_email_result(email_id):
        try:
            email = redis_store.get_email(email_id)
            classification = redis_store.get_classification_result(email_id)
            feedback = redis_store.get_feedback(email_id)
            
            if not email and not classification:
                return jsonify({'error': 'Email not found'}), 404
            
            return jsonify({
                'email': email,
                'classification': classification,
                'feedback': feedback
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/email/<email_id>/feedback', methods=['POST'])
    def submit_feedback(email_id):
        try:
            data = request.get_json()
            
            if 'is_correct' not in data:
                return jsonify({'error': 'Missing required field: is_correct'}), 400
            
            feedback_data = {
                'is_correct': data.get('is_correct', False),
                'corrected_label': data.get('corrected_label'),
                'notes': data.get('notes', '')
            }
            
            async_process = data.get('async', True)
            
            if async_process:
                task = process_feedback_task.delay(email_id, feedback_data)
                return jsonify({
                    'email_id': email_id,
                    'task_id': task.id,
                    'status': 'processing'
                }), 202
            else:
                result = process_feedback_task(email_id, feedback_data)
                return jsonify(result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/classifications', methods=['GET'])
    def get_recent_classifications():
        try:
            limit = int(request.args.get('limit', 100))
            classifications = redis_store.get_recent_classifications(limit)
            
            return jsonify({
                'count': len(classifications),
                'classifications': classifications
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/stats', methods=['GET'])
    def get_statistics():
        try:
            stats = redis_store.get_statistics()
            
            try:
                top_words = classifier.get_top_spam_words(20)
            except:
                top_words = []
            
            return jsonify({
                'statistics': stats,
                'top_spam_words': top_words
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/reputation/<sender>', methods=['GET'])
    def get_reputation(sender):
        try:
            reputation = redis_store.get_sender_reputation(sender)
            
            return jsonify({
                'sender': sender,
                'reputation': reputation,
                'level': 'excellent' if reputation >= 80 else 'good' if reputation >= 60 else 'fair' if reputation >= 40 else 'poor'
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/rules', methods=['GET'])
    def get_rules():
        try:
            rules = redis_store.get_all_rules()
            
            return jsonify({
                'count': len(rules),
                'rules': rules
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/rules', methods=['POST'])
    def create_rule():
        try:
            data = request.get_json()
            
            required_fields = ['name', 'type', 'condition']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            rule_id = str(uuid.uuid4())
            rule = {
                'name': data.get('name'),
                'type': data.get('type'),
                'condition': data.get('condition'),
                'weight': data.get('weight', 1.0),
                'priority': data.get('priority', 50),
                'enabled': data.get('enabled', True),
                'description': data.get('description', '')
            }
            
            redis_store.save_rule(rule_id, rule)
            
            return jsonify({
                'rule_id': rule_id,
                'rule': rule
            }), 201
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/rules/<rule_id>', methods=['GET'])
    def get_rule(rule_id):
        try:
            rule = redis_store.get_rule(rule_id)
            
            if not rule:
                return jsonify({'error': 'Rule not found'}), 404
            
            return jsonify({
                'rule_id': rule_id,
                'rule': rule
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/rules/<rule_id>', methods=['DELETE'])
    def delete_rule(rule_id):
        try:
            deleted = redis_store.delete_rule(rule_id)
            
            if not deleted:
                return jsonify({'error': 'Rule not found'}), 404
            
            return jsonify({
                'rule_id': rule_id,
                'deleted': True
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/blacklist/<list_type>', methods=['GET'])
    def get_blacklist(list_type):
        try:
            valid_types = ['keywords', 'senders', 'ips']
            if list_type not in valid_types:
                return jsonify({'error': f'Invalid list type. Must be one of: {valid_types}'}), 400
            
            items = redis_store.get_blacklist(list_type)
            
            return jsonify({
                'list_type': list_type,
                'count': len(items),
                'items': items
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/blacklist/<list_type>', methods=['POST'])
    def add_to_blacklist(list_type):
        try:
            valid_types = ['keywords', 'senders', 'ips']
            if list_type not in valid_types:
                return jsonify({'error': f'Invalid list type. Must be one of: {valid_types}'}), 400
            
            data = request.get_json()
            
            if 'value' not in data:
                return jsonify({'error': 'Missing required field: value'}), 400
            
            redis_store.add_to_blacklist(list_type, data.get('value'))
            
            return jsonify({
                'list_type': list_type,
                'value': data.get('value'),
                'added': True
            }), 201
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/blacklist/<list_type>/<value>', methods=['DELETE'])
    def remove_from_blacklist(list_type, value):
        try:
            valid_types = ['keywords', 'senders', 'ips']
            if list_type not in valid_types:
                return jsonify({'error': f'Invalid list type. Must be one of: {valid_types}'}), 400
            
            removed = redis_store.remove_from_blacklist(list_type, value)
            
            return jsonify({
                'list_type': list_type,
                'value': value,
                'removed': bool(removed)
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/model/train', methods=['POST'])
    def train_model():
        try:
            data = request.get_json()
            
            if 'training_data' not in data:
                return jsonify({'error': 'Missing required field: training_data'}), 400
            
            training_data = data.get('training_data')
            
            if len(training_data) < 10:
                return jsonify({'error': 'At least 10 training samples are required'}), 400
            
            async_process = data.get('async', True)
            
            if async_process:
                task = train_model_task.delay(training_data)
                return jsonify({
                    'task_id': task.id,
                    'status': 'training'
                }), 202
            else:
                metrics = train_model_task(training_data)
                return jsonify(metrics), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/model/update', methods=['POST'])
    def trigger_model_update():
        try:
            data = request.get_json() or {}
            async_process = data.get('async', True)
            
            if async_process:
                task = incremental_model_update.delay()
                return jsonify({
                    'task_id': task.id,
                    'status': 'updating'
                }), 202
            else:
                result = incremental_model_update()
                return jsonify(result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/text/clean', methods=['POST'])
    def clean_text():
        try:
            data = request.get_json()
            
            if 'text' not in data and 'html' not in data:
                return jsonify({'error': 'Missing required field: text or html'}), 400
            
            if 'html' in data:
                cleaned_text = TextCleaner.extract_text_from_html(data.get('html'))
                is_html = True
            else:
                cleaned_text = data.get('text', '')
                is_html = False
            
            return jsonify({
                'original_length': len(data.get('html') or data.get('text', '')),
                'cleaned_length': len(cleaned_text),
                'cleaned_text': cleaned_text,
                'is_html': is_html
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/config', methods=['GET'])
    def get_config():
        try:
            return jsonify({
                'spam_threshold': Config.SPAM_THRESHOLD,
                'online_learning_enabled': Config.ONLINE_LEARNING_ENABLED,
                'online_learning_batch_size': Config.ONLINE_LEARNING_BATCH_SIZE,
                'model_update_interval_hours': Config.MODEL_UPDATE_INTERVAL_HOURS,
                'high_priority_threshold': Config.HIGH_PRIORITY_THRESHOLD,
                'auto_block_threshold': Config.AUTO_BLOCK_THRESHOLD,
                'phishing_detection_enabled': Config.PHISHING_DETECTION_ENABLED,
                'phishing_score_weight': Config.PHISHING_SCORE_WEIGHT,
                'clustering_enabled': Config.CLUSTERING_ENABLED,
                'bounce_analysis_enabled': Config.BOUNCE_ANALYSIS_ENABLED,
                'rule_priorities': Config.RULE_PRIORITIES,
                'rule_weights': Config.RULE_WEIGHTS
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/phishing/analyze', methods=['POST'])
    def analyze_phishing():
        try:
            data = request.get_json()
            
            if 'sender' not in data or 'subject' not in data or 'body' not in data:
                return jsonify({'error': 'Missing required fields: sender, subject, body'}), 400
            
            async_process = data.get('async', False)
            
            if async_process:
                task = analyze_phishing_task.delay(data)
                return jsonify({
                    'task_id': task.id,
                    'status': 'processing'
                }), 202
            else:
                result = phishing_detector.detect_phishing(data)
                return jsonify(result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cluster/analyze', methods=['POST'])
    def cluster_emails():
        try:
            data = request.get_json()
            
            if 'emails' not in data:
                return jsonify({'error': 'Missing required field: emails'}), 400
            
            method = data.get('method', 'dbscan')
            emails = data.get('emails', [])
            
            if len(emails) < 2:
                return jsonify({'error': 'At least 2 emails are required for clustering'}), 400
            
            async_process = data.get('async', False)
            
            if async_process:
                task = cluster_emails_task.delay(emails, method)
                return jsonify({
                    'task_id': task.id,
                    'status': 'processing'
                }), 202
            else:
                result = email_clustering.cluster_emails(emails, method)
                return jsonify(result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cluster/campaigns', methods=['GET'])
    def detect_campaigns():
        try:
            limit = int(request.args.get('limit', 50))
            recent_classifications = redis_store.get_recent_classifications(limit)
            
            emails = []
            for item in recent_classifications:
                if item.get('email'):
                    emails.append(item['email'])
            
            result = email_clustering.detect_spam_campaign(emails)
            
            return jsonify(result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/bounce/analyze', methods=['POST'])
    def analyze_bounce():
        try:
            data = request.get_json()
            
            async_process = data.get('async', False)
            
            if async_process:
                task = analyze_bounce_task.delay(data)
                return jsonify({
                    'task_id': task.id,
                    'status': 'processing'
                }), 202
            else:
                result = bounce_analyzer.analyze_bounce(data)
                return jsonify(result), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/bounce/hijacked', methods=['GET'])
    def get_hijacked_accounts():
        try:
            threshold = float(request.args.get('threshold', Config.BOUNCE_HIJACK_THRESHOLD))
            async_process = request.args.get('async', 'false').lower() == 'true'
            
            if async_process:
                task = detect_hijacked_accounts_task.delay(threshold)
                return jsonify({
                    'task_id': task.id,
                    'status': 'processing'
                }), 202
            else:
                result = bounce_analyzer.get_hijacked_accounts(threshold)
                return jsonify({
                    'total_detected': len(result),
                    'threshold': threshold,
                    'hijacked_accounts': result
                }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/bounce/stats', methods=['GET'])
    def get_bounce_stats():
        try:
            sender = request.args.get('sender')
            async_process = request.args.get('async', 'false').lower() == 'true'
            
            if async_process:
                task = get_bounce_stats_task.delay(sender)
                return jsonify({
                    'task_id': task.id,
                    'status': 'processing'
                }), 202
            else:
                stats = bounce_analyzer.get_bounce_statistics(sender)
                return jsonify(stats), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/bounce/record-delivery', methods=['POST'])
    def record_delivery():
        try:
            data = request.get_json()
            
            if 'sender' not in data:
                return jsonify({'error': 'Missing required field: sender'}), 400
            
            bounce_analyzer.record_successful_delivery(data.get('sender'))
            
            return jsonify({
                'sender': data.get('sender'),
                'recorded': True
            }), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard', methods=['GET'])
    def dashboard():
        try:
            stats = redis_store.get_statistics()
            recent = redis_store.get_recent_classifications(10)
            rules = redis_store.get_all_rules()
            
            return render_template_string(DASHBOARD_TEMPLATE, 
                stats=stats,
                recent=recent,
                rules=rules
            )
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app


DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>垃圾邮件过滤系统 - 仪表盘</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #333; color: white; padding: 20px; border-radius: 8px; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 32px; font-weight: bold; color: #333; }
        .stat-label { color: #666; margin-top: 5px; }
        .spam { color: #e74c3c; }
        .ham { color: #27ae60; }
        .section { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2 { color: #333; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .spam-badge { background: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .ham-badge { background: #27ae60; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .score-bar { height: 8px; background: #ecf0f1; border-radius: 4px; overflow: hidden; }
        .score-fill { height: 100%; background: linear-gradient(90deg, #27ae60 0%, #f39c12 50%, #e74c3c 100%); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ 垃圾邮件过滤系统</h1>
            <p>实时监控与分析仪表盘</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_emails }}</div>
                <div class="stat-label">总邮件数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value spam">{{ stats.spam_count }}</div>
                <div class="stat-label">垃圾邮件</div>
            </div>
            <div class="stat-card">
                <div class="stat-value ham">{{ stats.ham_count }}</div>
                <div class="stat-label">正常邮件</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ "%.1f%%"|format(stats.spam_rate * 100) }}</div>
                <div class="stat-label">垃圾率</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 最近分类记录</h2>
            <table>
                <tr>
                    <th>邮件ID</th>
                    <th>发件人</th>
                    <th>主题</th>
                    <th>垃圾评分</th>
                    <th>分类结果</th>
                </tr>
                {% for item in recent %}
                <tr>
                    <td><small>{{ item.email_id[:16] }}...</small></td>
                    <td>{{ item.email.sender if item.email else 'N/A' }}</td>
                    <td>{{ item.email.subject[:50] if item.email else 'N/A' }}</td>
                    <td>
                        <div class="score-bar">
                            <div class="score-fill" style="width: {{ "%.1f"|format(item.result.spam_probability * 100) }}%"></div>
                        </div>
                        <small>{{ "%.2f"|format(item.result.spam_probability) }}</small>
                    </td>
                    <td>
                        {% if item.result.is_spam %}
                        <span class="spam-badge">垃圾邮件</span>
                        {% else %}
                        <span class="ham-badge">正常</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="section">
            <h2>⚙️ 自定义规则</h2>
            <p>当前规则数: {{ rules|length }}</p>
            <ul>
            {% for rule in rules %}
                <li>{{ rule.name }} (权重: {{ rule.weight }}) - {{ '启用' if rule.enabled else '禁用' }}</li>
            {% endfor %}
            </ul>
        </div>
    </div>
</body>
</html>
"""
