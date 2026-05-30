import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import json


def generate_competitor_data():
    platforms = ['京东', '天猫', '拼多多', '苏宁']
    competitors = ['品牌A旗舰店', '品牌B自营店', '品牌C专营店', '品牌D专卖店', '品牌E旗舰店']
    promo_options = [
        '', '满2000减200', '限时秒杀', '新人立减300', '百亿补贴',
        '会员专享9折', '满2000减200,限时秒杀', '直播间专享价', '以旧换新补贴500',
    ]
    base_prices = {
        '品牌A旗舰店': 4999, '品牌B自营店': 4599, '品牌C专营店': 3999,
        '品牌D专卖店': 4299, '品牌E旗舰店': 4799,
    }
    records = []
    for platform in platforms:
        for competitor in competitors:
            base = base_prices[competitor]
            variation = random.uniform(-0.06, 0.04)
            original = round(base * (1 + random.uniform(0, 0.12)), 2)
            current = round(base * (1 + variation), 2)
            discount = round((1 - current / original) * 100, 1) if original > 0 else 0
            promo = random.choice(promo_options)
            stock = random.choice(['有货', '有货', '有货', '预售'])
            records.append({
                'product_name': '智能手机',
                'platform': platform,
                'competitor_name': competitor,
                'original_price': original,
                'current_price': current,
                'discount': discount,
                'promo_tags': promo if promo else '无促销',
                'stock_status': stock,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'product_category': '数码产品',
            })
    return pd.DataFrame(records)


def generate_price_history(our_price=4699, days=90):
    dates = [datetime.now() - timedelta(days=i) for i in range(days, 0, -1)]
    np.random.seed(42)
    trend = np.linspace(0, -0.03, days)
    noise = np.random.normal(0, 0.015, days)
    our_prices = our_price * (1 + trend + noise)
    our_prices = np.round(our_prices, 2)

    comp_a_prices = our_prices * np.random.uniform(1.03, 1.12, days)
    comp_b_prices = our_prices * np.random.uniform(0.92, 1.0, days)
    comp_c_prices = our_prices * np.random.uniform(0.85, 0.95, days)
    market_avg = (our_prices + comp_a_prices + comp_b_prices + comp_c_prices) / 4

    records = []
    for i, date in enumerate(dates):
        records.append({'date': date, 'source': '本店', 'price': our_prices[i]})
        records.append({'date': date, 'source': '品牌A', 'price': round(comp_a_prices[i], 2)})
        records.append({'date': date, 'source': '品牌B', 'price': round(comp_b_prices[i], 2)})
        records.append({'date': date, 'source': '品牌C', 'price': round(comp_c_prices[i], 2)})
        records.append({'date': date, 'source': '市场均价', 'price': round(market_avg[i], 2)})
    return pd.DataFrame(records)


def generate_our_price_history(our_price=4699, days=90):
    dates = [datetime.now() - timedelta(days=i) for i in range(days, 0, -1)]
    np.random.seed(42)
    trend = np.linspace(0, -0.03, days)
    noise = np.random.normal(0, 0.015, days)
    prices = our_price * (1 + trend + noise)
    return pd.DataFrame({
        'date': dates,
        'price': np.round(prices, 2),
    })


def ensure_data_dir():
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def save_demo_data():
    data_dir = ensure_data_dir()
    comp_df = generate_competitor_data()
    comp_df.to_csv(os.path.join(data_dir, 'competitor_prices.csv'), index=False, encoding='utf-8-sig')
    hist_df = generate_price_history()
    hist_df.to_csv(os.path.join(data_dir, 'price_history.csv'), index=False, encoding='utf-8-sig')
    return comp_df, hist_df
