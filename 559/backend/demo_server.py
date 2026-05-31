import asyncio
import json
import random
import time
import websockets
from datetime import datetime
from collections import deque, defaultdict
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config


class SentimentAnalyzer:
    def __init__(self):
        self.keywords = config.SENTIMENT_KEYWORDS
        self.chat_buffer = deque(maxlen=200)
        self.sentiment_counts = defaultdict(int)

    def analyze_message(self, message):
        result = {
            'positive': 0, 'negative': 0, 'neutral': 0, 'intent_buy': 0,
            'matched_words': [], 'sentiment_score': 0
        }
        for category, config_item in self.keywords.items():
            for word in config_item['words']:
                if word in message:
                    result[category] += 1
                    result['matched_words'].append({'word': word, 'category': category})
                    result['sentiment_score'] += config_item['weight']
        return result

    def add_message(self, message, product_name=''):
        analysis = self.analyze_message(message)
        self.chat_buffer.append({
            'message': message,
            'product': product_name,
            'timestamp': datetime.now().isoformat(),
            **analysis
        })
        for cat in ['positive', 'negative', 'neutral', 'intent_buy']:
            self.sentiment_counts[cat] += analysis[cat]
        return analysis

    def get_sentiment_summary(self):
        total = sum(self.sentiment_counts.values())
        if total == 0:
            return {
                'positive_ratio': 0, 'negative_ratio': 0,
                'neutral_ratio': 0, 'intent_buy_ratio': 0,
                'overall_score': 0, 'trend': 'stable'
            }
        positive_ratio = self.sentiment_counts['positive'] / total
        negative_ratio = self.sentiment_counts['negative'] / total
        neutral_ratio = self.sentiment_counts['neutral'] / total
        intent_buy_ratio = self.sentiment_counts['intent_buy'] / total
        recent_messages = list(self.chat_buffer)[-50:]
        if len(recent_messages) >= 10:
            recent_score = sum(m['sentiment_score'] for m in recent_messages[-10:]) / 10
            older_score = sum(m['sentiment_score'] for m in recent_messages[:10]) / min(len(recent_messages[:10]), 1)
            if recent_score > older_score + 0.5:
                trend = 'rising'
            elif recent_score < older_score - 0.5:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        overall_score = (
            positive_ratio * 40 + intent_buy_ratio * 30 +
            (1 - negative_ratio) * 20 + neutral_ratio * 10
        )
        return {
            'positive_ratio': round(positive_ratio * 100, 1),
            'negative_ratio': round(negative_ratio * 100, 1),
            'neutral_ratio': round(neutral_ratio * 100, 1),
            'intent_buy_ratio': round(intent_buy_ratio * 100, 1),
            'overall_score': round(overall_score, 1),
            'trend': trend
        }

    def get_recent_sentiment_momentum(self, window=10):
        recent = list(self.chat_buffer)[-window:]
        if not recent:
            return 0
        return sum(m['sentiment_score'] for m in recent) / len(recent)


class HotWordExtractor:
    def __init__(self):
        self.word_freq = defaultdict(int)
        self.category_freq = defaultdict(lambda: defaultdict(int))
        self.hot_word_categories = config.HOT_WORD_CATEGORIES

    def extract_from_message(self, message, product_name=''):
        for category, words in self.hot_word_categories.items():
            for word in words:
                if word in message:
                    self.word_freq[word] += 1
                    self.category_freq[category][word] += 1

    def get_top_hot_words(self, top_n=10):
        sorted_words = sorted(self.word_freq.items(), key=lambda x: x[1], reverse=True)
        return [
            {'word': word, 'count': count, 'category': self._get_word_category(word)}
            for word, count in sorted_words[:top_n]
        ]

    def get_category_summary(self):
        result = {}
        for category, word_counts in self.category_freq.items():
            total = sum(word_counts.values())
            top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            result[category] = {
                'total_count': total,
                'top_words': [{'word': w, 'count': c} for w, c in top_words],
                'heat_level': 'high' if total > 30 else 'medium' if total > 10 else 'low'
            }
        return result

    def _get_word_category(self, word):
        for category, words in self.hot_word_categories.items():
            if word in words:
                return category
        return 'other'


