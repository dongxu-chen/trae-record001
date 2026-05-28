"""
Flask Web应用
提供价格监控的可视化界面、API接口、报表导出
"""
import io
import json
from datetime import datetime, timedelta
from collections import defaultdict

from flask import (
    Flask, render_template, request, jsonify,
    send_file, redirect, url_for, flash,
)
from flask_cors import CORS
from loguru import logger

from config import FLASK_CONFIG, SPIDER_CONFIG, ALERT_CONFIG, ANALYSIS_CONFIG
from database.models import (
    Product, PriceHistory, Alert, Promotion,
    PricePrediction, CrossPromotion, ComplianceCheck,
)
from database.mongo import get_db
from report.exporter import ReportExporter
from alerts.notifier import get_notifier
from proxy_pool.pool import get_proxy_pool
from analysis.price_predictor import get_predictor
from analysis.cross_promo import get_cross_promo_detector
from analysis.fraud_detector import get_fraud_detector


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = FLASK_CONFIG.get('secret_key', 'dev-secret')
    CORS(app)

    @app.route('/')
    def index():
        db = get_db()
        products_count = db['products'].count_documents({})
        alerts_count = db['alerts'].count_documents({'status': 'unread'})
        promotions_count = db['promotions'].count_documents({'active': True})
        price_records = db['price_history'].count_documents({})

        recent_alerts = list(
            db['alerts'].find({}).sort('created_at', -1).limit(10)
        )
        for a in recent_alerts:
            a['_id'] = str(a['_id'])

        sources = db['products'].distinct('source')

        return render_template(
            'index.html',
            products_count=products_count,
            alerts_count=alerts_count,
            promotions_count=promotions_count,
            price_records=price_records,
            recent_alerts=recent_alerts,
            sources=sources,
        )

    @app.route('/products')
    def products():
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        source = request.args.get('source', '').strip() or None
        category = request.args.get('category', '').strip() or None
        search = request.args.get('search', '').strip()

        query = {}
        if source:
            query['source'] = source
        if category:
            query['category'] = category
        if search:
            query['$or'] = [
                {'name': {'$regex': search, '$options': 'i'}},
                {'brand': {'$regex': search, '$options': 'i'}},
                {'product_id': {'$regex': search, '$options': 'i'}},
            ]

        skip = (page - 1) * page_size
        db = get_db()
        cursor = db['products'].find(query).sort('updated_at', -1).skip(skip).limit(page_size)
        products_list = list(cursor)
        total = db['products'].count_documents(query)

        for p in products_list:
            p['_id'] = str(p['_id'])

        sources = db['products'].distinct('source')

        return render_template(
            'products.html',
            products=products_list,
            total=total,
            page=page,
            page_size=page_size,
            source=source,
            category=category,
            search=search,
            sources=sources,
            total_pages=(total + page_size - 1) // page_size,
        )

    @app.route('/product/<product_id>')
    def product_detail(product_id):
        product = Product.get_by_id(product_id)
        if not product:
            flash('商品未找到', 'error')
            return redirect(url_for('products'))

        product['_id'] = str(product['_id'])

        history = PriceHistory.get_history(product_id)
        history_data = []
        for h in history:
            history_data.append({
                'timestamp': h['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(h['timestamp'], datetime) else str(h['timestamp']),
                'price': h.get('price'),
                'original_price': h.get('original_price'),
                'in_stock': h.get('in_stock'),
                'is_on_promotion': h.get('is_on_promotion'),
            })

        return render_template(
            'product_detail.html',
            product=product,
            history_data=history_data,
        )

    @app.route('/api/price_history/<product_id>')
    def api_price_history(product_id):
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        history = PriceHistory.get_history(product_id, start_date=start_date)

        data = []
        for h in history:
            data.append({
                'timestamp': h['timestamp'].isoformat() if isinstance(h['timestamp'], datetime) else str(h['timestamp']),
                'price': h.get('price'),
                'original_price': h.get('original_price'),
                'in_stock': h.get('in_stock'),
                'is_on_promotion': h.get('is_on_promotion'),
            })

        return jsonify({
            'product_id': product_id,
            'data': data,
        })

    @app.route('/alerts')
    def alerts():
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        alert_type = request.args.get('alert_type', '').strip() or None
        status = request.args.get('status', '').strip() or None

        alerts_list, total = Alert.get_alerts(
            alert_type=alert_type, status=status,
            page=page, page_size=page_size,
        )
        for a in alerts_list:
            a['_id'] = str(a['_id'])

        return render_template(
            'alerts.html',
            alerts=alerts_list,
            total=total,
            page=page,
            page_size=page_size,
            alert_type=alert_type,
            status=status,
            total_pages=(total + page_size - 1) // page_size,
        )

    @app.route('/api/alerts/<alert_id>/read', methods=['POST'])
    def api_mark_alert_read(alert_id):
        from bson import ObjectId
        Alert.mark_as_read(ObjectId(alert_id))
        return jsonify({'status': 'success'})

    @app.route('/api/alerts/send_test', methods=['POST'])
    def api_send_test_alert():
        notifier = get_notifier()
        test_alert = {
            'alert_type': 'price_drop',
            'product_id': 'test_001',
            'product_name': '测试商品',
            'source': 'test',
            'old_price': 100.0,
            'new_price': 80.0,
            'change_ratio': -0.2,
            'message': '这是一条测试告警',
        }
        results = notifier.send_alert(test_alert)
        return jsonify({'status': 'success', 'results': results})

    @app.route('/promotions')
    def promotions():
        db = get_db()
        promotions_list = list(db['promotions'].find({'active': True}).sort('start_date', -1))
        for p in promotions_list:
            p['_id'] = str(p['_id'])

        return render_template('promotions.html', promotions=promotions_list)

    @app.route('/export/products')
    def export_products():
        source = request.args.get('source', '').strip() or None
        format_type = request.args.get('format', 'xlsx')
        result = ReportExporter.export_products(source=source, format=format_type)
        if result:
            return send_file(
                io.BytesIO(result['content']),
                mimetype=result['mimetype'],
                as_attachment=True,
                download_name=result['filename'],
            )
        flash('没有可导出的数据', 'warning')
        return redirect(url_for('products'))

    @app.route('/export/price_history/<product_id>')
    def export_price_history(product_id):
        format_type = request.args.get('format', 'xlsx')
        result = ReportExporter.export_price_history(product_id, format=format_type)
        if result:
            return send_file(
                io.BytesIO(result['content']),
                mimetype=result['mimetype'],
                as_attachment=True,
                download_name=result['filename'],
            )
        flash('没有可导出的数据', 'warning')
        return redirect(url_for('product_detail', product_id=product_id))

    @app.route('/export/alerts')
    def export_alerts():
        alert_type = request.args.get('alert_type', '').strip() or None
        format_type = request.args.get('format', 'xlsx')
        result = ReportExporter.export_alerts(alert_type=alert_type, format=format_type)
        if result:
            return send_file(
                io.BytesIO(result['content']),
                mimetype=result['mimetype'],
                as_attachment=True,
                download_name=result['filename'],
            )
        flash('没有可导出的数据', 'warning')
        return redirect(url_for('alerts'))

    @app.route('/export/promotions')
    def export_promotions():
        source = request.args.get('source', '').strip() or None
        format_type = request.args.get('format', 'xlsx')
        result = ReportExporter.export_promotions(source=source, format=format_type)
        if result:
            return send_file(
                io.BytesIO(result['content']),
                mimetype=result['mimetype'],
                as_attachment=True,
                download_name=result['filename'],
            )
        flash('没有可导出的数据', 'warning')
        return redirect(url_for('promotions'))

    @app.route('/api/summary')
    def api_summary():
        db = get_db()
        products_count = db['products'].count_documents({})
        alerts_count = db['alerts'].count_documents({'status': 'unread'})
        promotions_count = db['promotions'].count_documents({'active': True})

        price_trend = list(
            db['price_history'].aggregate([
                {
                    '$group': {
                        '_id': {
                            '$dateToString': {
                                'format': '%Y-%m-%d',
                                'date': '$timestamp',
                            }
                        },
                        'avg_price': {'$avg': '$price'},
                        'count': {'$sum': 1},
                    }
                },
                {'$sort': {'_id': -1}},
                {'$limit': 30},
            ])
        )

        return jsonify({
            'products_count': products_count,
            'alerts_count': alerts_count,
            'promotions_count': promotions_count,
            'price_trend': price_trend,
        })

    @app.route('/api/price_comparison')
    def api_price_comparison():
        db = get_db()
        products = list(db['products'].find({}, {'name': 1, 'source': 1, 'current_price': 1, 'brand': 1}))

        grouped = defaultdict(list)
        for p in products:
            key = p.get('name', 'unknown')
            grouped[key].append({
                'source': p.get('source', ''),
                'price': p.get('current_price'),
            })

        comparison = []
        for name, sources in grouped.items():
            prices = [s['price'] for s in sources if s.get('price') is not None]
            if prices:
                comparison.append({
                    'name': name,
                    'sources': sources,
                    'lowest': min(prices),
                    'highest': max(prices),
                    'average': sum(prices) / len(prices),
                })

        return jsonify({'comparison': comparison[:50]})

    @app.route('/predictions')
    def predictions():
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        alert_level = request.args.get('alert_level', '').strip() or None
        db = get_db()
        query = {}
        if alert_level:
            query['alert_level'] = alert_level
        skip = (page - 1) * page_size
        cursor = db['price_predictions'].find(query).sort('created_at', -1).skip(skip).limit(page_size)
        predictions_list = list(cursor)
        total = db['price_predictions'].count_documents(query)
        for p in predictions_list:
            p['_id'] = str(p['_id'])
        return render_template(
            'predictions.html',
            predictions=predictions_list,
            total=total,
            page=page,
            page_size=page_size,
            alert_level=alert_level,
            total_pages=(total + page_size - 1) // page_size,
        )

    @app.route('/api/predictions/<product_id>')
    def api_prediction_detail(product_id):
        prediction = PricePrediction.get_latest(product_id)
        if prediction:
            prediction['_id'] = str(prediction['_id'])
            return jsonify(prediction)
        return jsonify({'error': 'not found'}), 404

    @app.route('/cross_promotions')
    def cross_promotions():
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        db = get_db()
        skip = (page - 1) * page_size
        cursor = db['cross_promotions'].find({}).sort('created_at', -1).skip(skip).limit(page_size)
        promos = list(cursor)
        total = db['cross_promotions'].count_documents({})
        for p in promos:
            p['_id'] = str(p['_id'])
        return render_template(
            'cross_promotions.html',
            promotions=promos,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    @app.route('/compliance')
    def compliance():
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        risk_level = request.args.get('risk_level', '').strip() or None
        db = get_db()
        query = {}
        if risk_level:
            query['compliance_level'] = risk_level
        skip = (page - 1) * page_size
        cursor = db['compliance_checks'].find(query).sort('created_at', -1).skip(skip).limit(page_size)
        checks = list(cursor)
        total = db['compliance_checks'].count_documents(query)
        for c in checks:
            c['_id'] = str(c['_id'])
        return render_template(
            'compliance.html',
            checks=checks,
            total=total,
            page=page,
            page_size=page_size,
            risk_level=risk_level,
            total_pages=(total + page_size - 1) // page_size,
        )

    @app.route('/api/compliance/<product_id>')
    def api_compliance_detail(product_id):
        check = ComplianceCheck.get_latest(product_id)
        if check:
            check['_id'] = str(check['_id'])
            return jsonify(check)
        return jsonify({'error': 'not found'}), 404

    @app.route('/settings')
    def settings():
        return render_template(
            'settings.html',
            spider_config=SPIDER_CONFIG,
            alert_config=ALERT_CONFIG,
            analysis_config=ANALYSIS_CONFIG,
        )

    @app.route('/api/proxy_status')
    def api_proxy_status():
        pool = get_proxy_pool()
        return jsonify(pool.status())

    @app.route('/api/proxy/refresh', methods=['POST'])
    def api_proxy_refresh():
        pool = get_proxy_pool()
        pool.refresh(force=True)
        return jsonify({'status': 'success', 'pool_size': pool.size})

    @app.route('/api/proxy/health_check', methods=['POST'])
    def api_proxy_health_check():
        pool = get_proxy_pool()
        before_size = pool.size
        pool.active_health_check()
        after_size = pool.size
        return jsonify({
            'status': 'success',
            'removed': before_size - after_size,
            'remaining': after_size,
        })

    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.utcnow(),
            'spider_config': SPIDER_CONFIG,
        }

    return app


app = create_app()