from datetime import datetime, timedelta
from collections import Counter
from flask import Flask, request, jsonify, redirect, abort, make_response, send_file
from flask_apscheduler import APScheduler
from config import config
from models import db, ShortURL, VisitLog
from utils import generate_secure_short_code, is_valid_url, get_client_ip, parse_user_agent, generate_qrcode, generate_csv


def cleanup_expired_urls(app):
    with app.app_context():
        now = datetime.utcnow()
        expired = ShortURL.query.filter(
            ShortURL.expires_at.isnot(None),
            ShortURL.expires_at < now,
            ShortURL.is_active == True
        ).all()
        for url in expired:
            url.is_active = False
        if expired:
            db.session.commit()
            app.logger.info(f'Cleaned up {len(expired)} expired short URLs')


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    with app.app_context():
        db.create_all()

    if not scheduler.get_job('cleanup_expired_urls'):
        scheduler.add_job(
            id='cleanup_expired_urls',
            func=cleanup_expired_urls,
            args=[app],
            trigger='interval',
            hours=app.config['CLEANUP_INTERVAL_HOURS'],
            next_run_time=datetime.utcnow() + timedelta(minutes=5)
        )

    def check_password_auth(short_code):
        cookie_name = f'url_auth_{short_code}'
        if request.cookies.get(cookie_name) == 'authorized':
            return True
        return False

    def set_password_auth_cookie(response, short_code):
        response.set_cookie(
            f'url_auth_{short_code}',
            'authorized',
            max_age=60*60*24*7,
            httponly=True,
            secure=not app.debug
        )
        return response

    @app.route('/api/shorten', methods=['POST'])
    def create_short_url():
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400

        original_url = data['url'].strip()

        if not is_valid_url(original_url):
            return jsonify({'error': 'Invalid URL format'}), 400

        expiry_days = data.get('expiry_days', app.config['DEFAULT_EXPIRY_DAYS'])
        try:
            expiry_days = int(expiry_days)
            if expiry_days < 0:
                expiry_days = 0
            elif expiry_days > app.config['MAX_EXPIRY_DAYS']:
                expiry_days = app.config['MAX_EXPIRY_DAYS']
        except (ValueError, TypeError):
            expiry_days = app.config['DEFAULT_EXPIRY_DAYS']

        expires_at = None
        if expiry_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=expiry_days)

        password = data.get('password')

        short_code_length = app.config['SHORT_CODE_LENGTH']
        max_attempts = app.config['MAX_SHORT_CODE_ATTEMPTS']
        short_code = None

        for attempt in range(max_attempts):
            candidate = generate_secure_short_code(short_code_length + attempt // 3)
            if not ShortURL.query.filter_by(short_code=candidate).first():
                short_code = candidate
                break

        if short_code is None:
            return jsonify({'error': 'Failed to generate unique short code'}), 500

        new_url = ShortURL(
            original_url=original_url,
            short_code=short_code,
            expires_at=expires_at
        )
        new_url.set_password(password)

        db.session.add(new_url)
        db.session.commit()

        short_url_full = f'{request.host_url}{new_url.short_code}'

        return jsonify({
            'original_url': new_url.original_url,
            'short_code': new_url.short_code,
            'short_url': short_url_full,
            'qr_url': f'{request.host_url}api/qrcode/{new_url.short_code}',
            'has_password': new_url.has_password,
            'expires_at': new_url.expires_at.isoformat() if new_url.expires_at else None,
            'access_count': new_url.access_count,
            'created_at': new_url.created_at.isoformat()
        }), 201

    @app.route('/api/shorten/batch', methods=['POST'])
    def batch_create_short_url():
        data = request.get_json()

        if not data or 'urls' not in data or not isinstance(data['urls'], list):
            return jsonify({'error': 'URLs array is required'}), 400

        if len(data['urls']) > 100:
            return jsonify({'error': 'Maximum 100 URLs per batch'}), 400

        expiry_days = data.get('expiry_days', app.config['DEFAULT_EXPIRY_DAYS'])
        try:
            expiry_days = int(expiry_days)
            if expiry_days < 0:
                expiry_days = 0
            elif expiry_days > app.config['MAX_EXPIRY_DAYS']:
                expiry_days = app.config['MAX_EXPIRY_DAYS']
        except (ValueError, TypeError):
            expiry_days = app.config['DEFAULT_EXPIRY_DAYS']

        expires_at = None
        if expiry_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=expiry_days)

        password = data.get('password')
        results = []
        short_code_length = app.config['SHORT_CODE_LENGTH']
        max_attempts = app.config['MAX_SHORT_CODE_ATTEMPTS']

        for url_data in data['urls']:
            if isinstance(url_data, str):
                original_url = url_data.strip()
            elif isinstance(url_data, dict) and 'url' in url_data:
                original_url = url_data['url'].strip()
            else:
                results.append({'error': 'Invalid URL entry', 'success': False})
                continue

            if not is_valid_url(original_url):
                results.append({'error': f'Invalid URL: {original_url}', 'success': False})
                continue

            short_code = None
            for attempt in range(max_attempts):
                candidate = generate_secure_short_code(short_code_length + attempt // 3)
                if not ShortURL.query.filter_by(short_code=candidate).first():
                    short_code = candidate
                    break

            if short_code is None:
                results.append({'error': 'Failed to generate unique short code', 'success': False})
                continue

            new_url = ShortURL(
                original_url=original_url,
                short_code=short_code,
                expires_at=expires_at
            )
            new_url.set_password(password)
            db.session.add(new_url)

            short_url_full = f'{request.host_url}{new_url.short_code}'
            results.append({
                'original_url': new_url.original_url,
                'short_code': new_url.short_code,
                'short_url': short_url_full,
                'qr_url': f'{request.host_url}api/qrcode/{new_url.short_code}',
                'has_password': new_url.has_password,
                'success': True
            })

        db.session.commit()

        return jsonify({
            'total': len(results),
            'success': sum(1 for r in results if r.get('success')),
            'results': results
        }), 201

    @app.route('/api/export/csv', methods=['GET'])
    def export_csv():
        short_urls = ShortURL.query.order_by(ShortURL.created_at.desc()).all()
        csv_output = generate_csv(short_urls)
        output = make_response(csv_output.getvalue())
        output.headers['Content-Disposition'] = 'attachment; filename=short_urls.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

    @app.route('/api/qrcode/<short_code>')
    def get_qrcode(short_code):
        short_url = ShortURL.query.filter_by(short_code=short_code, is_active=True).first()
        if not short_url:
            abort(404)

        size = request.args.get('size', default=10, type=int)
        size = max(1, min(50, size))

        short_url_full = f'{request.host_url}{short_code}'
        qr_image = generate_qrcode(short_url_full, size=size)
        return send_file(qr_image, mimetype='image/png')

    @app.route('/<short_code>/verify', methods=['POST'])
    def verify_password(short_code):
        short_url = ShortURL.query.filter_by(short_code=short_code, is_active=True).first()

        if not short_url:
            abort(404)

        if short_url.is_expired():
            abort(410)

        if not short_url.has_password:
            return redirect(f'/{short_code}', code=302)

        data = request.get_json() or request.form
        password = data.get('password', '')

        if short_url.check_password(password):
            response = jsonify({
                'success': True,
                'redirect_url': f'/{short_code}'
            })
            return set_password_auth_cookie(response, short_code)
        else:
            return jsonify({'success': False, 'error': 'Incorrect password'}), 401

    @app.route('/<short_code>')
    def redirect_to_original(short_code):
        short_url = ShortURL.query.filter_by(short_code=short_code, is_active=True).first()

        if not short_url:
            abort(404)

        if short_url.is_expired():
            abort(410)

        if short_url.has_password and not check_password_auth(short_code):
            return jsonify({
                'error': 'Password required',
                'verify_url': f'/{short_code}/verify',
                'message': 'POST password to verify endpoint to access this URL'
            }), 403

        client_ip = get_client_ip(request)
        user_agent = request.user_agent.string
        referrer = request.referrer

        visit = VisitLog(
            short_url_id=short_url.id,
            ip_address=client_ip,
            user_agent=user_agent,
            referrer=referrer
        )
        db.session.add(visit)

        short_url.increment_access()

        return redirect(short_url.original_url, code=302)

    @app.route('/api/stats/<short_code>')
    def get_stats(short_code):
        short_url = ShortURL.query.filter_by(short_code=short_code).first()

        if not short_url:
            return jsonify({'error': 'Short URL not found'}), 404

        visits = VisitLog.query.filter_by(short_url_id=short_url.id).order_by(VisitLog.visited_at.desc()).limit(50).all()

        ua_list = []
        browser_list = []
        os_list = []
        device_list = []
        referrer_list = []
        ip_list = []

        for visit in visits:
            if visit.user_agent:
                ua_info = parse_user_agent(visit.user_agent)
                ua_list.append(visit.user_agent)
                browser_list.append(ua_info['browser'])
                os_list.append(ua_info['os'])
                device_list.append(ua_info['device'])
            if visit.referrer:
                referrer_list.append(visit.referrer)
            if visit.ip_address:
                ip_list.append(visit.ip_address)

        return jsonify({
            'short_url': short_url.to_dict(),
            'summary': {
                'total_visits': short_url.access_count,
                'unique_ips': len(set(ip_list)),
                'unique_referrers': len(set(referrer_list))
            },
            'user_agent_stats': {
                'browsers': dict(Counter(browser_list).most_common(10)),
                'operating_systems': dict(Counter(os_list).most_common(10)),
                'devices': dict(Counter(device_list).most_common(10))
            },
            'referrer_stats': {
                'top_referrers': dict(Counter(referrer_list).most_common(10)),
                'direct_visits': len([r for r in referrer_list if r is None])
            },
            'recent_visits': [v.to_dict() for v in visits[:10]]
        })

    @app.route('/api/admin/cleanup', methods=['POST'])
    def manual_cleanup():
        cleanup_expired_urls(app)
        return jsonify({'message': 'Cleanup triggered'}), 200

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(410)
    def gone(error):
        return jsonify({'error': 'This short URL has expired'}), 410

    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000)
