import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta


class InfluencerDataGenerator:
    def __init__(self, seed=42):
        np.random.seed(seed)
        random.seed(seed)
        self.platforms = ['Instagram', 'TikTok', 'YouTube', 'Xiaohongshu', 'Weibo']
        self.categories = ['美妆', '时尚', '美食', '旅行', '科技', '健身', '母婴', '游戏', '教育', '生活方式']
        self.cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '重庆', '南京', '武汉', '西安']
        self.influencer_names = self._generate_influencer_names(50)
        
    def _generate_influencer_names(self, count):
        first_names = ['小', '大', '超级', '可爱', '美丽', '时尚', '潮流', '创意', '神秘', '温柔']
        second_names = ['红', '咖', '达人', '博主', '女王', '王子', '酱', '君', '哥', '姐']
        suffixes = ['的日常', '分享', '工作室', '日记', '手记', '时光', '空间', '乐园', '世界', '花园']
        
        names = []
        for i in range(count):
            name = f"{random.choice(first_names)}{random.choice(second_names)}{random.choice(suffixes)}{i+1}"
            names.append(name)
        return names
    
    def generate_influencer_data(self, count=50):
        data = []
        for i in range(count):
            platform = random.choice(self.platforms)
            category = random.choice(self.categories)
            followers = self._generate_followers(platform)
            avg_views = followers * np.random.uniform(0.05, 0.4)
            avg_likes = avg_views * np.random.uniform(0.03, 0.15)
            avg_comments = avg_likes * np.random.uniform(0.05, 0.2)
            avg_shares = avg_comments * np.random.uniform(0.1, 0.5)
            
            influencer = {
                'id': f'INF{i+1:04d}',
                'name': self.influencer_names[i],
                'platform': platform,
                'category': category,
                'followers': int(followers),
                'avg_views': int(avg_views),
                'avg_likes': int(avg_likes),
                'avg_comments': int(avg_comments),
                'avg_shares': int(avg_shares),
                'post_frequency': np.random.randint(3, 30),
                'account_age': np.random.randint(6, 60),
                'city': random.choice(self.cities),
                'cooperation_price': self._generate_price(followers, platform),
                'verified': random.random() > 0.3,
                'last_active': (datetime.now() - timedelta(days=np.random.randint(0, 30))).strftime('%Y-%m-%d')
            }
            data.append(influencer)
        
        return pd.DataFrame(data)
    
    def _generate_followers(self, platform):
        if platform == 'YouTube':
            base = np.random.lognormal(12, 2)
        elif platform == 'TikTok':
            base = np.random.lognormal(13, 1.8)
        elif platform == 'Instagram':
            base = np.random.lognormal(12.5, 1.9)
        elif platform == 'Xiaohongshu':
            base = np.random.lognormal(11, 1.7)
        else:
            base = np.random.lognormal(13.5, 2)
        return max(1000, int(base))
    
    def _generate_price(self, followers, platform):
        base_rate = {
            'YouTube': 0.03,
            'TikTok': 0.02,
            'Instagram': 0.025,
            'Xiaohongshu': 0.02,
            'Weibo': 0.015
        }
        rate = base_rate[platform] * np.random.uniform(0.5, 2)
        return int(followers * rate / 100) * 100
    
    def generate_follower_demographics(self, influencer_df):
        demographics = []
        for _, row in influencer_df.iterrows():
            age_dist = self._generate_age_distribution(row['category'])
            gender_dist = self._generate_gender_distribution(row['category'])
            location_dist = self._generate_location_distribution()
            interest_dist = self._generate_interest_distribution(row['category'])
            
            demo = {
                'influencer_id': row['id'],
                'influencer_name': row['name'],
                'age_18_24': age_dist[0],
                'age_25_34': age_dist[1],
                'age_35_44': age_dist[2],
                'age_45_plus': age_dist[3],
                'gender_male': gender_dist[0],
                'gender_female': gender_dist[1],
                **location_dist,
                **interest_dist
            }
            demographics.append(demo)
        
        return pd.DataFrame(demographics)
    
    def _generate_age_distribution(self, category):
        if category in ['美妆', '时尚']:
            dist = [0.45, 0.35, 0.15, 0.05]
        elif category in ['游戏', '科技']:
            dist = [0.5, 0.35, 0.1, 0.05]
        elif category in ['母婴']:
            dist = [0.15, 0.45, 0.3, 0.1]
        elif category in ['旅行', '美食']:
            dist = [0.3, 0.4, 0.2, 0.1]
        else:
            dist = [0.35, 0.35, 0.2, 0.1]
        
        noise = np.random.uniform(-0.08, 0.08, 4)
        dist = np.clip(np.array(dist) + noise, 0.05, 0.7)
        return dist / dist.sum()
    
    def _generate_gender_distribution(self, category):
        if category in ['美妆', '时尚', '母婴']:
            male_ratio = np.random.uniform(0.1, 0.25)
        elif category in ['游戏', '科技', '汽车']:
            male_ratio = np.random.uniform(0.6, 0.85)
        elif category in ['健身']:
            male_ratio = np.random.uniform(0.35, 0.55)
        else:
            male_ratio = np.random.uniform(0.25, 0.5)
        return [male_ratio, 1 - male_ratio]
    
    def _generate_location_distribution(self):
        locations = {}
        total = 1.0
        
        tier1_ratio = np.random.uniform(0.25, 0.45)
        locations['location_tier1'] = tier1_ratio
        total -= tier1_ratio
        
        tier2_ratio = np.random.uniform(0.3, 0.4)
        locations['location_tier2'] = tier2_ratio
        total -= tier2_ratio
        
        locations['location_tier3_plus'] = total
        return locations
    
    def _generate_interest_distribution(self, category):
        interests = {}
        main_interest = category
        interest_list = ['美妆', '时尚', '美食', '旅行', '科技', '健身', '母婴', '游戏', '教育', '音乐']
        
        for interest in interest_list:
            if interest == main_interest:
                interests[f'interest_{interest}'] = np.random.uniform(0.3, 0.6)
            else:
                interests[f'interest_{interest}'] = np.random.uniform(0.02, 0.15)
        
        return interests
    
    def generate_campaign_data(self, influencer_df, campaign_count=100):
        campaigns = []
        campaign_names = ['618大促', '双11狂欢', '新品上市', '品牌曝光', '新品试用', 
                         '节日营销', '会员日', '周年庆', '夏季推广', '冬季推广']
        
        for i in range(campaign_count):
            influencer = influencer_df.sample(n=1).iloc[0]
            start_date = datetime.now() - timedelta(days=np.random.randint(30, 365))
            duration = np.random.randint(7, 60)
            
            reach = int(influencer['avg_views'] * np.random.uniform(0.8, 1.5))
            engagement = int(reach * np.random.uniform(0.02, 0.12))
            clicks = int(engagement * np.random.uniform(0.1, 0.4))
            conversions = int(clicks * np.random.uniform(0.03, 0.2))
            
            campaign_cost = influencer['cooperation_price'] * np.random.uniform(0.8, 1.5)
            revenue = conversions * np.random.uniform(100, 800)
            
            campaign = {
                'campaign_id': f'CMP{i+1:04d}',
                'campaign_name': random.choice(campaign_names),
                'influencer_id': influencer['id'],
                'influencer_name': influencer['name'],
                'platform': influencer['platform'],
                'category': influencer['category'],
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': (start_date + timedelta(days=duration)).strftime('%Y-%m-%d'),
                'duration_days': duration,
                'budget': int(campaign_cost),
                'actual_cost': int(campaign_cost * np.random.uniform(0.9, 1.1)),
                'reach': reach,
                'impressions': int(reach * np.random.uniform(1.2, 2)),
                'engagement': engagement,
                'clicks': clicks,
                'conversions': conversions,
                'revenue': int(revenue),
                'content_type': random.choice(['图文', '短视频', '直播', '长视频']),
                'target_audience': random.choice(['年轻女性', '都市白领', '学生群体', '家庭主妇', '科技爱好者'])
            }
            campaigns.append(campaign)
        
        return pd.DataFrame(campaigns)


def generate_sample_data():
    generator = InfluencerDataGenerator()
    influencer_df = generator.generate_influencer_data(50)
    demo_df = generator.generate_follower_demographics(influencer_df)
    campaign_df = generator.generate_campaign_data(influencer_df, 100)
    return influencer_df, demo_df, campaign_df


if __name__ == '__main__':
    influencer_df, demo_df, campaign_df = generate_sample_data()
    print("网红数据 shape:", influencer_df.shape)
    print("粉丝画像数据 shape:", demo_df.shape)
    print("营销活动数据 shape:", campaign_df.shape)
    print("\n网红数据示例:")
    print(influencer_df[['name', 'platform', 'category', 'followers', 'cooperation_price']].head())
