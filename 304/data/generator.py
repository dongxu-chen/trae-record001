import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np
import pandas as pd

from config import config
from .models import User, News, UserBehavior


class DataGenerator:
    def __init__(self):
        self.categories = config.CATEGORY_LIST
        self.category_to_id = {cat: idx for idx, cat in enumerate(self.categories)}

    def generate_users(self, num_users: int = None) -> List[User]:
        num_users = num_users or config.NUM_USERS
        users = []
        for user_id in range(num_users):
            age = random.randint(18, 65)
            gender = random.choice(['M', 'F'])
            registration_date = datetime.now() - timedelta(days=random.randint(1, 365))
            users.append(User(
                user_id=user_id,
                age=age,
                gender=gender,
                registration_date=registration_date
            ))
        return users

    def generate_news(self, num_news: int = None) -> List[News]:
        num_news = num_news or config.NUM_NEWS
        news_list = []
        titles = self._generate_titles(num_news)

        for news_id in range(num_news):
            category = random.choice(self.categories)
            category_id = self.category_to_id[category]
            publish_time = datetime.now() - timedelta(hours=random.randint(1, 24 * 30))

            news_list.append(News(
                news_id=news_id,
                title=titles[news_id],
                category=category,
                category_id=category_id,
                content=f"这是一篇关于{category}的新闻内容，编号为{news_id}。",
                publish_time=publish_time,
                author=f"作者{random.randint(1, 100)}",
                tags=[f"标签{random.randint(1, 20)}" for _ in range(random.randint(1, 3))]
            ))
        return news_list

    def _generate_titles(self, num_titles: int) -> List[str]:
        templates = [
            "重磅！{topic}领域迎来重大突破",
            "深度解析：{topic}背后的秘密",
            "最新消息：{topic}引发广泛关注",
            "专家解读：{topic}将如何改变我们的生活",
            "必看！{topic}的十大关键点",
            "独家报道：{topic}最新进展",
            "热议：{topic}成为行业焦点",
            "调查显示：{topic}正在改变市场格局",
            "权威发布：{topic}白皮书正式发布",
            "前瞻：{topic}未来发展趋势分析"
        ]

        topic_by_category = {
            '科技': ['人工智能', '区块链', '5G通信', '量子计算', '元宇宙'],
            '财经': ['股市', '比特币', '房地产', '货币政策', '新能源'],
            '体育': ['世界杯', '奥运会', 'NBA', '足球联赛', '网球'],
            '娱乐': ['电影', '音乐', '综艺节目', '明星', '游戏'],
            '军事': ['国防', '武器装备', '军事演习', '国际局势', '航天'],
            '教育': ['高考', '考研', '在线教育', '职业培训', '留学'],
            '健康': ['养生', '医疗', '心理健康', '运动健身', '营养'],
            '旅游': ['国内游', '出境游', '自驾游', '民宿', '景点推荐'],
            '美食': ['家常菜', '烘焙', '饮品', '地方小吃', '米其林'],
            '汽车': ['新能源汽车', '自动驾驶', 'SUV', '豪华车', '二手车']
        }

        titles = []
        for i in range(num_titles):
            category = random.choice(self.categories)
            topic = random.choice(topic_by_category.get(category, ['新闻']))
            template = random.choice(templates)
            titles.append(template.format(topic=topic))
        return titles

    def generate_user_behaviors(
        self,
        users: List[User],
        news_list: List[News],
        num_behaviors: int = 10000
    ) -> List[UserBehavior]:
        behaviors = []
        news_by_category = {}
        for news in news_list:
            if news.category not in news_by_category:
                news_by_category[news.category] = []
            news_by_category[news.category].append(news)

        user_preferences = {}
        for user in users:
            pref_categories = random.sample(
                self.categories,
                random.randint(2, 5)
            )
            user_preferences[user.user_id] = {
                cat: random.uniform(0.5, 2.0) for cat in pref_categories
            }

        behavior_types = ['view', 'view', 'view', 'view', 'like', 'share']

        for _ in range(num_behaviors):
            user = random.choice(users)
            prefs = user_preferences.get(user.user_id, {})

            if prefs and random.random() < 0.7:
                category = random.choices(
                    list(prefs.keys()),
                    weights=list(prefs.values()),
                    k=1
                )[0]
            else:
                category = random.choice(self.categories)

            candidate_news = news_by_category.get(category, news_list)
            news = random.choice(candidate_news)

            behavior_type = random.choice(behavior_types)
            timestamp = datetime.now() - timedelta(minutes=random.randint(1, 60 * 24 * 7))
            duration = random.uniform(10, 300) if behavior_type == 'view' else 0.0

            behaviors.append(UserBehavior(
                user_id=user.user_id,
                news_id=news.news_id,
                behavior_type=behavior_type,
                timestamp=timestamp,
                duration=duration
            ))

        behaviors.sort(key=lambda x: x.timestamp)
        return behaviors

    def generate_training_data(
        self,
        behaviors: List[UserBehavior],
        news_list: List[News]
    ) -> pd.DataFrame:
        news_dict = {news.news_id: news for news in news_list}

        data = []
        for behavior in behaviors:
            news = news_dict.get(behavior.news_id)
            if not news:
                continue

            weight = config.BEHAVIOR_WEIGHTS.get(behavior.behavior_type, 1.0)
            if behavior.duration > 0:
                weight += behavior.duration * config.BEHAVIOR_WEIGHTS['duration']

            label = 1 if behavior.behavior_type in ['view', 'like', 'share'] else 0

            data.append({
                'user_id': behavior.user_id,
                'news_id': behavior.news_id,
                'category_id': news.category_id,
                'behavior_type': behavior.behavior_type,
                'duration': behavior.duration,
                'weight': weight,
                'label': label,
                'timestamp': behavior.timestamp
            })

        df = pd.DataFrame(data)

        negative_samples = self._generate_negative_samples(df, news_list)
        df = pd.concat([df, negative_samples], ignore_index=True)

        return df

    def _generate_negative_samples(
        self,
        positive_df: pd.DataFrame,
        news_list: List[News],
        neg_pos_ratio: int = 3
    ) -> pd.DataFrame:
        user_positive_news = positive_df.groupby('user_id')['news_id'].apply(set).to_dict()
        all_news_ids = set(n.news_id for n in news_list)
        news_dict = {news.news_id: news for news in news_list}

        negative_data = []
        num_negatives = len(positive_df) * neg_pos_ratio

        for _ in range(num_negatives):
            user_id = random.choice(positive_df['user_id'].unique())
            positive_news = user_positive_news.get(user_id, set())
            candidate_news = list(all_news_ids - positive_news)

            if not candidate_news:
                continue

            news_id = random.choice(candidate_news)
            news = news_dict[news_id]

            negative_data.append({
                'user_id': user_id,
                'news_id': news_id,
                'category_id': news.category_id,
                'behavior_type': 'none',
                'duration': 0.0,
                'weight': 1.0,
                'label': 0,
                'timestamp': datetime.now()
            })

        return pd.DataFrame(negative_data)

    def generate_user_news_pairs(
        self,
        user_id: int,
        candidate_news_ids: List[int],
        news_list: List[News]
    ) -> pd.DataFrame:
        news_dict = {news.news_id: news for news in news_list}
        data = []

        for news_id in candidate_news_ids:
            news = news_dict.get(news_id)
            if news:
                data.append({
                    'user_id': user_id,
                    'news_id': news_id,
                    'category_id': news.category_id
                })

        return pd.DataFrame(data)
