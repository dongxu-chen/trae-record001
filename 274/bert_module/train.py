import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from bert_module import IntentClassifier, AttributeExtractor


def train_intent_classifier():
    print('=' * 50)
    print('Training Intent Classifier...')
    print('=' * 50)
    
    data_path = os.path.join(Config.DATA_DIR, 'intent_data.json')
    save_path = Config.INTENT_MODEL_PATH
    
    classifier = IntentClassifier()
    classifier.train(data_path, save_path)
    
    print('\nTesting Intent Classifier...')
    test_texts = [
        '我想买iPhone 15',
        '苹果和华为哪个手机好',
        '什么是4K屏幕'
    ]
    
    for text in test_texts:
        result = classifier.predict(text)
        print(f'Text: {text}')
        print(f'Intent: {result["intent"]}, Confidence: {result["confidence"]:.4f}')
        print()


def train_attribute_extractor():
    print('=' * 50)
    print('Training Attribute Extractor...')
    print('=' * 50)
    
    data_path = os.path.join(Config.DATA_DIR, 'attribute_data.json')
    save_path = Config.ATTR_MODEL_PATH
    
    extractor = AttributeExtractor()
    extractor.train(data_path, save_path)
    
    print('\nTesting Attribute Extractor...')
    test_texts = [
        '苹果iPhone 15 256G手机',
        '索尼WH-1000XM5降噪耳机',
        '戴尔27寸4K显示器'
    ]
    
    for text in test_texts:
        result = extractor.extract(text)
        print(f'Text: {text}')
        print(f'Brands: {result["brands"]}')
        print(f'Categories: {result["categories"]}')
        print(f'Specs: {result["specs"]}')
        print()


if __name__ == '__main__':
    Config.ensure_dirs()
    
    train_intent_classifier()
    train_attribute_extractor()
    
    print('=' * 50)
    print('Training completed!')
    print('=' * 50)
