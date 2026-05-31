import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC_VIEWER = 'live_viewer_events'
KAFKA_TOPIC_CLICK = 'product_click_events'
KAFKA_TOPIC_ORDER = 'order_events'
KAFKA_TOPIC_CHAT = 'chat_events'
KAFKA_TOPIC_COMPETITOR = 'competitor_events'

WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', 8765))

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

FLINK_PARALLELISM = 2

PRODUCTS = [
    {'id': 1, 'name': '口红套装', 'price': 199, 'cost': 60, 'category': '美妆', 'stock': 500},
    {'id': 2, 'name': '护肤精华', 'price': 399, 'cost': 120, 'category': '美妆', 'stock': 300},
    {'id': 3, 'name': '运动鞋', 'price': 599, 'cost': 200, 'category': '服饰', 'stock': 200},
    {'id': 4, 'name': '蓝牙耳机', 'price': 299, 'cost': 90, 'category': '数码', 'stock': 800},
    {'id': 5, 'name': '保温杯', 'price': 89, 'cost': 25, 'category': '家居', 'stock': 1200},
    {'id': 6, 'name': '零食大礼包', 'price': 128, 'cost': 45, 'category': '食品', 'stock': 900},
]

COMPETITORS = [
    {'id': 1, 'name': '竞品直播间A', 'product': '口红套装', 'product_id': 1, 'base_price': 189},
    {'id': 2, 'name': '竞品直播间B', 'product': '护肤精华', 'product_id': 2, 'base_price': 379},
    {'id': 3, 'name': '竞品直播间C', 'product': '运动鞋', 'product_id': 3, 'base_price': 549},
]

SENTIMENT_KEYWORDS = {
    'positive': {
        'words': ['好', '棒', '赞', '喜欢', '不错', '值得', '已下单', '回购', '推荐',
                  '实惠', '划算', '优惠', '好看', '漂亮', '好用', '满意', '爱上',
                  '绝了', '牛', '冲', '抢', '买', '想要', '心动'],
        'weight': 1.0
    },
    'negative': {
        'words': ['贵', '差', '假', '骗', '退款', '投诉', '慢', '烂', '坑', '不靠谱',
                  '失望', '难用', '垃圾', '不值', '黑心', '质量差', '过期', '破损'],
        'weight': -1.0
    },
    'neutral': {
        'words': ['看看', '考虑', '对比', '还行', '一般', '了解', '观望', '问问'],
        'weight': 0.0
    },
    'intent_buy': {
        'words': ['怎么买', '链接', '下单', '包邮', '优惠', '折扣', '满减', '赠品',
                  '怎么付', '能便宜', '团购', '拼单', '什么时候发货'],
        'weight': 0.8
    }
}

HOT_WORD_CATEGORIES = {
    'price': ['优惠', '折扣', '便宜', '划算', '满减', '减价', '特价', '限时', '秒杀', '促销'],
    'quality': ['质量', '正品', '品牌', '材质', '效果', '好用', '耐用', '真货'],
    'logistics': ['发货', '快递', '包邮', '到货', '物流', '配送', '仓储'],
    'service': ['售后', '退换', '客服', '保修', '保障', '赔付'],
    'feature': ['新款', '限量', '独家', '爆款', '网红', '明星同款', '热卖'],
}

CHAT_TEMPLATES = {
    'positive': [
        '这个{product}真的太好了！',
        '已下单{product}！',
        '{product}质量绝了',
        '回购{product}好几次了',
        '推荐{product}！',
        '{product}太划算了',
        '喜欢{product}！冲冲冲',
        '{product}漂亮！心动了',
    ],
    'negative': [
        '{product}太贵了吧',
        '上次买的{product}质量差',
        '{product}发货太慢了',
        '{product}不值这个价',
        '{product}有破损',
    ],
    'neutral': [
        '看看{product}再说',
        '{product}和竞品对比怎样',
        '了解下{product}',
        '{product}还行吧',
    ],
    'intent_buy': [
        '{product}怎么买？',
        '{product}有优惠吗？',
        '{product}包邮吗？',
        '{product}什么时候发货？',
        '{product}有满减吗？',
        '{product}有赠品吗？',
        '{product}能便宜点吗？',
    ],
}

GUIDED_SCRIPT_TEMPLATES = {
    'low_conversion': [
        '家人们！{product}限时秒杀，错过再等一年！现在下单立省{save}元！',
        '还犹豫什么？{product}库存只剩{stock}件，手慢无！前50名下单额外送赠品！',
        '直播间专属价！{product}原价{price}元，今天只要{sale_price}元！限量抢购！',
    ],
    'high_complaint': [
        '感谢大家的反馈！关于{product}的问题我们已经注意到了，现在下单的宝宝享受无忧退换保障！',
        '理解大家的顾虑！{product}现在支持7天无理由退换，质量问题包赔！放心拍！',
    ],
    'high_question': [
        '很多宝宝问{product}的{feature}，这里统一回复：{answer}',
        '{product}核心卖点：{feature}，相比同类型产品优势明显！',
    ],
    'heat_dropping': [
        '来来来！直播间红包雨马上开启！点赞破{target}继续加码！',
        '下一波福利品马上上线！只要{price}元！先关注不迷路！',
        '家人们动动手指点个赞！点赞到{target}抽免单！',
    ],
    'hot_product': [
        '{product}卖爆了！已经卖出{sold}件！库存告急，还没下单的宝宝抓紧！',
        '{product}好评如潮！回购率超高！今天最后{stock}件，抢完即止！',
    ],
    'competitor_price': [
        '别家{product}卖{comp_price}元？我们直播间只要{our_price}元！还送赠品！',
        '比价随便比！{product}我们保证全网最低价！买贵补差！',
    ],
}

PERSONA_TAGS = {
    'age_groups': ['18-24', '25-30', '31-40', '40+'],
    'genders': ['female', 'male'],
    'interests': ['美妆', '服饰', '数码', '家居', '食品', '母婴', '运动'],
    'consume_levels': ['high', 'medium', 'low'],
    'regions': ['一线城市', '二线城市', '三线城市', '四线及以下'],
}

VIRTUAL_STREAMER_CONFIG = {
    'name': '小智AI主播',
    'avatar': '🤖',
    'tick_interval_seconds': 3,
    'max_speech_length': 50,
    'personality': 'energetic',
    'strategies': {
        'greeting': ['欢迎来到直播间！', '家人们好！今天福利多多！'],
        'product_intro': [
            '接下来给大家介绍{product}，只要{price}元！',
            '{product}来啦！直播专享价{price}元，错过不再有！',
        ],
        'urgency': [
            '{product}库存不多了！只剩{stock}件！',
            '最后{stock}件{product}，抢完就下架！',
        ],
        'interaction': [
            '宝宝们觉得{product}怎么样？扣1想要！',
            '想要的扣想要！{product}马上上链接！',
        ],
        'closing': [
            '感谢宝宝们的陪伴！下一波福利更精彩！',
            '别走开！马上有更大力度的优惠！',
        ],
    },
}

HOT_PREDICTION_CONFIG = {
    'velocity_window': 10,
    'acceleration_window': 20,
    'hot_threshold_score': 70,
    'trend_weights': {
        'click_velocity': 0.25,
        'order_velocity': 0.25,
        'click_acceleration': 0.20,
        'order_acceleration': 0.15,
        'sentiment_momentum': 0.15,
    },
    'prediction_horizon_minutes': 10,
}
