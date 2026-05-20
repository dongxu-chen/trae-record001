import sqlite3
import pandas as pd
import jieba
import json
import os
from collections import Counter
from datetime import datetime
from config import DB_PATH, CSV_PATH, ASPECTS, ASPECT_KEYWORDS, DATA_DIR

STOPWORDS_PATH = os.path.join(DATA_DIR, 'stopwords.txt')


def load_stopwords():
    stopwords = set()
    if os.path.exists(STOPWORDS_PATH):
        with open(STOPWORDS_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word:
                    stopwords.add(word)
    return stopwords


STOPWORDS = load_stopwords()


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        comment_id TEXT PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        comment_text TEXT,
        rating REAL,
        comment_time TEXT,
        user_name TEXT,
        sentiment_score REAL,
        sentiment_label TEXT,
        sentiment_label_cn TEXT,
        positive_prob REAL,
        negative_prob REAL,
        aspects TEXT,
        aspect_sentiments TEXT,
        opinion_pairs TEXT,
        model_used TEXT
    )
    ''')
    
    try:
        cursor.execute('ALTER TABLE comments ADD COLUMN positive_prob REAL')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE comments ADD COLUMN negative_prob REAL')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE comments ADD COLUMN opinion_pairs TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE comments ADD COLUMN model_used TEXT')
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()


def save_comments_to_db(comments):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for comment in comments:
        aspects_str = ','.join(comment.get('aspects', []))
        aspect_sentiments_str = json.dumps(comment.get('aspect_sentiments', {}), ensure_ascii=False)
        opinion_pairs_str = json.dumps(comment.get('opinion_pairs', []), ensure_ascii=False)
        
        cursor.execute('''
        INSERT OR REPLACE INTO comments 
        (comment_id, product_name, category, comment_text, rating, comment_time, 
         user_name, sentiment_score, sentiment_label, sentiment_label_cn, 
         positive_prob, negative_prob, aspects, aspect_sentiments, opinion_pairs, model_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comment['comment_id'],
            comment['product_name'],
            comment['category'],
            comment['comment_text'],
            comment['rating'],
            comment['comment_time'],
            comment['user_name'],
            comment['score'],
            comment['label'],
            comment['label_cn'],
            comment.get('positive_prob', 0.5),
            comment.get('negative_prob', 0.5),
            aspects_str,
            aspect_sentiments_str,
            opinion_pairs_str,
            comment.get('model_used', 'bert')
        ))
    
    conn.commit()
    conn.close()


def load_comments_from_db(start_date=None, end_date=None, category=None, sentiment_label=None):
    conn = sqlite3.connect(DB_PATH)
    query = 'SELECT * FROM comments WHERE 1=1'
    params = []
    
    if start_date:
        query += ' AND comment_time >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND comment_time <= ?'
        params.append(end_date + ' 23:59:59')
    if category and category != 'all':
        query += ' AND category = ?'
        params.append(category)
    if sentiment_label and sentiment_label != 'all':
        query += ' AND sentiment_label = ?'
        params.append(sentiment_label)
    
    query += ' ORDER BY comment_time DESC'
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df


def load_all_comments():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM comments ORDER BY comment_time DESC', conn)
    conn.close()
    return df


def get_sentiment_statistics(df):
    total = len(df)
    if total == 0:
        return {'positive': 0, 'neutral': 0, 'negative': 0, 'positive_rate': 0, 'avg_score': 0}
    
    positive = len(df[df['sentiment_label'] == 'positive'])
    neutral = len(df[df['sentiment_label'] == 'neutral'])
    negative = len(df[df['sentiment_label'] == 'negative'])
    
    return {
        'total': total,
        'positive': positive,
        'neutral': neutral,
        'negative': negative,
        'positive_rate': round(positive / total * 100, 2),
        'negative_rate': round(negative / total * 100, 2),
        'avg_score': round(df['sentiment_score'].mean(), 4),
        'avg_rating': round(df['rating'].mean(), 2)
    }


def get_sentiment_trend(df):
    if df.empty:
        return []
    
    df['date'] = pd.to_datetime(df['comment_time']).dt.strftime('%Y-%m-%d')
    
    trend_data = df.groupby('date').agg({
        'sentiment_score': 'mean',
        'comment_id': 'count'
    }).reset_index()
    
    trend_data.columns = ['date', 'avg_score', 'count']
    trend_data['avg_score'] = trend_data['avg_score'].round(4)
    
    return trend_data.to_dict('records')


