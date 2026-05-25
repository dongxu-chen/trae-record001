import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    USE_TINYBERT = os.getenv('USE_TINYBERT', 'true').lower() == 'true'
    TINYBERT_MODEL_NAME = os.getenv('TINYBERT_MODEL_NAME', 'huawei-noah/TinyBERT_4L_zh')
    BERT_MODEL_NAME = os.getenv('BERT_MODEL_NAME', 'bert-base-chinese')
    
    INTENT_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'intent_classifier')
    ATTR_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'attribute_extractor')
    
    MAX_SEQ_LENGTH = 64
    BATCH_SIZE = 64
    EPOCHS = 15
    LEARNING_RATE = 3e-5
    
    USE_QUANTIZATION = os.getenv('USE_QUANTIZATION', 'true').lower() == 'true'
    USE_ONNX = os.getenv('USE_ONNX', 'false').lower() == 'true'
    INFERENCE_BATCH_SIZE = 1
    
    REWRITE_CONFIDENCE_THRESHOLD = float(os.getenv('REWRITE_CONFIDENCE_THRESHOLD', 0.7))
    
    INTENT_LABELS = ['购买意向', '比价', '知识查询']
    ATTRIBUTE_LABELS = ['O', 'B-BRAND', 'I-BRAND', 'B-CATEGORY', 'I-CATEGORY', 'B-SPEC', 'I-SPEC']
    
    ES_HOST = os.getenv('ES_HOST', 'localhost')
    ES_PORT = int(os.getenv('ES_PORT', 9200))
    ES_INDEX = os.getenv('ES_INDEX', 'ecommerce_products')
    
    KG_PATH = os.path.join(BASE_DIR, 'data', 'knowledge_graph.json')
    SYNONYM_PATH = os.path.join(BASE_DIR, 'data', 'synonyms.txt')
    
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    MODEL_DIR = os.path.join(BASE_DIR, 'models')
    
    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.MODEL_DIR, exist_ok=True)
        os.makedirs(cls.INTENT_MODEL_PATH, exist_ok=True)
        os.makedirs(cls.ATTR_MODEL_PATH, exist_ok=True)