class GuidedScriptGenerator:
    def __init__(self):
        self.templates = config.GUIDED_SCRIPT_TEMPLATES

    def generate_scripts(self, context):
        scripts = []
        if context.get('conversion_rate', 100) < 3:
            product = context.get('hot_product', config.PRODUCTS[0])
            stock = product.get('stock', 100)
            price = product.get('price', 100)
            save = random.randint(20, 50)
            sale_price = price - save
            template = random.choice(self.templates['low_conversion'])
            script = template.format(
                product=product['name'], stock=max(stock - random.randint(10, 50), 5),
                price=price, save=save, sale_price=sale_price
            )
            scripts.append({
                'type': 'conversion_boost', 'priority': 'high',
                'script': script,
                'reason': f'当前转化率{context["conversion_rate"]:.1f}%，低于3%阈值'
            })
        sentiment = context.get('sentiment_summary', {})
        if sentiment.get('negative_ratio', 0) > 15:
            product = context.get('hot_product', config.PRODUCTS[0])
            template = random.choice(self.templates['high_complaint'])
            script = template.format(product=product['name'])
            scripts.append({
                'type': 'damage_control', 'priority': 'urgent',
                'script': script,
                'reason': f'负面评论占比{sentiment["negative_ratio"]:.1f}%，需要安抚用户'
            })
        if sentiment.get('intent_buy_ratio', 0) > 20:
            product = context.get('hot_product', config.PRODUCTS[0])
            hot_words = context.get('hot_words', [])
            feature = hot_words[0]['word'] if hot_words else '品质'
            answer = '全部支持，放心购买！'
            template = random.choice(self.templates['high_question'])
            script = template.format(product=product['name'], feature=feature, answer=answer)
            scripts.append({
                'type': 'question_response', 'priority': 'medium',
                'script': script,
                'reason': f'购买意向评论占比{sentiment["intent_buy_ratio"]:.1f}%，用户问题多'
            })
        if context.get('heat_score', 100) < 40:
            template = random.choice(self.templates['heat_dropping'])
            target = context.get('current_viewers', 1000) * 2
            price = random.choice([9.9, 19.9, 29.9])
            script = template.format(target=target, price=price)
            scripts.append({
                'type': 'heat_boost', 'priority': 'high',
                'script': script,
                'reason': f'热度指数{context["heat_score"]:.1f}，低于40阈值'
            })
        hot_product = context.get('hot_product')
        if hot_product:
            sold = context.get('product_orders', {}).get(hot_product['name'], {}).get('count', 0)
            if sold > 5:
                template = random.choice(self.templates['hot_product'])
                stock = max(hot_product.get('stock', 100) - sold * 2, 5)
                script = template.format(product=hot_product['name'], sold=sold, stock=stock)
                scripts.append({
                    'type': 'hot_product_push', 'priority': 'medium',
                    'script': script,
                    'reason': f'{hot_product["name"]}已售{sold}件，属于爆款'
                })
        competitor_data = context.get('competitor_data', {})
        for comp in competitor_data.values():
            our_product = next(
                (p for p in config.PRODUCTS if p['id'] == comp.get('product_id')), None
            )
            if our_product and our_product['price'] <= comp['current_price']:
                template = random.choice(self.templates['competitor_price'])
                script = template.format(
                    product=our_product['name'],
                    comp_price=comp['current_price'],
                    our_price=our_product['price']
                )
                scripts.append({
                    'type': 'price_advantage', 'priority': 'medium',
                    'script': script,
                    'reason': f'竞品{comp["competitor_name"]}同款售价¥{comp["current_price"]}，我们有价格优势'
                })
                break
        scripts.sort(key=lambda x: {'urgent': 0, 'high': 1, 'medium': 2}.get(x['priority'], 3))
        return scripts[:5]


