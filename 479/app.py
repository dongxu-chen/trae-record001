import os
import uuid
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv

from models import SentimentAnalyzer, RuleBasedSentiment
from core import (
    ConversationManager, AlertManager, AlertConfig,
    AttributionAnalyzer, create_attribution_analyzer,
    ResponseStrategyEngine, create_response_suggester,
    ConversationCoaching, create_conversation_coaching,
    TrendDataCollector, create_trend_collector
)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

conversation_manager = ConversationManager()
alert_manager = AlertManager()
attribution_analyzer = create_attribution_analyzer()
response_suggester = create_response_suggester()
conversation_coaching = create_conversation_coaching()
trend_collector = create_trend_collector()

try:
    sentiment_analyzer = SentimentAnalyzer()
    use_bert = True
except Exception as e:
    print(f"Warning: Failed to load BERT model, using rule-based analyzer: {e}")
    sentiment_analyzer = RuleBasedSentiment()
    use_bert = False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'model_loaded': use_bert,
        'model_type': 'BERT' if use_bert else 'RuleBased',
        'enabled_channels': alert_manager.get_enabled_channels()
    })


@app.route('/api/sessions', methods=['POST'])
def create_session():
    session_id = str(uuid.uuid4())
    return jsonify({
        'session_id': session_id,
        'message': 'Session created successfully'
    })


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def end_session(session_id):
    conversation_manager.remove_conversation(session_id)
    alert_manager.clear_alerts(session_id)
    return jsonify({'message': 'Session ended'})


@app.route('/api/sessions/<session_id>/history', methods=['GET'])
def get_history(session_id):
    history = conversation_manager.get_history(session_id)
    sentiment_history = conversation_manager.get_sentiment_history(session_id)
    trend = alert_manager.get_sentiment_trend(sentiment_history)
    alerts = alert_manager.get_alerts(session_id)
    context_summary = conversation_manager.get_context_summary(session_id)
    user_profile = alert_manager.get_user_profile(session_id)
    
    history_dicts = [turn.to_dict() for turn in history]
    attribution_changes = attribution_analyzer.analyze_all_changes(history_dicts)
    attribution_stats = attribution_analyzer.get_change_statistics(attribution_changes)
    
    quality_analysis = conversation_coaching.analyze_conversation_quality(history_dicts)
    
    return jsonify({
        'history': history_dicts,
        'sentiment_history': sentiment_history,
        'trend': trend,
        'alerts': alerts,
        'context_summary': context_summary,
        'user_profile': user_profile,
        'attribution_changes': [c.to_dict() for c in attribution_changes],
        'attribution_stats': attribution_stats,
        'quality_analysis': quality_analysis
    })


@app.route('/api/sessions/<session_id>/summary', methods=['GET'])
def get_context_summary(session_id):
    summary = conversation_manager.get_context_summary(session_id)
    important_turns = conversation_manager.get_important_turns(session_id)
    return jsonify({
        'summary': summary,
        'important_turns': important_turns
    })


@app.route('/api/sessions/<session_id>/attribution', methods=['GET'])
def get_attribution_analysis(session_id):
    history = conversation_manager.get_history(session_id)
    history_dicts = [turn.to_dict() for turn in history]
    
    attribution_changes = attribution_analyzer.analyze_all_changes(history_dicts)
    attribution_stats = attribution_analyzer.get_change_statistics(attribution_changes)
    
    return jsonify({
        'changes': [c.to_dict() for c in attribution_changes],
        'statistics': attribution_stats
    })


@app.route('/api/sessions/<session_id>/suggestions', methods=['GET'])
def get_response_suggestions(session_id):
    history = conversation_manager.get_history(session_id)
    if not history:
        return jsonify({'suggestions': [], 'quick_replies': []})
    
    last_customer = None
    for turn in reversed(history):
        if turn.speaker == 'customer' and turn.sentiment_result:
            last_customer = turn
            break
    
    if not last_customer:
        return jsonify({'suggestions': [], 'quick_replies': []})
    
    history_dicts = [turn.to_dict() for turn in history]
    suggestions = response_suggester.generate_suggestions(history_dicts, last_customer.sentiment_result)
    quick_replies = response_suggester.get_quick_replies(last_customer.sentiment_result.get('predicted_label', 'neutral'))
    
    quality_analysis = conversation_coaching.analyze_conversation_quality(history_dicts)
    
    return jsonify({
        'suggestions': [s.to_dict() for s in suggestions],
        'quick_replies': quick_replies,
        'quality_analysis': quality_analysis,
        'context_info': response_suggester.analyze_context(history_dicts, last_customer.sentiment_result)
    })


