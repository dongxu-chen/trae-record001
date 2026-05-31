import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

DEFAULT_CONFIG = {
    "language": "zh-CN",
    "supported_languages": {
        "zh-CN": "中文（普通话）",
        "zh-TW": "中文（台湾）",
        "en-US": "英语（美国）",
        "en-GB": "英语（英国）",
        "ja-JP": "日语",
        "ko-KR": "韩语",
        "fr-FR": "法语",
        "de-DE": "德语",
        "es-ES": "西班牙语",
        "ru-RU": "俄语"
    },
    "hotwords": [
        "人工智能",
        "机器学习",
        "深度学习",
        "神经网络",
        "自然语言处理",
        "计算机视觉",
        "区块链",
        "云计算",
        "大数据",
        "物联网"
    ],
    "websocket": {
        "host": "localhost",
        "port": 8765
    },
    "audio": {
        "sample_rate": 16000,
        "chunk_size": 512,
        "energy_threshold": 300,
        "dynamic_energy_threshold": True,
        "pause_threshold": 0.3,
        "non_speaking_duration": 0.2
    },
    "streaming": {
        "enabled": True,
        "target_latency_ms": 500,
        "min_send_interval_ms": 300,
        "partial_send_interval_ms": 300,
        "buffer_duration_sec": 0.3,
        "max_silence_frames": 10,
        "audio_queue_size": 100,
        "recognition_queue_size": 50
    },
    "punctuation": {
        "use_bert": True,
        "device": "auto",
        "model_name_zh": "ckiplab/albert-tiny-chinese-ws",
        "model_name_en": "oliverguhr/fullstop-punctuation-multilang-large",
        "fallback_enabled": True
    },
    "hotword_trie": {
        "enabled": True,
        "similarity_threshold": 0.6,
        "default_weight": 1.0,
        "weight_increment_per_match": 0.01,
        "weight_decay": 0.999
    },
    "diarization": {
        "enabled": True,
        "max_speakers": 6,
        "min_speakers": 2,
        "distance_threshold": 0.65,
        "min_segment_duration_sec": 0.5
    },
    "translation": {
        "enabled": False,
        "target_lang": "en",
        "service": "google",
        "cache_capacity": 500,
        "retry_attempts": 3
    }
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def add_hotword(word):
    config = load_config()
    if word not in config['hotwords']:
        config['hotwords'].append(word)
        save_config(config)
        return True
    return False

def remove_hotword(word):
    config = load_config()
    if word in config['hotwords']:
        config['hotwords'].remove(word)
        save_config(config)
        return True
    return False

def set_language(lang_code):
    config = load_config()
    if lang_code in config['supported_languages']:
        config['language'] = lang_code
        save_config(config)
        return True
    return False
