import re
import jieba
from snownlp import SnowNLP
from config import ASPECTS, ASPECT_KEYWORDS, SENTIMENT_THRESHOLD


def clean_text(text):
    if not isinstance(text, str):
        return ''
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、；：""''（）\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def analyze_sentiment(text):
    try:
        cleaned_text = clean_text(text)
        if not cleaned_text:
            return {'score': 0.5, 'label': 'neutral', 'label_cn': '中性'}
        
        s = SnowNLP(cleaned_text)
        score = s.sentiments
        
        if score >= SENTIMENT_THRESHOLD:
            label = 'positive'
            label_cn = '正向'
        elif score <= (1 - SENTIMENT_THRESHOLD):
            label = 'negative'
            label_cn = '负向'
        else:
            label = 'neutral'
            label_cn = '中性'
        
        return {
            'score': round(score, 4),
            'label': label,
            'label_cn': label_cn
        }
    except Exception as e:
        return {
            'score': 0.5,
            'label': 'neutral',
            'label_cn': '中性'
        }


def extract_aspects(text):
    cleaned_text = clean_text(text)
    if not cleaned_text:
        return []
    
    found_aspects = set()
    words = jieba.lcut(cleaned_text)
    
    for aspect, keywords in ASPECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in words or keyword in cleaned_text:
                found_aspects.add(aspect)
                break
    
    return list(found_aspects)


def analyze_aspect_sentiment(text, aspect):
    cleaned_text = clean_text(text)
    if not cleaned_text:
        return {'score': 0.5, 'label': 'neutral', 'label_cn': '中性'}
    
    keywords = ASPECT_KEYWORDS.get(aspect, [])
    aspect_related = []
    sentences = re.split(r'[。！？；]', cleaned_text)
    
    for sentence in sentences:
        if any(kw in sentence for kw in keywords):
            aspect_related.append(sentence)
    
    if not aspect_related:
        return {'score': 0.5, 'label': 'neutral', 'label_cn': '中性'}
    
    aspect_text = '。'.join(aspect_related)
    return analyze_sentiment(aspect_text)


def full_analysis(text):
    result = {}
    result.update(analyze_sentiment(text))
    result['aspects'] = extract_aspects(text)
    
    aspect_sentiments = {}
    for aspect in result['aspects']:
        aspect_sentiments[aspect] = analyze_aspect_sentiment(text, aspect)
    result['aspect_sentiments'] = aspect_sentiments
    
    return result


def analyze_comments_batch(comments):
    results = []
    for comment in comments:
        text = comment.get('comment_text', '')
        analysis = full_analysis(text)
        comment.update(analysis)
        results.append(comment)
    return results


if __name__ == '__main__':
    test_texts = [
        '这款手机性价比很高，质量也很好，物流也很快！',
        '价格太贵了，而且质量很差，物流还慢，不推荐！',
        '价格还行，质量一般吧，没什么特别的。'
    ]
    
    for text in test_texts:
        print(f'文本: {text}')
        result = full_analysis(text)
        print(f'分析结果: {result}')
        print('-' * 50)