class MultiObjectiveOptimizer:
    def __init__(self):
        self.w_click_rate = 0.35
        self.w_profit_rate = 0.35
        self.w_stock_urgency = 0.30

    def optimize(self, products, click_data, order_data, stock_data, persona_boost=None):
        results = []
        for product in products:
            name = product['name']
            clicks = click_data.get(name, 0)
            orders = order_data.get(name, {}).get('count', 0)
            stock = stock_data.get(name, product.get('stock', 100))
            click_rate = (orders / clicks * 100) if clicks > 0 else 0
            profit_rate = ((product['price'] - product['cost']) / product['price'] * 100) if product['price'] > 0 else 0
            initial_stock = product.get('stock', 100)
            stock_ratio = stock / initial_stock if initial_stock > 0 else 0
            if stock_ratio < 0.2:
                stock_urgency = 95 + (0.2 - stock_ratio) * 25
            elif stock_ratio < 0.5:
                stock_urgency = 60 + (0.5 - stock_ratio) * 116
            else:
                stock_urgency = stock_ratio * 30
            click_rate_norm = min(click_rate / 15, 1) * 100
            profit_rate_norm = min(profit_rate / 80, 1) * 100
            stock_urgency_norm = min(stock_urgency, 100)
            composite_score = (
                self.w_click_rate * click_rate_norm +
                self.w_profit_rate * profit_rate_norm +
                self.w_stock_urgency * stock_urgency_norm
            )
            if persona_boost and product['category'] in persona_boost.get('top_interests', []):
                composite_score *= (1 + persona_boost.get('interest_multiplier', 0.15))
            if persona_boost and product['price'] <= persona_boost.get('price_sensitivity', 200):
                composite_score *= (1 + persona_boost.get('price_multiplier', 0.10))
            stock_status = 'danger' if stock_ratio < 0.2 else 'warning' if stock_ratio < 0.5 else 'normal'
            results.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'cost': product['cost'],
                'category': product['category'],
                'stock': stock,
                'initial_stock': initial_stock,
                'click_rate': round(click_rate, 2),
                'profit_rate': round(profit_rate, 2),
                'stock_urgency': round(stock_urgency, 1),
                'stock_status': stock_status,
                'composite_score': round(composite_score, 2),
                'persona_boosted': bool(persona_boost and (
                    product['category'] in persona_boost.get('top_interests', []) or
                    product['price'] <= persona_boost.get('price_sensitivity', 200)
                )),
                'objectives': {
                    'click_rate': round(click_rate_norm, 1),
                    'profit_rate': round(profit_rate_norm, 1),
                    'stock_urgency': round(stock_urgency_norm, 1)
                }
            })
        results.sort(key=lambda x: x['composite_score'], reverse=True)
        return results


class UserPersonaTracker:
    def __init__(self):
        self.tags = config.PERSONA_TAGS
        self.age_distribution = defaultdict(int)
        self.gender_distribution = defaultdict(int)
        self.interest_distribution = defaultdict(int)
        self.consume_level_distribution = defaultdict(int)
        self.region_distribution = defaultdict(int)
        self.total_users = 0
        self.user_actions = deque(maxlen=500)
        self._init_random_distribution()

    def _init_random_distribution(self):
        for _ in range(random.randint(800, 2000)):
            self.add_random_user()

    def add_random_user(self):
        age = random.choices(self.tags['age_groups'], weights=[30, 35, 25, 10])[0]
        gender = random.choices(self.tags['genders'], weights=[70, 30])[0]
        interest = random.choices(self.tags['interests'], weights=[25, 20, 15, 12, 15, 8, 5])[0]
        consume_level = random.choices(self.tags['consume_levels'], weights=[20, 50, 30])[0]
        region = random.choices(self.tags['regions'], weights=[30, 35, 25, 10])[0]
        self.age_distribution[age] += 1
        self.gender_distribution[gender] += 1
        self.interest_distribution[interest] += 1
        self.consume_level_distribution[consume_level] += 1
        self.region_distribution[region] += 1
        self.total_users += 1

    def record_action(self, action_type, product_name='', category=''):
        age = random.choices(self.tags['age_groups'], weights=[30, 35, 25, 10])[0]
        gender = random.choices(self.tags['genders'], weights=[70, 30])[0]
        interest = category if category in self.tags['interests'] else random.choice(self.tags['interests'])
        consume_level = random.choices(self.tags['consume_levels'], weights=[20, 50, 30])[0]
        self.user_actions.append({
            'action': action_type,
            'product': product_name,
            'category': category,
            'age': age,
            'gender': gender,
            'interest': interest,
            'consume_level': consume_level,
            'timestamp': datetime.now().isoformat()
        })
        if action_type == 'click':
            self.interest_distribution[interest] += random.randint(1, 3)
        elif action_type == 'order':
            self.age_distribution[age] += 2
            self.interest_distribution[interest] += 3
            self.consume_level_distribution[consume_level] += 2

    def tick_update(self):
        if random.random() < 0.3:
            self.add_random_user()
        if random.random() < 0.1 and self.total_users > 0:
            rm_age = random.choice(self.tags['age_groups'])
            if self.age_distribution[rm_age] > 0:
                self.age_distribution[rm_age] = max(0, self.age_distribution[rm_age] - 1)
                self.total_users = max(0, self.total_users - 1)

    def get_persona_summary(self):
        total = max(self.total_users, 1)
        age_dist = {k: round(v / total * 100, 1) for k, v in sorted(self.age_distribution.items())}
        gender_dist = {k: round(v / total * 100, 1) for k, v in self.gender_distribution.items()}
        sorted_interests = sorted(self.interest_distribution.items(), key=lambda x: x[1], reverse=True)
        top_interests = [k for k, v in sorted_interests[:3]]
        interest_dist = {k: round(v / total * 100, 1) for k, v in sorted_interests}
        consume_dist = {k: round(v / total * 100, 1) for k, v in self.consume_level_distribution.items()}
        region_dist = {k: round(v / total * 100, 1) for k, v in sorted(self.region_distribution.items())}
        high_ratio = self.consume_level_distribution.get('high', 0) / total
        price_sensitivity = 150 if high_ratio > 0.25 else 250 if high_ratio > 0.15 else 400
        return {
            'total_users': self.total_users,
            'age_distribution': age_dist,
            'gender_distribution': gender_dist,
            'interest_distribution': interest_dist,
            'consume_level_distribution': consume_dist,
            'region_distribution': region_dist,
            'top_interests': top_interests,
            'price_sensitivity': price_sensitivity,
            'interest_multiplier': 0.15,
            'price_multiplier': 0.10
        }


