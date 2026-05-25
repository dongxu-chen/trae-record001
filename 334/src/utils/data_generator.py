import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings('ignore')


class MovieDataGenerator:
    def __init__(self, random_seed=42):
        np.random.seed(random_seed)
        random.seed(random_seed)
        
        self.genres = ['动作', '喜剧', '爱情', '科幻', '悬疑', '动画', '惊悚', 
                       '剧情', '冒险', '犯罪', '战争', '家庭', '奇幻', '音乐']
        self.directors = [
            '张艺谋', '陈凯歌', '冯小刚', '李安', '王家卫', '吴宇森', '徐克', 
            '陈思诚', '吴京', '贾樟柯', '宁浩', '管虎', '周星驰', '姜文',
            'Christopher Nolan', 'Steven Spielberg', 'James Cameron',
            'Martin Scorsese', 'Quentin Tarantino', 'Disney Animation'
        ]
        self.actors = [
            '成龙', '周润发', '刘德华', '梁朝伟', '周星驰', '李连杰', '甄子丹',
            '吴京', '沈腾', '黄渤', '徐峥', '胡歌', '易烊千玺', '张译',
            'Tom Hanks', 'Leonardo DiCaprio', 'Robert Downey Jr.',
            'Scarlett Johansson', 'Dwayne Johnson', 'Tom Cruise'
        ]
        self.seasons = ['Q1', 'Q2', 'Q3', 'Q4']
        
        self.genre_popularity = {
            '动作': 1.2, '科幻': 1.3, '动画': 1.1, '冒险': 1.15,
            '喜剧': 1.0, '爱情': 0.9, '剧情': 0.95, '悬疑': 0.85,
            '惊悚': 0.7, '犯罪': 0.8, '战争': 0.75, '家庭': 0.9,
            '奇幻': 1.05, '音乐': 0.6
        }
        
        self.director_power = {d: np.random.uniform(0.5, 1.5) for d in self.directors}
        self.actor_power = {a: np.random.uniform(0.5, 1.5) for a in self.actors}
        
        self.holiday_multiplier = {
            'Spring Festival': 1.8,
            'National Day': 1.6,
            'Summer Vacation': 1.4,
            'Weekend': 1.2,
            'Regular': 1.0
        }

    def _generate_release_date(self):
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2025, 12, 31)
        days_between = (end_date - start_date).days
        random_days = np.random.randint(0, days_between)
        return start_date + timedelta(days=random_days)

    def _get_release_period(self, release_date):
        month = release_date.month
        day = release_date.day
        
        spring_festival = datetime(release_date.year, 2, 10)
        if abs((release_date - spring_festival).days) <= 7:
            return 'Spring Festival'
        
        national_day = datetime(release_date.year, 10, 1)
        if abs((release_date - national_day).days) <= 7:
            return 'National Day'
        
        if month in [7, 8]:
            return 'Summer Vacation'
        
        if release_date.weekday() >= 5:
            return 'Weekend'
        
        return 'Regular'

    def _generate_pre_sales(self, base_potential, days=21):
        sales = []
        base_daily = base_potential * 0.01
        
        for i in range(max(1, days)):
            growth_factor = 1 + np.random.uniform(-0.1, 0.3)
            day_factor = 1 + (i / days) * 2
            daily = base_daily * day_factor * growth_factor
            daily += np.random.normal(0, daily * 0.2)
            sales.append(max(0, daily))
        
        return sales

    def _generate_point_screen_data(self, base_potential):
        has_point_screen = np.random.random() < 0.4
        
        if not has_point_screen:
            return None
        
        screen_count = np.random.randint(30, 300)
        total_viewers = int(screen_count * 100 * np.random.uniform(0.3, 0.9))
        point_screen_days = np.random.randint(1, 7)
        
        return {
            'screen_count': int(screen_count),
            'total_viewers': int(total_viewers),
            'average_occupancy': round(np.random.uniform(0.3, 0.95), 2),
            'point_screen_days': int(point_screen_days),
            'average_score': round(np.random.uniform(6.0, 9.5), 1),
            'positive_review_ratio': round(np.random.uniform(0.5, 0.98), 2),
            'social_media_mentions': int(total_viewers * np.random.uniform(0.1, 0.8)),
            'want_to_watch_increase': int(base_potential * np.random.uniform(0.05, 0.3)),
            'viewer_comments': None
        }

    def _generate_wom_scoring(self):
        has_scoring = np.random.random() < 0.5
        
        if not has_scoring:
            return None
        
        base_score = np.random.uniform(5.5, 9.5)
        
        return {
            'douban_score': round(base_score + np.random.uniform(-0.5, 0.5), 1),
            'maoyan_score': round(base_score + np.random.uniform(-0.3, 0.7), 1),
            'taopiaopiao_score': round(base_score + np.random.uniform(-0.3, 0.7), 1),
            'imdb_score': round(base_score + np.random.uniform(-1.0, 0.5), 1),
            'rotten_tomatoes': round(base_score * 10 + np.random.uniform(-10, 10), 0),
            'metacritic': round(base_score * 10 + np.random.uniform(-10, 10), 0)
        }

    def _generate_promotion_spend(self, total_budget, days):
        if days <= 0:
            return []
        
        spend_pattern = np.random.choice(['front_loaded', 'back_loaded', 'uniform', 'pulsed'])
        
        daily_spend = np.zeros(days)
        
        if spend_pattern == 'front_loaded':
            weights = np.exp(np.linspace(2, 0, days))
        elif spend_pattern == 'back_loaded':
            weights = np.exp(np.linspace(0, 2, days))
        elif spend_pattern == 'uniform':
            weights = np.ones(days)
        else:
            weights = np.ones(days)
            pulse_days = np.random.choice(days, size=max(1, days // 5), replace=False)
            weights[pulse_days] *= 3
        
        weights = weights / weights.sum() * total_budget
        
        for i in range(days):
            daily_spend[i] = max(0, weights[i] * np.random.uniform(0.7, 1.3))
        
        scale_factor = total_budget / (daily_spend.sum() + 1e-6)
        daily_spend = daily_spend * scale_factor
        
        return daily_spend.tolist()

    def generate_movie(self, idx):
        release_date = self._generate_release_date()
        num_genres = np.random.randint(1, 4)
        movie_genres = random.sample(self.genres, num_genres)
        director = random.choice(self.directors)
        main_actor = random.choice(self.actors)
        
        genre_factor = np.mean([self.genre_popularity.get(g, 1.0) for g in movie_genres])
        director_factor = self.director_power[director]
        actor_factor = self.actor_power[main_actor]
        
        release_period = self._get_release_period(release_date)
        schedule_factor = self.holiday_multiplier[release_period]
        
        base_potential = np.random.uniform(1000, 50000)
        promotion_budget = base_potential * np.random.uniform(0.1, 0.5)
        runtime = int(np.random.normal(120, 25))
        
        competition_count = np.random.randint(0, 10)
        competition_budget = promotion_budget * np.random.uniform(0.3, 1.5) if competition_count > 0 else 0
        competition_factor = 1 / (1 + competition_count * 0.05)
        
        pre_sales_days = np.random.randint(7, 60)
        pre_sales = self._generate_pre_sales(base_potential, pre_sales_days)
        pre_sales_total = sum(pre_sales)
        
        daily_promotion = self._generate_promotion_spend(promotion_budget, pre_sales_days)
        
        point_screen_data = self._generate_point_screen_data(base_potential)
        wom_scoring = self._generate_wom_scoring()
        
        base_first_week = (base_potential * genre_factor * director_factor * 
                          actor_factor * schedule_factor * competition_factor)
        base_total = base_first_week * np.random.uniform(2.0, 4.5)
        
        pre_sales_boost = 1 + (pre_sales_total / (base_potential + 1e-6)) * 0.3
        promotion_boost = 1 + (promotion_budget / (base_potential + 1e-6)) * 0.2
        
        first_week = base_first_week * pre_sales_boost * promotion_boost
        total = base_total * pre_sales_boost * promotion_boost
        
        noise = np.random.normal(1, 0.15)
        first_week *= noise
        total *= np.random.normal(1, 0.12)
        
        first_week = max(100, first_week)
        total = max(first_week, total)
        
        return {
            'title': f'电影_{idx:04d}',
            'genres': movie_genres,
            'director': director,
            'main_actor': main_actor,
            'release_date': release_date.strftime('%Y-%m-%d'),
            'promotion_budget': promotion_budget,
            'runtime': runtime,
            'production_budget': base_potential * np.random.uniform(0.3, 0.8),
            'promotion_timeseries': {
                'daily_spend': daily_promotion,
                'spend_pattern': 'random',
                'total_spend': sum(daily_promotion)
            },
            'competition_environment': {
                'same_period_movies': competition_count,
                'average_competitor_budget': competition_budget,
                'genre_overlap_ratio': np.random.uniform(0, 1),
                'competitor_ratings': [round(np.random.uniform(5, 9), 1) for _ in range(competition_count)]
            },
            'pre_sales_data': {
                'total_amount': pre_sales_total,
                'daily_sales': pre_sales,
                'presale_days': pre_sales_days,
                'wish_count': int(base_potential * np.random.uniform(0.1, 0.5))
            },
            'point_screen_data': point_screen_data,
            'wom_scoring': wom_scoring,
            '_target': {
                'first_week_box_office': round(first_week, 2),
                'total_box_office': round(total, 2)
            }
        }

    def generate_dataset(self, n_samples=500):
        print(f"Generating {n_samples} movie samples...")
        
        X = []
        y = []
        
        for i in range(n_samples):
            movie = self.generate_movie(i + 1)
            target = movie.pop('_target')
            X.append(movie)
            y.append([target['first_week_box_office'], target['total_box_office']])
        
        y = np.array(y)
        
        print(f"Dataset generated: {len(X)} samples")
        print(f"First week box office range: {y[:, 0].min():.0f} - {y[:, 0].max():.0f} 万元")
        print(f"Total box office range: {y[:, 1].min():.0f} - {y[:, 1].max():.0f} 万元")
        print(f"Average first week: {y[:, 0].mean():.0f} 万元")
        print(f"Average total: {y[:, 1].mean():.0f} 万元")
        
        return X, y

    def save_dataset(self, X, y, output_dir='data'):
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        df = pd.DataFrame(X)
        df['first_week_box_office'] = y[:, 0]
        df['total_box_office'] = y[:, 1]
        
        df.to_csv(f'{output_dir}/movie_dataset.csv', index=False, encoding='utf-8-sig')
        print(f"Dataset saved to {output_dir}/movie_dataset.csv")
        
        return df
