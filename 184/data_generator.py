import random
import pandas as pd
from datetime import datetime, timedelta
from config import PRODUCT_CATEGORIES

COMMENT_TEMPLATES = {
    'positive': {
        '价格': [
            '价格非常实惠，性价比很高，物超所值！',
            '这个价格能买到这么好的东西，太划算了！',
            '比实体店便宜很多，非常满意！',
            '价格公道，质量也不错，推荐购买！',
            '赶上促销活动买的，太值了！',
            '虽然有点小贵，但是一分钱一分货，值得！'
        ],
        '质量': [
            '质量很好，做工精细，非常满意！',
            '品质不错，用了一段时间没有任何问题。',
            '和描述的一样，是正品，值得信赖！',
            '做工很精致，细节处理得很好。',
            '用料很扎实，感觉能用很久。',
            '超出预期，质量比想象中好太多！'
        ],
        '物流': [
            '物流很快，第二天就收到了！',
            '快递小哥服务很好，包装也很完整。',
            '发货速度快，配送准时，点赞！',
            '包装很严实，没有任何破损。',
            '物流给力，比预计时间提前到了！',
            '顺丰就是快，服务也很棒！'
        ],
        '服务': [
            '客服态度很好，有问必答，很专业！',
            '售后服务很到位，解决问题很及时。',
            '商家服务态度很好，耐心解答我的问题。',
            '客服很热情，购物体验非常棒！',
            '回复很快，问题解决得很满意。',
            '服务周到，下次还会再来！'
        ],
        'general': [
            '整体来说很满意，已经推荐给朋友了！',
            '这次购物体验很好，下次还会回购。',
            '商品不错，和预期相符，好评！',
            '非常满意的一次购物，给五星好评！',
            '物有所值，推荐大家购买！',
            '收到货很惊喜，比想象中好！'
        ]
    },
    'negative': {
        '价格': [
            '价格太贵了，感觉不值这个价。',
            '性价比太低，买后悔了。',
            '比别家贵很多，不推荐购买。',
            '价格虚高，质量配不上价格。',
            '以为会便宜，结果还是买贵了。',
            '不值这个价钱，有点失望。'
        ],
        '质量': [
            '质量很差，用了几天就坏了。',
            '做工粗糙，和图片描述不符。',
            '感觉是假货，质量太差了。',
            '用起来很不顺畅，不推荐。',
            '质量一般，和价格不成正比。',
            '收到的商品有瑕疵，很不满意！'
        ],
        '物流': [
            '物流太慢了，等了好多天才到。',
            '包装很差，收到货都破损了。',
            '快递员态度不好，很不愉快。',
            '发货很慢，催了好几次才发。',
            '物流信息一直不更新，很着急。',
            '配送延迟，体验很差！'
        ],
        '服务': [
            '客服态度很差，问半天不回复。',
            '售后推诿，问题一直没解决。',
            '服务太糟糕了，再也不来了。',
            '客服很不专业，问什么都不知道。',
            '退款流程太麻烦，体验很差。',
            '联系不上客服，很生气！'
        ],
        'general': [
            '整体体验很差，非常失望。',
            '不会再买了，很糟糕的购物体验。',
            '和描述相差太远，不推荐。',
            '后悔买了，建议大家慎重考虑。',
            '这次购物很不愉快，差评！',
            '实物与图片严重不符，太坑了！'
        ]
    },
    'neutral': {
        '价格': [
            '价格中规中矩，不算贵也不便宜。',
            '价格还行，看个人需求吧。',
            '价位合理，有需要的可以考虑。',
            '价格一般，没有特别惊喜。'
        ],
        '质量': [
            '质量一般吧，能用。',
            '品质还可以，符合这个价位。',
            '中规中矩，没有特别出彩的地方。',
            '还行，和预期差不多。'
        ],
        '物流': [
            '物流速度一般，正常时效。',
            '快递还行，没有特别快也不慢。',
            '包装一般，还好没破损。',
            '发货速度正常，能接受。'
        ],
        '服务': [
            '客服态度一般，有问有答吧。',
            '服务还行，没什么特别的。',
            '中规中矩的服务，不好不坏。',
            '回复速度一般，解决了问题。'
        ],
        'general': [
            '整体一般，不好不坏。',
            '还可以吧，看个人喜好。',
            '没什么特别的，普普通通。',
            '符合预期，没有惊喜也没有失望。'
        ]
    }
}

PRODUCT_NAMES = {
    '手机数码': ['iPhone 15', '小米14', '华为Mate60', 'OPPO Find X7', 'vivo X100', '三星S24', '荣耀Magic6', '一加12'],
    '家用电器': ['海尔冰箱', '美的空调', '格力空调', '小米电视', 'TCL电视', '九阳豆浆机', '苏泊尔电饭煲', '飞利浦吸尘器'],
    '服装鞋帽': ['耐克运动鞋', '阿迪达斯卫衣', '优衣库T恤', '李宁运动裤', '波司登羽绒服', '森马牛仔裤', '安踏跑步鞋', '太平鸟连衣裙'],
    '食品生鲜': ['三只松鼠坚果', '良品铺子零食', '蒙牛纯牛奶', '伊利酸奶', '五常大米', '智利车厘子', '澳洲牛排', '阳澄湖大闸蟹'],
    '美妆护肤': ['SK-II神仙水', '兰蔻小黑瓶', '雅诗兰黛眼霜', '资生堂防晒霜', '欧莱雅洗面奶', '完美日记口红', '花西子气垫', '自然堂面膜'],
    '家居用品': ['宜家沙发', '全友床架', '喜临门床垫', '欧普台灯', '得力收纳盒', '乐扣乐扣保鲜盒', '双立人刀具', '苏泊尔锅具']
}

def generate_random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86399)
    return start_date + timedelta(days=random_days, seconds=random_seconds)

def generate_comment():
    category = random.choice(PRODUCT_CATEGORIES)
    product = random.choice(PRODUCT_NAMES[category])
    
    sentiment_choice = random.choices(['positive', 'negative', 'neutral'], weights=[0.6, 0.25, 0.15])[0]
    
    num_aspects = random.randint(1, 3)
    available_aspects = ['价格', '质量', '物流', '服务', 'general']
    selected_aspects = random.sample(available_aspects, num_aspects)
    
    comment_text = ''
    for aspect in selected_aspects:
        templates = COMMENT_TEMPLATES[sentiment_choice][aspect]
        comment_text += random.choice(templates) + ' '
    
    comment_text = comment_text.strip()
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    comment_time = generate_random_date(start_date, end_date)
    
    rating_base = {'positive': 5, 'neutral': 3, 'negative': 1}
    rating = rating_base[sentiment_choice] + random.choice([-0.5, 0, 0.5])
    rating = max(1, min(5, rating))
    
    return {
        'comment_id': '',
        'product_name': product,
        'category': category,
        'comment_text': comment_text,
        'rating': round(rating, 1),
        'comment_time': comment_time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_name': f'用户{random.randint(1000, 9999)}'
    }

def generate_comments(num_comments=1000):
    comments = []
    for i in range(num_comments):
        comment = generate_comment()
        comment['comment_id'] = f'C{i+1:06d}'
        comments.append(comment)
    return comments

def save_comments_to_csv(comments, filepath):
    df = pd.DataFrame(comments)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f'已生成 {len(comments)} 条评论数据，保存至 {filepath}')

if __name__ == '__main__':
    from config import CSV_PATH
    comments = generate_comments(1000)
    save_comments_to_csv(comments, CSV_PATH)
