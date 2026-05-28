import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

GENRES = ['动作', '喜剧', '剧情', '科幻', '恐怖', '爱情', '动画', '悬疑', '冒险', '战争']
ACTORS = ['演员A', '演员B', '演员C', '演员D', '演员E', '演员F', '演员G', '演员H', '演员I', '演员J']
DIRECTORS = ['导演A', '导演B', '导演C', '导演D', '导演E', '导演F', '导演G', '导演H']
AGE_GROUPS = ['18-25', '26-35', '36-45', '46-55', '55+']
OCCUPATIONS = ['学生', '工程师', '教师', '医生', '艺术家', '商人', '自由职业', '公务员']


def generate_movies(num_movies=200):
    movies = []
    for i in range(num_movies):
        movie_id = f'M{i+1:03d}'
        num_genres = random.randint(1, 3)
        genres = random.sample(GENRES, num_genres)
        num_actors = random.randint(2, 5)
        actors = random.sample(ACTORS, num_actors)
        director = random.choice(DIRECTORS)
        release_year = random.randint(2010, 2024)
        budget = random.randint(10, 200) * 1000000
        runtime = random.randint(80, 180)
        is_sequel = random.choice([0, 1])
        production_company = random.choice(['公司A', '公司B', '公司C', '公司D', '公司E'])
        
        movies.append({
            'movie_id': movie_id,
            'title': f'电影_{movie_id}',
            'genres': '|'.join(genres),
            'actors': '|'.join(actors),
            'director': director,
            'release_year': release_year,
            'budget': budget,
            'runtime': runtime,
            'is_sequel': is_sequel,
            'production_company': production_company
        })
    
    return pd.DataFrame(movies)


def generate_users(num_users=100):
    users = []
    for i in range(num_users):
        user_id = f'U{i+1:03d}'
        age_group = random.choice(AGE_GROUPS)
        gender = random.choice(['M', 'F'])
        occupation = random.choice(OCCUPATIONS)
        city = random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安'])
        watch_frequency = random.choice(['低频', '中频', '高频'])
        
        genre_preferences = {}
        for genre in GENRES:
            genre_preferences[f'pref_{genre}'] = round(random.uniform(0, 1), 2)
        
        user_data = {
            'user_id': user_id,
            'age_group': age_group,
            'gender': gender,
            'occupation': occupation,
            'city': city,
            'watch_frequency': watch_frequency
        }
        user_data.update(genre_preferences)
        users.append(user_data)
    
    return pd.DataFrame(users)


def generate_ratings(users_df, movies_df, num_ratings=5000):
    ratings = []
    user_ids = users_df['user_id'].tolist()
    movie_ids = movies_df['movie_id'].tolist()
    
    for _ in range(num_ratings):
        user_id = random.choice(user_ids)
        movie_id = random.choice(movie_ids)
        
        user_row = users_df[users_df['user_id'] == user_id].iloc[0]
        movie_row = movies_df[movies_df['movie_id'] == movie_id].iloc[0]
        
        base_rating = 3.0
        movie_genres = movie_row['genres'].split('|')
        for genre in movie_genres:
            base_rating += (user_row[f'pref_{genre}'] - 0.5) * 0.5
        
        if user_row['age_group'] in ['18-25', '26-35']:
            if '科幻' in movie_genres or '动作' in movie_genres:
                base_rating += 0.3
        
        if user_row['age_group'] in ['46-55', '55+']:
            if '剧情' in movie_genres or '爱情' in movie_genres:
                base_rating += 0.3
        
        rating = max(1, min(5, round(base_rating + np.random.normal(0, 0.5), 1)))
        
        days_ago = random.randint(1, 365)
        rating_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        ratings.append({
            'user_id': user_id,
            'movie_id': movie_id,
            'rating': rating,
            'rating_date': rating_date
        })
    
    return pd.DataFrame(ratings).drop_duplicates(subset=['user_id', 'movie_id'])


def generate_boxoffice_data(movies_df):
    boxoffice_records = []
    
    for _, movie_row in movies_df.iterrows():
        budget = movie_row['budget']
        release_year = movie_row['release_year']
        genres = movie_row['genres'].split('|')
        
        base_opening = budget * 0.15
        
        genre_multiplier = 1.0
        if '动作' in genres or '科幻' in genres:
            genre_multiplier *= 1.3
        if '喜剧' in genres:
            genre_multiplier *= 1.15
        if '恐怖' in genres:
            genre_multiplier *= 0.85
        if '动画' in genres:
            genre_multiplier *= 1.2
        
        year_multiplier = 1.0 + (release_year - 2010) * 0.03
        
        sequel_multiplier = 1.4 if movie_row['is_sequel'] else 1.0
        
        director_boost = 1.0
        if movie_row['director'] in ['导演A', '导演B', '导演C']:
            director_boost = 1.25
        
        opening_weekend = base_opening * genre_multiplier * year_multiplier * sequel_multiplier * director_boost
        opening_weekend *= np.random.normal(1.0, 0.2)
        opening_weekend = max(500000, opening_weekend)
        
        total_revenue = opening_weekend * random.uniform(2.5, 4.0)
        
        boxoffice_records.append({
            'movie_id': movie_row['movie_id'],
            'opening_weekend_revenue': int(opening_weekend),
            'total_revenue': int(total_revenue),
            'release_month': random.randint(1, 12),
            'release_weekday': random.randint(0, 6),
            'holiday_season': random.choice([0, 1]),
            'marketing_spend': int(budget * random.uniform(0.2, 0.5)),
            'num_screens': random.randint(1000, 8000)
        })
    
    return pd.DataFrame(boxoffice_records)


def generate_all_data():
    print("正在生成模拟数据...")
    
    movies_df = generate_movies(200)
    print(f"生成电影数据: {len(movies_df)} 条")
    
    users_df = generate_users(100)
    print(f"生成用户数据: {len(users_df)} 条")
    
    ratings_df = generate_ratings(users_df, movies_df, 6000)
    print(f"生成评分数据: {len(ratings_df)} 条")
    
    boxoffice_df = generate_boxoffice_data(movies_df)
    print(f"生成票房数据: {len(boxoffice_df)} 条")
    
    movies_df.to_csv('data/movies.csv', index=False)
    users_df.to_csv('data/users.csv', index=False)
    ratings_df.to_csv('data/ratings.csv', index=False)
    boxoffice_df.to_csv('data/boxoffice.csv', index=False)
    
    print("数据已保存到 data/ 目录")
    return movies_df, users_df, ratings_df, boxoffice_df


if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)
    generate_all_data()