def get_aspect_statistics(df):
    aspect_stats = {}
    
    for aspect in ASPECTS:
        aspect_comments = df[df['aspects'].str.contains(aspect, na=False)]
        if len(aspect_comments) == 0:
            aspect_stats[aspect] = {
                'count': 0,
                'positive': 0,
                'neutral': 0,
                'negative': 0,
                'avg_score': 0
            }
            continue
        
        positive = len(aspect_comments[aspect_comments['sentiment_label'] == 'positive'])
        neutral = len(aspect_comments[aspect_comments['sentiment_label'] == 'neutral'])
        negative = len(aspect_comments[aspect_comments['sentiment_label'] == 'negative'])
        
        aspect_stats[aspect] = {
            'count': len(aspect_comments),
            'positive': positive,
            'neutral': neutral,
            'negative': negative,
            'positive_rate': round(positive / len(aspect_comments) * 100, 2),
            'avg_score': round(aspect_comments['sentiment_score'].mean(), 4)
        }
    
    return aspect_stats


def get_word_frequency(df, top_n=50, sentiment_filter=None):
    if sentiment_filter:
        df = df[df['sentiment_label'] == sentiment_filter]
    
    all_words = []
    
    for text in df['comment_text']:
        words = jieba.lcut(text)
        for word in words:
            if len(word) > 1 and word not in STOPWORDS:
                all_words.append(word)
    
    word_counts = Counter(all_words)
    top_words = word_counts.most_common(top_n)
    
    return [{'word': w, 'count': c} for w, c in top_words]


def get_opinion_pairs_statistics(df):
    from ast import literal_eval
    
    all_pairs = []
    
    for pairs_str in df['opinion_pairs'].dropna():
        try:
            pairs = literal_eval(pairs_str)
            all_pairs.extend(pairs)
        except:
            try:
                pairs = json.loads(pairs_str.replace("'", '"'))
                all_pairs.extend(pairs)
            except:
                pass
    
    target_counter = Counter()
    opinion_counter = Counter()
    aspect_pair_counter = Counter()
    
    for pair in all_pairs:
        if isinstance(pair, dict):
            target_counter[pair.get('target', '')] += 1
            opinion_counter[pair.get('opinion', '')] += 1
            aspect_pair_counter[f"{pair.get('aspect', '')}_{pair.get('sentiment', '')}"] += 1
    
    return {
        'top_targets': [{'word': w, 'count': c} for w, c in target_counter.most_common(20)],
        'top_opinions': [{'word': w, 'count': c} for w, c in opinion_counter.most_common(20)]
    }


def get_negative_words(df, top_n=20):
    negative_df = df[df['sentiment_label'] == 'negative']
    return get_word_frequency(negative_df, top_n=top_n)


def get_category_statistics(df):
    if df.empty:
        return []
    
    category_stats = df.groupby('category').agg({
        'comment_id': 'count',
        'sentiment_score': 'mean',
        'rating': 'mean'
    }).reset_index()
    
    category_stats.columns = ['category', 'count', 'avg_sentiment_score', 'avg_rating']
    category_stats['avg_sentiment_score'] = category_stats['avg_sentiment_score'].round(4)
    category_stats['avg_rating'] = category_stats['avg_rating'].round(2)
    
    return category_stats.to_dict('records')


def get_product_statistics(df, product_name=None):
    if df.empty:
        return []
    
    if product_name:
        df = df[df['product_name'] == product_name]
    
    if df.empty:
        return []
    
    product_stats = df.groupby('product_name').agg({
        'comment_id': 'count',
        'sentiment_score': 'mean',
        'rating': 'mean'
    }).reset_index()
    
    product_stats.columns = ['product_name', 'count', 'avg_sentiment_score', 'avg_rating']
    product_stats['avg_sentiment_score'] = product_stats['avg_sentiment_score'].round(4)
    product_stats['avg_rating'] = product_stats['avg_rating'].round(2)
    
    return product_stats.to_dict('records')


def get_all_products(df):
    if df.empty:
        return []
    return sorted(df['product_name'].unique().tolist())


def analyze_comments_batch_bert(comments):
    from aspect_extractor import full_analysis
    
    results = []
    total = len(comments)
    
    for i, comment in enumerate(comments):
        if i % 100 == 0:
            print(f'分析进度: {i}/{total}')
        
        text = comment.get('comment_text', '')
        analysis = full_analysis(text)
        comment.update(analysis)
        comment['model_used'] = 'bert'
        results.append(comment)
    
    print(f'分析完成: {total}/{total}')
    return results


def import_csv_to_db(csv_path=None, analyze=True):
    if csv_path is None:
        csv_path = CSV_PATH
    
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    if analyze:
        comments = df.to_dict('records')
        comments = analyze_comments_batch_bert(comments)
        df = pd.DataFrame(comments)
    
    init_database()
    save_comments_to_db(df.to_dict('records'))
    print(f'已导入 {len(df)} 条评论数据到数据库')


if __name__ == '__main__':
    from data_generator import generate_comments, save_comments_to_csv
    
    print('生成评论数据...')
    comments = generate_comments(1000)
    save_comments_to_csv(comments, CSV_PATH)
    
    print('分析并导入数据库...')
    import_csv_to_db()
    
    print('测试查询...')
    df = load_all_comments()
    print(f'总评论数: {len(df)}')
    print(get_sentiment_statistics(df))
