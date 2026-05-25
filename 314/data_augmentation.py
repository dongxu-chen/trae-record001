import re
import random
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class AugmentResult:
    original_text: str
    augmented_texts: List[str]
    methods_used: List[str]
    augmentation_stats: Dict


class TextDataAugmentor:
    def __init__(self, random_seed: int = 42):
        random.seed(random_seed)
        np.random.seed(random_seed)
        self._init_synonym_dictionary()
        self._init_back_translation_map()
    
    def _init_synonym_dictionary(self):
        self.synonym_dict = {
            '很好': ['非常好', '特别好', '相当好', '很不错', '挺好的', '超赞'],
            '不错': ['挺好', '还可以', '还行', '不赖', '可以'],
            '很差': ['不好', '糟糕', '差劲', '不怎么样', '一般般'],
            '推荐': ['建议购买', '值得入手', '强烈推荐', '值得推荐'],
            '喜欢': ['爱了', '中意', '很满意', '超喜欢'],
            '满意': ['很满意', '挺满意', '非常满意', '比较满意'],
            '不满意': ['不太满意', '很失望', '有点失望', '不尽人意'],
            '便宜': ['实惠', '划算', '不贵', '性价比高', '物美价廉'],
            '贵': ['不便宜', '价格偏高', '有点贵', '价格不菲'],
            '快': ['迅速', '很快', '挺快', '效率高'],
            '慢': ['很慢', '慢死了', '龟速', '效率低'],
            '漂亮': ['好看', '美观', '精致', '颜值高'],
            '丑': ['不好看', '难看', '丑爆了', '颜值低'],
            '舒服': ['舒适', '很舒服', '超舒服', '安逸'],
            '难受': ['不舒服', '不舒适', '难受', '煎熬'],
            '耐用': ['结实', '耐造', '质量好', '经久耐用'],
            '容易坏': ['不耐用', '质量差', '易坏', '不结实'],
            '清晰': ['清楚', '高清', '很清晰', '清晰度高'],
            '模糊': ['不清楚', '不清晰', '糊', '发虚'],
            '方便': ['便捷', '省事', '省心', '很方便'],
            '麻烦': ['不方便', '费事', '繁琐', '折腾'],
        }
        
        self.stopwords = {
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '在',
            '这', '那', '有', '个', '上', '下', '也', '还', '很', '太',
            '非常', '特别', '真的', '实在', '确实', '其实', '感觉',
            '我', '你', '他', '她', '它', '我们', '你们', '他们',
        }
    
    def _init_back_translation_map(self):
        self.back_translation_map = {
            'zh-en-zh': {
                '这款手机很好用': ['This phone is very easy to use', '这款手机非常好用'],
                '质量不错': ['The quality is good', '质量很好'],
                '推荐购买': ['Recommend to buy', '建议购买'],
                '性价比很高': ['Great value for money', '物超所值'],
                '物流很快': ['The logistics is very fast', '配送速度很快'],
                '客服态度好': ['Customer service attitude is good', '客服服务态度很好'],
                '包装精美': ['The packaging is exquisite', '包装很精致'],
                '正品保证': ['Authentic guarantee', '保证正品'],
                '使用方便': ['Easy to use', '使用起来很方便'],
                '做工精细': ['Workmanship is fine', '做工很精细'],
                '续航能力强': ['Strong battery life', '续航很强'],
                '拍照清晰': ['Photos are clear', '拍照很清晰'],
                '屏幕清晰': ['The screen is clear', '屏幕很清晰'],
                '声音清晰': ['The sound is clear', '声音很清晰'],
                '手感好': ['Good hand feel', '手感不错'],
                '外观好看': ['Good looking appearance', '外观很漂亮'],
            }
        }
        
        self.pseudo_translation_patterns = [
            (r'很(.{1,2})', r'非常\1'),
            (r'非常(.{1,2})', r'特别\1'),
            (r'(.{1,2})好', r'\1很不错'),
            (r'(.{1,2})快', r'\1迅速'),
            (r'不(.{1,2})', r'不太\1'),
            (r'没有(.{1,2})', r'并无\1'),
        ]
    
    def augment(
        self,
        text: str,
        num_augments: int = 5,
        methods: Optional[List[str]] = None,
        min_length: int = 5
    ) -> AugmentResult:
        if len(text) < min_length:
            return AugmentResult(
                original_text=text,
                augmented_texts=[],
                methods_used=[],
                augmentation_stats={'error': '文本太短，不适合数据增强'}
            )
        
        if methods is None:
            methods = [
                'synonym_replacement',
                'random_deletion',
                'random_swap',
                'random_insertion',
                'pseudo_back_translation',
                'text_shuffling',
                'char_replacement',
                'contextual_insertion'
            ]
        
        augmented_texts = []
        methods_used = []
        method_counts = defaultdict(int)
        
        available_methods = methods.copy()
        
        for _ in range(num_augments):
            if not available_methods:
                available_methods = methods.copy()
            
            method = random.choice(available_methods)
            augmented_text = self._apply_augmentation(text, method)
            
            if augmented_text and augmented_text != text and len(augmented_text) >= min_length:
                augmented_texts.append(augmented_text)
                methods_used.append(method)
                method_counts[method] += 1
            
            available_methods.remove(method)
        
        augmented_texts = list(dict.fromkeys(augmented_texts))
        
        stats = {
            'original_length': len(text),
            'num_augments_generated': len(augmented_texts),
            'num_augments_requested': num_augments,
            'method_distribution': dict(method_counts),
            'augmentation_ratio': len(augmented_texts) / num_augments if num_augments > 0 else 0
        }
        
        return AugmentResult(
            original_text=text,
            augmented_texts=augmented_texts,
            methods_used=list(dict.fromkeys(methods_used)),
            augmentation_stats=stats
        )
    
    def _apply_augmentation(self, text: str, method: str) -> Optional[str]:
        try:
            if method == 'synonym_replacement':
                return self._synonym_replacement(text)
            elif method == 'random_deletion':
                return self._random_deletion(text)
            elif method == 'random_swap':
                return self._random_swap(text)
            elif method == 'random_insertion':
                return self._random_insertion(text)
            elif method == 'pseudo_back_translation':
                return self._pseudo_back_translation(text)
            elif method == 'text_shuffling':
                return self._text_shuffling(text)
            elif method == 'char_replacement':
                return self._char_replacement(text)
            elif method == 'contextual_insertion':
                return self._contextual_insertion(text)
            else:
                return None
        except Exception:
            return None
    
    def _synonym_replacement(self, text: str, p: float = 0.3) -> str:
        words = list(text)
        replaced = 0
        
        for i in range(len(words)):
            if random.random() < p:
                char = words[i]
                for key, synonyms in self.synonym_dict.items():
                    if char in key and len(key) <= 2:
                        if synonyms:
                            synonym = random.choice(synonyms)
                            if len(key) == 1:
                                words[i] = synonym[0] if synonym else char
                                replaced += 1
                            else:
                                pass
                        break
        
        if replaced == 0:
            for key, synonyms in self.synonym_dict.items():
                if key in text and synonyms:
                    synonym = random.choice(synonyms)
                    text = text.replace(key, synonym, 1)
                    return text
        
        return ''.join(words)
    
    def _random_deletion(self, text: str, p: float = 0.1) -> str:
        chars = list(text)
        
        if len(chars) <= 3:
            return text
        
        keep_indices = []
        for i in range(len(chars)):
            if chars[i] in self.stopwords:
                if random.random() < p * 2:
                    continue
            else:
                if random.random() < p:
                    continue
            keep_indices.append(i)
        
        if len(keep_indices) < 3:
            keep_indices = sorted(random.sample(range(len(chars)), max(3, len(chars) // 2)))
        
        return ''.join([chars[i] for i in sorted(keep_indices)])
    
    def _random_swap(self, text: str, n_swaps: int = 2) -> str:
        chars = list(text)
        
        if len(chars) < 4:
            return text
        
        for _ in range(n_swaps):
            i, j = random.sample(range(len(chars)), 2)
            chars[i], chars[j] = chars[j], chars[i]
        
        return ''.join(chars)
    
    def _random_insertion(self, text: str, n_insertions: int = 2) -> str:
        chars = list(text)
        
        filler_words = ['真的', '确实', '非常', '特别', '很', '太', '挺', '比较']
        
        for _ in range(n_insertions):
            pos = random.randint(0, len(chars))
            filler = random.choice(filler_words)
            chars.insert(pos, random.choice(filler))
        
        return ''.join(chars)
    
    def _pseudo_back_translation(self, text: str) -> str:
        if text in self.back_translation_map['zh-en-zh']:
            return self.back_translation_map['zh-en-zh'][text][1]
        
        for pattern, replacement in self.pseudo_translation_patterns:
            if re.search(pattern, text):
                return re.sub(pattern, replacement, text, count=1)
        
        all_synonyms = []
        for key, synonyms in self.synonym_dict.items():
            if key in text:
                all_synonyms.append((key, synonyms))
        
        if all_synonyms:
            key, synonyms = random.choice(all_synonyms)
            synonym = random.choice(synonyms)
            return text.replace(key, synonym, 1)
        
        return text
    
    def _text_shuffling(self, text: str) -> str:
        sentences = re.split(r'([。！？.!?，,])', text)
        
        if len(sentences) < 3:
            return text
        
        sentence_parts = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence_parts.append(sentences[i] + sentences[i + 1])
            else:
                sentence_parts.append(sentences[i])
        
        if len(sentence_parts) >= 2:
            i, j = random.sample(range(len(sentence_parts)), 2)
            sentence_parts[i], sentence_parts[j] = sentence_parts[j], sentence_parts[i]
        
        return ''.join(sentence_parts)
    
    def _char_replacement(self, text: str, p: float = 0.05) -> str:
        similar_chars = {
            '0': ['O', 'o', '〇'],
            '1': ['l', 'I', '一'],
            '2': ['Z', 'z'],
            'a': ['@', 'α'],
            'b': ['6', 'β'],
            'g': ['9', 'q'],
            's': ['5', '$'],
            '的': ['の', '啲'],
            '是': ['系', '4'],
            '不': ['吥', '8'],
        }
        
        chars = list(text)
        
        for i in range(len(chars)):
            if random.random() < p and chars[i] in similar_chars:
                replacements = similar_chars[chars[i]]
                chars[i] = random.choice(replacements)
        
        return ''.join(chars)
    
    def _contextual_insertion(self, text: str) -> str:
        positive_inserts = [
            '个人感觉 ',
            '我认为 ',
            '总的来说 ',
            '事实上 ',
            '实际上 ',
            '老实说 ',
        ]
        
        negative_inserts = [
            '可惜的是 ',
            '遗憾的是 ',
            '美中不足的是 ',
            '但是 ',
            '不过 ',
        ]
        
        neutral_inserts = [
            '另外，',
            '还有，',
            '此外，',
            '而且，',
        ]
        
        insert_type = random.choice(['positive', 'negative', 'neutral'])
        
        if insert_type == 'positive':
            insert = random.choice(positive_inserts)
            return insert + text
        elif insert_type == 'negative':
            insert = random.choice(negative_inserts)
            return text + '。' + insert + '还有提升空间'
        else:
            insert = random.choice(neutral_inserts)
            if len(text) > 10:
                mid = len(text) // 2
                return text[:mid] + insert + text[mid:]
            else:
                return insert + text
    
    def augment_short_comments(
        self,
        comments: List[str],
        per_comment_augments: int = 3,
        methods: Optional[List[str]] = None
    ) -> Dict[str, AugmentResult]:
        results = {}
        
        for idx, comment in enumerate(comments):
            result = self.augment(
                text=comment,
                num_augments=per_comment_augments,
                methods=methods
            )
            results[f'comment_{idx}'] = result
        
        return results
    
    def create_augmented_dataset(
        self,
        original_texts: List[str],
        labels: Optional[List[int]] = None,
        augment_per_sample: int = 4,
        balance_classes: bool = False
    ) -> Tuple[List[str], Optional[List[int]]]:
        augmented_texts = []
        augmented_labels = []
        
        if labels and balance_classes:
            from collections import Counter
            label_counts = Counter(labels)
            max_count = max(label_counts.values())
            
            for text, label in zip(original_texts, labels):
                augmented_texts.append(text)
                augmented_labels.append(label)
                
                samples_needed = max_count - label_counts[label]
                if samples_needed > 0:
                    n_augments = min(augment_per_sample, samples_needed)
                    result = self.augment(text, num_augments=n_augments)
                    for aug_text in result.augmented_texts:
                        augmented_texts.append(aug_text)
                        augmented_labels.append(label)
                        label_counts[label] += 1
        else:
            for i, text in enumerate(original_texts):
                augmented_texts.append(text)
                if labels:
                    augmented_labels.append(labels[i])
                
                result = self.augment(text, num_augments=augment_per_sample)
                for aug_text in result.augmented_texts:
                    augmented_texts.append(aug_text)
                    if labels:
                        augmented_labels.append(labels[i])
        
        return augmented_texts, augmented_labels if labels else None
    
    def get_method_description(self) -> Dict[str, str]:
        return {
            'synonym_replacement': '同义词替换 - 随机将文本中的词汇替换为同义词',
            'random_deletion': '随机删除 - 以一定概率随机删除文本中的字符',
            'random_swap': '随机交换 - 随机交换文本中两个字符的位置',
            'random_insertion': '随机插入 - 随机在文本中插入语气词或修饰词',
            'pseudo_back_translation': '伪回译 - 模拟翻译过程进行句式转换',
            'text_shuffling': '句子打乱 - 随机打乱句子顺序',
            'char_replacement': '字符替换 - 将字符替换为形似字符',
            'contextual_insertion': '上下文插入 - 在文本前后插入过渡短语',
        }
