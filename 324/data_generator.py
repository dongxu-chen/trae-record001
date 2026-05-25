import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from config import GENRES, PLATFORMS, TIME_SLOTS, ACTOR_POPULARITY, SEASON_EFFECT, RANDOM_SEED, MAX_EPISODES
from utils import generate_season_dates, get_season

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

GENRE_POPULARITY = {
    '都市': 1.0, '古装': 1.1, '悬疑': 0.95, '爱情': 1.05, '谍战': 0.9,
    '奇幻': 1.15, '家庭': 0.95, '军旅': 0.85, '校园': 0.9, '职场': 0.95
}

PLATFORM_WEIGHT = {
    '湖南卫视': 1.2, '浙江卫视': 1.1, '东方卫视': 1.15, '江苏卫视': 1.05,
    '北京卫视': 1.0, '腾讯视频': 0.95, '爱奇艺': 0.93, '优酷': 0.9
}

TIMESLOT_WEIGHT = {
    '黄金档(19:30-21:00)': 1.3,
    '次黄金档(21:00-22:30)': 1.1,
    '周播剧场(22:00-24:00)': 0.9,
    '午间档(12:00-14:00)': 0.7
}

def generate_drama_basic_info(drama_id=None):
    drama = {
        'drama_id': drama_id or f'D{random.randint(1000, 9999)}',
        'drama_name': f'电视剧_{random.randint(1, 999)}',
        'genre': random.choice(GENRES),
        'platform': random.choice(PLATFORMS),
        'time_slot': random.choice(TIME_SLOTS),
        'actor_level': random.choice(list(ACTOR_POPULARITY.keys())),
        'num_episodes': random.choice([24, 30, 36, 40]),
        'production_budget': random.uniform(5000, 50000),
        'director_reputation': random.uniform(0.3, 1.0),
        'is_sequel': random.choice([0, 1]),
        'start_date': datetime(2023 + random.randint(0, 1), random.randint(1, 12), random.randint(1, 28))
    }
    return drama

def generate_episodic_ratings(drama_info, add_noise=True):
    n = drama_info['num_episodes']
    base_rating = 1.5
    
    genre_factor = GENRE_POPULARITY[drama_info['genre']]
    platform_factor = PLATFORM_WEIGHT[drama_info['platform']]
    timeslot_factor = TIMESLOT_WEIGHT[drama_info['time_slot']]
    actor_factor = ACTOR_POPULARITY[drama_info['actor_level']]
    director_factor = drama_info['director_reputation']
    sequel_factor = 1.2 if drama_info['is_sequel'] else 1.0
    budget_factor = 0.8 + (drama_info['production_budget'] / 50000) * 0.4
    
    base_rating = base_rating * genre_factor * platform_factor * timeslot_factor * \
                  actor_factor * director_factor * sequel_factor * budget_factor
    
    dates = generate_season_dates(drama_info['start_date'], n, days_per_episode=1)
    
    ratings = []
    for i in range(n):
        episode = i + 1
        season = get_season(dates[i])
        season_factor = SEASON_EFFECT[season]
        
        episode_pattern = 1.0
        if episode <= 2:
            episode_pattern = 0.85 + episode * 0.075
        elif episode >= n - 2:
            episode_pattern = 1.0 + (n - episode) * 0.05
        else:
            mid_point = n / 2
            dist_from_mid = abs(episode - mid_point) / mid_point
            episode_pattern = 0.95 + (1 - dist_from_mid) * 0.15
        
        cliffhanger_bonus = 0
        if episode in [int(n * 0.25), int(n * 0.5), int(n * 0.75), n - 1]:
            cliffhanger_bonus = random.uniform(0.1, 0.3)
        
        day_of_week = dates[i].weekday()
        weekend_factor = 1.15 if day_of_week >= 5 else 1.0
        
        rating = base_rating * season_factor * episode_pattern * weekend_factor + cliffhanger_bonus
        
        if add_noise:
            rating += np.random.normal(0, 0.15)
        
        rating = max(0.3, min(rating, 8.0))
        ratings.append(round(rating, 3))
    
    return dates, ratings

