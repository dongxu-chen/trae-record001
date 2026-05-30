import os

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = "ecommerce_products"

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saved_models")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_files")

FEATURE_COLUMNS = [
    "title_match_score",
    "title_exact_match",
    "title_term_overlap",
    "title_bm25_score",
    "category_match",
    "price_score",
    "sales_volume_norm",
    "click_rate",
    "cart_rate",
    "conversion_rate",
    "ctr_7d",
    "ctr_30d",
    "return_rate",
    "review_score_norm",
    "title_length",
    "query_length",
    "query_title_length_ratio",
    "price_percentile",
    "brand_match",
    "time_decayed_ctr",
    "time_decayed_conversion",
    "click_trend",
    "sales_recency_ratio",
    "user_category_match",
    "user_brand_match",
    "user_price_similarity",
    "user_has_purchase_history",
    "user_activity_level",
]

PERSONALIZATION_FEATURES = [
    "user_category_match",
    "user_brand_match",
    "user_price_similarity",
    "user_has_purchase_history",
    "user_activity_level",
]

MULTI_OBJECTIVE_WEIGHTS = {
    "relevance": 0.5,
    "conversion": 0.3,
    "freshness": 0.2,
}

LABEL_COLUMN = "relevance_label"
GROUP_COLUMN = "query_group_id"

LIGHTGBM_PARAMS = {
    "objective": "lambdarank",
    "metric": "ndcg",
    "ndcg_at": [1, 3, 5, 10],
    "learning_rate": 0.05,
    "num_leaves": 63,
    "max_depth": 6,
    "min_data_in_leaf": 20,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "lambda_l1": 0.1,
    "lambda_l2": 0.1,
    "min_gain_to_split": 0.01,
    "verbose": 1,
}

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
