import random
from datetime import datetime


def generate_demo_crawl_data(product_name='智能手机', category='数码产品'):
    platforms = [
        {'name': '京东', 'competitors': ['品牌A旗舰店', '品牌B自营店', '品牌C专营店']},
        {'name': '天猫', 'competitors': ['品牌A官方旗舰店', '品牌B专卖店', '品牌C旗舰店']},
        {'name': '拼多多', 'competitors': ['品牌A百亿补贴', '品牌B品牌馆', '品牌C直销']},
        {'name': '苏宁', 'competitors': ['品牌A自营', '品牌B旗舰店', '品牌C自营']},
    ]
    promo_options = [
        [], ['满2000减200'], ['限时秒杀'], ['新人立减300'],
        ['满2000减200', '限时秒杀'], ['百亿补贴'], ['会员专享9折'],
        ['满2000减200', 'PLUS会员9.5折'], ['直播间专享价'], ['以旧换新补贴500'],
    ]
    base_prices = {
        '品牌A': 4999, '品牌B': 4599, '品牌C': 3999,
        '品牌A旗舰店': 4999, '品牌B自营店': 4599, '品牌C专营店': 3999,
        '品牌A官方旗舰店': 4999, '品牌B专卖店': 4599, '品牌C旗舰店': 3999,
        '品牌A百亿补贴': 4699, '品牌B品牌馆': 4299, '品牌C直销': 3799,
        '品牌A自营': 4999, '品牌B旗舰店': 4499, '品牌C自营': 3999,
    }

    items = []
    for platform in platforms:
        for competitor in platform['competitors']:
            base_price = base_prices.get(competitor, 4500)
            price_variation = random.uniform(-0.08, 0.05)
            original_price = round(base_price * (1 + random.uniform(0, 0.15)), 2)
            current_price = round(base_price * (1 + price_variation), 2)
            discount = round((1 - current_price / original_price) * 100, 1) if original_price > 0 else 0
            promo = random.choice(promo_options)
            stock = random.choice(['有货', '有货', '有货', '预售', '缺货'])

            items.append({
                'product_name': product_name,
                'platform': platform['name'],
                'competitor_name': competitor,
                'original_price': original_price,
                'current_price': current_price,
                'discount': discount,
                'promo_tags': ', '.join(promo) if promo else '无促销',
                'stock_status': stock,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'product_category': category,
                'url': f'https://example.com/product/{hash(competitor) % 10000}',
            })
    return items
