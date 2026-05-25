import re
import numpy as np
import pandas as pd
from collections import defaultdict

POSITIVE_WORDS = [
    '好看', '精彩', '不错', '喜欢', '推荐', '超赞', '太棒了', '好看的', '很喜欢', '爱了',
    '演技', '在线', '剧情', '紧凑', '节奏', '好', '棒', '赞', '强', '牛', '优秀', '出色',
    '过瘾', '上头', '上头了', '追了', '追剧', '期待', '好评', '满分', '良心', '精品',
    '最佳', '顶级', '完美', '感动', '震撼', '惊艳', '动人', '走心', '用心', '诚意',
    '哭了', '爆笑', '好笑', '甜', '虐', '爽', '燃', '炸', '神仙', '宝藏', '神剧',
    '值得', '不亏', '入股', '追更', '催更', '二刷', '三刷', '反复', '看不够', '没看够',
    '颜值', '高', '在线', '台词', '功底', '服化道', '精美', '用心', '考究', '细节', '到位'
]

NEGATIVE_WORDS = [
    '难看', '烂', '垃圾', '差评', '失望', '浪费', '弃剧', '看不下去', '无聊', '尴尬',
    '烂片', '烂剧', '毁了', '毁经典', '注水', '拖沓', '节奏慢', '快进', '跳着看',
    '演技差', '面瘫', '尴尬癌', '辣眼睛', '丑', '油腻', '恶心', '离谱', '奇葩',
    '脑残', '智障', '傻子', '侮辱智商', '逻辑', '不通', 'bug', '穿帮', '抄袭',
    '三观', '不正', '狗血', '玛丽苏', '白莲花', '绿茶', '人设', '崩塌', '崩了',
    '劝退', '拜拜', '再也不看', '踩雷', '坑', '骗', '圈钱', '吃相难看', '烂尾',
    '结尾', '垃圾', '虎头蛇尾', '高开低走', '崩了', '垮了', '扑街', '凉了', '糊了'
]

EMOJI_SENTIMENT = {
    '😊': 0.8, '😄': 0.8, '😍': 0.9, '🥰': 0.9, '😘': 0.85,
    '👍': 0.7, '👏': 0.75, '❤️': 0.9, '🔥': 0.8, '✨': 0.7,
    '😂': 0.6, '🤣': 0.6, '😭': -0.3, '😢': -0.5, '😠': -0.8,
    '😡': -0.9, '👎': -0.7, '💔': -0.8, '🤮': -0.9, '🤢': -0.8
}

INTENSIFIERS = {
    '非常': 1.5, '特别': 1.5, '超级': 1.6, '太': 1.4, '真的': 1.3,
    '好': 1.2, '很': 1.2, '超': 1.4, '巨': 1.4, '爆': 1.5,
    '极其': 1.6, '相当': 1.3, '格外': 1.3, '分外': 1.3
}

NEGATIONS = ['不', '没', '没有', '别', '不要', '非', '否', '无', '未', '莫']

COMMENTS_TEMPLATES = {
    'positive': [
        '这剧{adv}好看！{actor}演技{adv}在线',
        '剧情{adv}紧凑，追{adv}上头了',
        '{adv}推荐！今年看过最好的剧',
        '第{ep}集{adv}精彩，{adv}感动',
        '{actor}演得{adv}好，入坑了',
        '服化道{adv}精美，看得出来很用心',
        '{adv}喜欢这部剧的节奏，不拖沓',
        '今晚的剧情{adv}燃！{adv}期待下一集',
        '这才是良心剧，{adv}值得追',
        '看哭了，{actor}的共情能力{adv}强'
    ],
    'negative': [
        '这剧{adv}难看，{adv}失望',
        '剧情{adv}拖沓，快进着看都嫌慢',
        '{actor}演技{adv}尴尬，看不下去了',
        '什么鬼剧情，逻辑{adv}不通',
        '弃剧了，{adv}浪费时间',
        '人设{adv}崩塌，白瞎了这么好的题材',
        '{adv}狗血，{adv}侮辱智商',
        '节奏{adv}乱，剪辑{adv}差',
        '{adv}失望，再也不看这个导演的剧了',
        '{adv}烂尾，前面白追了'
    ],
    'neutral': [
        '今天更新了，来看一眼',
        '第{ep}集看完了',
        '大家觉得{actor}演得怎么样？',
        '讨论一下今晚的剧情',
        '收视率出来了吗？',
        '今天这集还行吧',
        '有人一起追剧吗？',
        '{ep}集打卡',
        '等更新等得好辛苦',
        '你们觉得接下来剧情会怎么走？'
    ]
}

