from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BIOWEIGHTS = {
    '蛋白质': 2.0, '基因': 2.0, '细胞': 2.0, '分子': 1.8, '受体': 1.9,
    '抗体': 1.9, '酶': 1.8, 'DNA': 2.0, 'RNA': 2.0, '基因组': 2.0,
    '突变': 1.7, '表达': 1.6, '信号': 1.5, '通路': 1.7, '肿瘤': 1.9,
    '癌症': 1.8, '疾病': 1.6, '治疗': 1.7, '药物': 1.8, '疫苗': 1.9,
    '病毒': 1.9, '细菌': 1.7, '免疫': 1.8, '炎症': 1.7, '代谢': 1.7,
    '神经': 1.6, '心血管': 1.7, '临床': 1.5, '诊断': 1.6, '病理': 1.7,
    '药理': 1.7, '毒性': 1.6, '剂量': 1.5, '疗效': 1.7, '副作用': 1.6,
    '患者': 1.5, '症状': 1.5, '预后': 1.6, '复发': 1.6, '转移': 1.7,
    '干细胞': 2.0, 'CRISPR': 2.0, '测序': 1.8, '生物标志物': 1.9,
    '靶向': 1.7, '表观遗传': 1.9, '转录': 1.7, '翻译': 1.5,
    '人工智能': 1.5, '机器学习': 1.5, '深度学习': 1.5, '神经网络': 1.5,
    '自然语言': 1.5, '计算机视觉': 1.5, '大数据': 1.4, '云计算': 1.4,
    '物联网': 1.4, '区块链': 1.4, '自动驾驶': 1.4, '推荐系统': 1.3,
    'protein': 2.0, 'gene': 2.0, 'cell': 2.0, 'molecular': 1.8, 'receptor': 1.9,
    'antibody': 1.9, 'enzyme': 1.8, 'mutation': 1.7, 'expression': 1.6,
    'pathway': 1.7, 'tumor': 1.9, 'cancer': 1.8, 'disease': 1.6,
    'therapy': 1.7, 'drug': 1.8, 'vaccine': 1.9, 'virus': 1.9,
    'bacteria': 1.7, 'immune': 1.8, 'inflammation': 1.7, 'metabolism': 1.7,
    'clinical': 1.5, 'diagnosis': 1.6, 'pathology': 1.7, 'pharmacology': 1.7,
    'toxicity': 1.6, 'dosage': 1.5, 'efficacy': 1.7, 'patient': 1.5,
    'symptom': 1.5, 'prognosis': 1.6, 'recurrence': 1.6, 'metastasis': 1.7,
    'stem cell': 2.0, 'sequencing': 1.8, 'biomarker': 1.9, 'targeted': 1.7,
    'epigenetic': 1.9, 'transcription': 1.7, 'translation': 1.5,
}

DEFAULT_STOPWORDS = set([
    '的', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看',
    '好', '自己', '这', '那', '这个', '那个', '他', '她', '它', '们', '而',
    '与', '或', '但', '但是', '因为', '所以', '如果', '虽然', '然而', '还是',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'and', 'but', 'if', 'or', 'because', 'until', 'while',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
    'she', 'her', 'it', 'its', 'they', 'them', 'their', 'this', 'that',
    'am', 'not', 'no', 'yes', 'up', 'down', 'out', 'off', 'over', 'under',
])

import re

def tokenize_chinese(text):
    pattern = re.compile(r'[\u4e00-\u9fa5]+')
    segments = []
    for match in pattern.finditer(text):
        segment = match.group()
        bigrams = [segment[i:i+2] for i in range(len(segment) - 1)]
        trigrams = [segment[i:i+3] for i in range(len(segment) - 2)]
        
        for i in range(len(segment)):
            for length in [4, 3, 2]:
                if i + length <= len(segment):
                    word = segment[i:i+length]
                    if word in BIOWEIGHTS:
                        segments.append(word)
                        break
            else:
                if i + 2 <= len(segment):
                    segments.append(segment[i:i+2])
    
    return segments

def tokenize_english(text):
    words = re.findall(r'[a-zA-Z]{2,}', text.lower())
    return words

def extract_entities(text):
    entities = []
    for term in sorted(BIOWEIGHTS.keys(), key=len, reverse=True):
        if term.lower() in text.lower():
            count = text.lower().count(term.lower())
            entities.extend([term] * count)
            text = text.replace(term, ' ' * len(term))
    return entities

def count_words(words, custom_stopwords):
    word_count = {}
    all_stopwords = DEFAULT_STOPWORDS | set(custom_stopwords)
    
    for word in words:
        lower = word.lower()
        if lower not in all_stopwords and len(word) > 1:
            weight = BIOWEIGHTS.get(word, BIOWEIGHTS.get(lower, 1.0))
            if word in word_count:
                word_count[word] = (word_count[word][0] + 1, weight)
            else:
                word_count[word] = (1, weight)
    
    result = []
    for word, (count, weight) in word_count.items():
        weighted_count = max(1, int(count * weight))
        result.append({'word': word, 'count': weighted_count})
    
    result.sort(key=lambda x: x['count'], reverse=True)
    return result

@app.route('/api/biobert/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    text = data.get('text', '')
    custom_stopwords = data.get('stopWords', [])
    
    if not text or not text.strip():
        return jsonify({'words': [], 'engine': 'biobert'})
    
    entities = extract_entities(text)
    remaining_text = text
    for entity in entities:
        remaining_text = remaining_text.replace(entity, ' ', 1)
    
    chinese_words = tokenize_chinese(remaining_text)
    english_words = tokenize_english(remaining_text)
    
    all_words = entities + chinese_words + english_words
    
    words = count_words(all_words, custom_stopwords)
    
    return jsonify({'words': words, 'engine': 'biobert'})

@app.route('/api/biobert/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'engine': 'biobert'})

if __name__ == '__main__':
    print('BioBERT service starting on http://localhost:3002')
    app.run(host='0.0.0.0', port=3002, debug=True)