def generate_social_media_data(drama_info, dates, ratings):
    n = len(dates)
    social_data = []
    
    base_volume = drama_info['production_budget'] * 0.1 * ACTOR_POPULARITY[drama_info['actor_level']]
    
    for i in range(n):
        episode = i + 1
        rating = ratings[i]
        
        volume_multiplier = 1.0 + (rating / np.mean(ratings) - 1) * 0.5
        if episode == 1 or episode == n:
            volume_multiplier *= 1.5
        elif episode % 5 == 0:
            volume_multiplier *= 1.2
            
        post_volume = int(base_volume * volume_multiplier * random.uniform(0.7, 1.3))
        repost_volume = int(post_volume * random.uniform(0.3, 0.6))
        like_volume = int(post_volume * random.uniform(1.0, 2.5))
        comment_volume = int(post_volume * random.uniform(0.2, 0.5))
        
        search_index = int(1000 * (rating / np.mean(ratings)) * random.uniform(0.8, 1.2))
        
        sentiment_score = random.uniform(0.3, 0.9)
        if rating > np.mean(ratings):
            sentiment_score = random.uniform(0.6, 0.95)
        elif rating < np.mean(ratings) * 0.8:
            sentiment_score = random.uniform(0.2, 0.5)
        
        social_data.append({
            'episode': episode,
            'date': dates[i],
            'post_volume': post_volume,
            'repost_volume': repost_volume,
            'like_volume': like_volume,
            'comment_volume': comment_volume,
            'search_index': search_index,
            'sentiment_score': round(sentiment_score, 3)
        })
    
    return pd.DataFrame(social_data)

def generate_historical_dramas(count=50):
    dramas_data = []
    
    for i in range(count):
        drama_info = generate_drama_basic_info(f'D{1000 + i}')
        dates, ratings = generate_episodic_ratings(drama_info)
        social_df = generate_social_media_data(drama_info, dates, ratings)
        
        drama_data = {
            'info': drama_info,
            'ratings': ratings,
            'dates': dates,
            'social_data': social_df
        }
        dramas_data.append(drama_data)
    
    return dramas_data

def generate_feature_matrix(dramas_data):
    features = []
    targets = []
    
    for drama in dramas_data:
        info = drama['info']
        ratings = drama['ratings']
        social_df = drama['social_data']
        dates = drama['dates']
        
        n = len(ratings)
        for i in range(n):
            episode = i + 1
            
            feature_row = {
                'episode': episode,
                'num_episodes': info['num_episodes'],
                'genre': info['genre'],
                'platform': info['platform'],
                'time_slot': info['time_slot'],
                'actor_level': info['actor_level'],
                'actor_score': ACTOR_POPULARITY[info['actor_level']],
                'production_budget': info['production_budget'],
                'director_reputation': info['director_reputation'],
                'is_sequel': info['is_sequel'],
                'day_of_week': dates[i].weekday(),
                'is_weekend': 1 if dates[i].weekday() >= 5 else 0,
                'month': dates[i].month,
                'post_volume': social_df.iloc[i]['post_volume'],
                'repost_volume': social_df.iloc[i]['repost_volume'],
                'like_volume': social_df.iloc[i]['like_volume'],
                'comment_volume': social_df.iloc[i]['comment_volume'],
                'search_index': social_df.iloc[i]['search_index'],
                'sentiment_score': social_df.iloc[i]['sentiment_score']
            }
            
            if i > 0:
                feature_row['prev_rating'] = ratings[i - 1]
            else:
                feature_row['prev_rating'] = np.mean(ratings) * 0.8
            
            if i > 1:
                feature_row['prev_2_rating'] = ratings[i - 2]
            else:
                feature_row['prev_2_rating'] = np.mean(ratings) * 0.8
            
            if i > 2:
                feature_row['prev_3_rating'] = ratings[i - 3]
            else:
                feature_row['prev_3_rating'] = np.mean(ratings) * 0.8
            
            if i > 0:
                feature_row['rating_change_1'] = ratings[i - 1] - (ratings[i - 2] if i > 1 else ratings[i - 1])
                feature_row['rating_ma3'] = np.mean(ratings[max(0, i - 3):i])
            else:
                feature_row['rating_change_1'] = 0
                feature_row['rating_ma3'] = np.mean(ratings) * 0.8
            
            features.append(feature_row)
            targets.append(ratings[i])
    
    features_df = pd.DataFrame(features)
    
    features_df = pd.get_dummies(features_df, columns=['genre', 'platform', 'time_slot', 'actor_level'])
    
    return features_df, np.array(targets)

