import re
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import config


class TextPreprocessor:
    def __init__(self, vocab_size=5000):
        self.tokenizer = Tokenizer(num_words=vocab_size, oov_token='<OOV>')
        self.vocab_size = vocab_size
    
    def fit(self, texts):
        self.tokenizer.fit_on_texts(texts)
    
    def transform(self, texts, max_length):
        sequences = self.tokenizer.texts_to_sequences(texts)
        return pad_sequences(sequences, maxlen=max_length, padding='post', truncating='post')
    
    def fit_transform(self, texts, max_length):
        self.fit(texts)
        return self.transform(texts, max_length)


def clean_text(text):
    if not isinstance(text, str):
        return ''
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_duration_features(duration):
    if pd.isna(duration) or duration <= 0:
        return 0, 0, 0
    minutes = duration // 60
    seconds = duration % 60
    duration_category = 0
    if duration < 60:
        duration_category = 0
    elif duration < 300:
        duration_category = 1
    elif duration < 900:
        duration_category = 2
    else:
        duration_category = 3
    return duration, duration_category, minutes


def normalize_numeric_features(df, numeric_cols):
    scaler = StandardScaler()
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols].fillna(0))
    return scaler


def process_tags(tags_list, max_tags=5):
    if isinstance(tags_list, str):
        tags = tags_list.split(',')
    elif isinstance(tags_list, list):
        tags = tags_list
    else:
        tags = []
    tags = [t.strip() for t in tags if t.strip()][:max_tags]
    while len(tags) < max_tags:
        tags.append('')
    return tags


def process_user_history(history_items, max_items=10):
    if isinstance(history_items, str):
        items = history_items.split(',')
    elif isinstance(history_items, list):
        items = history_items
    else:
        items = []
    items = [str(item).strip() for item in items if item][:max_items]
    while len(items) < max_items:
        items.append('')
    return items


def build_vocab_from_data(df):
    title_processor = TextPreprocessor(vocab_size=config.TITLE_VOCAB_SIZE)
    tag_processor = TextPreprocessor(vocab_size=config.TAGS_VOCAB_SIZE)
    
    all_titles = df['title'].apply(clean_text).tolist()
    all_tags = df['tags'].apply(lambda x: ' '.join(process_tags(x))).tolist()
    
    title_processor.fit(all_titles)
    tag_processor.fit(all_tags)
    
    return title_processor, tag_processor


def preprocess_video_features(df, title_processor, tag_processor):
    df = df.copy()
    
    df['title_clean'] = df['title'].apply(clean_text)
    title_seq = title_processor.transform(df['title_clean'].tolist(), config.MAX_TITLE_LENGTH)
    
    df['tags_processed'] = df['tags'].apply(process_tags)
    tag_seqs = []
    for tags in df['tags_processed']:
        tag_seq = tag_processor.transform(tags, 1)
        tag_seqs.append(tag_seq.flatten())
    tag_seqs = np.array(tag_seqs)
    
    duration_features = df['duration'].apply(extract_duration_features).tolist()
    duration_array = np.array([[f[0], f[1], f[2]] for f in duration_features])
    
    cover_features = np.random.randn(len(df), 8)
    
    return {
        'title': title_seq,
        'tags': tag_seqs,
        'duration': duration_array,
        'cover': cover_features,
        'category': df['category'].astype(str).values
    }


def preprocess_user_features(df, user_processor=None):
    df = df.copy()
    
    df['history_processed'] = df['user_history'].apply(
        lambda x: process_user_history(x, config.MAX_HISTORY_ITEMS)
    )
    
    if user_processor is None:
        user_processor = TextPreprocessor(vocab_size=config.USER_HISTORY_SIZE)
        all_history = df['history_processed'].apply(lambda x: ' '.join(x)).tolist()
        user_processor.fit(all_history)
    
    history_seqs = []
    for history in df['history_processed']:
        hist_seq = user_processor.transform(history, 1)
        history_seqs.append(hist_seq.flatten())
    history_seqs = np.array(history_seqs)
    
    return {
        'user_history': history_seqs,
        'user_id': df['user_id'].astype(str).values
    }, user_processor


def combine_features(video_features, user_features):
    combined = {}
    combined.update(video_features)
    combined.update(user_features)
    return combined


def create_feature_columns():
    import tensorflow as tf
    from tensorflow.keras import layers
    
    feature_columns = []
    
    category_column = tf.feature_column.categorical_column_with_vocabulary_list(
        'category', config.VIDEO_CATEGORIES
    )
    category_embedding = tf.feature_column.embedding_column(
        category_column, dimension=config.EMBEDDING_DIM
    )
    feature_columns.append(category_embedding)
    
    user_id_column = tf.feature_column.categorical_column_with_hash_bucket(
        'user_id', hash_bucket_size=1000
    )
    user_id_embedding = tf.feature_column.embedding_column(
        user_id_column, dimension=config.EMBEDDING_DIM
    )
    feature_columns.append(user_id_embedding)
    
    duration_buckets = tf.feature_column.bucketized_column(
        tf.feature_column.numeric_column('duration_raw'),
        boundaries=[60, 300, 900, 1800]
    )
    duration_indicator = tf.feature_column.indicator_column(duration_buckets)
    feature_columns.append(duration_indicator)
    
    return feature_columns
