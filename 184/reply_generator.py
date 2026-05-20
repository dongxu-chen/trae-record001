import random
from collections import defaultdict
from config import ASPECTS


REPLY_TEMPLATES = {
    'general': {
        'apology': [
            '非常抱歉给您带来了不好的体验！',
            '亲，非常抱歉让您失望了！',
            '您好，对于这次不愉快的购物经历我们深表歉意！',
            '很抱歉没有达到您的期望，我们会认真改进！'
        ],
        'thanks': [
            '感谢您的反馈，这对我们非常重要！',
            '谢谢您的宝贵意见，我们会认真对待！',
            '非常感谢您抽出时间反馈问题！',
            '感谢您的监督，我们会努力做得更好！'
        ],
        'solution': [
            '我们已经将您的问题反馈给相关部门，会尽快处理。',
            '请您私信我们您的订单号，我们会为您妥善处理。',
            '您可以联系我们的客服热线400-XXX-XXXX，我们会全力解决。',
            '我们的客服会在24小时内联系您，请保持电话畅通。'
        ],
        'invitation': [
            '希望能给我们一次改进的机会，期待再次为您服务！',
            '我们会认真吸取教训，期待您的再次光临！',
            '请相信我们会做得更好，期待您的下次体验！'
        ],
        'signature': [
            '【XXX官方旗舰店】',
            '【XXX客服团队】',
            '【XXX售后服务中心】'
        ]
    },
    'aspects': {
        '价格': {
            'apology': [
                '关于价格方面的问题我们非常重视，',
                '对于价格让您感到不满意我们深表歉意，',
                '您对价格的反馈我们已经收到，'
            ],
            'explanation': [
                '我们的定价是基于产品成本和市场行情制定的，后续会推出更多优惠活动。',
                '我们会在促销期间推出更多折扣，建议您关注店铺活动。',
                '我们会将您的意见反馈给定价部门，优化价格策略。'
            ],
            'solution': [
                '如果您是近期购买的，我们可以为您申请价格保护。',
                '您可以领取店铺优惠券，享受更多优惠。'
            ]
        },
        '质量': {
            'apology': [
                '产品质量问题是我们的责任，非常抱歉！',
                '对于产品质量让您失望我们感到非常抱歉，',
                '质量问题是我们最重视的，给您带来困扰很抱歉，'
            ],
            'explanation': [
                '我们的产品都经过严格质检，这次的问题属于偶发情况。',
                '可能是运输过程中造成的损坏，我们会加强包装保护。',
                '我们会加强生产环节的质量把控，避免类似问题。'
            ],
            'solution': [
                '我们可以为您提供免费退换货服务，来回运费由我们承担。',
                '请您提供问题照片，我们会立即为您补发或退款。',
                '您可以申请售后退换货，我们会优先处理您的订单。'
            ]
        },
        '物流': {
            'apology': [
                '物流配送问题给您带来不便非常抱歉！',
                '对于物流速度让您不满意我们深表歉意，',
                '快递服务没有达到预期我们很抱歉，'
            ],
            'explanation': [
                '快递时效受天气和交通影响，我们会催促快递方加快配送。',
                '我们会与快递合作方沟通，提升配送服务质量。',
                '可能是物流分拣出现延误，我们已经联系快递方处理。'
            ],
            'solution': [
                '我们已经联系快递公司催促派送，预计很快就能送达。',
                '如果包裹有损坏，我们可以为您申请补发或退款。',
                '后续我们会更换更可靠的物流服务商。'
            ]
        },
        '服务': {
            'apology': [
                '客服服务没有让您满意非常抱歉！',
                '对于服务态度问题我们深表歉意，',
                '客服回复不及时给您带来困扰很抱歉，'
            ],
            'explanation': [
                '可能是咨询高峰期客服回复较慢，我们会增加客服人员。',
                '我们会加强客服培训，提升服务质量和响应速度。',
                '客服人员的服务问题我们会严肃处理，加强管理。'
            ],
            'solution': [
                '我们会对相关客服人员进行培训和处理。',
                '您的问题我们会安排专属客服为您一对一解决。',
                '后续我们会优化客服系统，提升咨询体验。'
            ]
        }
    }
}


def analyze_comment_issues(comment):
    aspects = comment.get('aspects', [])
    if isinstance(aspects, str):
        aspects = aspects.split(',')
    
    opinion_pairs = comment.get('opinion_pairs', [])
    if isinstance(opinion_pairs, str):
        try:
            import json
            opinion_pairs = json.loads(opinion_pairs.replace("'", '"'))
        except:
            opinion_pairs = []
    
    issues = defaultdict(list)
    
    for pair in opinion_pairs:
        if isinstance(pair, dict) and pair.get('sentiment') == 'negative':
            aspect = pair.get('aspect', '其他')
            if aspect in ASPECTS:
                issues[aspect].append(pair)
    
    if not issues:
        for aspect in aspects:
            if aspect in ASPECTS and comment.get('sentiment_label') == 'negative':
                issues[aspect] = []
    
    return dict(issues)