def generate_single_drama_features(drama_info, dates, ratings, social_df, episode_idx):
    i = episode_idx
    episode = i + 1
    
    feature_row = {
        'episode': episode,
        'num_episodes': drama_info['num_episodes'],
        'actor_score': ACTOR_POPULARITY[drama_info['actor_level']],
        'production_budget': drama_info['production_budget'],
        'director_reputation': drama_info['director_reputation'],
        'is_sequel': drama_info['is_sequel'],
        'day_of_week': dates[i].weekday(),
        'is_weekend': 1 if dates[i].weekday() >= 5 else 0,
        'month': dates[i].month,
        'post_volume': social_df.iloc[i]['post_volume'],
        'repost_volume': social_df.iloc[i]['repost_volume'],
        'like_volume': social_df.iloc[i]['like_volume'],
        'comment_volume': social_df.iloc[i]['comment_volume'],
        'search_index': social_df.iloc[i]['search_index'],
        'sentiment_score': social_df.iloc[i]['sentiment_score']
    }
    
    for g in GENRES:
        feature_row[f'genre_{g}'] = 1 if drama_info['genre'] == g else 0
    
    for p in PLATFORMS:
        feature_row[f'platform_{p}'] = 1 if drama_info['platform'] == p else 0
    
    for t in TIME_SLOTS:
        feature_row[f'time_slot_{t}'] = 1 if drama_info['time_slot'] == t else 0
    
    for a in ACTOR_POPULARITY:
        feature_row[f'actor_level_{a}'] = 1 if drama_info['actor_level'] == a else 0
    
    if i > 0:
        feature_row['prev_rating'] = ratings[i - 1]
    else:
        feature_row['prev_rating'] = np.mean(ratings) * 0.8 if ratings else 1.5
    
    if i > 1:
        feature_row['prev_2_rating'] = ratings[i - 2]
    else:
        feature_row['prev_2_rating'] = feature_row['prev_rating']
    
    if i > 2:
        feature_row['prev_3_rating'] = ratings[i - 3]
    else:
        feature_row['prev_3_rating'] = feature_row['prev_rating']
    
    if i > 0:
        feature_row['rating_change_1'] = ratings[i - 1] - (ratings[i - 2] if i > 1 else ratings[i - 1])
        feature_row['rating_ma3'] = np.mean(ratings[max(0, i - 3):i])
    else:
        feature_row['rating_change_1'] = 0
        feature_row['rating_ma3'] = feature_row['prev_rating']
    
    return feature_row

def generate_trailer_heat(drama_info, days_before_premiere=30):
    """
    生成预告片热度数据（首播前预期）
    
    特征包括：
    - 预告片播放量、点赞、评论、转发
    - 话题阅读量、讨论量
    - 搜索指数
    - 主演相关热度
    - 营销投入热度
    """
    from config import PREMIERE_PREDICTION_PARAMS
    
    base_heat = drama_info['production_budget'] * 0.5
    actor_multiplier = ACTOR_POPULARITY[drama_info['actor_level']]
    genre_multiplier = GENRE_POPULARITY[drama_info['genre']]
    platform_multiplier = PLATFORM_WEIGHT[drama_info['platform']]
    sequel_multiplier = 1.5 if drama_info['is_sequel'] else 1.0
    director_multiplier = 0.8 + drama_info['director_reputation'] * 0.4
    
    base_heat = base_heat * actor_multiplier * genre_multiplier * platform_multiplier * sequel_multiplier * director_multiplier
    
    heat_data = []
    premiere_date = drama_info['start_date']
    
    for day_offset in range(days_before_premiere, 0, -1):
        current_date = premiere_date - timedelta(days=day_offset)
        days_to_premiere = day_offset
        
        growth_phase = 1.0
        if days_to_premiere <= 7:
            growth_phase = 2.5 - (days_to_premiere / 7) * 1.5
        elif days_to_premiere <= 14:
            growth_phase = 1.5
        elif days_to_premiere <= 21:
            growth_phase = 1.2
        
        day_random = random.uniform(0.8, 1.2)
        
        trailer_views = int(base_heat * growth_phase * day_random * random.uniform(0.5, 1.5))
        trailer_likes = int(trailer_views * random.uniform(0.05, 0.15))
        trailer_comments = int(trailer_views * random.uniform(0.02, 0.08))
        trailer_reposts = int(trailer_views * random.uniform(0.03, 0.10))
        
        topic_reading = int(trailer_views * random.uniform(5.0, 15.0))
        topic_discussion = int(trailer_views * random.uniform(0.1, 0.5))
        
        search_index = int(base_heat * growth_phase * day_random * random.uniform(0.001, 0.005))
        search_index = min(search_index, PREMIERE_PREDICTION_PARAMS['heat_saturation_point'])
        
        actor_heat = int(base_heat * actor_multiplier * growth_phase * day_random * random.uniform(0.01, 0.05))
        marketing_heat_index = int(base_heat * random.uniform(0.0005, 0.002))
        
        heat_data.append({
            'date': current_date,
            'days_to_premiere': days_to_premiere,
            'trailer_views': trailer_views,
            'trailer_likes': trailer_likes,
            'trailer_comments': trailer_comments,
            'trailer_reposts': trailer_reposts,
            'topic_reading': topic_reading,
            'topic_discussion': topic_discussion,
            'search_index': search_index,
            'actor_heat': actor_heat,
            'marketing_heat_index': marketing_heat_index,
            'cumulative_trailer_views': 0,
            'heat_momentum': 0
        })
    
    heat_df = pd.DataFrame(heat_data)
    
    heat_df['cumulative_trailer_views'] = heat_df['trailer_views'].cumsum()
    
    heat_df['heat_momentum'] = heat_df['trailer_views'].pct_change().fillna(0) * 100
    heat_df['heat_momentum'] = heat_df['heat_momentum'].clip(-100, 200)
    
    heat_df['composite_heat_score'] = (
        heat_df['trailer_views'] * 0.3 +
        heat_df['topic_reading'] * 0.2 +
        heat_df['search_index'] * 0.25 +
        heat_df['actor_heat'] * 0.15 +
        heat_df['marketing_heat_index'] * 0.1
    ) / 1000
    
    return heat_df

