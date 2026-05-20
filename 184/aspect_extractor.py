import re
import jieba
import jieba.posseg as pseg
from collections import defaultdict
from config import ASPECTS, ASPECT_KEYWORDS


jieba.setLogLevel(60)


POSITIVE_OPINION_WORDS = {
    '好', '棒', '赞', '优秀', '出色', '满意', '喜欢', '爱', '推荐', '划算',
    '实惠', '便宜', '快', '迅速', '准时', '专业', '热情', '耐心', '周到',
    '精致', '细腻', '耐用', '结实', '美观', '好看', '漂亮', '完美', '超值',
    '惊喜', '满意', '舒服', '好用', '实用', '方便', '省心', '放心', '靠谱',
    '清晰', '流畅', '稳定', '安全', '健康', '新鲜', '正宗', '正品', '真的',
    '不错', '可以', '还行', '挺好', '很棒', '超赞', '太赞', '完美', '绝佳'
}

NEGATIVE_OPINION_WORDS = {
    '差', '烂', '糟', '糟糕', '失望', '后悔', '不满', '生气', '愤怒', '贵',
    '慢', '晚', '迟', '拖延', '敷衍', '冷淡', '粗鲁', '推诿', '欺骗', '虚假',
    '劣质', '粗糙', '易碎', '易坏', '难用', '复杂', '麻烦', '心累', '闹心',
    '模糊', '卡顿', '闪退', '故障', '破损', '变形', '褪色', '异味', '过期',
    '假货', '山寨', '仿冒', '虚假', '夸大', '不实', '坑爹', '坑人', '无语',
    '很差', '太差', '太烂', '太糟', '不好', '不行', '不推荐', '别买', '避坑',
    '踩雷', '翻车', '打脸', '退货', '退款', '投诉', '举报', '差评'
}

OPINION_WORDS = POSITIVE_OPINION_WORDS | NEGATIVE_OPINION_WORDS


TARGET_WORDS = {
    '价格': {'价格', '价钱', '价位', '性价比', '钱', '元', '块', '优惠', '折扣', '促销'},
    '质量': {'质量', '品质', '做工', '材质', '用料', '手感', '质感', '工艺', '细节'},
    '物流': {'物流', '快递', '发货', '配送', '速度', '包装', '包裹', '快件', '送货'},
    '服务': {'服务', '客服', '售后', '态度', '回复', '解决', '处理', '效率', '专业度'}
}


def clean_text(text):
    if not isinstance(text, str):
        return ''
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：""''（）\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_sentences(text):
    sentences = re.split(r'[。！？；.!?;]', text)
    return [s.strip() for s in sentences if s.strip()]


def pos_tagging(text):
    words = pseg.cut(text)
    return [(word, flag) for word, flag in words]


def extract_dependency_pairs(sentence):
    pairs = []
    words = pos_tagging(sentence)
    
    for i, (word, flag) in enumerate(words):
        if word in OPINION_WORDS:
            opinion_word = word
            opinion_sentiment = 'positive' if word in POSITIVE_OPINION_WORDS else 'negative'
            
            target_word = None
            aspect = None
            
            window_start = max(0, i - 5)
            window_end = min(len(words), i + 5)
            
            for j in range(window_start, window_end):
                if j == i:
                    continue
                w, f = words[j]
                
                for asp, target_set in TARGET_WORDS.items():
                    if w in target_set:
                        target_word = w
                        aspect = asp
                        break
                
                if target_word:
                    break
            
            if not target_word:
                for j in range(window_start, window_end):
                    if j == i:
                        continue
                    w, f = words[j]
                    if f.startswith('n') and len(w) >= 2:
                        target_word = w
                        
                        for asp, keywords in ASPECT_KEYWORDS.items():
                            if any(kw in w for kw in keywords):
                                aspect = asp
                                break
                        break
            
            if target_word:
                if not aspect:
                    for asp, keywords in ASPECT_KEYWORDS.items():
                        if any(kw in sentence for kw in keywords):
                            aspect = asp
                            break
                
                pairs.append({
                    'target': target_word,
                    'opinion': opinion_word,
                    'aspect': aspect or '其他',
                    'sentiment': opinion_sentiment,
                    'position': i
                })
    
    return pairs


def rule_based_extraction(sentence):
    pairs = []
    
    for aspect, keywords in ASPECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in sentence:
                target_word = keyword
                
                opinion_word = None
                sentiment = 'neutral'
                
                for pos_word in POSITIVE_OPINION_WORDS:
                    if pos_word in sentence:
                        opinion_word = pos_word
                        sentiment = 'positive'
                        break
                
                if not opinion_word:
                    for neg_word in NEGATIVE_OPINION_WORDS:
                        if neg_word in sentence:
                            opinion_word = neg_word
                            sentiment = 'negative'
                            break
                
                if opinion_word:
                    pairs.append({
                        'target': target_word,
                        'opinion': opinion_word,
                        'aspect': aspect,
                        'sentiment': sentiment,
                        'position': sentence.find(keyword)
                    })
    
    return pairs