@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    data = request.json
    text = data.get('text', '')
    session_id = data.get('session_id')
    speaker = data.get('speaker', 'customer')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    context = conversation_manager.get_context_text(session_id) if session_id else []
    
    if use_bert:
        sentiment_result = sentiment_analyzer.predict(text, context)
        embedding = None
    else:
        sentiment_result = sentiment_analyzer.analyze(text)
        embedding = None
    
    conversation_manager.add_turn(
        session_id=session_id,
        text=text,
        speaker=speaker,
        sentiment_result=sentiment_result,
        embedding=embedding
    )
    
    trend_collector.record_message(session_id, text, speaker, sentiment_result)
    
    sentiment_history = conversation_manager.get_sentiment_history(session_id)
    trend = alert_manager.get_sentiment_trend(sentiment_history)
    context_summary = conversation_manager.get_context_summary(session_id)
    
    history = conversation_manager.get_history(session_id)
    history_dicts = [turn.to_dict() for turn in history]
    
    attribution_changes = attribution_analyzer.analyze_all_changes(history_dicts)
    attribution_stats = attribution_analyzer.get_change_statistics(attribution_changes)
    
    suggestions = []
    quick_replies = []
    if speaker == 'customer':
        suggestions = response_suggester.generate_suggestions(history_dicts, sentiment_result)
        quick_replies = response_suggester.get_quick_replies(sentiment_result.get('predicted_label', 'neutral'))
    
    alerts = []
    if speaker == 'customer':
        alerts = alert_manager.generate_alerts(session_id, sentiment_result, sentiment_history)
        for alert in alerts:
            trend_collector.record_alert(session_id)
    
    quality_analysis = conversation_coaching.analyze_conversation_quality(history_dicts)
    
    return jsonify({
        'session_id': session_id,
        'sentiment': sentiment_result,
        'trend': trend,
        'alerts': [alert.to_dict() for alert in alerts],
        'context_summary': context_summary,
        'suggestions': [s.to_dict() for s in suggestions],
        'quick_replies': quick_replies,
        'attribution': {
            'changes': [c.to_dict() for c in attribution_changes],
            'statistics': attribution_stats
        },
        'quality_analysis': quality_analysis
    })


@app.route('/api/trends/daily', methods=['GET'])
def get_daily_trends():
    date = request.args.get('date')
    daily = trend_collector.get_daily_stats(date)
    
    if daily:
        return jsonify(daily.to_dict())
    return jsonify({'message': 'No data for specified date'}), 404


@app.route('/api/trends/weekly', methods=['GET'])
def get_weekly_trends():
    base_date = request.args.get('date')
    weekly = trend_collector.get_weekly_stats(base_date)
    return jsonify(weekly.to_dict())


@app.route('/api/trends/analysis', methods=['GET'])
def get_trend_analysis():
    period = request.args.get('period', '7d')
    analysis = trend_collector.get_trend_analysis(period)
    return jsonify(analysis)


@app.route('/api/trends/hourly', methods=['GET'])
def get_hourly_distribution():
    date = request.args.get('date')
    hourly = trend_collector.get_hourly_distribution(date)
    return jsonify(hourly)


@app.route('/api/alerts/channels', methods=['GET'])
def get_alert_channels():
    enabled_channels = alert_manager.get_enabled_channels()
    return jsonify({
        'enabled_channels': enabled_channels,
        'available_channels': ['wechat_work', 'email', 'sms']
    })


