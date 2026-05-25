import re
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TextQualityResult:
    usefulness_score: float
    authenticity_score: float
    completeness_score: float
    overall_text_score: float
    usefulness_evidence: List[str]
    authenticity_evidence: List[str]
    completeness_evidence: List[str]
    keyword_analysis: Dict


class BERTTextAnalyzer:
    def __init__(self, use_pretrained: bool = False):
        self.use_pretrained = use_pretrained
        self._init_patterns()
        if use_pretrained:
            self._init_bert_model()
    
    def _init_patterns(self):
        self.useful_keywords = {
            'positive': [
                '推荐', '值得', '很好', '非常好', '优秀', '出色', '满意', '惊喜',
                '性价比高', '实用', '方便', '舒适', '美观', '耐用', '质量好',
                '客服好', '物流快', '包装好', '正品', '真的', '确实',
                '详细', '具体', '清晰', '全面', '专业', '客观', '中肯'
            ],
            'negative': [
                '垃圾', '很差', '不好', '劣质', '假货', '骗人', '坑人',
                '退款', '退货', '投诉', '曝光', '警告', '别买', '不要买',
                '虚假', '夸大', '误导', '欺诈'
            ],
            'detail': [
                '使用', '体验', '感受', '效果', '功能', '性能', '配置',
                '外观', '尺寸', '重量', '材质', '做工', '细节',
                '对比', '比较', '测试', '实测', '实际', '具体来说'
            ]
        }
        
        self.authenticity_patterns = {
            'suspicious': [
                r'^[1-5]星?$',
                r'^(很好|不错|差评|好评)$',
                r'^[a-zA-Z0-9\s]+$',
                r'重复|复制|粘贴',
                r'刷单|刷好评|刷信誉',
                r'^哈哈+^|^呵呵+$',
                r'^[^\u4e00-\u9fa5a-zA-Z0-9]+$'
            ],
            'emotional_intensifiers': [
                '非常', '极其', '特别', '简直', '完全', '绝对', '100%', '百分之百'
            ]
        }
        
        self.completeness_patterns = {
            'aspect_indicators': {
                'product_quality': ['质量', '品质', '做工', '材质', '耐用', '结实'],
                'appearance': ['外观', '颜值', '设计', '颜色', '款式', '样式'],
                'functionality': ['功能', '性能', '效果', '使用', '操作', '体验'],
                'service': ['客服', '售后', '服务', '态度', '解决', '回复'],
                'logistics': ['物流', '快递', '发货', '配送', '速度', '包装'],
                'price': ['价格', '性价比', '便宜', '贵', '划算', '实惠']
            }
        }
    
    def _init_bert_model(self):
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.tokenizer = AutoTokenizer.from_pretrained('bert-base-chinese')
            self.model = AutoModelForSequenceClassification.from_pretrained(
                'bert-base-chinese', num_labels=3
            ).to(self.device)
            self.model.eval()
            self.bert_available = True
        except Exception as e:
            print(f"警告: BERT模型加载失败，将使用规则引擎: {e}")
            self.bert_available = False
    
    def analyze(self, text: str) -> TextQualityResult:
        text = text.strip()
        
        usefulness_score, usefulness_evidence = self._analyze_usefulness(text)
        authenticity_score, authenticity_evidence = self._analyze_authenticity(text)
        completeness_score, completeness_evidence, keyword_analysis = self._analyze_completeness(text)
        
        weights = {
            'usefulness': 0.35,
            'authenticity': 0.35,
            'completeness': 0.30
        }
        
        overall_text_score = (
            usefulness_score * weights['usefulness'] +
            authenticity_score * weights['authenticity'] +
            completeness_score * weights['completeness']
        )
        
        return TextQualityResult(
            usefulness_score=round(usefulness_score, 4),
            authenticity_score=round(authenticity_score, 4),
            completeness_score=round(completeness_score, 4),
            overall_text_score=round(overall_text_score, 4),
            usefulness_evidence=usefulness_evidence,
            authenticity_evidence=authenticity_evidence,
            completeness_evidence=completeness_evidence,
            keyword_analysis=keyword_analysis
        )
    
    def _analyze_usefulness(self, text: str) -> Tuple[float, List[str]]:
        score = 0.0
        evidence = []
        text_lower = text.lower()
        
        text_length = len(text)
        if text_length >= 50:
            score += 0.2
            evidence.append(f"评论长度{text_length}字，内容较详实")
        elif text_length >= 20:
            score += 0.1
            evidence.append(f"评论长度{text_length}字，内容适中")
        else:
            score += 0.0
            evidence.append(f"评论长度{text_length}字，内容较简短")
        
        pos_matches = []
        for kw in self.useful_keywords['positive']:
            if kw in text:
                pos_matches.append(kw)
        if pos_matches:
            pos_score = min(0.25, len(pos_matches) * 0.05)
            score += pos_score
            evidence.append(f"正面评价词汇: {', '.join(pos_matches[:5])}")
        
        neg_matches = []
        for kw in self.useful_keywords['negative']:
            if kw in text:
                neg_matches.append(kw)
        if neg_matches:
            neg_score = min(0.25, len(neg_matches) * 0.05)
            score += neg_score
            evidence.append(f"负面评价词汇: {', '.join(neg_matches[:5])}")
        
        detail_matches = []
        for kw in self.useful_keywords['detail']:
            if kw in text:
                detail_matches.append(kw)
        if detail_matches:
            detail_score = min(0.30, len(detail_matches) * 0.06)
            score += detail_score
            evidence.append(f"细节描述词汇: {', '.join(detail_matches[:5])}")
        
        num_count = len(re.findall(r'\d+', text))
        if num_count >= 3:
            score += 0.15
            evidence.append(f"包含{num_count}处数字描述，更具说服力")
        elif num_count >= 1:
            score += 0.08
            evidence.append(f"包含{num_count}处数字描述")
        
        sentence_count = len(re.findall(r'[。！？.!?]', text))
        if sentence_count >= 4:
            score += 0.10
            evidence.append(f"包含{sentence_count}个句子，论述较充分")
        
        score = min(1.0, score)
        
        if score < 0.3:
            evidence.append("评论信息含量较低，参考价值有限")
        elif score < 0.6:
            evidence.append("评论有一定参考价值")
        else:
            evidence.append("评论信息丰富，参考价值较高")
        
        return score, evidence
    
    def _analyze_authenticity(self, text: str) -> Tuple[float, List[str]]:
        score = 1.0
        evidence = []
        text_lower = text.lower()
        
        for pattern in self.authenticity_patterns['suspicious']:
            if re.search(pattern, text_lower):
                score -= 0.2
                evidence.append(f"疑似模板化内容: 匹配模式 '{pattern}'")
        
        char_repeat = re.findall(r'(.)\1{4,}', text)
        if char_repeat:
            score -= 0.15
            evidence.append(f"存在字符重复现象: {''.join(char_repeat[:3])}")
        
        intensifier_count = sum(1 for w in self.authenticity_patterns['emotional_intensifiers'] if w in text)
        if intensifier_count >= 3:
            score -= 0.1
            evidence.append(f"情感修饰词过多（{intensifier_count}个），可能存在夸大")
        
        exclamation_count = text.count('!') + text.count('！')
        if exclamation_count >= 5:
            score -= 0.1
            evidence.append(f"感叹号过多（{exclamation_count}个），情绪化严重")
        
        if score >= 0.9 and len(text) >= 10:
            evidence.append("文本表达自然，无明显虚假特征")
        elif score >= 0.7:
            evidence.append("基本可信，但存在一些可疑特征")
        elif score >= 0.5:
            evidence.append("存在较多可疑特征，真实性存疑")
        else:
            evidence.append("高度疑似虚假评论")
        
        score = max(0.0, min(1.0, score))
        
        return score, evidence
    
    def _analyze_completeness(self, text: str) -> Tuple[float, List[str], Dict]:
        evidence = []
        aspect_scores = {}
        aspect_evidence = {}
        
        for aspect, keywords in self.completeness_patterns['aspect_indicators'].items():
            matches = [kw for kw in keywords if kw in text]
            if matches:
                aspect_scores[aspect] = min(1.0, len(matches) * 0.3)
                aspect_evidence[aspect] = matches
            else:
                aspect_scores[aspect] = 0.0
                aspect_evidence[aspect] = []
        
        covered_aspects = sum(1 for s in aspect_scores.values() if s > 0)
        total_aspects = len(aspect_scores)
        coverage_score = covered_aspects / total_aspects
        
        avg_aspect_score = np.mean(list(aspect_scores.values())) if aspect_scores else 0.0
        
        weights = {'coverage': 0.6, 'depth': 0.4}
        completeness_score = coverage_score * weights['coverage'] + avg_aspect_score * weights['depth']
        
        if covered_aspects >= 4:
            evidence.append(f"评论覆盖了{covered_aspects}/{total_aspects}个评价维度，分析全面")
        elif covered_aspects >= 2:
            evidence.append(f"评论覆盖了{covered_aspects}/{total_aspects}个评价维度")
        else:
            evidence.append(f"仅覆盖{covered_aspects}个评价维度，分析不够全面")
        
        aspect_names = {
            'product_quality': '产品质量',
            'appearance': '外观设计',
            'functionality': '功能体验',
            'service': '客户服务',
            'logistics': '物流配送',
            'price': '价格性价比'
        }
        
        for aspect, matches in aspect_evidence.items():
            if matches:
                evidence.append(f"- {aspect_names[aspect]}: {', '.join(matches)}")
        
        keyword_analysis = {
            'aspect_scores': {aspect_names[k]: round(v, 4) for k, v in aspect_scores.items()},
            'covered_aspects': covered_aspects,
            'total_aspects': total_aspects,
            'coverage_ratio': round(coverage_score, 4)
        }
        
        completeness_score = max(0.0, min(1.0, completeness_score))
        
        return completeness_score, evidence, keyword_analysis
    
    def _bert_analyze(self, text: str) -> Dict:
        if not self.bert_available or not self.use_pretrained:
            return {}
        
        try:
            import torch
            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            
            return {
                'bert_class': int(np.argmax(probs)),
                'bert_confidence': float(np.max(probs)),
                'bert_probabilities': {
                    'negative': float(probs[0]),
                    'neutral': float(probs[1]),
                    'positive': float(probs[2])
                }
            }
        except Exception as e:
            print(f"BERT推理失败: {e}")
            return {}
