import pandas as pd
from collections import defaultdict
from config import ASPECTS


def get_competitor_products():
    return {
        'iPhone 15': ['小米14', '华为Mate60', 'OPPO Find X7', 'vivo X100', '三星S24'],
        '小米14': ['iPhone 15', '华为Mate60', 'OPPO Find X7', 'vivo X100', '一加12'],
        '华为Mate60': ['iPhone 15', '小米14', 'OPPO Find X7', 'vivo X100', '荣耀Magic6'],
        '海尔冰箱': ['美的冰箱', '格力冰箱', '西门子冰箱', '容声冰箱', '卡萨帝冰箱'],
        '美的空调': ['格力空调', '海尔空调', '奥克斯空调', 'TCL空调', '小米空调'],
        '格力空调': ['美的空调', '海尔空调', '奥克斯空调', 'TCL空调', '小米空调'],
        '耐克运动鞋': ['阿迪达斯运动鞋', '安踏运动鞋', '李宁运动鞋', '特步运动鞋', '361°运动鞋'],
        '阿迪达斯卫衣': ['耐克卫衣', '李宁卫衣', '优衣库卫衣', '安踏卫衣', '彪马卫衣'],
        '三只松鼠坚果': ['良品铺子坚果', '百草味坚果', '恰恰坚果', '来伊份坚果', '沃隆坚果'],
        '良品铺子零食': ['三只松鼠零食', '百草味零食', '恰恰零食', '来伊份零食', '盐津铺子零食'],
        'SK-II神仙水': ['兰蔻小黑瓶', '雅诗兰黛小棕瓶', '资生堂红腰子', '海蓝之谜精粹水'],
        '兰蔻小黑瓶': ['SK-II神仙水', '雅诗兰黛小棕瓶', '资生堂红腰子', '欧莱雅黑精华'],
        '宜家沙发': ['全友沙发', '顾家沙发', '左右沙发', '芝华仕沙发', '林氏木业沙发'],
        '全友床架': ['宜家床架', '顾家床架', '左右床架', '芝华仕床架', '林氏木业床架']
    }


def analyze_competitor_comparison(main_product, df):
    competitors = get_competitor_products().get(main_product, [])
    
    if not competitors:
        all_products = df['product_name'].unique().tolist()
        competitors = [p for p in all_products if p != main_product][:5]
    
    all_products = [main_product] + competitors
    product_data = {}
    
    for product in all_products:
        product_df = df[df['product_name'] == product]
        if len(product_df) == 0:
            continue
        
        total = len(product_df)
        positive = len(product_df[product_df['sentiment_label'] == 'positive'])
        negative = len(product_df[product_df['sentiment_label'] == 'negative'])
        neutral = len(product_df[product_df['sentiment_label'] == 'neutral'])
        
        aspect_stats = {}
        for aspect in ASPECTS:
            aspect_df = product_df[product_df['aspects'].str.contains(aspect, na=False)]
            if len(aspect_df) > 0:
                aspect_positive = len(aspect_df[aspect_df['sentiment_label'] == 'positive'])
                aspect_stats[aspect] = {
                    'count': len(aspect_df),
                    'positive_rate': round(aspect_positive / len(aspect_df) * 100, 2),
                    'avg_score': round(aspect_df['sentiment_score'].mean(), 4)
                }
        
        product_data[product] = {
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_rate': round(positive / total * 100, 2),
            'negative_rate': round(negative / total * 100, 2),
            'avg_score': round(product_df['sentiment_score'].mean(), 4),
            'avg_rating': round(product_df['rating'].mean(), 2),
            'aspect_stats': aspect_stats
        }
    
    comparison = {
        'main_product': main_product,
        'competitors': competitors,
        'products': product_data,
        'ranking': sorted(
            product_data.items(),
            key=lambda x: x[1]['positive_rate'],
            reverse=True
        )
    }
    
    return comparison


def get_product_sentiment_trend(product_name, df, days=30):
    product_df = df[df['product_name'] == product_name].copy()
    if len(product_df) == 0:
        return []
    
    product_df['date'] = pd.to_datetime(product_df['comment_time']).dt.strftime('%Y-%m-%d')
    
    trend_data = product_df.groupby('date').agg({
        'sentiment_score': 'mean',
        'comment_id': 'count'
    }).reset_index()
    
    trend_data.columns = ['date', 'avg_score', 'count']
    trend_data['avg_score'] = trend_data['avg_score'].round(4)
    
    return trend_data.tail(days).to_dict('records')


def get_aspect_comparison(main_product, df):
    competitors = get_competitor_products().get(main_product, [])
    all_products = [main_product] + competitors
    
    aspect_comparison = defaultdict(dict)
    
    for product in all_products:
        product_df = df[df['product_name'] == product]
        if len(product_df) == 0:
            continue
        
        for aspect in ASPECTS:
            aspect_df = product_df[product_df['aspects'].str.contains(aspect, na=False)]
            if len(aspect_df) > 0:
                positive = len(aspect_df[aspect_df['sentiment_label'] == 'positive'])
                aspect_comparison[aspect][product] = {
                    'count': len(aspect_df),
                    'positive_rate': round(positive / len(aspect_df) * 100, 2)
                }
    
    return dict(aspect_comparison)


if __name__ == '__main__':
    from data_processor import load_all_comments
    
    df = load_all_comments()
    if len(df) > 0:
        main_product = df['product_name'].iloc[0]
        comparison = analyze_competitor_comparison(main_product, df)
        
        print(f'主商品: {comparison["main_product"]}')
        print(f'竞品: {comparison["competitors"]}')
        print('\n情感排名:')
        for rank, (product, data) in enumerate(comparison['ranking'], 1):
            print(f'{rank}. {product}: 正向率 {data["positive_rate"]}%, 平均分 {data["avg_score"]}')
