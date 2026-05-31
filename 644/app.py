from flask import Flask, request, jsonify, render_template
from config import Config
from core import SearchCorrector

app = Flask(__name__)
app.config.from_object(Config)

corrector = SearchCorrector(Config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/correct', methods=['POST'])
def correct_query():
    data = request.get_json()
    query = data.get('query', '')
    threshold = data.get('threshold')
    max_candidates = data.get('max_candidates')
    user_id = data.get('user_id')
    
    result = corrector.correct(query, threshold, max_candidates, user_id)
    return jsonify(result)

@app.route('/api/feedback/click', methods=['POST'])
def record_click():
    data = request.get_json()
    original_query = data.get('original_query', '')
    corrected_query = data.get('corrected_query', '')
    suggestion = data.get('suggestion', '')
    user_id = data.get('user_id')
    
    corrector.record_click(original_query, corrected_query, suggestion, user_id)
    return jsonify({'status': 'success', 'message': 'Click recorded'})

@app.route('/api/feedback/skip', methods=['POST'])
def record_skip():
    data = request.get_json()
    original_query = data.get('original_query', '')
    suggestion = data.get('suggestion', '')
    user_id = data.get('user_id')
    
    corrector.record_skip(original_query, suggestion, user_id)
    return jsonify({'status': 'success', 'message': 'Skip recorded'})

@app.route('/api/threshold', methods=['GET', 'POST'])
def threshold():
    if request.method == 'POST':
        data = request.get_json()
        new_threshold = data.get('threshold')
        if new_threshold is not None:
            corrector.set_threshold(float(new_threshold))
            return jsonify({'status': 'success', 'threshold': corrector.get_threshold()})
    return jsonify({'threshold': corrector.get_threshold()})

@app.route('/api/dynamic-threshold', methods=['POST'])
def get_dynamic_threshold():
    data = request.get_json()
    query = data.get('query', '')
    dynamic_threshold = corrector.get_dynamic_threshold_for_query(query)
    return jsonify({
        'query': query,
        'query_length': len(query),
        'dynamic_threshold': dynamic_threshold,
        'base_threshold': corrector.get_threshold()
    })

@app.route('/api/domain/words', methods=['GET'])
def get_domain_words():
    words = corrector.get_domain_words()
    return jsonify({'words': words[:100], 'total': len(words)})

@app.route('/api/domain/add', methods=['POST'])
def add_domain_word():
    data = request.get_json()
    word = data.get('word', '')
    weight = int(data.get('weight', 1))
    
    if word:
        corrector.add_domain_word(word, weight)
        return jsonify({'status': 'success', 'word': word, 'weight': weight})
    return jsonify({'status': 'error', 'message': 'Word is required'}), 400

@app.route('/api/seed/add', methods=['POST'])
def add_seed_correction():
    data = request.get_json()
    wrong = data.get('wrong', '')
    correct = data.get('correct', '')
    weight = int(data.get('weight', 80))
    
    if wrong and correct:
        corrector.add_seed_correction(wrong, correct, weight)
        return jsonify({'status': 'success', 'wrong': wrong, 'correct': correct, 'weight': weight})
    return jsonify({'status': 'error', 'message': 'Wrong and correct words are required'}), 400

@app.route('/api/seed/list', methods=['GET'])
def list_seed_corrections():
    seeds = corrector.get_seed_corrections()
    seed_list = []
    for wrong, corrections in seeds.items():
        for correct, weight in corrections:
            seed_list.append({
                'wrong': wrong,
                'correct': correct,
                'weight': weight
            })
    return jsonify({'seeds': seed_list[:100], 'total': len(seed_list)})

@app.route('/api/user/profile', methods=['POST'])
def get_user_profile():
    data = request.get_json()
    user_id = data.get('user_id', '')
    if user_id:
        profile = corrector.get_user_profile(user_id)
        return jsonify(profile)
    return jsonify({'status': 'error', 'message': 'user_id is required'}), 400

@app.route('/api/evaluation/metrics', methods=['GET'])
def get_evaluation_metrics():
    metrics = corrector.get_evaluation_metrics()
    return jsonify(metrics)

@app.route('/api/multilingual/detect', methods=['POST'])
def detect_language():
    data = request.get_json()
    query = data.get('query', '')
    lang_type = corrector.multilingual.detect_language_mix(query)
    tokens = corrector.multilingual.split_mixed_tokens(query)
    return jsonify({
        'query': query,
        'language_type': lang_type,
        'tokens': [{'text': t[0], 'type': t[1]} for t in tokens]
    })

@app.route('/api/multilingual/correct', methods=['POST'])
def correct_multilingual():
    data = request.get_json()
    query = data.get('query', '')
    corrected, details = corrector.multilingual.correct_multilingual(query)
    return jsonify({
        'original': query,
        'corrected': corrected,
        'details': details
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
