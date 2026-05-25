import os
import random
import numpy as np
import pandas as pd
import config

SAMPLE_TITLES = [
    "如何学好Python编程", "机器学习入门教程", "美食制作全过程",
    "游戏精彩集锦", "旅游vlog分享", "科技产品评测",
    "音乐MV首播", "动漫解说合集", "健身打卡第一天",
    "生活小妙招分享", "考研经验分享", "职场生存技巧",
    "宠物日常记录", "手工制作教程", "摄影技巧分享",
    "汽车试驾体验", "电影深度解析", "小说推荐榜单",
    "穿搭分享教程", "减肥励志日记"
]

SAMPLE_TAGS = [
    "Python", "机器学习", "深度学习", "AI", "编程",
    "美食", "烹饪", "家常菜", "甜点", "烘焙",
    "游戏", "电竞", "手游", "单机", "网游",
    "旅游", "旅行", "风景", "攻略", "自驾游",
    "科技", "数码", "评测", "手机", "电脑",
    "音乐", "歌曲", "翻唱", "原创", "舞蹈",
    "动漫", "二次元", "漫画", "动画", "Cosplay",
    "教育", "学习", "考研", "英语", "数学",
    "生活", "日常", "vlog", "记录", "分享",
    "体育", "运动", "健身", "篮球", "足球"
]


def generate_multi_target_labels(row):
    click = row['click']
    
    like_prob = click * 0.3
    if row['category'] in ['音乐', '动漫', '游戏']:
        like_prob += 0.15
    if '精彩' in row['title'] or '推荐' in row['title']:
        like_prob += 0.1
    
    like = 1 if random.random() < like_prob and click else 0
    
    share_prob = click * 0.15
    if row['category'] in ['教育', '科技', '生活']:
        share_prob += 0.1
    if row['duration'] > 600:
        share_prob += 0.05
    
    share = 1 if random.random() < share_prob and click else 0
    
    return pd.Series([click, like, share])


def generate_sample_data(num_samples=10000, save_path=None, multi_target=True):
    random.seed(42)
    np.random.seed(42)
    
    data = []
    
    for i in range(num_samples):
        user_id = f"user_{random.randint(0, 1000)}"
        video_id = f"video_{random.randint(0, 5000)}"
        
        title = random.choice(SAMPLE_TITLES)
        num_tags = random.randint(1, 5)
        tags = random.sample(SAMPLE_TAGS, num_tags)
        tags_str = ",".join(tags)
        
        category = random.choice(config.VIDEO_CATEGORIES)
        
        duration = int(np.random.lognormal(mean=5, sigma=1))
        duration = max(10, min(duration, 7200))
        
        num_history = random.randint(1, 10)
        history_videos = [f"video_{random.randint(0, 5000)}" for _ in range(num_history)]
        user_history = ",".join(history_videos)
        
        click_prob = 0.3
        if category in ["娱乐", "游戏", "音乐"]:
            click_prob += 0.15
        if num_tags >= 3:
            click_prob += 0.1
        if 60 <= duration <= 600:
            click_prob += 0.1
        if "Python" in tags or "机器学习" in tags:
            click_prob += 0.05
        
        click_prob = min(click_prob, 0.9)
        click = 1 if random.random() < click_prob else 0
        
        data.append({
            "user_id": user_id,
            "video_id": video_id,
            "title": title,
            "tags": tags_str,
            "category": category,
            "duration": duration,
            "user_history": user_history,
            "click": click
        })
    
    df = pd.DataFrame(data)
    
    if multi_target:
        print("Generating multi-target labels (click, like, share)...")
        df[['click', 'like', 'share']] = df.apply(generate_multi_target_labels, axis=1)
    else:
        df['like'] = df['click']
        df['share'] = df['click']
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"Data saved to {save_path}")
    
    return df


def split_train_test(df, test_ratio=0.2):
    shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)
    split_idx = int(len(shuffled) * (1 - test_ratio))
    train_df = shuffled.iloc[:split_idx]
    test_df = shuffled.iloc[split_idx:]
    return train_df, test_df


def create_cover_features(num_samples, feature_dim=8):
    return np.random.randn(num_samples, feature_dim)


def extract_multi_target_labels(df):
    targets = []
    for target in config.MULTI_TARGET:
        if target in df.columns:
            targets.append(df[target].values.astype(np.float32))
        else:
            targets.append(df['click'].values.astype(np.float32))
    
    return np.column_stack(targets)


def print_label_stats(df):
    print("\nLabel Statistics:")
    for target in config.MULTI_TARGET:
        if target in df.columns:
            rate = df[target].mean()
            print(f"  {target}: {rate:.4f} ({rate*100:.2f}%)")
    
    if 'click' in df.columns and 'like' in df.columns and 'share' in df.columns:
        print("\nConversion Rates:")
        click_users = df[df['click'] == 1]
        if len(click_users) > 0:
            click_to_like = click_users['like'].mean()
            click_to_share = click_users['share'].mean()
            print(f"  Click -> Like: {click_to_like:.4f}")
            print(f"  Click -> Share: {click_to_share:.4f}")


if __name__ == "__main__":
    df = generate_sample_data(
        num_samples=20000,
        save_path=os.path.join(config.DATA_DIR, "sample_data.csv"),
        multi_target=True
    )
    print(f"Generated {len(df)} samples")
    print_label_stats(df)
    print("\nCategory distribution:")
    print(df['category'].value_counts())
    print("\nFirst 5 rows:")
    print(df.head())
