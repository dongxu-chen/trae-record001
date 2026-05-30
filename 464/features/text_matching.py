import math
from collections import Counter

import jieba

_token_cache = {}


def tokenize(text):
    if text in _token_cache:
        return _token_cache[text]
    tokens = list(jieba.cut(text))
    _token_cache[text] = tokens
    return tokens


def clear_cache():
    global _token_cache
    _token_cache = {}


def title_match_score(q_tokens, t_tokens):
    if not q_tokens or not t_tokens:
        return 0.0
    q_set = set(q_tokens)
    t_set = set(t_tokens)
    intersection = q_set & t_set
    if not intersection:
        return 0.0
    precision = len(intersection) / len(t_set)
    recall = len(intersection) / len(q_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def title_exact_match(q_tokens, t_tokens):
    if not q_tokens:
        return 0.0
    q_set = set(q_tokens)
    t_set = set(t_tokens)
    return len(q_set & t_set) / len(q_set)


def title_term_overlap(q_tokens, t_tokens):
    if not q_tokens or not t_tokens:
        return 0.0
    q_counter = Counter(q_tokens)
    t_counter = Counter(t_tokens)
    overlap = 0
    for token in q_counter:
        if token in t_counter:
            overlap += min(q_counter[token], t_counter[token])
    return overlap / len(q_tokens)


def compute_bm25(q_tokens, t_tokens, idf_dict=None, k1=1.5, b=0.75, avgdl=10.0):
    if not q_tokens or not t_tokens:
        return 0.0
    doc_len = len(t_tokens)
    tf_dict = Counter(t_tokens)
    score = 0.0
    for token in q_tokens:
        tf = tf_dict.get(token, 0)
        idf = idf_dict.get(token, math.log(10000 / 2)) if idf_dict else math.log(10000 / 2)
        tf_component = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avgdl))
        score += idf * tf_component
    return score


def category_match(q_tokens, cat_tokens):
    if not q_tokens or not cat_tokens:
        return 0.0
    return len(set(q_tokens) & set(cat_tokens)) / len(set(q_tokens) | set(cat_tokens))


def brand_match(query, brand):
    if not brand:
        return 0.0
    return 1.0 if brand.lower() in query.lower() else 0.0


def price_score(price, min_price=0, max_price=10000):
    if max_price == min_price:
        return 0.5
    return 1.0 - abs(price - (min_price + max_price) / 2) / (max_price - min_price)


def price_percentile(price, price_list):
    if not price_list:
        return 0.5
    return sum(1 for p in price_list if p <= price) / len(price_list)


def compute_text_features(query, product, idf_dict=None, price_list=None):
    title = product.get("title", "")
    category = product.get("category", "")
    brand = product.get("brand", "")
    price = product.get("price", 0)

    q_tokens = tokenize(query)
    t_tokens = tokenize(title)
    cat_tokens = tokenize(category)

    features = {}
    features["title_match_score"] = title_match_score(q_tokens, t_tokens)
    features["title_exact_match"] = title_exact_match(q_tokens, t_tokens)
    features["title_term_overlap"] = title_term_overlap(q_tokens, t_tokens)
    features["title_bm25_score"] = compute_bm25(q_tokens, t_tokens, idf_dict)
    features["category_match"] = category_match(q_tokens, cat_tokens)
    features["brand_match"] = brand_match(query, brand)
    features["price_score"] = price_score(price)
    features["price_percentile"] = price_percentile(price, price_list) if price_list else 0.5
    features["title_length"] = len(title)
    features["query_length"] = len(query)
    features["query_title_length_ratio"] = len(query) / max(len(title), 1)
    return features


def exponential_decay(age_days, half_life=7.0):
    return math.exp(-math.log(2) * age_days / half_life)


def compute_time_decayed_behavior_features(product):
    features = {}

    ctr_1d = product.get("ctr_1d", product.get("ctr_7d", 0.0) * 1.2)
    ctr_3d = product.get("ctr_3d", product.get("ctr_7d", 0.0) * 1.1)
    ctr_7d = product.get("ctr_7d", 0.0)
    ctr_14d = product.get("ctr_14d", product.get("ctr_30d", 0.0) * 0.9)
    ctr_30d = product.get("ctr_30d", 0.0)

    decayed_ctr = (
        ctr_1d * exponential_decay(1, half_life=7) +
        ctr_3d * exponential_decay(3, half_life=7) +
        ctr_7d * exponential_decay(7, half_life=7) +
        ctr_14d * exponential_decay(14, half_life=7) +
        ctr_30d * exponential_decay(30, half_life=7)
    ) / (
        exponential_decay(1, half_life=7) +
        exponential_decay(3, half_life=7) +
        exponential_decay(7, half_life=7) +
        exponential_decay(14, half_life=7) +
        exponential_decay(30, half_life=7)
    )
    features["time_decayed_ctr"] = min(decayed_ctr, 1.0)

    conv_1d = product.get("conv_1d", product.get("conversion_rate", 0.0) * 1.2)
    conv_3d = product.get("conv_3d", product.get("conversion_rate", 0.0) * 1.1)
    conv_7d = product.get("conversion_rate", 0.0)
    conv_14d = product.get("conv_14d", conv_7d * 0.9)
    conv_30d = product.get("conv_30d", conv_7d * 0.8)

    decayed_conv = (
        conv_1d * exponential_decay(1, half_life=14) +
        conv_3d * exponential_decay(3, half_life=14) +
        conv_7d * exponential_decay(7, half_life=14) +
        conv_14d * exponential_decay(14, half_life=14) +
        conv_30d * exponential_decay(30, half_life=14)
    ) / (
        exponential_decay(1, half_life=14) +
        exponential_decay(3, half_life=14) +
        exponential_decay(7, half_life=14) +
        exponential_decay(14, half_life=14) +
        exponential_decay(30, half_life=14)
    )
    features["time_decayed_conversion"] = min(decayed_conv, 1.0)

    click_trend = ctr_1d / max(ctr_30d, 0.0001)
    features["click_trend"] = min(click_trend, 2.0)

    sales_recent = product.get("sales_7d", product.get("sales_volume", 1000) * 0.1)
    sales_long = product.get("sales_volume", 0)
    recency_ratio = sales_recent / max(sales_long / 4.28, 1.0)
    features["sales_recency_ratio"] = min(recency_ratio, 2.0)

    return features


def compute_behavior_features(product):
    features = {}
    features["sales_volume_norm"] = min(product.get("sales_volume", 0) / 10000.0, 1.0)
    features["click_rate"] = product.get("click_rate", 0.0)
    features["cart_rate"] = product.get("cart_rate", 0.0)
    features["conversion_rate"] = product.get("conversion_rate", 0.0)
    features["ctr_7d"] = product.get("ctr_7d", 0.0)
    features["ctr_30d"] = product.get("ctr_30d", 0.0)
    features["return_rate"] = product.get("return_rate", 0.0)
    features["review_score_norm"] = product.get("review_score", 0.0) / 5.0
    return features


def compute_all_features(query, product, idf_dict=None, price_list=None):
    text_feats = compute_text_features(query, product, idf_dict, price_list)
    behavior_feats = compute_behavior_features(product)
    time_decayed_feats = compute_time_decayed_behavior_features(product)
    text_feats.update(behavior_feats)
    text_feats.update(time_decayed_feats)
    return text_feats
