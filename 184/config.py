import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'comments.db')
CSV_PATH = os.path.join(DATA_DIR, 'comments.csv')

ASPECTS = ['价格', '质量', '物流', '服务']

ASPECT_KEYWORDS = {
    '价格': ['价格', '便宜', '贵', '划算', '性价比', '实惠', '不值', '高价', '低价', '优惠', '促销', '打折'],
    '质量': ['质量', '品质', '做工', '耐用', '结实', '精致', '粗糙', '劣质', '好用', '难用', '正品', '假货'],
    '物流': ['物流', '快递', '发货', '配送', '速度', '慢', '快', '准时', '延误', '包装', '破损'],
    '服务': ['服务', '客服', '售后', '态度', '耐心', '热情', '冷淡', '推诿', '解决', '回复', '专业']
}

SENTIMENT_THRESHOLD = 0.6

PRODUCT_CATEGORIES = ['手机数码', '家用电器', '服装鞋帽', '食品生鲜', '美妆护肤', '家居用品']