def predict_premiere_rating(drama_info, trailer_heat_df=None):
    """
    基于预告片热度预测首播收视率
    
    融合多维度特征：
    - 预告片热度（35%）
    - 演员阵容热度（25%）
    - 平台影响力（20%）
    - 题材受欢迎度（10%）
    - 营销热度（10%）
    """
    from config import PREMIERE_PREDICTION_PARAMS
    
    params = PREMIERE_PREDICTION_PARAMS
    
    if trailer_heat_df is None:
        trailer_heat_df = generate_trailer_heat(drama_info)
    
    latest_heat = trailer_heat_df.iloc[-1]
    
    avg_heat = trailer_heat_df['composite_heat_score'].mean()
    max_heat = trailer_heat_df['composite_heat_score'].max()
    heat_momentum = trailer_heat_df['heat_momentum'].iloc[-3:].mean()
    
    heat_score = min(1.0, (avg_heat * 0.4 + max_heat * 0.4 + heat_momentum * 0.002 * 0.2) / 1000)
    
    cast_score = ACTOR_POPULARITY[drama_info['actor_level']]
    platform_score = (PLATFORM_WEIGHT[drama_info['platform']] - 0.8) / 0.5
    genre_score = (GENRE_POPULARITY[drama_info['genre']] - 0.8) / 0.35
    marketing_score = min(1.0, latest_heat['marketing_heat_index'] / 50)
    
    base_rating = 1.2
    
    heat_factor = 0.7 + heat_score * 0.6
    cast_factor = 0.7 + cast_score * 0.5
    platform_factor = 0.7 + platform_score * 0.5
    genre_factor = 0.85 + genre_score * 0.3
    marketing_factor = 0.8 + marketing_score * 0.4
    
    if drama_info['is_sequel']:
        sequel_bonus = 0.3
    else:
        sequel_bonus = 0
    
    director_bonus = drama_info['director_reputation'] * 0.2
    
    premiere_prediction = base_rating * heat_factor * cast_factor * platform_factor * \
                          genre_factor * marketing_factor + sequel_bonus + director_bonus
    
    premiere_prediction = max(0.5, min(premiere_prediction, 6.0))
    
    prediction_interval = premiere_prediction * 0.2
    lower_bound = max(0.3, premiere_prediction - prediction_interval)
    upper_bound = min(8.0, premiere_prediction + prediction_interval)
    
    confidence = 0.5 + min(0.4, (latest_heat['cumulative_trailer_views'] / 10000000) * 0.4)
    
    feature_contribution = {
        'trailer_heat': {
            'weight': params['trailer_heat_weight'],
            'score': round(heat_score, 3),
            'contribution': round(heat_factor, 3)
        },
        'cast_heat': {
            'weight': params['cast_heat_weight'],
            'score': round(cast_score, 3),
            'contribution': round(cast_factor, 3)
        },
        'platform': {
            'weight': params['platform_weight'],
            'score': round(platform_score, 3),
            'contribution': round(platform_factor, 3)
        },
        'genre': {
            'weight': params['genre_weight'],
            'score': round(genre_score, 3),
            'contribution': round(genre_factor, 3)
        },
        'marketing': {
            'weight': params['marketing_weight'],
            'score': round(marketing_score, 3),
            'contribution': round(marketing_factor, 3)
        }
    }
    
    return {
        'predicted_rating': round(premiere_prediction, 4),
        'lower_bound': round(lower_bound, 4),
        'upper_bound': round(upper_bound, 4),
        'confidence': round(confidence, 3),
        'feature_contribution': feature_contribution,
        'key_metrics': {
            'avg_composite_heat': round(avg_heat, 2),
            'max_composite_heat': round(max_heat, 2),
            'cumulative_views': int(latest_heat['cumulative_trailer_views']),
            'final_search_index': int(latest_heat['search_index']),
            'heat_momentum': round(heat_momentum, 2)
        }
    }

