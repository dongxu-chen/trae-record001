import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    DEBUG = True
    SECRET_KEY = 'ecommerce-search-correction-secret-key'
    
    CORRECTION_THRESHOLD = 0.7
    MAX_CANDIDATES = 10
    MAX_EDIT_DISTANCE = 2
    
    MIN_THRESHOLD = 0.5
    MAX_THRESHOLD = 0.9
    
    DOMAIN_DICT_PATH = os.path.join(BASE_DIR, 'data', 'domain_dict.txt')
    USER_FEEDBACK_PATH = os.path.join(BASE_DIR, 'data', 'user_feedback.json')
    LANGUAGE_MODEL_PATH = os.path.join(BASE_DIR, 'data', 'language_model.pkl')
    SEED_CORRECTIONS_PATH = os.path.join(BASE_DIR, 'data', 'seed_corrections.txt')
    USER_PREFERENCE_PATH = os.path.join(BASE_DIR, 'data', 'user_preference.json')
    EVALUATION_PATH = os.path.join(BASE_DIR, 'data', 'evaluation.json')
    
    NGRAM_N = 2
    LAMBDA = 0.4
    
    PINYIN_SIMILARITY_WEIGHT = 0.3
    PERSONALIZATION_WEIGHT = 0.2
    
    ENABLE_MULTILINGUAL = True
