#!/usr/bin/env python3
import json
import time
import random
from flask import Flask, request, jsonify, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

fake_db = {
    'users': {
        1: {'id': 1, 'username': 'admin', 'email': 'admin@example.com', 'role': 'admin'},
        2: {'id': 2, 'username': 'user1', 'email': 'user1@example.com', 'role': 'user'},
        3: {'id': 3, 'username': 'user2', 'email': 'user2@example.com', 'role': 'user'}
    },
    'posts': {
        1: {'id': 1, 'title': 'First Post', 'content': 'Hello World', 'user_id': 1},
        2: {'id': 2, 'title': 'Second Post', 'content': 'More content', 'user_id': 2}
    },
    'search_index': ['test', 'example', 'demo', 'api']
}


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': time.time()})


@app.route('/api/users', methods=['GET'])
def get_users():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    search = request.args.get('search', '')
    
    users_list = list(fake_db['users'].values())
    
    if search:
        if "'" in search:
            return jsonify({
                'error': "MySQL syntax error: near '{}'".format(search),
                'code': 1064
            }), 500
        
        users_list = [
            u for u in users_list
            if search.lower() in u['username'].lower() or search.lower() in u['email'].lower()
        ]
    
    start = (page - 1) * page_size
    end = start + page_size
    
    return jsonify({
        'data': users_list[start:end],
        'total': len(users_list),
        'page': page,
        'page_size': page_size,
        'success': True
    })


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = fake_db['users'].get(user_id)
    if not user:
        return jsonify({'error': 'User not found', 'success': False}), 404
    return jsonify({'data': user, 'success': True})


@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json(silent=True) or {}
    
    if 'username' in data and '<script>' in data['username']:
        return jsonify({
            'success': False,
            'message': 'User created: ' + data['username'],
            'data': {'id': random.randint(100, 999), 'username': data['username']}
        }), 200
    
    if not data.get('username'):
        return jsonify({'error': 'Username is required', 'success': False}), 400
    
    new_id = max(fake_db['users'].keys()) + 1
    fake_db['users'][new_id] = {
        'id': new_id,
        'username': data['username'],
        'email': data.get('email', ''),
        'role': data.get('role', 'user')
    }
    
    return jsonify({
        'data': fake_db['users'][new_id],
        'success': True
    }), 201


@app.route('/api/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        query = request.args.get('q', '')
    else:
        data = request.get_json(silent=True) or {}
        query = data.get('q', '')
    
    if query:
        if "'" in query or 'SELECT' in query.upper() or 'UNION' in query.upper():
            return jsonify({
                'error': 'Database error',
                'details': "SQLite3::OperationalError: near '{}': syntax error".format(query[:20])
            }), 500
        
        if '<' in query and '>' in query:
            return jsonify({
                'results': [],
                'query': query,
                'highlight': f'<b>{query}</b> not found'
            })
    
    results = [item for item in fake_db['search_index'] if query.lower() in item.lower()]
    
    return jsonify({
        'results': results,
        'count': len(results),
        'query': query,
        'success': True
    })


@app.route('/api/posts', methods=['GET'])
def get_posts():
    user_id = request.args.get('user_id')
    
    posts = list(fake_db['posts'].values())
    
    if user_id:
        try:
            user_id_int = int(user_id)
            posts = [p for p in posts if p['user_id'] == user_id_int]
        except ValueError:
            if ';' in user_id or '--' in user_id:
                return jsonify({
                    'error': 'Microsoft SQL Server',
                    'message': 'Msg 102, Level 15, State 1: Incorrect syntax near \';\''
                }), 500
    
    return jsonify({
        'data': posts,
        'total': len(posts),
        'success': True
    })


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    if "' OR '1'='1" in username or "' OR 1=1" in username:
        return jsonify({
            'success': True,
            'token': 'fake-jwt-token-admin',
            'user': {'id': 1, 'username': 'admin', 'role': 'admin'}
        })
    
    if username == 'admin' and password == 'admin123':
        return jsonify({
            'success': True,
            'token': 'fake-jwt-token-admin',
            'user': {'id': 1, 'username': 'admin', 'role': 'admin'}
        })
    
    return jsonify({
        'success': False,
        'error': 'Invalid credentials'
    }), 401


@app.route('/api/echo', methods=['POST'])
def echo():
    data = request.get_json(silent=True) or {}
    
    response_data = {
        'echo': data,
        'success': True
    }
    
    if data.get('xss'):
        response_data['reflected'] = f"Received: {data['xss']}"
    
    return jsonify(response_data)


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found', 'success': False}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error', 'success': False}), 500


if __name__ == '__main__':
    print("Starting mock API server on http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=False)
