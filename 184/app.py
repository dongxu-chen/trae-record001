import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
import data_processor as dp
from aspect_extractor import full_analysis
from config import PRODUCT_CATEGORIES, CSV_PATH
from data_generator import generate_comments, save_comments_to_csv
from competitor_analyzer import analyze_competitor_comparison, get_aspect_comparison
from alert_system import get_alert_system
from reply_generator import generate_multiple_replies, generate_reply_by_issue

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)


def check_and_init_data():
    if os.path.exists(CSV_PATH):
        try:
            df = dp.load_all_comments()
            if len(df) > 0:
                print('数据已存在，跳过初始化')
                return True
        except Exception as e:
            pass
    
    print('正在生成初始数据...')
    comments = generate_comments(1000)
    save_comments_to_csv(comments, CSV_PATH)
    dp.import_csv_to_db(analyze=True)
    print('初始数据生成完成')
    return True


@app.route('/')
def index():
    return render_template('index.html', categories=PRODUCT_CATEGORIES)


@app.route('/api/overview')
def api_overview():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    
    df = dp.load_comments_from_db(start_date, end_date, category)
    stats = dp.get_sentiment_statistics(df)
    category_stats = dp.get_category_statistics(df)
    opinion_stats = dp.get_opinion_pairs_statistics(df) if 'opinion_pairs' in df.columns else {'top_targets': [], 'top_opinions': []}
    
    return jsonify({
        'statistics': stats,
        'category_stats': category_stats,
        'opinion_stats': opinion_stats
    })


@app.route('/api/trend')
def api_trend():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    
    df = dp.load_comments_from_db(start_date, end_date, category)
    trend = dp.get_sentiment_trend(df)
    
    return jsonify({'trend': trend})


@app.route('/api/aspects')
def api_aspects():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    
    df = dp.load_comments_from_db(start_date, end_date, category)
    aspects = dp.get_aspect_statistics(df)
    
    return jsonify({'aspects': aspects})


@app.route('/api/wordcloud')
def api_wordcloud():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    sentiment = request.args.get('sentiment', 'all')
    
    df = dp.load_comments_from_db(start_date, end_date, category)
    
    if sentiment == 'positive':
        words = dp.get_word_frequency(df, top_n=50, sentiment_filter='positive')
    elif sentiment == 'negative':
        words = dp.get_word_frequency(df, top_n=50, sentiment_filter='negative')
    else:
        words = dp.get_word_frequency(df, top_n=50)
    
    return jsonify({'words': words})


@app.route('/api/negative-words')
def api_negative_words():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    
    df = dp.load_comments_from_db(start_date, end_date, category)
    negative_words = dp.get_negative_words(df, top_n=20)
    
    return jsonify({'negative_words': negative_words})


@app.route('/api/comments')
def api_comments():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    sentiment = request.args.get('sentiment', 'all')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    
    df = dp.load_comments_from_db(start_date, end_date, category, sentiment)
    
    total = len(df)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    comments = df.iloc[start_idx:end_idx].to_dict('records')
    
    return jsonify({
        'total': total,
        'page': page,
        'page_size': page_size,
        'comments': comments
    })


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': '文本不能为空'}), 400
    
    result = full_analysis(text)
    return jsonify(result)


@app.route('/api/opinion-pairs')
def api_opinion_pairs():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    
    df = dp.load_comments_from_db(start_date, end_date, category)
    opinion_stats = dp.get_opinion_pairs_statistics(df) if 'opinion_pairs' in df.columns else {'top_targets': [], 'top_opinions': []}
    
    return jsonify(opinion_stats)


@app.route('/api/products')
def api_products():
    df = dp.load_all_comments()
    products = dp.get_all_products(df)
    return jsonify({'products': products})


@app.route('/api/competitor-comparison')
def api_competitor_comparison():
    product_name = request.args.get('product', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', 'all')
    
    df = dp.load_comments_from_db(start_date, end_date, category)
    
    if not product_name:
        products = dp.get_all_products(df)
        product_name = products[0] if products else ''
    
    comparison = analyze_competitor_comparison(product_name, df)
    aspect_comparison = get_aspect_comparison(product_name, df)
    
    return jsonify({
        'comparison': comparison,
        'aspect_comparison': aspect_comparison
    })


@app.route('/api/alerts')
def api_alerts():
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 20))
    
    alert_system = get_alert_system()
    alerts = alert_system.get_alerts(unread_only=unread_only, limit=limit)
    summary = alert_system.get_alert_summary()
    
    return jsonify({
        'alerts': alerts,
        'summary': summary
    })


@app.route('/api/alerts/check', methods=['POST'])
def api_check_alerts():
    df = dp.load_all_comments()
    alert_system = get_alert_system()
    alerts = alert_system.check_alerts(df)
    
    return jsonify({
        'success': True,
        'new_alerts': [a for a in alerts if a],
        'total_alerts': alert_system.get_alert_summary()
    })


@app.route('/api/alerts/read', methods=['POST'])
def api_mark_alert_read():
    data = request.get_json()
    alert_id = data.get('alert_id', '')
    mark_all = data.get('mark_all', False)
    
    alert_system = get_alert_system()
    
    if mark_all:
        alert_system.mark_all_as_read()
        return jsonify({'success': True, 'message': '全部标记为已读'})
    
    if alert_id:
        success = alert_system.mark_as_read(alert_id)
        return jsonify({'success': success, 'message': '已标记' if success else '未找到该预警'})
    
    return jsonify({'success': False, 'message': '缺少参数'}), 400


@app.route('/api/generate-reply', methods=['POST'])
def api_generate_reply():
    data = request.get_json()
    comment = data.get('comment', {})
    aspect = data.get('aspect', '')
    issue_text = data.get('issue_text', '')
    style = data.get('style', '')
    
    if aspect and issue_text:
        reply = generate_reply_by_issue(aspect, issue_text, style=style)
        return jsonify({
            'success': True,
            'reply': reply
        })
    
    if comment:
        replies = generate_multiple_replies(comment, count=3)
        return jsonify({
            'success': True,
            'replies': replies
        })
    
    return jsonify({'success': False, 'message': '缺少评论数据'}), 400


@app.route('/api/refresh-data')
def api_refresh_data():
    try:
        comments = generate_comments(1000)
        save_comments_to_csv(comments, CSV_PATH)
        dp.import_csv_to_db(analyze=True)
        
        df = dp.load_all_comments()
        alert_system = get_alert_system()
        alert_system.check_alerts(df)
        
        return jsonify({'success': True, 'message': '数据刷新成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    check_and_init_data()
    app.run(debug=True, host='0.0.0.0', port=5000)
