import os
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, disconnect
from config import WEB_SECRET_KEY, BASE_DIR
from .ssh_session import SSHSessionManager
from core.host_manager import HostManager
from core.diff_tool import DiffTool
import json

static_folder = os.path.join(BASE_DIR, 'web', 'static')
template_folder = os.path.join(BASE_DIR, 'web', 'templates')

app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)
app.config['SECRET_KEY'] = WEB_SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

session_manager = SSHSessionManager()
host_manager = HostManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/terminal')
def terminal():
    hosts = host_manager.list_hosts()
    return render_template('terminal.html', hosts=hosts)


@app.route('/api/hosts')
def api_hosts():
    hosts = host_manager.list_hosts()
    return jsonify([{
        'hostname': h.hostname,
        'ip': h.ip,
        'port': h.port,
        'username': h.username,
        'groups': h.groups
    } for h in hosts])


@app.route('/api/diff', methods=['POST'])
def api_diff():
    data = request.json
    old_text = data.get('old', '')
    new_text = data.get('new', '')
    format_type = data.get('format', 'html')
    
    diff_result = DiffTool.compare_text(old_text, new_text)
    
    if format_type == 'html':
        output = DiffTool.format_diff_html(diff_result)
    else:
        output = DiffTool.format_diff_text(diff_result)
    
    return jsonify({
        'has_changes': diff_result.has_changes,
        'stats': diff_result.stats,
        'output': output
    })


@socketio.on('connect')
def handle_connect():
    pass


@socketio.on('ssh_connect')
def handle_ssh_connect(data):
    hostname = data.get('hostname')
    cols = data.get('cols', 80)
    rows = data.get('rows', 24)
    
    def output_callback(output_data):
        emit('ssh_output', {'data': output_data}, room=request.sid)
    
    try:
        session = session_manager.create_session(hostname, output_callback)
        if not session:
            emit('ssh_error', {'error': f'Host {hostname} not found'})
            return
        
        session.connect(term='xterm', cols=cols, rows=rows)
        
        session_info = {
            'session_id': session.session_id,
            'hostname': hostname
        }
        emit('ssh_connected', session_info)
    except Exception as e:
        emit('ssh_error', {'error': str(e)})


@socketio.on('ssh_input')
def handle_ssh_input(data):
    session_id = data.get('session_id')
    input_data = data.get('data', '')
    
    session = session_manager.get_session(session_id)
    if session:
        session.send(input_data)


@socketio.on('ssh_resize')
def handle_ssh_resize(data):
    session_id = data.get('session_id')
    cols = data.get('cols', 80)
    rows = data.get('rows', 24)
    
    session = session_manager.get_session(session_id)
    if session:
        session.resize(cols, rows)


@socketio.on('ssh_disconnect')
def handle_ssh_disconnect(data):
    session_id = data.get('session_id')
    if session_id:
        session_manager.close_session(session_id)
    disconnect()


@socketio.on('disconnect')
def handle_disconnect():
    pass


def create_app():
    return app


def run_server(host='0.0.0.0', port=5000, debug=False):
    socketio.run(app, host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
