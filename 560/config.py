import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    IMAGE_SIZE = 256
    CANVAS_SIZE = 1000
    FONT_UNITS_PER_EM = 1000
    BASELINE = 200
    ASCENDER = 800
    DESCENDER = -200
    
    CHAR_SETS = {
        'english_lower': 'abcdefghijklmnopqrstuvwxyz',
        'english_upper': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'digits': '0123456789',
        'punctuation': '.,!?;:()[]{}"\'-_+/\\<>@#$%^&*=',
        'chinese_common': '的一是了我不人在他有这个上们来到时大地为子中你说生国年着就那和要她出也得里后自以会家可下而过天去能对小多然于心学么之都好看起发当没成只如事把还用第样道想作种开美总从无情己面最女但现前些所同日手又行意动方期它头经长儿回位分爱老因很给名法间斯知世什两次使身者被高已亲其进此话常与活正感见明问力理尔点文几定本公特做外孩相西果走将月十实向声车全信重三机工物气每并别真打太新比才便夫再书部水像眼少家经'
    }
    
    @classmethod
    def get_all_chars(cls):
        return ''.join(cls.CHAR_SETS.values())
    
    @classmethod
    def get_char_list(cls, include_chinese=True):
        chars = []
        chars.extend(list(cls.CHAR_SETS['english_lower']))
        chars.extend(list(cls.CHAR_SETS['english_upper']))
        chars.extend(list(cls.CHAR_SETS['digits']))
        chars.extend(list(cls.CHAR_SETS['punctuation']))
        if include_chinese:
            chars.extend(list(cls.CHAR_SETS['chinese_common']))
        return chars

class TrainingConfig:
    BATCH_SIZE = 16
    LEARNING_RATE = 0.0002
    EPOCHS = 100
    LATENT_DIM = 128
    HIDDEN_DIM = 256
    SAVE_INTERVAL = 10
    
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    SAMPLES_DIR = os.path.join(DATA_DIR, 'samples')
    MODEL_DIR = os.path.join(BASE_DIR, 'models')
    OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
    
    @classmethod
    def ensure_dirs(cls):
        for dir_path in [cls.DATA_DIR, cls.SAMPLES_DIR, cls.MODEL_DIR, cls.OUTPUT_DIR]:
            os.makedirs(dir_path, exist_ok=True)