@app.route('/api/alerts/config', methods=['POST'])
def update_alert_config():
    data = request.json
    try:
        config = AlertConfig(
            enabled_channels=data.get('enabled_channels', []),
            wechat_webhook_url=data.get('wechat_webhook_url', ''),
            email_smtp_server=data.get('email_smtp_server', ''),
            email_smtp_port=data.get('email_smtp_port', 587),
            email_sender=data.get('email_sender', ''),
            email_password=data.get('email_password', ''),
            email_recipients=data.get('email_recipients', []),
            sms_api_url=data.get('sms_api_url', ''),
            sms_api_key=data.get('sms_api_key', ''),
            sms_recipients=data.get('sms_recipients', []),
            min_alert_severity=data.get('min_alert_severity', 'medium')
        )
        alert_manager.multi_channel_manager.update_config(config)
        return jsonify({'status': 'ok', 'message': 'Alert config updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/alerts/test/<channel>', methods=['POST'])
def test_alert_channel(channel):
    success = alert_manager.test_alert_channel(channel)
    return jsonify({
        'channel': channel,
        'success': success,
        'message': 'Test sent successfully' if success else 'Test failed'
    })


@app.route('/api/users/<user_id>/profile', methods=['GET'])
def get_user_emotion_profile(user_id):
    profile = alert_manager.get_user_profile(user_id)
    return jsonify(profile)


@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')


@socketio.on('join_session')
def handle_join_session(data):
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        emit('session_joined', {'session_id': session_id}, room=session_id)


@socketio.on('leave_session')
def handle_leave_session(data):
    session_id = data.get('session_id')
    if session_id:
        leave_room(session_id)
        emit('session_left', {'session_id': session_id}, room=session_id)


@socketio.on('send_message')
def handle_send_message(data):
    session_id = data.get('session_id')
    text = data.get('text', '')
    speaker = data.get('speaker', 'customer')
    
    if not session_id:
        session_id = str(uuid.uuid4())
        join_room(session_id)
    
    if not text:
        emit('error', {'message': 'Text is required'}, room=session_id)
        return
    
    context = conversation_manager.get_context_text(session_id)
    
    if use_bert:
        sentiment_result = sentiment_analyzer.predict(text, context)
        embedding = None
    else:
        sentiment_result = sentiment_analyzer.analyze(text)
        embedding = None
    
    conversation_manager.add_turn(
        session_id=session_id,
        text=text,
        speaker=speaker,
        sentiment_result=sentiment_result,
        embedding=embedding
    )
    
    trend_collector.record_message(session_id, text, speaker, sentiment_result)
    
    emit('message_received', {
        'text': text,
        'speaker': speaker,
        'sentiment': sentiment_result
    }, room=session_id)
    
    sentiment_history = conversation_manager.get_sentiment_history(session_id)
    trend = alert_manager.get_sentiment_trend(sentiment_history)
    
    emit('trend_update', trend, room=session_id)
    
    context_summary = conversation_manager.get_context_summary(session_id)
    emit('context_update', context_summary, room=session_id)
    
    history = conversation_manager.get_history(session_id)
    history_dicts = [turn.to_dict() for turn in history]
    
    attribution_changes = attribution_analyzer.analyze_all_changes(history_dicts)
    if attribution_changes:
        latest_change = attribution_changes[-1]
        emit('attribution_update', {
            'latest_change': latest_change.to_dict(),
            'statistics': attribution_analyzer.get_change_statistics(attribution_changes)
        }, room=session_id)
    
    if speaker == 'customer':
        alerts = alert_manager.generate_alerts(session_id, sentiment_result, sentiment_history)
        if alerts:
            for alert in alerts:
                emit('alert', alert.to_dict(), room=session_id)
                trend_collector.record_alert(session_id)
        
        suggestions = response_suggester.generate_suggestions(history_dicts, sentiment_result)
        quick_replies = response_suggester.get_quick_replies(sentiment_result.get('predicted_label', 'neutral'))
        quality_analysis = conversation_coaching.analyze_conversation_quality(history_dicts)
        
        emit('suggestions_update', {
            'suggestions': [s.to_dict() for s in suggestions],
            'quick_replies': quick_replies,
            'quality_analysis': quality_analysis
        }, room=session_id)
    
    user_profile = alert_manager.get_user_profile(session_id)
    emit('profile_update', user_profile, room=session_id)
    
    return {
        'session_id': session_id,
        'sentiment': sentiment_result,
        'trend': trend
    }


@socketio.on('get_history')
def handle_get_history(data):
    session_id = data.get('session_id')
    if session_id:
        history = conversation_manager.get_history(session_id)
        sentiment_history = conversation_manager.get_sentiment_history(session_id)
        trend = alert_manager.get_sentiment_trend(sentiment_history)
        alerts = alert_manager.get_alerts(session_id)
        context_summary = conversation_manager.get_context_summary(session_id)
        user_profile = alert_manager.get_user_profile(session_id)
        
        history_dicts = [turn.to_dict() for turn in history]
        attribution_changes = attribution_analyzer.analyze_all_changes(history_dicts)
        attribution_stats = attribution_analyzer.get_change_statistics(attribution_changes)
        quality_analysis = conversation_coaching.analyze_conversation_quality(history_dicts)
        
        emit('history_response', {
            'history': history_dicts,
            'sentiment_history': sentiment_history,
            'trend': trend,
            'alerts': alerts,
            'context_summary': context_summary,
            'user_profile': user_profile,
            'attribution_changes': [c.to_dict() for c in attribution_changes],
            'attribution_stats': attribution_stats,
            'quality_analysis': quality_analysis
        }, room=session_id)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)
