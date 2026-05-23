from flask import Flask, render_template, request, jsonify, send_file
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import StringType
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import numpy as np
from io import StringIO, BytesIO

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_ROOT, 'classification_rules.json')
DATA_DIR = os.path.join(APP_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

spark = None
user_segments_cache = None
monthly_trends_cache = None


def get_spark():
    global spark
    if spark is None:
        spark = SparkSession.builder \
            .appName("UserProfileWeb") \
            .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
            .config("spark.driver.host", "127.0.0.1") \
            .config("spark.sql.adaptive.enabled", "true") \
            .enableHiveSupport() \
            .getOrCreate()
    return spark


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def generate_mock_data(spark, num_users=5000):
    np.random.seed(42)
    user_ids = [f"user_{i:06d}" for i in range(1, num_users + 1)]
    categories = ['电子产品', '服装鞋帽', '食品饮料', '家居用品', '美妆护肤', '母婴用品', '运动户外']
    
    config = load_config()
    analysis_date = datetime.strptime(config['analysis_config']['analysis_date'], '%Y-%m-%d')
    
    orders = []
    for user_id in user_ids:
        user_type = np.random.choice(['high', 'growth', 'sleep', 'churn'], p=[0.15, 0.35, 0.25, 0.25])
        
        if user_type == 'high':
            num_orders = np.random.randint(20, 80)
            avg_amount = np.random.uniform(500, 2000)
        elif user_type == 'growth':
            num_orders = np.random.randint(5, 30)
            avg_amount = np.random.uniform(200, 800)
        elif user_type == 'sleep':
            num_orders = np.random.randint(3, 15)
            avg_amount = np.random.uniform(100, 500)
        else:
            num_orders = np.random.randint(1, 8)
            avg_amount = np.random.uniform(50, 300)
        
        for _ in range(num_orders):
            days_ago = np.random.randint(0, 365)
            order_date = analysis_date - timedelta(days=days_ago)
            category = np.random.choice(categories)
            amount = np.random.uniform(avg_amount * 0.5, avg_amount * 1.5)
            
            orders.append({
                'user_id': user_id,
                'order_id': f"order_{np.random.randint(1000000, 9999999)}",
                'order_date': order_date.strftime('%Y-%m-%d'),
                'category': category,
                'amount': round(amount, 2),
                'quantity': np.random.randint(1, 5)
            })
    
    return spark.createDataFrame(pd.DataFrame(orders))


def create_segmentation_udf(segments_config):
    def classify_user(recency, activity, consumption):
        recency_val = recency if recency and recency > 0 else 365
        activity_val = activity if activity else 0
        consumption_val = consumption if consumption else 0
        
        sorted_segments = sorted(segments_config, key=lambda x: x['priority'])
        
        for seg in sorted_segments:
            cond = seg['conditions']
            match = True
            
            if 'recency_max' in cond and recency_val > cond['recency_max']:
                match = False
            if 'recency_min' in cond and recency_val < cond['recency_min']:
                match = False
            if 'consumption_min' in cond and consumption_val < cond['consumption_min']:
                match = False
            if 'activity_min' in cond and activity_val < cond['activity_min']:
                match = False
            
            if match:
                return seg['name']
        return '未知用户'
    
    return F.udf(classify_user, StringType())


def calculate_user_profile(orders_df, config):
    analysis_date_str = config['analysis_config']['analysis_date']
    preference_days = config['analysis_config']['preference_days']
    weights = config['weights']
    num_partitions = config['analysis_config']['num_partitions']
    
    orders_df = orders_df.repartition(num_partitions, 'user_id').cache()
    
    order_activity = orders_df.groupBy('user_id').agg(
        F.count('order_id').alias('order_count'),
        F.sum('amount').alias('total_amount'),
        F.max('order_date').alias('last_order_date'),
        F.datediff(F.lit(analysis_date_str), F.max('order_date')).alias('days_since_last_order')
    )
    
    user_activity = order_activity.withColumn(
        'activity_score',
        F.log1p(F.col('order_count') * weights['order_count_weight'])
    ).withColumn(
        'recency_score',
        F.col('days_since_last_order')
    )
    
    order_stats = orders_df.groupBy('user_id').agg(
        F.sum('amount').alias('total_spend'),
        F.avg('amount').alias('avg_order_value'),
        F.countDistinct(F.date_format('order_date', 'yyyy-MM')).alias('active_months'),
        F.sum('quantity').alias('total_quantity')
    )
    
    order_stats = order_stats.withColumn(
        'consumption_score',
        F.log1p(F.col('total_spend')) * F.col('active_months') / 12
    )
    
    analysis_date = datetime.strptime(analysis_date_str, '%Y-%m-%d')
    cutoff_date = analysis_date - timedelta(days=preference_days)
    recent_orders = orders_df.filter(F.col('order_date') >= cutoff_date.strftime('%Y-%m-%d'))
    
    category_pref = recent_orders.groupBy('user_id', 'category').agg(
        F.sum('amount').alias('category_spend'),
        F.count('order_id').alias('category_orders')
    ).withColumn(
        'preference_score',
        F.col('category_orders') * 0.5 + F.log1p(F.col('category_spend')) * 0.5
    )
    
    window_spec = Window.partitionBy('user_id').orderBy(F.desc('preference_score'))
    user_preference = category_pref.withColumn('rank', F.rank().over(window_spec)) \
        .filter(F.col('rank') == 1) \
        .select('user_id', F.col('category').alias('preferred_category'))
    
    category_avg_price = orders_df.groupBy('category').agg(F.avg('amount').alias('category_avg_price'))
    broadcast_category_price = F.broadcast(category_avg_price)
    
    user_price_behavior = orders_df.join(broadcast_category_price, 'category') \
        .withColumn('price_ratio', F.col('amount') / F.col('category_avg_price')) \
        .groupBy('user_id').agg(F.avg('price_ratio').alias('avg_price_ratio'))
    
    price_levels = config['price_sensitivity']['levels']
    price_sensitivity_expr = F.when(F.col('avg_price_ratio') < price_levels[0]['max_ratio'], price_levels[0]['score'])
    for level in price_levels[1:-1]:
        price_sensitivity_expr = price_sensitivity_expr.when(
            F.col('avg_price_ratio') < level['max_ratio'], level['score']
        )
    price_sensitivity_expr = price_sensitivity_expr.otherwise(price_levels[-1]['score'])
    
    user_price_behavior = user_price_behavior.withColumn('price_sensitivity', price_sensitivity_expr)
    
    user_features = user_activity.join(order_stats, 'user_id', 'outer') \
        .join(user_preference, 'user_id', 'outer') \
        .join(user_price_behavior, 'user_id', 'outer') \
        .fillna(0)
    
    segment_udf = create_segmentation_udf(config['segments'])
    user_segments = user_features.withColumn(
        'segment',
        segment_udf(F.col('recency_score'), F.col('activity_score'), F.col('consumption_score'))
    ).cache()
    
    return user_segments


def calculate_monthly_trends(orders_df, config):
    analysis_date_str = config['analysis_config']['analysis_date']
    analysis_date = datetime.strptime(analysis_date_str, '%Y-%m-%d')
    
    monthly_data = []
    segments_config = config['segments']
    segment_udf = create_segmentation_udf(segments_config)
    
    for month_offset in range(11, -1, -1):
        month_end = analysis_date - timedelta(days=month_offset * 30)
        month_end_str = month_end.strftime('%Y-%m-%d')
        month_label = month_end.strftime('%Y-%m')
        
        month_orders = orders_df.filter(F.col('order_date') <= month_end_str)
        
        order_activity = month_orders.groupBy('user_id').agg(
            F.count('order_id').alias('order_count'),
            F.sum('amount').alias('total_amount'),
            F.datediff(F.lit(month_end_str), F.max('order_date')).alias('days_since_last_order')
        )
        
        user_activity = order_activity.withColumn(
            'activity_score',
            F.log1p(F.col('order_count') * 10)
        ).withColumn('recency_score', F.col('days_since_last_order'))
        
        order_stats = month_orders.groupBy('user_id').agg(
            F.sum('amount').alias('total_spend'),
            F.countDistinct(F.date_format('order_date', 'yyyy-MM')).alias('active_months')
        ).withColumn(
            'consumption_score',
            F.log1p(F.col('total_spend')) * F.col('active_months') / 12
        )
        
        user_features = user_activity.join(order_stats, 'user_id', 'outer').fillna(0)
        user_segments = user_features.withColumn(
            'segment',
            segment_udf(F.col('recency_score'), F.col('activity_score'), F.col('consumption_score'))
        )
        
        segment_counts = user_segments.groupBy('segment').count().collect()
        month_data = {'month': month_label}
        for row in segment_counts:
            month_data[row['segment']] = row['count']
        monthly_data.append(month_data)
    
    return pd.DataFrame(monthly_data).fillna(0)


@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', 
                         config=config,
                         business_events=get_business_events())


