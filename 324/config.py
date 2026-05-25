import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

GENRES = ['都市', '古装', '悬疑', '爱情', '谍战', '奇幻', '家庭', '军旅', '校园', '职场']
PLATFORMS = ['湖南卫视', '浙江卫视', '东方卫视', '江苏卫视', '北京卫视', '腾讯视频', '爱奇艺', '优酷']
TIME_SLOTS = ['黄金档(19:30-21:00)', '次黄金档(21:00-22:30)', '周播剧场(22:00-24:00)', '午间档(12:00-14:00)']

ACTOR_POPULARITY = {
    '顶级': 1.0,
    '一线': 0.8,
    '二线': 0.6,
    '三线': 0.4,
    '新人': 0.2
}

SEASON_EFFECT = {
    '春季': 1.0,
    '夏季': 1.1,
    '秋季': 0.95,
    '冬季': 1.05
}

RANDOM_SEED = 42
MAX_EPISODES = 40

XGBOOST_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': RANDOM_SEED
}

LSTM_PARAMS = {
    'units': 64,
    'dropout': 0.2,
    'recurrent_dropout': 0.2,
    'epochs': 50,
    'batch_size': 16,
    'validation_split': 0.2
}

TIME_GATE_PARAMS = {
    'time_decay_rate': 0.1,
    'max_interval_days': 30,
    'use_trainable_decay': True,
    'interval_scaling': 'log'
}

REVENUE_MODEL_PARAMS = {
    'rating_revenue_coef': 5000,
    'platform_fee_min': 500000,
    'platform_fee_max': 5000000,
    'avg_ad_price_per_second': 0.8,
    'ad_duration_per_episode': 300,
    'rating_bonus_per_point': 500000,
    'peak_bonus_per_point': 300000,
    'actor_bonus_per_level': 1000000,
    'director_bonus_factor': 500000,
    'sequel_bonus': 500000,
    'overseas_rights_ratio': 0.15,
    'ip_derivative_ratio': 0.1,
    'operating_cost_ratio': 0.3,
    'tax_rate': 0.25,
    'roi_threshold_good': 0.3,
    'roi_threshold_normal': 0.1,
    'payback_period_max': 3
}

PREMIERE_PREDICTION_PARAMS = {
    'trailer_heat_weight': 0.35,
    'cast_heat_weight': 0.25,
    'platform_weight': 0.2,
    'genre_weight': 0.1,
    'marketing_weight': 0.1,
    'decay_days_before_premiere': 7,
    'heat_saturation_point': 1000000
}

COMPETITION_PARAMS = {
    'direct_competitor_penalty': 0.15,
    'same_genre_penalty': 0.10,
    'same_platform_penalty': 0.05,
    'same_timeslot_penalty': 0.20,
    'strong_cast_penalty': 0.12,
    'sequel_bonus_vs_competitor': 0.08,
    'market_saturation_threshold': 3,
    'max_competition_penalty': 0.40
}

ADVERTISING_PARAMS = {
    'base_cpm': 50,
    'rating_multiplier': 100,
    'prime_time_bonus': 1.5,
    'weekend_bonus': 1.2,
    'peak_episode_bonus': 1.3,
    'sentiment_bonus': 0.2,
    'audience_demographic_value': {
        '18-24': 1.2,
        '25-34': 1.5,
        '35-44': 1.3,
        '45-54': 1.0,
        '55+': 0.8
    },
    'ad_slots': {
        'pre_episode': {'name': '片头广告', 'duration': 15, 'multiplier': 0.8},
        'mid_episode_1': {'name': '中插广告1', 'duration': 30, 'multiplier': 1.2},
        'mid_episode_2': {'name': '中插广告2', 'duration': 30, 'multiplier': 1.1},
        'post_episode': {'name': '片尾广告', 'duration': 15, 'multiplier': 0.7},
        'corner_bug': {'name': '角标广告', 'duration': 0, 'multiplier': 0.5}
    },
    'seasonal_multipliers': {
        '春季': 1.0,
        '夏季': 1.2,
        '秋季': 0.95,
        '冬季': 1.1
    }
}

AUDIENCE_PROFILE_PARAMS = {
    'age_groups': ['18-24', '25-34', '35-44', '45-54', '55+'],
    'gender_split': {'male': 0.45, 'female': 0.55},
    'genre_audience_preference': {
        '都市': {'18-24': 0.25, '25-34': 0.35, '35-44': 0.25, '45-54': 0.10, '55+': 0.05},
        '古装': {'18-24': 0.30, '25-34': 0.30, '35-44': 0.20, '45-54': 0.12, '55+': 0.08},
        '悬疑': {'18-24': 0.20, '25-34': 0.35, '35-44': 0.25, '45-54': 0.15, '55+': 0.05},
        '爱情': {'18-24': 0.35, '25-34': 0.30, '35-44': 0.20, '45-54': 0.10, '55+': 0.05},
        '谍战': {'18-24': 0.15, '25-34': 0.30, '35-44': 0.30, '45-54': 0.18, '55+': 0.07},
        '奇幻': {'18-24': 0.35, '25-34': 0.30, '35-44': 0.20, '45-54': 0.10, '55+': 0.05},
        '家庭': {'18-24': 0.10, '25-34': 0.25, '35-44': 0.35, '45-54': 0.20, '55+': 0.10},
        '军旅': {'18-24': 0.15, '25-34': 0.25, '35-44': 0.30, '45-54': 0.20, '55+': 0.10},
        '校园': {'18-24': 0.50, '25-34': 0.30, '35-44': 0.12, '45-54': 0.06, '55+': 0.02},
        '职场': {'18-24': 0.20, '25-34': 0.40, '35-44': 0.25, '45-54': 0.10, '55+': 0.05}
    },
    'overlap_threshold_high': 0.7,
    'overlap_threshold_medium': 0.5,
    'cross_promotion_score_threshold': 0.6,
    'social_platform_preference': {
        '18-24': {'微博': 0.4, '抖音': 0.5, 'B站': 0.3, '小红书': 0.35},
        '25-34': {'微博': 0.35, '抖音': 0.45, 'B站': 0.2, '小红书': 0.45},
        '35-44': {'微博': 0.3, '抖音': 0.4, 'B站': 0.1, '小红书': 0.3},
        '45-54': {'微博': 0.2, '抖音': 0.35, 'B站': 0.05, '小红书': 0.2},
        '55+': {'微博': 0.1, '抖音': 0.25, 'B站': 0.02, '小红书': 0.1}
    }
}