class VirtualStreamer:
    def __init__(self):
        self.config = config.VIRTUAL_STREAMER_CONFIG
        self.name = self.config['name']
        self.avatar = self.config['avatar']
        self.state = 'idle'
        self.current_product = None
        self.current_script = ''
        self.script_history = deque(maxlen=20)
        self.tick_counter = 0
        self.total_speeches = 0
        self.auto_sell_orders = 0
        self.state_duration = 0

    def tick(self, context):
        self.tick_counter += 1
        self.state_duration += 1
        action = self._decide_action(context)
        return action

    def _decide_action(self, context):
        products = context.get('products', config.PRODUCTS)
        click_data = context.get('click_data', {})
        order_data = context.get('order_data', {})
        stock_data = context.get('stock_data', {})
        sentiment = context.get('sentiment_summary', {})
        hot_product = context.get('hot_product')
        heat_score = context.get('heat_score', 50)
        conversion_rate = context.get('conversion_rate', 0)

        if self.state == 'idle' or self.state_duration > 5:
            strategy = self._select_strategy(context)
            self.state = strategy['state']
            self.state_duration = 0

        if self.state == 'intro':
            if not self.current_product or self.state_duration == 1:
                self.current_product = hot_product or random.choice(products)
            stock = stock_data.get(self.current_product['name'], self.current_product.get('stock', 100))
            template = random.choice(self.config['strategies']['product_intro'])
            script = template.format(
                product=self.current_product['name'],
                price=self.current_product['price'],
                stock=max(stock, 1)
            )
            self.current_script = script
            self.script_history.append({
                'timestamp': datetime.now().isoformat(),
                'state': self.state,
                'product': self.current_product['name'],
                'script': script
            })
            self.total_speeches += 1
            return {
                'state': self.state,
                'product': self.current_product['name'],
                'script': script,
                'auto_action': None
            }

        if self.state == 'urgency':
            product = self.current_product or hot_product or random.choice(products)
            stock = stock_data.get(product['name'], product.get('stock', 100))
            template = random.choice(self.config['strategies']['urgency'])
            script = template.format(product=product['name'], stock=max(stock, 1))
            self.current_script = script
            self.script_history.append({
                'timestamp': datetime.now().isoformat(),
                'state': self.state,
                'product': product['name'],
                'script': script
            })
            self.total_speeches += 1
            auto_action = None
            if stock < 50 and random.random() < 0.3:
                auto_action = {'type': 'restock_alert', 'product': product['name'], 'stock': stock}
            return {
                'state': self.state,
                'product': product['name'],
                'script': script,
                'auto_action': auto_action
            }

        if self.state == 'interaction':
            product = self.current_product or hot_product or random.choice(products)
            template = random.choice(self.config['strategies']['interaction'])
            script = template.format(product=product['name'])
            self.current_script = script
            self.script_history.append({
                'timestamp': datetime.now().isoformat(),
                'state': self.state,
                'product': product['name'],
                'script': script
            })
            self.total_speeches += 1
            return {
                'state': self.state,
                'product': product['name'],
                'script': script,
                'auto_action': None
            }

        if self.state == 'closing':
            template = random.choice(self.config['strategies']['closing'])
            script = template.format()
            self.current_script = script
            self.script_history.append({
                'timestamp': datetime.now().isoformat(),
                'state': self.state,
                'product': '',
                'script': script
            })
            self.total_speeches += 1
            return {
                'state': self.state,
                'product': '',
                'script': script,
                'auto_action': None
            }

        template = random.choice(self.config['strategies']['greeting'])
        script = template.format()
        self.current_script = script
        self.script_history.append({
            'timestamp': datetime.now().isoformat(),
            'state': 'greeting',
            'product': '',
            'script': script
        })
        self.total_speeches += 1
        return {
            'state': 'greeting',
            'product': '',
            'script': script,
            'auto_action': None
        }

    def _select_strategy(self, context):
        heat_score = context.get('heat_score', 50)
        conversion_rate = context.get('conversion_rate', 0)
        sentiment = context.get('sentiment_summary', {})

        if conversion_rate < 2:
            return {'state': 'urgency'}
        if sentiment.get('intent_buy_ratio', 0) > 25:
            return {'state': 'interaction'}
        if heat_score < 30:
            return {'state': 'interaction'}
        r = random.random()
        if r < 0.4:
            return {'state': 'intro'}
        elif r < 0.6:
            return {'state': 'urgency'}
        elif r < 0.85:
            return {'state': 'interaction'}
        else:
            return {'state': 'closing'}

    def get_status(self):
        state_labels = {
            'idle': '待机', 'intro': '商品介绍', 'urgency': '促单逼单',
            'interaction': '互动引导', 'closing': '过渡衔接', 'greeting': '开场问候'
        }
        return {
            'name': self.name,
            'avatar': self.avatar,
            'state': self.state,
            'state_label': state_labels.get(self.state, self.state),
            'current_product': self.current_product['name'] if self.current_product else '',
            'current_script': self.current_script,
            'total_speeches': self.total_speeches,
            'script_history': list(self.script_history)[-8:],
            'is_active': True
        }