def generate_reply(comment, style='professional'):
    issues = analyze_comment_issues(comment)
    
    styles = {
        'professional': {
            'greeting': '尊敬的顾客，',
            'tone': 'formal'
        },
        'friendly': {
            'greeting': '亲，',
            'tone': 'casual'
        },
        'sincere': {
            'greeting': '您好，',
            'tone': 'warm'
        }
    }
    
    selected_style = styles.get(style, styles['professional'])
    
    reply_parts = [selected_style['greeting']]
    
    if issues:
        for aspect in issues.keys():
            if aspect in REPLY_TEMPLATES['aspects']:
                templates = REPLY_TEMPLATES['aspects'][aspect]
                reply_parts.append(random.choice(templates['apology']))
                reply_parts.append(random.choice(templates['explanation']))
                reply_parts.append(random.choice(templates['solution']))
    else:
        reply_parts.append(random.choice(REPLY_TEMPLATES['general']['apology']))
    
    reply_parts.append(random.choice(REPLY_TEMPLATES['general']['thanks']))
    reply_parts.append(random.choice(REPLY_TEMPLATES['general']['solution']))
    
    if style == 'friendly':
        reply_parts.append(random.choice(REPLY_TEMPLATES['general']['invitation']))
    
    reply_parts.append(random.choice(REPLY_TEMPLATES['general']['signature']))
    
    return ''.join(reply_parts)


def generate_multiple_replies(comment, count=3):
    styles = ['professional', 'friendly', 'sincere']
    replies = []
    
    for i in range(min(count, len(styles))):
        reply = generate_reply(comment, style=styles[i])
        replies.append({
            'style': styles[i],
            'style_name': {'professional': '专业正式', 'friendly': '亲切友好', 'sincere': '诚恳道歉'}[styles[i]],
            'content': reply
        })
    
    return replies


def generate_reply_by_issue(aspect, issue_text, style='professional'):
    styles = {
        'professional': {
            'greeting': '尊敬的顾客，',
            'tone': 'formal'
        },
        'friendly': {
            'greeting': '亲，',
            'tone': 'casual'
        },
        'sincere': {
            'greeting': '您好，',
            'tone': 'warm'
        }
    }
    
    selected_style = styles.get(style, styles['professional'])
    
    reply_parts = [selected_style['greeting']]
    
    if aspect in REPLY_TEMPLATES['aspects']:
        templates = REPLY_TEMPLATES['aspects'][aspect]
        reply_parts.append(random.choice(templates['apology']))
        reply_parts.append(random.choice(templates['explanation']))
        reply_parts.append(random.choice(templates['solution']))
    else:
        reply_parts.append(random.choice(REPLY_TEMPLATES['general']['apology']))
    
    reply_parts.append(random.choice(REPLY_TEMPLATES['general']['thanks']))
    
    if aspect == '质量':
        reply_parts.append('请您私信我们订单号和问题照片，我们会立即为您处理。')
    elif aspect == '物流':
        reply_parts.append('请您提供快递单号，我们会联系快递公司核实处理。')
    elif aspect == '服务':
        reply_parts.append('我们会对相关服务人员进行培训，确保类似问题不再发生。')
    elif aspect == '价格':
        reply_parts.append('后续我们会推出更多优惠活动，请您持续关注。')
    
    reply_parts.append(random.choice(REPLY_TEMPLATES['general']['signature']))
    
    return ''.join(reply_parts)


if __name__ == '__main__':
    test_comment = {
        'comment_text': '价格太贵了，而且质量很差，物流还慢，客服态度也不好，不推荐！',
        'sentiment_label': 'negative',
        'aspects': ['价格', '质量', '物流', '服务'],
        'opinion_pairs': [
            {'target': '价格', 'opinion': '贵', 'aspect': '价格', 'sentiment': 'negative'},
            {'target': '质量', 'opinion': '差', 'aspect': '质量', 'sentiment': 'negative'},
            {'target': '物流', 'opinion': '慢', 'aspect': '物流', 'sentiment': 'negative'},
            {'target': '客服', 'opinion': '不好', 'aspect': '服务', 'sentiment': 'negative'}
        ]
    }
    
    print('测试评论:', test_comment['comment_text'])
    print('\n识别到的问题:', analyze_comment_issues(test_comment))
    print('\n生成的回复方案:')
    
    replies = generate_multiple_replies(test_comment, count=3)
    for i, reply in enumerate(replies, 1):
        print(f'\n【方案{i} - {reply["style_name"]}】')
        print(reply['content'])
