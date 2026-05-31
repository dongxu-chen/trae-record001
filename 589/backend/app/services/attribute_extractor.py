import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedAttribute:
    key: str
    value: str
    confidence: float
    source: str


@dataclass
class AttributeExtractionResult:
    raw_text: str
    extracted_attributes: Dict[str, Any]
    normalized_spec: Dict[str, Any]
    quality_score: float
    extraction_method: str


class AttributePattern:
    def __init__(self, key: str, patterns: List[str], category: Optional[str] = None):
        self.key = key
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.category = category


class AttributeExtractor:
    def __init__(self):
        self._init_patterns()
        self._init_unit_normalizers()
        self._init_category_hierarchy()

    def _init_patterns(self):
        self.patterns: Dict[str, List[AttributePattern]] = {
            "color": [
                AttributePattern("color", [
                    r"(?:颜色|color|colour|色系)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(黑|白|灰|红|橙|黄|绿|青|蓝|紫|粉|金|银|棕|米|咖|驼|藏青|军绿|墨绿|酒红|枣红|香槟|玫瑰金|深空灰|土豪金|哑光黑|亮黑色|珍珠白|象牙白|奶白色|米白色|天蓝色|湖蓝色|宝蓝色|藏蓝色|墨绿色|浅绿色|深绿色|浅粉色|深粉色|浅紫色|深紫色|浅黄色|深黄色|浅灰色|深灰色|浅棕色|深棕色)[色]?",
                ])
            ],
            "size": [
                AttributePattern("size", [
                    r"(?:尺寸|大小|size|尺码|规格)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(XS|S|M|L|XL|XXL|XXXL|XXXXL|2XL|3XL|4XL|5XL|特大|大码|小码|均码|加大|加小)(?:$|[\s，,。；;)）])",
                    r"(\d+(?:\.\d+)?)\s*(?:cm|厘米|公分|mm|毫米|m|米|英寸|inch|in)(?:\s*[xX×*]\s*\d+(?:\.\d+)?\s*(?:cm|厘米|公分|mm|毫米|m|米)?)?",
                ])
            ],
            "capacity": [
                AttributePattern("capacity", [
                    r"(?:容量|内存|运存|存储|storage|capacity)[：:]\s*([^\s，,。；;]+)",
                    r"(\d+(?:\.\d+)?)\s*(?:GB|G|MB|M|TB|T|KB|K)(?:\s*[/+]\s*\d+\s*(?:GB|G)?)?\b",
                    r"(\d+(?:\.\d+)?)\s*(?:升|L|ml|毫升|公升)(?:\s*[/+]\s*\d+\s*(?:升|L|ml)?)?\b",
                ])
            ],
            "weight": [
                AttributePattern("weight", [
                    r"(?:重量|毛重|净重|weight)[：:]\s*([^\s，,。；;]+)",
                    r"(\d+(?:\.\d+)?)\s*(?:kg|千克|公斤|g|克|mg|毫克|磅|lb)\b",
                ])
            ],
            "material": [
                AttributePattern("material", [
                    r"(?:材质|材料|面料|材质成分|material)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(纯棉|全棉|涤纶|聚酯纤维|锦纶|氨纶|羊毛|羊绒|真丝|桑蚕丝|丝绸|亚麻|苎麻|粘胶|莫代尔|冰丝|速干面料|牛仔布|灯芯绒|皮革|真皮|牛皮|羊皮|PU|PVC|塑料|ABS|PC|不锈钢|铝合金|铜|铁|陶瓷|玻璃|硅胶|橡胶|乳胶|海绵)(?:$|[\s，,。；;)）])",
                ])
            ],
            "brand": [
                AttributePattern("brand", [
                    r"(?:品牌|牌子|brand)[：:]\s*([^\s，,。；;]+)",
                ])
            ],
            "model": [
                AttributePattern("model", [
                    r"(?:型号|款式|model)[：:]\s*([^\s，,。；;]+)",
                ])
            ],
            "version": [
                AttributePattern("version", [
                    r"(?:版本|款型|标准版|青春版|旗舰版|专业版|高配版|低配版|豪华版|尊享版|至尊版)",
                    r"(?:^|[\s，,。；;（(])(2023款|2024款|2025款|新款|老款|升级版|经典版|国际版|国行版|美版|日版|韩版|欧版)(?:$|[\s，,。；;)）])",
                ])
            ],
            "dimensions": [
                AttributePattern("dimensions", [
                    r"(?:尺寸|长宽高|体积)[：:]\s*([^\s，,。；;]+)",
                    r"(\d+(?:\.\d+)?\s*(?:cm|毫米|米|英寸)\s*[xX×*]\s*\d+(?:\.\d+)?\s*(?:cm|毫米|米|英寸)\s*[xX×*]\s*\d+(?:\.\d+)?\s*(?:cm|毫米|米|英寸))",
                ])
            ],
            "cpu": [
                AttributePattern("cpu", [
                    r"(?:CPU|处理器|芯片|处理器型号)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(骁龙|天玑|麒麟|苹果A|Intel|AMD|M1|M2|M3|M4|酷睿|i3|i5|i7|i9|锐龙|R3|R5|R7|R9|高通|联发科|华为海思)([^\s，,。；;)]*?)(?:$|[\s，,。；;)）])",
                ])
            ],
            "screen_size": [
                AttributePattern("screen_size", [
                    r"(?:屏幕尺寸|屏幕大小|显示屏)[：:]\s*([^\s，,。；;]+)",
                    r"(\d+(?:\.\d+)?)\s*(?:英寸|吋|寸)\s*(?:屏幕|显示屏)?",
                ])
            ],
            "battery": [
                AttributePattern("battery", [
                    r"(?:电池容量|电池)[：:]\s*([^\s，,。；;]+)",
                    r"(\d+(?:\.\d+)?)\s*(?:mAh|毫安时|Wh|瓦时)\b",
                ])
            ],
            "camera": [
                AttributePattern("camera", [
                    r"(?:摄像头|相机|像素|镜头)[：:]\s*([^\s，,。；;]+)",
                    r"(\d+(?:\.\d+)?)\s*(?:万|W|百万|M)?\s*(?:像素|镜头|主摄)\b",
                ])
            ],
            "network": [
                AttributePattern("network", [
                    r"(?:网络|网络类型|支持网络)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(5G|4G|3G|2G|全网通|移动|联通|电信|双卡双待|单卡)(?:$|[\s，,。；;)）])",
                ])
            ],
            "origin": [
                AttributePattern("origin", [
                    r"(?:产地|来源|进口|国产)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(进口|国产|原装|行货|水货|港版|台版)(?:$|[\s，,。；;)）])",
                ])
            ],
            "gender": [
                AttributePattern("gender", [
                    r"(?:适用人群|适用性别|适合)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(男款|女款|中性|男士|女士|情侣款|儿童|成人|中老年)(?:$|[\s，,。；;)）])",
                ])
            ],
            "season": [
                AttributePattern("season", [
                    r"(?:适用季节|季节)[：:]\s*([^\s，,。；;]+)",
                    r"(?:^|[\s，,。；;（(])(春季|夏季|秋季|冬季|春夏|秋冬|四季通用|春秋)(?:$|[\s，,。；;)）])",
                ])
            ],
        }

    def _init_unit_normalizers(self):
        self.unit_normalizers = {
            "weight": {
                "kg": 1.0, "千克": 1.0, "公斤": 1.0,
                "g": 0.001, "克": 0.001,
                "mg": 0.000001, "毫克": 0.000001,
                "lb": 0.453592, "磅": 0.453592,
            },
            "capacity_digital": {
                "TB": 1024.0, "T": 1024.0,
                "GB": 1.0, "G": 1.0,
                "MB": 1/1024, "M": 1/1024,
            },
            "capacity_volume": {
                "L": 1.0, "升": 1.0, "公升": 1.0,
                "ml": 0.001, "毫升": 0.001,
            },
            "length": {
                "m": 1.0, "米": 1.0,
                "cm": 0.01, "厘米": 0.01, "公分": 0.01,
                "mm": 0.001, "毫米": 0.001,
                "英寸": 0.0254, "inch": 0.0254, "in": 0.0254,
            },
            "screen": {
                "英寸": 1.0, "吋": 1.0, "寸": 1.0,
            },
            "battery": {
                "mAh": 1.0, "毫安时": 1.0,
                "Wh": 1000.0, "瓦时": 1000.0,
            },
        }

    def _init_category_hierarchy(self):
        self.category_keywords = {
            "手机数码": ["手机", "数码", "平板", "笔记本", "电脑", "相机", "智能手表", "耳机", "音响"],
            "家用电器": ["电视", "冰箱", "洗衣机", "空调", "热水器", "油烟机", "燃气灶", "电饭煲", "微波炉", "电磁炉"],
            "服装鞋帽": ["衣服", "服装", "鞋子", "帽子", "袜子", "T恤", "衬衫", "外套", "裤子", "裙子", "运动鞋", "皮鞋", "靴子"],
            "美妆个护": ["化妆品", "护肤品", "口红", "面膜", "香水", "洗发水", "沐浴露", "牙膏", "剃须刀", "美容仪"],
            "食品生鲜": ["食品", "零食", "饮料", "牛奶", "水果", "蔬菜", "肉类", "海鲜", "粮油", "干货"],
            "家居家装": ["家具", "家纺", "灯具", "装修", "建材", "五金", "厨具", "餐具", "床上用品", "收纳"],
            "母婴用品": ["奶粉", "纸尿裤", "婴儿车", "童装", "玩具", "奶瓶", "辅食", "早教"],
            "运动户外": ["运动", "户外", "健身", "跑步", "篮球", "足球", "帐篷", "登山", "骑行", "垂钓"],
            "图书音像": ["图书", "书籍", "小说", "教育", "考试", "音乐", "电影", "游戏"],
            "汽车用品": ["汽车", "车载", "机油", "轮胎", "坐垫", "香水", "导航", "行车记录仪"],
        }

    def extract(self, raw_text: str, product_name: Optional[str] = None, 
                description: Optional[str] = None,
                category: Optional[str] = None) -> AttributeExtractionResult:
        
        combined_text = " ".join(filter(None, [product_name, raw_text, description]))
        
        extracted: Dict[str, List[ExtractedAttribute]] = {}
        total_confidence = 0.0
        extraction_count = 0
        
        for attr_name, patterns in self.patterns.items():
            if self._is_attribute_relevant(attr_name, category):
                for pattern in patterns:
                    matches = self._find_matches(combined_text, pattern)
                    if matches:
                        if attr_name not in extracted:
                            extracted[attr_name] = []
                        extracted[attr_name].extend(matches)
                        total_confidence += sum(m.confidence for m in matches)
                        extraction_count += len(matches)
        
        normalized = self._normalize_attributes(extracted, category)
        category_prediction, category_conf = self._predict_category(combined_text, category)
        
        normalized["predicted_category"] = category_prediction
        normalized["category_confidence"] = category_conf
        
        quality_score = self._calculate_quality_score(
            extracted, normalized, extraction_count, total_confidence
        )
        
        return AttributeExtractionResult(
            raw_text=raw_text,
            extracted_attributes={k: [{"value": v.value, "confidence": v.confidence, "source": v.source} 
                                      for v in vals] 
                                  for k, vals in extracted.items()},
            normalized_spec=normalized,
            quality_score=quality_score,
            extraction_method="rule_based_regex"
        )

    def _is_attribute_relevant(self, attr_name: str, category: Optional[str]) -> bool:
        if not category:
            return True
        
        irrelevant_for_category = {
            "服装鞋帽": ["cpu", "screen_size", "battery", "camera", "network", "capacity"],
            "手机数码": ["material", "season", "gender"],
            "食品生鲜": ["cpu", "screen_size", "battery", "camera", "network"],
        }
        
        for cat, irrelevant in irrelevant_for_category.items():
            if cat in category and attr_name in irrelevant:
                return False
        return True

    def _find_matches(self, text: str, pattern: AttributePattern) -> List[ExtractedAttribute]:
        results = []
        for regex in pattern.patterns:
            for match in regex.finditer(text):
                if match.groups():
                    value = match.group(1).strip()
                    confidence = self._calculate_confidence(value, pattern.key)
                    results.append(ExtractedAttribute(
                        key=pattern.key,
                        value=value,
                        confidence=confidence,
                        source=f"regex:{regex.pattern[:50]}"
                    ))
        return results

    def _calculate_confidence(self, value: str, attr_name: str) -> float:
        if not value or len(value) < 1:
            return 0.0
        
        confidence = 0.5
        
        if attr_name in ["color", "gender", "season", "network", "origin"]:
            known_values = self._get_known_values(attr_name)
            if any(v in value for v in known_values):
                confidence += 0.3
        
        if re.search(r"\d", value) and attr_name in ["size", "capacity", "weight", "dimensions", 
                                                       "screen_size", "battery", "camera"]:
            confidence += 0.2
        
        if re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", value):
            confidence += 0.1
        
        if len(value) <= 20:
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _get_known_values(self, attr_name: str) -> List[str]:
        known = {
            "color": ["黑", "白", "灰", "红", "橙", "黄", "绿", "青", "蓝", "紫", "粉", "金", "银"],
            "gender": ["男", "女", "中性", "男士", "女士"],
            "season": ["春", "夏", "秋", "冬"],
            "network": ["5G", "4G", "3G", "全网通"],
            "origin": ["进口", "国产"],
            "material": ["棉", "涤纶", "羊毛", "真丝", "亚麻", "皮革", "不锈钢", "塑料"],
        }
        return known.get(attr_name, [])

    def _normalize_attributes(self, extracted: Dict[str, List[ExtractedAttribute]], 
                              category: Optional[str]) -> Dict[str, Any]:
        normalized = {}
        
        for attr_name, attributes in extracted.items():
            if not attributes:
                continue
            
            best_attr = max(attributes, key=lambda a: a.confidence)
            
            if best_attr.confidence < 0.3:
                continue
            
            normalized[attr_name] = {
                "value": best_attr.value,
                "confidence": best_attr.confidence,
                "normalized_value": self._normalize_value(attr_name, best_attr.value),
                "unit": self._extract_unit(attr_name, best_attr.value),
                "all_values": [{"value": a.value, "confidence": a.confidence} for a in attributes],
            }
        
        if "color" in normalized:
            normalized["color_family"] = self._get_color_family(normalized["color"]["value"])
        
        return normalized

    def _normalize_value(self, attr_name: str, value: str) -> Optional[float]:
        number_match = re.search(r"(\d+(?:\.\d+)?)", value)
        if not number_match:
            return None
        
        number = float(number_match.group(1))
        unit_match = re.search(r"(GB|G|MB|M|TB|T|kg|克|g|ml|L|升|cm|毫米|米|英寸|mAh|Wh)", value, re.IGNORECASE)
        
        if not unit_match:
            return number
        
        unit = unit_match.group(0)
        
        normalizers = {
            "capacity": self.unit_normalizers["capacity_digital"],
            "weight": self.unit_normalizers["weight"],
            "screen_size": self.unit_normalizers["screen"],
            "battery": self.unit_normalizers["battery"],
            "size": self.unit_normalizers["length"],
            "dimensions": self.unit_normalizers["length"],
        }
        
        normalizer_map = normalizers.get(attr_name, {})
        
        for unit_key, multiplier in normalizer_map.items():
            if unit_key.lower() == unit.lower():
                return number * multiplier
        
        return number

    def _extract_unit(self, attr_name: str, value: str) -> Optional[str]:
        unit_match = re.search(r"(GB|G|MB|M|TB|T|kg|克|g|ml|L|升|cm|毫米|米|英寸|mAh|Wh|万像素)", value, re.IGNORECASE)
        if unit_match:
            return unit_match.group(0)
        return None

    def _get_color_family(self, color: str) -> Optional[str]:
        color_families = {
            "黑": ["黑", "墨黑", "炭黑", "哑光黑", "亮黑", "深空灰"],
            "白": ["白", "米白", "奶白", "象牙白", "珍珠白"],
            "灰": ["灰", "银灰", "烟灰", "浅灰", "深灰"],
            "红": ["红", "酒红", "枣红", "玫红", "正红", "中国红"],
            "蓝": ["蓝", "深蓝", "浅蓝", "天蓝", "湖蓝", "宝蓝", "藏蓝"],
            "绿": ["绿", "墨绿", "军绿", "浅绿", "深绿", "薄荷绿"],
            "黄": ["黄", "金黄", "柠檬黄", "土黄", "鹅黄"],
            "紫": ["紫", "深紫", "浅紫", "薰衣草紫"],
            "粉": ["粉", "樱花粉", "浅粉", "深粉", "玫粉"],
            "金": ["金", "黄金", "玫瑰金", "香槟金", "土豪金"],
            "银": ["银", "银色", "亮银"],
            "橙": ["橙", "橘色", "橙色", "橘红"],
            "棕": ["棕", "咖", "驼", "深棕", "浅棕"],
        }
        
        for family, colors in color_families.items():
            if any(c in color for c in colors):
                return family
        return None

    def _predict_category(self, text: str, explicit_category: Optional[str]) -> Tuple[str, float]:
        if explicit_category:
            return explicit_category, 1.0
        
        text_lower = text.lower()
        best_category = "其他"
        best_score = 0.0
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_category = category
        
        confidence = min(best_score / max(len(self.category_keywords.get(best_category, [])), 1), 1.0)
        
        return best_category, confidence

    def _calculate_quality_score(self, extracted: Dict[str, List[ExtractedAttribute]],
                                  normalized: Dict[str, Any],
                                  extraction_count: int,
                                  total_confidence: float) -> float:
        if extraction_count == 0:
            return 0.0
        
        avg_confidence = total_confidence / extraction_count
        attribute_coverage = len(extracted) / len(self.patterns)
        high_confidence_ratio = sum(
            1 for attrs in extracted.values() 
            for a in attrs if a.confidence >= 0.7
        ) / max(extraction_count, 1)
        
        score = (
            avg_confidence * 0.4 +
            attribute_coverage * 0.3 +
            high_confidence_ratio * 0.3
        )
        
        return round(score, 3)

    def extract_batch(self, items: List[Dict[str, Any]]) -> List[AttributeExtractionResult]:
        results = []
        for item in items:
            result = self.extract(
                raw_text=item.get("spec_text", ""),
                product_name=item.get("name"),
                description=item.get("description"),
                category=item.get("category")
            )
            results.append(result)
        return results