@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())


@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        new_config = request.json
        save_config(new_config)
        global user_segments_cache, monthly_trends_cache
        user_segments_cache = None
        monthly_trends_cache = None
        return jsonify({'success': True, 'message': '配置已更新'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/recalculate', methods=['POST'])
def recalculate():
    try:
        spark = get_spark()
        config = load_config()
        
        orders_df = generate_mock_data(spark)
        
        global user_segments_cache, monthly_trends_cache
        user_segments_cache = calculate_user_profile(orders_df, config)
        monthly_trends_cache = calculate_monthly_trends(orders_df, config)
        
        segment_counts = user_segments_cache.groupBy('segment').count().toPandas()
        
        return jsonify({
            'success': True,
            'segment_counts': segment_counts.to_dict('records'),
            'total_users': int(user_segments_cache.count())
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/trends')
def get_trends():
    try:
        spark = get_spark()
        config = load_config()
        orders_df = generate_mock_data(spark)
        trends_df = calculate_monthly_trends(orders_df, config)
        
        return jsonify({
            'success': True,
            'trends': trends_df.to_dict('records'),
            'business_events': get_business_events()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/users')
def get_users():
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        segment = request.args.get('segment', '')
        min_activity = float(request.args.get('min_activity', 0))
        max_activity = float(request.args.get('max_activity', 999))
        min_spend = float(request.args.get('min_spend', 0))
        
        spark = get_spark()
        config = load_config()
        orders_df = generate_mock_data(spark)
        user_segments = calculate_user_profile(orders_df, config)
        
        query = user_segments
        if segment:
            query = query.filter(F.col('segment') == segment)
        if min_activity > 0:
            query = query.filter(F.col('activity_score') >= min_activity)
        if max_activity < 999:
            query = query.filter(F.col('activity_score') <= max_activity)
        if min_spend > 0:
            query = query.filter(F.col('total_spend') >= min_spend)
        
        total = query.count()
        users_df = query.orderBy(F.desc('total_spend')) \
            .limit(page_size).offset((page - 1) * page_size) \
            .toPandas()
        
        return jsonify({
            'success': True,
            'users': users_df.fillna('').to_dict('records'),
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/export')
def export_users():
    try:
        segment = request.args.get('segment', '')
        min_activity = float(request.args.get('min_activity', 0))
        min_spend = float(request.args.get('min_spend', 0))
        
        spark = get_spark()
        config = load_config()
        orders_df = generate_mock_data(spark)
        user_segments = calculate_user_profile(orders_df, config)
        
        query = user_segments
        if segment:
            query = query.filter(F.col('segment') == segment)
        if min_activity > 0:
            query = query.filter(F.col('activity_score') >= min_activity)
        if min_spend > 0:
            query = query.filter(F.col('total_spend') >= min_spend)
        
        users_df = query.select(
            'user_id', 'segment', 'total_spend', 'order_count', 
            'activity_score', 'recency_score', 'preferred_category',
            'price_sensitivity', 'last_order_date'
        ).toPandas()
        
        output = StringIO()
        users_df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        
        filename = f"user_profile_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        mem_output = BytesIO()
        mem_output.write(output.getvalue().encode('utf-8-sig'))
        mem_output.seek(0)
        
        return send_file(
            mem_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


def get_business_events():
    return [
        {'date': '2024-06', 'name': '618大促', 'impact': '高'},
        {'date': '2024-09', 'name': '周年庆', 'impact': '中'},
        {'date': '2024-11', 'name': '双11狂欢', 'impact': '高'},
        {'date': '2024-12', 'name': '双12+年终', 'impact': '中'},
        {'date': '2025-01', 'name': '年货节', 'impact': '高'}
    ]


@app.route('/api/overview')
def get_overview():
    try:
        spark = get_spark()
        config = load_config()
        orders_df = generate_mock_data(spark)
        user_segments = calculate_user_profile(orders_df, config)
        
        segment_stats = user_segments.groupBy('segment').agg(
            F.count('user_id').alias('user_count'),
            F.round(F.avg('total_spend'), 2).alias('avg_total_spend'),
            F.round(F.avg('order_count'), 2).alias('avg_order_count'),
            F.round(F.avg('activity_score'), 2).alias('avg_activity_score'),
            F.round(F.avg('recency_score'), 1).alias('avg_recency_days')
        ).toPandas()
        
        segment_order = ['高价值用户', '成长用户', '沉睡用户', '流失用户']
        segment_stats['segment'] = pd.Categorical(
            segment_stats['segment'], 
            categories=segment_order, 
            ordered=True
        )
        segment_stats = segment_stats.sort_values('segment').reset_index(drop=True)
        
        return jsonify({
            'success': True,
            'stats': segment_stats.fillna(0).to_dict('records'),
            'total_users': int(user_segments.count())
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