def generate_premiere_features(drama_info, trailer_heat_df=None):
    """生成首播预测特征向量"""
    if trailer_heat_df is None:
        trailer_heat_df = generate_trailer_heat(drama_info)
    
    latest = trailer_heat_df.iloc[-1]
    avg_df = trailer_heat_df.mean()
    
    features = {
        'production_budget': drama_info['production_budget'],
        'actor_score': ACTOR_POPULARITY[drama_info['actor_level']],
        'director_reputation': drama_info['director_reputation'],
        'is_sequel': drama_info['is_sequel'],
        'num_episodes': drama_info['num_episodes'],
        'avg_trailer_views': avg_df['trailer_views'],
        'cumulative_views': latest['cumulative_trailer_views'],
        'max_trailer_views': trailer_heat_df['trailer_views'].max(),
        'trailer_likes': latest['trailer_likes'],
        'trailer_comments': latest['trailer_comments'],
        'topic_reading': latest['topic_reading'],
        'topic_discussion': latest['topic_discussion'],
        'search_index': latest['search_index'],
        'actor_heat': latest['actor_heat'],
        'marketing_index': latest['marketing_heat_index'],
        'composite_heat': latest['composite_heat_score'],
        'heat_momentum': avg_df['heat_momentum'],
        'views_growth_rate': (latest['trailer_views'] / trailer_heat_df['trailer_views'].iloc[0] - 1) if trailer_heat_df['trailer_views'].iloc[0] > 0 else 0
    }
    
    for g in GENRES:
        features[f'genre_{g}'] = 1 if drama_info['genre'] == g else 0
    
    for p in PLATFORMS:
        features[f'platform_{p}'] = 1 if drama_info['platform'] == p else 0
    
    return features

if __name__ == '__main__':
    dramas = generate_historical_dramas(10)
    print(f"Generated {len(dramas)} historical dramas")
    
    features, targets = generate_feature_matrix(dramas)
    print(f"Feature matrix shape: {features.shape}")
    print(f"Columns: {list(features.columns)[:10]}...")
    print(f"Target ratings range: {targets.min():.3f} - {targets.max():.3f}")
    
    print("\n" + "="*60)
    print("Testing Trailer Heat and Premiere Prediction")
    print("="*60)
    
    test_drama = generate_drama_basic_info('PREMIERE001')
    test_drama['drama_name'] = '测试剧集'
    test_drama['genre'] = '古装'
    test_drama['platform'] = '湖南卫视'
    test_drama['actor_level'] = '顶级'
    
    print(f"\nDrama: {test_drama['drama_name']}")
    print(f"Genre: {test_drama['genre']}, Platform: {test_drama['platform']}")
    print(f"Actor: {test_drama['actor_level']}, Budget: {test_drama['production_budget']:,.0f}万")
    
    print("\nGenerating trailer heat data...")
    heat_df = generate_trailer_heat(test_drama, days_before_premiere=30)
    print(f"Heat data shape: {heat_df.shape}")
    print(f"\nLast 7 days before premiere:")
    print(heat_df[['days_to_premiere', 'trailer_views', 'search_index', 'composite_heat_score', 'heat_momentum']].tail(7).to_string(index=False))
    
    print("\nPredicting premiere rating...")
    premiere_result = predict_premiere_rating(test_drama, heat_df)
    print(f"\nPredicted Premiere Rating: {premiere_result['predicted_rating']:.3f}%")
    print(f"Prediction Interval: [{premiere_result['lower_bound']:.3f}, {premiere_result['upper_bound']:.3f}]")
    print(f"Confidence: {premiere_result['confidence']:.2%}")
    
    print("\nFeature Contribution:")
    for name, data in premiere_result['feature_contribution'].items():
        print(f"  {name}: weight={data['weight']}, score={data['score']}, contribution={data['contribution']}")
    
    print(f"\nKey Metrics: {premiere_result['key_metrics']}")
