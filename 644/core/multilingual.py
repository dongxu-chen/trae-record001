import re
import jieba
from pypinyin import lazy_pinyin, Style

class MultilingualCorrector:
    def __init__(self, domain_dict):
        self.domain_dict = domain_dict
        self.english_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.chinese_chars = set()
        self._init_chinese_chars()
        
        self.brand_mapping = {
            'apple': '苹果',
            'iphone': 'iPhone',
            'huawei': '华为',
            'xiaomi': '小米',
            'samsung': '三星',
            'oppo': 'OPPO',
            'vivo': 'vivo',
            'lenovo': '联想',
            'dell': '戴尔',
            'hp': '惠普',
            'sony': '索尼',
            'nike': '耐克',
            'adidas': '阿迪达斯',
            'uniqlo': '优衣库',
            'zara': 'ZARA',
            'coca': '可口',
            'cola': '可乐',
            'nongfu': '农夫',
            'shanquan': '山泉',
            'kangshifu': '康师傅',
            'yili': '伊利',
            'mengniu': '蒙牛'
        }
        
        self.common_english_words = {
            'phone': '手机',
            'case': '壳',
            'charger': '充电器',
            'earphone': '耳机',
            'headphone': '耳机',
            'bluetooth': '蓝牙',
            'computer': '电脑',
            'laptop': '笔记本',
            'notebook': '笔记本',
            'tablet': '平板',
            'watch': '手表',
            'mouse': '鼠标',
            'keyboard': '键盘',
            'monitor': '显示器',
            'router': '路由器',
            'power': '电源',
            'bank': '宝',
            'cable': '线',
            'stand': '支架',
            'cover': '套',
            'film': '膜',
            'stick': '杆',
            'dress': '连衣裙',
            'shirt': '衬衫',
            'tshirt': 'T恤',
            'jeans': '牛仔裤',
            'pants': '裤子',
            'shoes': '鞋',
            'coat': '外套',
            'hat': '帽子',
            'scarf': '围巾',
            'gloves': '手套',
            'socks': '袜子',
            'belt': '腰带',
            'milk': '牛奶',
            'bread': '面包',
            'noodle': '面',
            'water': '水',
            'biscuit': '饼干',
            'chocolate': '巧克力',
            'chip': '薯片',
            'drink': '饮料',
            'coffee': '咖啡',
            'tea': '茶',
            'oil': '油',
            'rice': '米',
            'flour': '面粉',
            'sauce': '酱油',
            'salt': '盐',
            'sugar': '糖',
            'paper': '纸',
            'tissue': '纸',
            'detergent': '洗衣液',
            'shampoo': '洗发水',
            'soap': '沐浴露'
        }
    
    def _init_chinese_chars(self):
        for codepoint in range(0x4e00, 0x9fff + 1):
            self.chinese_chars.add(chr(codepoint))
    
    def detect_language_mix(self, query):
        has_chinese = any(c in self.chinese_chars for c in query)
        has_english = any(c in self.english_chars for c in query)
        has_number = any(c.isdigit() for c in query)
        
        if has_chinese and has_english:
            return 'zh_en_mixed'
        elif has_english and not has_chinese:
            return 'english'
        elif has_chinese and not has_english:
            return 'chinese'
        else:
            return 'other'
    
    def split_mixed_tokens(self, query):
        tokens = []
        current = ''
        current_type = None
        
        for c in query:
            if c in self.english_chars:
                char_type = 'english'
            elif c in self.chinese_chars:
                char_type = 'chinese'
            elif c.isdigit():
                char_type = 'number'
            else:
                char_type = 'other'
            
            if current_type is None:
                current_type = char_type
                current = c
            elif char_type == current_type:
                current += c
            else:
                if current.strip():
                    tokens.append((current, current_type))
                current = c
                current_type = char_type
        
        if current.strip():
            tokens.append((current, current_type))
        
        return tokens
    
    def translate_english_token(self, token):
        token_lower = token.lower()
        
        if token_lower in self.brand_mapping:
            return self.brand_mapping[token_lower]
        
        if token_lower in self.common_english_words:
            return self.common_english_words[token_lower]
        
        return None
    
    def correct_mixed_query(self, query):
        tokens = self.split_mixed_tokens(query)
        corrected_tokens = []
        corrections = []
        
        for token, token_type in tokens:
            if token_type == 'english':
                translation = self.translate_english_token(token)
                if translation:
                    corrected_tokens.append(translation)
                    corrections.append({
                        'original': token,
                        'corrected': translation,
                        'type': 'en_to_zh'
                    })
                else:
                    pinyin_words = self.domain_dict.get_words_by_pinyin(token.lower())
                    if pinyin_words:
                        best_word = pinyin_words[0]
                        corrected_tokens.append(best_word)
                        corrections.append({
                            'original': token,
                            'corrected': best_word,
                            'type': 'pinyin'
                        })
                    else:
                        corrected_tokens.append(token)
            elif token_type == 'chinese':
                pinyin = ''.join(lazy_pinyin(token))
                pinyin_words = self.domain_dict.get_words_by_pinyin(pinyin)
                if pinyin_words and token not in self.domain_dict.words:
                    best_word = pinyin_words[0]
                    if best_word != token:
                        corrected_tokens.append(best_word)
                        corrections.append({
                            'original': token,
                            'corrected': best_word,
                            'type': 'zh_pinyin'
                        })
                    else:
                        corrected_tokens.append(token)
                else:
                    corrected_tokens.append(token)
            else:
                corrected_tokens.append(token)
        
        corrected_query = ''.join(corrected_tokens)
        return corrected_query, corrections
    
    def correct_english_query(self, query):
        query_lower = query.lower().strip()
        
        if query_lower in self.brand_mapping:
            return self.brand_mapping[query_lower], [{
                'original': query,
                'corrected': self.brand_mapping[query_lower],
                'type': 'brand'
            }]
        
        pinyin_words = self.domain_dict.get_words_by_pinyin(query_lower)
        if pinyin_words:
            best_word = pinyin_words[0]
            return best_word, [{
                'original': query,
                'corrected': best_word,
                'type': 'pinyin'
            }]
        
        words = query_lower.split()
        if len(words) > 1:
            translated_parts = []
            corrections = []
            for word in words:
                if word in self.common_english_words:
                    translated = self.common_english_words[word]
                    translated_parts.append(translated)
                    corrections.append({
                        'original': word,
                        'corrected': translated,
                        'type': 'en_to_zh'
                    })
                else:
                    translated_parts.append(word)
            
            translated = ''.join(translated_parts)
            if translated != query:
                return translated, corrections
        
        return query, []
    
    def correct_multilingual(self, query):
        lang_type = self.detect_language_mix(query)
        
        if lang_type == 'zh_en_mixed':
            return self.correct_mixed_query(query)
        elif lang_type == 'english':
            return self.correct_english_query(query)
        else:
            return query, []