class HotProductPredictor:
    def __init__(self):
        self.config = config.HOT_PREDICTION_CONFIG
        self.click_history = defaultdict(lambda: deque(maxlen=60))
        self.order_history = defaultdict(lambda: deque(maxlen=60))
        self.prediction_cache = {}

    def record_tick(self, click_data, order_data):
        timestamp = time.time()
        for product_name, count in click_data.items():
            self.click_history[product_name].append((timestamp, count))
        for product_name, data in order_data.items():
            self.order_history[product_name].append((timestamp, data.get('count', 0)))

    def predict(self, products, click_data, order_data, stock_data, sentiment_momentum=0):
        self.record_tick(click_data, order_data)
        predictions = []
        w = self.config['trend_weights']

        for product in products:
            name = product['name']
            click_vel = self._calc_velocity(self.click_history[name])
            order_vel = self._calc_velocity(self.order_history[name])
            click_accel = self._calc_acceleration(self.click_history[name])
            order_accel = self._calc_acceleration(self.order_history[name])
            sentiment_m = max(0, sentiment_momentum) * 10

            click_vel_norm = min(click_vel / 5, 1) * 100
            order_vel_norm = min(order_vel / 2, 1) * 100
            click_accel_norm = min(max(click_accel, 0) / 3, 1) * 100
            order_accel_norm = min(max(order_accel, 0) / 1, 1) * 100
            sentiment_norm = min(sentiment_m, 100)

            hot_score = (
                w['click_velocity'] * click_vel_norm +
                w['order_velocity'] * order_vel_norm +
                w['click_acceleration'] * click_accel_norm +
                w['order_acceleration'] * order_accel_norm +
                w['sentiment_momentum'] * sentiment_norm
            )

            stock = stock_data.get(name, product.get('stock', 100))
            initial_stock = product.get('stock', 100)
            stock_ratio = stock / initial_stock if initial_stock > 0 else 0

            if hot_score >= 70 and click_accel > 0 and order_accel > 0:
                prediction_level = 'explosive'
            elif hot_score >= 50 and (click_accel > 0 or order_accel > 0):
                prediction_level = 'rising'
            elif hot_score >= 30:
                prediction_level = 'potential'
            else:
                prediction_level = 'stable'

            estimated_peak_time = None
            if prediction_level in ('explosive', 'rising'):
                if click_vel > 0:
                    remaining_stock = stock
                    burn_rate = order_vel * 3
                    if burn_rate > 0:
                        minutes_to_stockout = remaining_stock / burn_rate
                        estimated_peak_time = max(5, min(minutes_to_stockout, 60))

            predictions.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'category': product['category'],
                'stock': stock,
                'hot_score': round(hot_score, 1),
                'prediction_level': prediction_level,
                'metrics': {
                    'click_velocity': round(click_vel, 2),
                    'order_velocity': round(order_vel, 2),
                    'click_acceleration': round(click_accel, 2),
                    'order_acceleration': round(order_accel, 2),
                    'sentiment_momentum': round(sentiment_momentum, 2)
                },
                'estimated_peak_minutes': round(estimated_peak_time, 0) if estimated_peak_time else None,
                'stock_burn_rate': round(order_vel * 3, 1),
                'recommendation': self._get_recommendation(prediction_level, stock_ratio, hot_score)
            })

        predictions.sort(key=lambda x: x['hot_score'], reverse=True)
        self.prediction_cache = {p['name']: p for p in predictions}
        return predictions

    def _calc_velocity(self, history):
        if len(history) < 2:
            return 0
        recent = list(history)[-self.config['velocity_window']:]
        if len(recent) < 2:
            return 0
        values = [v for _, v in recent]
        if len(values) < 2:
            return 0
        diffs = [values[i] - values[i - 1] for i in range(1, len(values)) if values[i] > values[i - 1]]
        return sum(diffs) / len(diffs) if diffs else 0

    def _calc_acceleration(self, history):
        if len(history) < 3:
            return 0
        recent = list(history)[-self.config['acceleration_window']:]
        if len(recent) < 3:
            return 0
        values = [v for _, v in recent]
        if len(values) < 3:
            return 0
        velocities = [values[i] - values[i - 1] for i in range(1, len(values))]
        if len(velocities) < 2:
            return 0
        accel = velocities[-1] - velocities[-2]
        return accel

    def _get_recommendation(self, level, stock_ratio, hot_score):
        if level == 'explosive':
            if stock_ratio < 0.3:
                return '紧急补货！爆款即将售罄！'
            return '加大推广力度，爆款确认！'
        elif level == 'rising':
            if stock_ratio < 0.5:
                return '准备补货，趋势上升中'
            return '增加曝光，上升趋势明显'
        elif level == 'potential':
            return '持续观察，有潜在爆发可能'
        else:
            return '稳定销售，暂无爆发迹象'