def extract_aspect_opinion_pairs(text):
    cleaned_text = clean_text(text)
    if not cleaned_text:
        return []
    
    all_pairs = []
    sentences = split_sentences(cleaned_text)
    
    for sentence in sentences:
        dep_pairs = extract_dependency_pairs(sentence)
        rule_pairs = rule_based_extraction(sentence)
        
        seen = set()
        for p in dep_pairs + rule_pairs:
            key = (p['target'], p['opinion'], p['aspect'])
            if key not in seen:
                seen.add(key)
                all_pairs.append(p)
    
    return all_pairs


def extract_aspects(text):
    pairs = extract_aspect_opinion_pairs(text)
    aspects = set()
    for pair in pairs:
        if pair['aspect'] in ASPECTS:
            aspects.add(pair['aspect'])
    return list(aspects)


def analyze_aspect_sentiment(text, aspect):
    pairs = extract_aspect_opinion_pairs(text)
    aspect_pairs = [p for p in pairs if p['aspect'] == aspect]
    
    if not aspect_pairs:
        return {'score': 0.5, 'label': 'neutral', 'label_cn': '中性', 'pairs': []}
    
    positive_count = sum(1 for p in aspect_pairs if p['sentiment'] == 'positive')
    negative_count = sum(1 for p in aspect_pairs if p['sentiment'] == 'negative')
    
    total = len(aspect_pairs)
    if total == 0:
        score = 0.5
    else:
        score = positive_count / total
    
    if score >= 0.6:
        label = 'positive'
        label_cn = '正向'
    elif score <= 0.4:
        label = 'negative'
        label_cn = '负向'
    else:
        label = 'neutral'
        label_cn = '中性'
    
    return {
        'score': round(score, 4),
        'label': label,
        'label_cn': label_cn,
        'pairs': aspect_pairs
    }


def full_analysis(text):
    from bert_sentiment import analyze_sentiment
    
    sentiment_result = analyze_sentiment(text)
    pairs = extract_aspect_opinion_pairs(text)
    
    aspects = set()
    aspect_pairs_map = defaultdict(list)
    for pair in pairs:
        if pair['aspect'] in ASPECTS:
            aspects.add(pair['aspect'])
            aspect_pairs_map[pair['aspect']].append(pair)
    
    aspect_sentiments = {}
    for aspect in aspects:
        aspect_pairs = aspect_pairs_map[aspect]
        positive_count = sum(1 for p in aspect_pairs if p['sentiment'] == 'positive')
        negative_count = sum(1 for p in aspect_pairs if p['sentiment'] == 'negative')
        total = len(aspect_pairs)
        
        if total > 0:
            aspect_score = positive_count / total
            if aspect_score >= 0.6:
                aspect_label = 'positive'
                aspect_label_cn = '正向'
            elif aspect_score <= 0.4:
                aspect_label = 'negative'
                aspect_label_cn = '负向'
            else:
                aspect_label = 'neutral'
                aspect_label_cn = '中性'
            
            aspect_sentiments[aspect] = {
                'score': round(aspect_score, 4),
                'label': aspect_label,
                'label_cn': aspect_label_cn,
                'pairs': aspect_pairs
            }
    
    result = {}
    result.update(sentiment_result)
    result['aspects'] = list(aspects)
    result['aspect_sentiments'] = aspect_sentiments
    result['opinion_pairs'] = pairs
    
    return result


if __name__ == '__main__':
    test_texts = [
        '这款手机价格非常实惠，质量也很好，物流速度很快！',
        '价格太贵了，而且质量很差，物流还慢，客服态度也不好，不推荐！',
        '价格还行，质量一般吧，没什么特别的。',
        '客服态度很好，有问必答，很专业！物流也给力，第二天就收到了。',
        '用了几天就坏了，质量太差，联系客服也不理人，非常失望！'
    ]
    
    for text in test_texts:
        print(f'文本: {text}')
        result = full_analysis(text)
        print(f'情感: {result["label_cn"]} ({result["score"]})')
        print(f'涉及方面: {result["aspects"]}')
        print(f'观点对:')
        for pair in result['opinion_pairs']:
            print(f'  [{pair["aspect"]}] {pair["target"]} - {pair["opinion"]} ({pair["sentiment"]})')
        print('-' * 50)