class SpecNormalizer:
    def __init__(self):
        self.extractor = AttributeExtractor()
        self._init_spec_aliases()

    def _init_spec_aliases(self):
        self.spec_aliases = {
            "颜色": "color",
            "颜色分类": "color",
            "色系": "color",
            "尺码": "size",
            "尺寸": "size",
            "大小": "size",
            "内存容量": "capacity",
            "存储容量": "capacity",
            "机身内存": "capacity",
            "运行内存": "capacity",
            "存储": "capacity",
            "重量": "weight",
            "毛重": "weight",
            "净重": "weight",
            "材质": "material",
            "面料": "material",
            "材料": "material",
            "品牌": "brand",
            "牌子": "brand",
            "型号": "model",
            "款号": "model",
            "规格": "model",
            "版本": "version",
            "款型": "version",
            "处理器": "cpu",
            "CPU": "cpu",
            "芯片": "cpu",
            "屏幕尺寸": "screen_size",
            "显示屏": "screen_size",
            "电池容量": "battery",
            "电池": "battery",
            "摄像头像素": "camera",
            "相机": "camera",
            "像素": "camera",
            "网络类型": "network",
            "支持网络": "network",
            "产地": "origin",
            "适用人群": "gender",
            "适用性别": "gender",
            "适用季节": "season",
            "季节": "season",
        }

    def normalize_spec_key(self, spec_key: str) -> Optional[str]:
        spec_key_clean = spec_key.strip().lower()
        return self.spec_aliases.get(spec_key, self.spec_aliases.get(spec_key_clean))

    def normalize_product_specs(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        raw_specs = product_data.get("specs", {})
        normalized = {}
        
        for key, value in raw_specs.items():
            norm_key = self.normalize_spec_key(key)
            if norm_key and value:
                if norm_key not in normalized:
                    normalized[norm_key] = []
                normalized[norm_key].append({
                    "original_key": key,
                    "value": str(value)
                })
        
        extraction_result = self.extractor.extract(
            raw_text=product_data.get("spec_text", ""),
            product_name=product_data.get("name"),
            description=product_data.get("description"),
            category=product_data.get("category")
        )
        
        result = {
            "normalized_specs": normalized,
            "extracted_attributes": extraction_result.extracted_attributes,
            "predicted_category": extraction_result.normalized_spec.get("predicted_category"),
            "category_confidence": extraction_result.normalized_spec.get("category_confidence"),
            "quality_score": extraction_result.quality_score,
        }
        
        return result

    def merge_specs_from_sources(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        merged = {}
        confidences = {}
        
        for source in sources:
            normalized = self.normalize_product_specs(source)
            
            for spec_key, spec_values in normalized["normalized_specs"].items():
                if spec_key not in merged:
                    merged[spec_key] = []
                    confidences[spec_key] = 0.0
                
                for sv in spec_values:
                    exists = any(m["value"] == sv["value"] for m in merged[spec_key])
                    if not exists:
                        merged[spec_key].append(sv)
                
                confidences[spec_key] = max(confidences[spec_key], normalized["quality_score"])
        
        return {
            "merged_specs": merged,
            "source_count": len(sources),
            "spec_confidences": confidences,
            "overall_confidence": sum(confidences.values()) / max(len(confidences), 1)
        }