class DemoDataGenerator:
    def __init__(self):
        self.current_viewers = 1500
        self.viewer_history = deque(maxlen=60)
        self.click_data = defaultdict(int)
        self.order_data = defaultdict(lambda: {'count': 0, 'amount': 0})
        self.category_data = defaultdict(lambda: {'clicks': 0, 'orders': 0})
        self.stock_data = {p['name']: p['stock'] for p in config.PRODUCTS}
        self.total_clicks = 0
        self.total_orders = 0
        self.conversion_rate = 0
        self.chat_analysis = {'question': 0, 'praise': 0, 'complaint': 0, 'neutral': 0}
        self.competitor_data = {}
        self.competitor_history = {c['id']: deque(maxlen=30) for c in config.COMPETITORS}
        self.heat_score = 50
        self.heat_history = deque(maxlen=60)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.hot_word_extractor = HotWordExtractor()
        self.script_generator = GuidedScriptGenerator()
        self.multi_optimizer = MultiObjectiveOptimizer()
        self.persona_tracker = UserPersonaTracker()
        self.virtual_streamer = VirtualStreamer()
        self.hot_predictor = HotProductPredictor()
        self.prev_click_data = {}
        self.prev_order_data = {}
        for _ in range(30):
            self.generate_viewer_event()
            self.generate_click_event()
            self.generate_order_event()
            self.generate_chat_event()
        for _ in range(5):
            self.generate_competitor_event()
        self.prev_click_data = dict(self.click_data)
        self.prev_order_data = {k: dict(v) for k, v in self.order_data.items()}

    def calculate_heat_score(self, viewer_count, clicks, orders):
        viewer_weight = 0.4
        click_weight = 0.3
        order_weight = 0.3
        normalized_viewers = min(viewer_count / 10000, 1)
        normalized_clicks = min(clicks / 1000, 1)
        normalized_orders = min(orders / 100, 1)
        return (viewer_weight * normalized_viewers + click_weight * normalized_clicks + order_weight * normalized_orders) * 100

    def generate_viewer_event(self):
        change = random.randint(-30, 50)
        self.current_viewers = max(100, self.current_viewers + change)
        timestamp = datetime.now().isoformat()
        self.viewer_history.append({'timestamp': timestamp, 'count': self.current_viewers})
        self.heat_score = self.calculate_heat_score(self.current_viewers, self.total_clicks, self.total_orders)
        self.heat_history.append({'timestamp': timestamp, 'score': self.heat_score})

    def generate_click_event(self):
        product = random.choice(config.PRODUCTS)
        click_count = random.randint(1, 15)
        self.click_data[product['name']] += click_count
        self.category_data[product['category']]['clicks'] += click_count
        self.total_clicks += click_count
        if self.total_clicks > 0:
            self.conversion_rate = (self.total_orders / self.total_clicks) * 100
        self.persona_tracker.record_action('click', product['name'], product['category'])

    def generate_order_event(self):
        product = random.choice(config.PRODUCTS)
        quantity = random.randint(1, 3)
        total_amount = product['price'] * quantity
        self.order_data[product['name']]['count'] += 1
        self.order_data[product['name']]['amount'] += total_amount
        self.category_data[product['category']]['orders'] += 1
        self.total_orders += 1
        self.stock_data[product['name']] = max(0, self.stock_data[product['name']] - quantity)
        if self.total_clicks > 0:
            self.conversion_rate = (self.total_orders / self.total_clicks) * 100
        self.persona_tracker.record_action('order', product['name'], product['category'])

    def generate_chat_event(self):
        product = random.choice(config.PRODUCTS)
        chat_type = random.choices(
            ['positive', 'negative', 'neutral', 'intent_buy'],
            weights=[0.35, 0.1, 0.2, 0.35]
        )[0]
        template = random.choice(config.CHAT_TEMPLATES[chat_type])
        message = template.format(product=product['name'])
        analysis = self.sentiment_analyzer.add_message(message, product['name'])
        self.hot_word_extractor.extract_from_message(message, product['name'])
        type_map = {'positive': 'praise', 'negative': 'complaint', 'neutral': 'neutral', 'intent_buy': 'question'}
        self.chat_analysis[type_map[chat_type]] += 1

    def generate_competitor_event(self):
        for competitor in config.COMPETITORS:
            prev_data = self.competitor_data.get(competitor['id'], {})
            prev_price = prev_data.get('current_price', competitor['base_price'])
            price_change = random.uniform(-3, 3)
            current_price = round(competitor['base_price'] + price_change, 2)
            prev_viewers = prev_data.get('viewer_count', random.randint(500, 5000))
            viewer_change = random.randint(-100, 150)
            viewer_count = max(100, prev_viewers + viewer_change)
            prev_sales = prev_data.get('sales_volume', random.randint(10, 200))
            sales_change = random.randint(0, 5)
            sales_volume = prev_sales + sales_change
            price_trend = 'up' if current_price > prev_price else 'down' if current_price < prev_price else 'stable'
            data_point = {
                'timestamp': datetime.now().isoformat(),
                'competitor_id': competitor['id'],
                'competitor_name': competitor['name'],
                'product': competitor['product'],
                'product_id': competitor['product_id'],
                'current_price': current_price,
                'price_trend': price_trend,
                'viewer_count': viewer_count,
                'sales_volume': sales_volume,
                'update_latency_ms': random.randint(50, 500)
            }
            self.competitor_data[competitor['id']] = data_point
            self.competitor_history[competitor['id']].append({
                'timestamp': data_point['timestamp'],
                'price': current_price,
                'viewers': viewer_count
            })

    def get_hot_product(self):
        if not self.click_data:
            return config.PRODUCTS[0]
        top_name = max(self.click_data.items(), key=lambda x: x[1])[0]
        return next((p for p in config.PRODUCTS if p['name'] == top_name), config.PRODUCTS[0])

    def get_summary_data(self):
        self.generate_viewer_event()
        self.generate_click_event()
        if random.random() < 0.4:
            self.generate_order_event()
        self.generate_chat_event()
        if random.random() < 0.5:
            self.generate_chat_event()
        self.generate_competitor_event()
        self.persona_tracker.tick_update()

        sentiment_summary = self.sentiment_analyzer.get_sentiment_summary()
        hot_words = self.hot_word_extractor.get_top_hot_words(10)
        hot_word_categories = self.hot_word_extractor.get_category_summary()
        hot_product = self.get_hot_product()

        persona_summary = self.persona_tracker.get_persona_summary()
        optimized_products = self.multi_optimizer.optimize(
            config.PRODUCTS, dict(self.click_data),
            {k: dict(v) for k, v in self.order_data.items()},
            self.stock_data,
            persona_boost=persona_summary
        )

        streamer_context = {
            'products': config.PRODUCTS,
            'click_data': dict(self.click_data),
            'order_data': {k: dict(v) for k, v in self.order_data.items()},
            'stock_data': self.stock_data,
            'sentiment_summary': sentiment_summary,
            'hot_product': hot_product,
            'heat_score': self.heat_score,
            'conversion_rate': self.conversion_rate
        }
        streamer_action = self.virtual_streamer.tick(streamer_context)

        sentiment_momentum = self.sentiment_analyzer.get_recent_sentiment_momentum()
        hot_predictions = self.hot_predictor.predict(
            config.PRODUCTS, dict(self.click_data),
            {k: dict(v) for k, v in self.order_data.items()},
            self.stock_data,
            sentiment_momentum
        )

        script_context = {
            'conversion_rate': self.conversion_rate,
            'heat_score': self.heat_score,
            'current_viewers': self.current_viewers,
            'sentiment_summary': sentiment_summary,
            'hot_product': hot_product,
            'hot_words': hot_words,
            'product_orders': {k: dict(v) for k, v in self.order_data.items()},
            'competitor_data': self.competitor_data
        }
        guided_scripts = self.script_generator.generate_scripts(script_context)

        competitor_realtime = {}
        for cid, cdata in self.competitor_data.items():
            our_product = next((p for p in config.PRODUCTS if p['id'] == cdata.get('product_id')), None)
            price_diff = 0
            price_advantage = False
            if our_product:
                price_diff = round(our_product['price'] - cdata['current_price'], 2)
                price_advantage = our_product['price'] <= cdata['current_price']
            competitor_realtime[cid] = {
                **cdata,
                'our_price': our_product['price'] if our_product else 0,
                'price_diff': price_diff,
                'price_advantage': price_advantage,
                'price_history': list(self.competitor_history.get(cid, []))
            }

        return {
            'current_viewers': self.current_viewers,
            'total_clicks': self.total_clicks,
            'total_orders': self.total_orders,
            'conversion_rate': round(self.conversion_rate, 2),
            'heat_score': round(self.heat_score, 2),
            'viewer_trend': list(self.viewer_history),
            'heat_trend': list(self.heat_history),
            'product_clicks': dict(self.click_data),
            'product_orders': {k: dict(v) for k, v in self.order_data.items()},
            'category_data': {k: dict(v) for k, v in self.category_data.items()},
            'chat_analysis': self.chat_analysis.copy(),
            'sentiment_analysis': sentiment_summary,
            'hot_words': hot_words,
            'hot_word_categories': hot_word_categories,
            'guided_scripts': guided_scripts,
            'recommended_products': optimized_products[:4],
            'competitor_data': competitor_realtime,
            'user_persona': persona_summary,
            'virtual_streamer': self.virtual_streamer.get_status(),
            'streamer_action': streamer_action,
            'hot_predictions': hot_predictions,
            'timestamp': datetime.now().isoformat()
        }


