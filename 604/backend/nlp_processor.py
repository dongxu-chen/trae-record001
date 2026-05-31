import re
import jieba
import jieba.analyse
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import numpy as np
from config import settings


class TextRankSummarizer:
    def __init__(self, damping: float = 0.85, max_iter: int = 100, tol: float = 1e-5):
        self.damping = damping
        self.max_iter = max_iter
        self.tol = tol

    def _sentence_similarity(self, s1: str, s2: str) -> float:
        w1 = set(jieba.lcut(s1))
        w2 = set(jieba.lcut(s2))
        stop = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他', '她', '它', '们', '把', '被', '让', '给', '从', '向', '对', '跟', '与', '及', '或', '但', '而', '如', '若', '为', '以', '因', '由', '于', '虽', '然', '还', '又', '再', '已', '曾', '将', '可', '能', '应', '该', '当', '必', '须', '得'}
        w1 = {w for w in w1 if len(w) > 1 and w not in stop}
        w2 = {w for w in w2 if len(w) > 1 and w not in stop}
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / (np.log(len(w1)) + np.log(len(w2))) if len(w1 & w2) > 0 else 0.0

    def summarize(self, text: str, num_sentences: int = 5) -> List[str]:
        sentences = re.split(r'[。；;\n]', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        if len(sentences) <= num_sentences:
            return sentences

        n = len(sentences)
        sim_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                sim = self._sentence_similarity(sentences[i], sentences[j])
                sim_matrix[i][j] = sim
                sim_matrix[j][i] = sim

        for i in range(n):
            row_sum = sim_matrix[i].sum()
            if row_sum > 0:
                sim_matrix[i] /= row_sum

        scores = np.ones(n) / n
        for _ in range(self.max_iter):
            new_scores = np.ones(n) * (1 - self.damping) / n
            for i in range(n):
                for j in range(n):
                    if i != j and sim_matrix[j][i] > 0:
                        new_scores[i] += self.damping * scores[j] * sim_matrix[j][i]
            if np.abs(new_scores - scores).sum() < self.tol:
                break
            scores = new_scores

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top_indices = sorted([idx for idx, _ in ranked[:num_sentences]])
        return [sentences[i] for i in top_indices]


class SentencingFactorExtractor:
    SENTENCING_CATEGORIES = {
        "犯罪情节": {
            "严重": ["情节严重", "后果严重", "数额巨大", "数额特别巨大", "造成严重后果", "严重影响", "恶性事件", "数额较大"],
            "一般": ["情节较轻", "情节一般", "数额较小", "后果较轻"],
            "轻微": ["情节轻微", "情节显著轻微", "危害不大"],
        },
        "主观恶性": {
            "故意": ["故意", "蓄意", "预谋", "恶意", "蓄谋已久", "明知故犯"],
            "过失": ["过失", "疏忽大意", "过于自信", "疏忽"],
            "间接故意": ["放任", "听之任之", "间接故意"],
        },
        "社会危害": {
            "重大": ["社会危害性大", "危害公共安全", "严重扰乱", "严重破坏", "造成恶劣影响"],
            "较小": ["社会危害性较小", "危害不大", "影响较小"],
        },
        "悔罪表现": {
            "有悔罪": ["如实供述", "主动投案", "自首", "坦白", "认罪认罚", "积极退赃", "赔偿损失", "取得谅解", "真诚悔罪", "有悔罪表现"],
            "无悔罪": ["拒不认罪", "翻供", "逃避侦查", "拒不供述"],
        },
        "累犯前科": {
            "累犯": ["累犯", "再犯", "多次犯罪", "前科", "曾因", "被判处", "刑满释放后"],
            "初犯": ["初犯", "偶犯", "无前科", "初次"],
        },
        "从重情节": {
            "从重": ["从重处罚", "教唆未成年人", "在缓刑期内", "携带凶器", "入户", "多人共同", "主犯", "组织者", "领导者"],
        },
        "从轻情节": {
            "从轻": ["从轻处罚", "减轻处罚", "从犯", "胁从犯", "未遂", "中止", "防卫过当", "限定责任能力", "未成年", "已满七十五周岁", "怀孕", "立功", "重大立功"],
        },
        "量刑幅度": {
            "法定刑": ["判处有期徒刑", "判处无期徒刑", "判处死刑", "处三年以下", "处三年以上十年以下", "处十年以上", "拘役", "管制", "罚金", "剥夺政治权利", "没收财产", "缓刑"],
        },
        "损害结果": {
            "人身损害": ["死亡", "重伤", "轻伤", "轻微伤", "伤残"],
            "财产损害": ["经济损失", "财产损失", "盗窃", "诈骗", "侵占", "挪用"],
        },
    }

    def extract(self, text: str) -> Dict[str, Any]:
        factors = {}
        for category, subcategories in self.SENTENCING_CATEGORIES.items():
            found = []
            for level, keywords in subcategories.items():
                matched = []
                for kw in keywords:
                    if kw in text:
                        matched.append(kw)
                if matched:
                    found.append({"level": level, "keywords": list(set(matched))})
            if found:
                factors[category] = found

        amount_factors = self._extract_amount_factors(text)
        if amount_factors:
            factors["涉案金额"] = amount_factors

        time_factors = self._extract_time_factors(text)
        if time_factors:
            factors["时间要素"] = time_factors

        return factors

    def _extract_amount_factors(self, text: str) -> List[Dict[str, str]]:
        results = []
        amount_patterns = [
            (r'(\d+[,\d]*\.?\d*万元?)', "金额"),
            (r'人民币(\d+[,\d]*\.?\d*万?元?)', "金额"),
        ]
        thresholds = {
            "盗窃罪": {"数额较大": (1000, 30000), "数额巨大": (30000, 300000), "数额特别巨大": (300000, float('inf'))},
            "诈骗罪": {"数额较大": (3000, 30000), "数额巨大": (30000, 500000), "数额特别巨大": (500000, float('inf'))},
            "抢劫罪": {"数额巨大": (30000, float('inf'))},
        }
        for pattern, label in amount_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                amount_str = m if isinstance(m, str) else m[0]
                if amount_str:
                    amount_val = self._parse_amount(amount_str)
                    if amount_val > 0:
                        grade = self._grade_amount(amount_val, text, thresholds)
                        results.append({"amount": amount_str, "value": amount_val, "grade": grade})
        return results

    def _parse_amount(self, amount_str: str) -> float:
        amount_str = amount_str.replace(',', '').replace('元', '')
        if '万' in amount_str:
            amount_str = amount_str.replace('万', '')
            try:
                return float(amount_str) * 10000
            except ValueError:
                return 0
        try:
            return float(amount_str)
        except ValueError:
            return 0

    def _grade_amount(self, value: float, text: str, thresholds: dict) -> str:
        if value >= 300000:
            return "数额特别巨大"
        elif value >= 30000:
            return "数额巨大"
        elif value >= 3000:
            return "数额较大"
        else:
            return "数额较小"

    def _extract_time_factors(self, text: str) -> List[Dict[str, str]]:
        results = []
        duration_patterns = [
            (r'(\d+)年(\d+)个月', "刑期"),
            (r'有期徒刑(\d+)年', "刑期"),
            (r'拘役(\d+)个月', "刑期"),
            (r'缓刑(\d+)年', "缓刑期"),
        ]
        for pattern, label in duration_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                results.append({"type": label, "value": m if isinstance(m, str) else ''.join(m) + ("年" if "年" in pattern else "个月")})
        return results

    def get_sentencing_summary(self, factors: Dict[str, Any]) -> Dict[str, Any]:
        summary = {
            "aggravating": [],
            "mitigating": [],
            "severity_assessment": "一般",
            "key_factors": []
        }
        if "从重情节" in factors:
            for item in factors["从重情节"]:
                summary["aggravating"].extend(item["keywords"])
        if "累犯前科" in factors:
            for item in factors["累犯前科"]:
                if item["level"] == "累犯":
                    summary["aggravating"].extend(item["keywords"])
        if "犯罪情节" in factors:
            for item in factors["犯罪情节"]:
                if item["level"] == "严重":
                    summary["aggravating"].extend(item["keywords"])
                    summary["severity_assessment"] = "严重"
                elif item["level"] == "轻微":
                    summary["severity_assessment"] = "轻微"

        if "从轻情节" in factors:
            for item in factors["从轻情节"]:
                summary["mitigating"].extend(item["keywords"])
        if "悔罪表现" in factors:
            for item in factors["悔罪表现"]:
                if item["level"] == "有悔罪":
                    summary["mitigating"].extend(item["keywords"])
        if "累犯前科" in factors:
            for item in factors["累犯前科"]:
                if item["level"] == "初犯":
                    summary["mitigating"].extend(item["keywords"])

        all_keywords = []
        for category, items in factors.items():
            for item in items:
                if "keywords" in item:
                    all_keywords.extend(item["keywords"])
        summary["key_factors"] = list(set(all_keywords))[:10]

        return summary


class NLPProcessor:
    def __init__(self):
        self._model = None
        self._embedding_model = None
        self._summarizer = TextRankSummarizer()
        self._sentencing_extractor = SentencingFactorExtractor()
        self._init_models()

    def _init_models(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(settings.BERT_MODEL_NAME)
            print("BERT模型加载成功")
        except Exception as e:
            print(f"BERT模型加载失败，使用模拟模式: {e}")
            self._embedding_model = None

    def get_embedding(self, text: str) -> List[float]:
        if self._embedding_model:
            try:
                embedding = self._embedding_model.encode(text)
                return embedding.tolist()
            except:
                pass
        return self._get_mock_embedding(text)

    def _get_mock_embedding(self, text: str) -> List[float]:
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        np.random.seed(int(hash_hex[:8], 16))
        embedding = np.random.randn(384)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()

    def analyze_case_description(self, text: str) -> Dict[str, Any]:
        legal_entities = self._extract_legal_entities(text)
        sentencing_factors = self._sentencing_extractor.extract(text)
        sentencing_summary = self._sentencing_extractor.get_sentencing_summary(sentencing_factors)
        key_points = self._extractive_summarize(text)
        case_type = self._classify_case_type(text)
        keywords = self._extract_keywords(text)

        return {
            "legal_entities": legal_entities,
            "sentencing_factors": sentencing_factors,
            "sentencing_summary": sentencing_summary,
            "key_points": key_points,
            "case_type": case_type,
            "keywords": keywords,
            "summary": self._generate_summary(text)
        }

    def _extract_legal_entities(self, text: str) -> Dict[str, List[str]]:
        entities = {
            "原告": [],
            "被告": [],
            "金额": [],
            "日期": [],
            "地点": [],
            "证据": [],
            "法条": [],
            "罪名": [],
            "法院": [],
            "诉讼请求": [],
            "量刑建议": [],
        }

        plaintiff_patterns = [
            r'原告[：:]\s*([^，。；;\n]+)',
            r'([^，。；;\n]+)诉称',
            r'公诉机关[：:]\s*([^，。；;\n]+)',
            r'自诉人[：:]\s*([^，。；;\n]+)',
        ]
        for pattern in plaintiff_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m and len(m) < 50:
                    entities["原告"].append(m.strip())

        defendant_patterns = [
            r'被告[：:]\s*([^，。；;\n]+)',
            r'被告人[：:]\s*([^，。；;\n]+)',
            r'([^，。；;\n]+)辩称',
        ]
        for pattern in defendant_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m and len(m) < 50:
                    entities["被告"].append(m.strip())

        amount_patterns = [
            r'(\d+[,\d]*\.?\d*万?元)',
            r'人民币(\d+[,\d]*\.?\d*万?元?)',
        ]
        for pattern in amount_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                amount = m[0] if isinstance(m, tuple) else m
                if amount:
                    entities["金额"].append(amount)

        date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})',
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            entities["日期"].extend(matches)

        location_patterns = [
            r'([^，。；;\n]{2,10}(?:省|市|区|县|镇|乡|村|街|路|号))',
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m and len(m) >= 3 and len(m) <= 15:
                    entities["地点"].append(m.strip())

        evidence_keywords = [
            '借条', '欠条', '合同', '协议', '转账记录', '银行流水',
            '收据', '发票', '证人证言', '鉴定意见', '勘验笔录',
            '视听资料', '电子数据', '书证', '物证', '被害人陈述',
            '被告人供述', '辩解', 'DNA鉴定', '指纹鉴定', '法医鉴定',
        ]
        for kw in evidence_keywords:
            if kw in text:
                entities["证据"].append(kw)

        law_patterns = [
            r'《([^》]+)》',
            r'([^，。；;\n]{2,8}法)第[一二三四五六七八九十百千\d]+条',
        ]
        for pattern in law_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                entities["法条"].append(m)

        crime_patterns = [
            r'犯([^，。；;\n]{2,8}罪)',
            r'以([^，。；;\n]{2,8}罪)',
            r'涉嫌([^，。；;\n]{2,8}罪)',
        ]
        for pattern in crime_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if len(m) >= 3:
                    entities["罪名"].append(m)

        court_patterns = [
            r'([^，。；;\n]{2,15}人民法院)',
            r'([^，。；;\n]{2,15}中级人民法院)',
        ]
        for pattern in court_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m and len(m) >= 5:
                    entities["法院"].append(m.strip())

        claim_patterns = [
            r'(请求判令[^，。；;\n]{5,80})',
            r'(诉请[^，。；;\n]{5,80})',
        ]
        for pattern in claim_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m and len(m) > 5:
                    entities["诉讼请求"].append(m.strip())

        sentencing_suggest_patterns = [
            r'(建议判处[^，。；;\n]{5,60})',
            r'(量刑建议[^，。；;\n]{5,60})',
        ]
        for pattern in sentencing_suggest_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m:
                    entities["量刑建议"].append(m.strip())

        for key in entities:
            entities[key] = list(set(entities[key]))

        return entities

    def _extractive_summarize(self, text: str) -> List[str]:
        sentences = self._summarizer.summarize(text, num_sentences=5)
        if not sentences:
            sentences = re.split(r'[。；;\n]', text)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
            sentences = sentences[:5]

        scored = []
        legal_signal_words = [
            '原告诉称', '被告辩称', '经审理查明', '本院认为', '判决如下',
            '借款', '合同', '违约', '利息', '赔偿', '犯罪', '故意',
            '盗窃', '诈骗', '抢劫', '伤害', '自首', '累犯', '未遂',
            '从轻', '从重', '减轻', '量刑', '判处',
        ]
        for i, sent in enumerate(sentences):
            score = 0
            for kw in legal_signal_words:
                if kw in sent:
                    score += 1
            if len(sent) > 15:
                score += 0.5
            scored.append((-score, i, sent))

        scored.sort()
        return [s[2] for s in scored[:5]]

    def _classify_case_type(self, text: str) -> str:
        case_types = {
            "民间借贷纠纷": ["借款", "借条", "欠条", "借贷", "利息", "还款"],
            "合同纠纷": ["合同", "协议", "违约", "履行", "解除"],
            "买卖合同纠纷": ["买卖", "货款", "货物", "交付"],
            "租赁合同纠纷": ["租赁", "租金", "承租", "出租"],
            "劳动争议": ["劳动", "工资", "工伤", "解除劳动合同", "经济补偿"],
            "交通事故责任纠纷": ["交通事故", "肇事", "交强险", "伤残"],
            "婚姻家庭纠纷": ["离婚", "抚养", "财产分割", "继承"],
            "盗窃罪": ["盗窃", "偷窃", "窃取"],
            "诈骗罪": ["诈骗", "骗取", "虚构事实"],
            "故意伤害罪": ["故意伤害", "殴打", "轻伤", "重伤"],
            "抢劫罪": ["抢劫", "暴力", "胁迫"],
        }

        max_score = 0
        case_type = "其他纠纷"

        for ctype, keywords in case_types.items():
            score = sum(2 if kw in text else 0 for kw in keywords)
            if score > max_score:
                max_score = score
                case_type = ctype

        return case_type

    def _extract_keywords(self, text: str) -> List[str]:
        words = jieba.lcut(text)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他', '她', '它', '们', '把', '被', '让', '给', '从', '向', '对', '跟', '与', '及', '或', '但', '而', '如', '若', '为', '以', '因', '由', '于', '虽', '然', '但', '是', '还', '又', '再', '已', '曾', '将', '要', '会', '可', '能', '应', '该', '当', '必', '须', '得', '到'}

        keywords = [w for w in words if len(w) > 1 and w not in stop_words]

        freq = {}
        for w in keywords:
            freq[w] = freq.get(w, 0) + 1

        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in sorted_keywords[:20]]

    def _generate_summary(self, text: str) -> str:
        top_sentences = self._summarizer.summarize(text, num_sentences=3)
        if top_sentences:
            return '。'.join(top_sentences) + '。'

        sentences = re.split(r'[。；;\n]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= 3:
            return ''.join(sentences)
        return '。'.join(sentences[:3]) + '。'