def clean_text(text):
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+#', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def analyze_sentiment(text):
    text = clean_text(text)
    if not text:
        return 0.5
    
    score = 0.0
    count = 0
    
    chars = list(text)
    n = len(chars)
    
    for i, char in enumerate(chars):
        if char in EMOJI_SENTIMENT:
            score += EMOJI_SENTIMENT[char]
            count += 1
    
    for window_size in range(4, 0, -1):
        for i in range(n - window_size + 1):
            segment = ''.join(chars[i:i + window_size])
            
            if segment in POSITIVE_WORDS:
                multiplier = 1.0
                for j in range(max(0, i - 3), i):
                    prev_char = ''.join(chars[max(0, j):i])
                    for neg in NEGATIONS:
                        if neg in prev_char:
                            multiplier = -1.0
                            break
                    if multiplier < 0:
                        break
                    for inten, val in INTENSIFIERS.items():
                        if inten in prev_char:
                            multiplier = val
                            break
                
                score += 1.0 * multiplier
                count += 1
            
            elif segment in NEGATIVE_WORDS:
                multiplier = 1.0
                for j in range(max(0, i - 3), i):
                    prev_char = ''.join(chars[max(0, j):i])
                    for neg in NEGATIONS:
                        if neg in prev_char:
                            multiplier = -1.0
                            break
                    if multiplier < 0:
                        break
                    for inten, val in INTENSIFIERS.items():
                        if inten in prev_char:
                            multiplier = val
                            break
                
                score += -1.0 * multiplier
                count += 1
    
    if count == 0:
        return 0.5
    
    normalized_score = (score / count + 1) / 2
    return max(0.0, min(1.0, normalized_score))

def generate_comments(episode, drama_genre, actor, rating, num_comments=50):
    comments = []
    adv_words = ['', '非常', '特别', '超级', '太', '真的', '好', '很']
    
    if rating >= 2.5:
        prob_pos, prob_neg, prob_neu = 0.6, 0.15, 0.25
    elif rating >= 1.8:
        prob_pos, prob_neg, prob_neu = 0.4, 0.3, 0.3
    elif rating >= 1.2:
        prob_pos, prob_neg, prob_neu = 0.25, 0.45, 0.3
    else:
        prob_pos, prob_neg, prob_neu = 0.1, 0.6, 0.3
    
    for _ in range(num_comments):
        r = np.random.random()
        if r < prob_pos:
            template_type = 'positive'
        elif r < prob_pos + prob_neg:
            template_type = 'negative'
        else:
            template_type = 'neutral'
        
        template = np.random.choice(COMMENTS_TEMPLATES[template_type])
        adv = np.random.choice(adv_words)
        
        comment = template.format(ep=episode, actor=actor, adv=adv)
        
        if template_type == 'positive' and np.random.random() < 0.3:
            comment += np.random.choice([' 😍', ' 👍', ' 🔥', ' ❤️', ' 👏', ''])
        elif template_type == 'negative' and np.random.random() < 0.3:
            comment += np.random.choice([' 😠', ' 💔', ' 👎', ' 🤮', ''])
        
        sentiment = analyze_sentiment(comment)
        
        comments.append({
            'comment': comment,
            'sentiment': round(sentiment, 3),
            'type': template_type
        })
    
    return pd.DataFrame(comments)

def generate_episode_comments_batch(drama_info, dates, ratings):
    all_comments = []
    actor = drama_info['actor_level'] + '演员'
    
    for i, (date, rating) in enumerate(zip(dates, ratings)):
        episode = i + 1
        num_comments = max(10, int(rating * 20 + np.random.randint(10, 30)))
        
        comments_df = generate_comments(episode, drama_info['genre'], actor, rating, num_comments)
        comments_df['episode'] = episode
        comments_df['date'] = date
        
        all_comments.append(comments_df)
    
    return pd.concat(all_comments, ignore_index=True)

def aggregate_episode_sentiment(comments_df):
    episode_stats = comments_df.groupby('episode').agg(
        avg_sentiment=('sentiment', 'mean'),
        median_sentiment=('sentiment', 'median'),
        std_sentiment=('sentiment', 'std'),
        positive_ratio=('type', lambda x: (x == 'positive').mean()),
        negative_ratio=('type', lambda x: (x == 'negative').mean()),
        neutral_ratio=('type', lambda x: (x == 'neutral').mean()),
        comment_count=('comment', 'count')
    ).reset_index()
    
    return episode_stats

def calculate_sentiment_trend(avg_sentiments, window=3):
    if len(avg_sentiments) < window:
        return np.zeros(len(avg_sentiments))
    
    smoothed = pd.Series(avg_sentiments).rolling(window=window, center=True).mean()
    trend = smoothed.diff().fillna(0).values
    
    return trend

def get_top_keywords(comments_df, top_n=10):
    all_words = defaultdict(int)
    
    for comment in comments_df['comment']:
        for word in POSITIVE_WORDS + NEGATIVE_WORDS:
            if word in comment:
                all_words[word] += 1
    
    sorted_words = sorted(all_words.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return sorted_words

if __name__ == '__main__':
    test_texts = [
        '这部剧非常好看，演员演技在线',
        '剧情太拖沓，看不下去了',
        '今天更新的第5集超级精彩',
        '没有想象中好看，有点失望',
        '不怎么样，一般般吧',
        '这个演员演得太好了，爱了爱了 😍',
        '什么垃圾剧情，太难看了 👎'
    ]
    
    print("Sentiment Analysis Test:")
    for text in test_texts:
        score = analyze_sentiment(text)
        print(f"  '{text}' -> {score:.3f}")
    
    print("\nGenerating sample comments...")
    sample_comments = generate_comments(5, '古装', '一线演员', 2.8, 5)
    print(sample_comments)