class DemoWebSocketServer:
    def __init__(self):
        self.generator = DemoDataGenerator()
        self.connected_clients = set()
        self.push_interval = 1.0

    async def register_client(self, websocket):
        self.connected_clients.add(websocket)
        print(f"新客户端连接，当前连接数: {len(self.connected_clients)}")

    async def unregister_client(self, websocket):
        self.connected_clients.discard(websocket)
        print(f"客户端断开连接，当前连接数: {len(self.connected_clients)}")

    async def push_data_to_clients(self):
        while True:
            if self.connected_clients:
                try:
                    data = self.generator.get_summary_data()
                    message = json.dumps(data, ensure_ascii=False)
                    disconnected = set()
                    for websocket in self.connected_clients:
                        try:
                            await websocket.send(message)
                        except Exception:
                            disconnected.add(websocket)
                    for websocket in disconnected:
                        await self.unregister_client(websocket)
                except Exception as e:
                    print(f"获取数据失败: {e}")
            await asyncio.sleep(self.push_interval)

    async def handle_client(self, websocket, path):
        await self.register_client(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('action') == 'ping':
                        await websocket.send(json.dumps({'action': 'pong', 'timestamp': datetime.now().isoformat()}))
                except Exception as e:
                    print(f"处理客户端消息失败: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start(self):
        print(f"启动演示WebSocket服务器: {config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}")
        push_task = asyncio.create_task(self.push_data_to_clients())
        async with websockets.serve(
            self.handle_client,
            config.WEBSOCKET_HOST,
            config.WEBSOCKET_PORT
        ):
            print("WebSocket服务器已启动，等待客户端连接...")
            await push_task


if __name__ == '__main__':
    server = DemoWebSocketServer()
    asyncio.run(server.start())
