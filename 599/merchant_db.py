import json
import os
from fuzzywuzzy import fuzz, process
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from collections import defaultdict

CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "医疗", "其他"]

CATEGORY_HIERARCHY = {
    "餐饮": {
        "parent": None,
        "children": ["快餐", "正餐", "咖啡茶饮", "外卖", "甜品"],
        "keywords": ["餐厅", "饭店", "酒楼", "面馆", "火锅", "烧烤"]
    },
    "快餐": {
        "parent": "餐饮",
        "children": [],
        "keywords": ["肯德基", "麦当劳", "必胜客", "德克士", "汉堡王", "真功夫", "和合谷"]
    },
    "正餐": {
        "parent": "餐饮",
        "children": [],
        "keywords": ["海底捞", "全聚德", "外婆家", "西贝", "眉州东坡", "小肥羊"]
    },
    "咖啡茶饮": {
        "parent": "餐饮",
        "children": [],
        "keywords": ["星巴克", "瑞幸咖啡", "喜茶", "奈雪", "COSTA", "太平洋咖啡"]
    },
    "交通": {
        "parent": None,
        "children": ["网约车", "公共交通", "加油停车", "航空铁路"],
        "keywords": ["出行", "打车", "地铁", "公交", "加油", "航空", "铁路"]
    },
    "网约车": {
        "parent": "交通",
        "children": [],
        "keywords": ["滴滴", "首汽约车", "神州专车", "曹操出行", "T3出行", "高德打车"]
    },
    "公共交通": {
        "parent": "交通",
        "children": [],
        "keywords": ["地铁", "公交", "轨道交通", "一卡通", "交通卡"]
    },
    "购物": {
        "parent": None,
        "children": ["电商", "超市", "服饰", "数码家电"],
        "keywords": ["购物", "商城", "超市", "电商", "网购"]
    },
    "电商": {
        "parent": "购物",
        "children": [],
        "keywords": ["淘宝", "天猫", "京东", "拼多多", "唯品会", "苏宁易购"]
    },
    "超市": {
        "parent": "购物",
        "children": [],
        "keywords": ["沃尔玛", "家乐福", "永辉超市", "物美", "盒马鲜生", "大润发"]
    },
    "娱乐": {
        "parent": None,
        "children": ["影视", "游戏", "健身", "演出"],
        "keywords": ["电影", "游戏", "健身", "娱乐", "KTV"]
    },
    "影视": {
        "parent": "娱乐",
        "children": [],
        "keywords": ["电影院", "影城", "万达电影", "横店影视", "爱奇艺", "腾讯视频"]
    },
    "医疗": {
        "parent": None,
        "children": ["医院", "药店", "体检"],
        "keywords": ["医院", "诊所", "药房", "体检", "医疗"]
    },
    "医院": {
        "parent": "医疗",
        "children": [],
        "keywords": ["医院", "诊所", "卫生院", "门诊部", "协和医院", "301医院"]
    },
    "药店": {
        "parent": "医疗",
        "children": [],
        "keywords": ["药房", "药店", "同仁堂", "国药", "大药房"]
    }
}

@dataclass
class MerchantInfo:
    name: str
    category: str
    sub_category: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    brand: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def _create_default_merchants() -> List[MerchantInfo]:
    merchants = []
    
    default_data = {
        "餐饮": [
            ("肯德基", "快餐", "肯德基"),
            ("麦当劳", "快餐", "麦当劳"),
            ("必胜客", "快餐", "必胜客"),
            ("星巴克", "咖啡茶饮", "星巴克"),
            ("海底捞", "正餐", "海底捞"),
            ("呷哺呷哺", "正餐", "呷哺呷哺"),
            ("全聚德", "正餐", "全聚德"),
            ("外婆家", "正餐", "外婆家"),
            ("西贝", "正餐", "西贝"),
            ("真功夫", "快餐", "真功夫"),
            ("德克士", "快餐", "德克士"),
            ("汉堡王", "快餐", "汉堡王"),
            ("喜茶", "咖啡茶饮", "喜茶"),
            ("奈雪", "咖啡茶饮", "奈雪"),
            ("瑞幸咖啡", "咖啡茶饮", "瑞幸咖啡"),
            ("COSTA", "咖啡茶饮", "COSTA"),
            ("眉州东坡", "正餐", "眉州东坡"),
            ("小肥羊", "正餐", "小肥羊"),
            ("大龙燚", "正餐", "大龙燚"),
            ("小龙坎", "正餐", "小龙坎"),
            ("杨国福", "正餐", "杨国福"),
            ("张亮麻辣烫", "正餐", "张亮麻辣烫"),
            ("和合谷", "快餐", "和合谷"),
            ("永和大王", "快餐", "永和大王"),
            ("庆丰包子", "快餐", "庆丰包子"),
        ],
        "交通": [
            ("滴滴出行", "网约车", "滴滴"),
            ("滴滴快车", "网约车", "滴滴"),
            ("滴滴专车", "网约车", "滴滴"),
            ("首汽约车", "网约车", "首汽约车"),
            ("神州专车", "网约车", "神州专车"),
            ("曹操出行", "网约车", "曹操出行"),
            ("T3出行", "网约车", "T3出行"),
            ("高德打车", "网约车", "高德"),
            ("美团打车", "网约车", "美团"),
            ("地铁", "公共交通", None),
            ("公交", "公共交通", None),
            ("轨道交通", "公共交通", None),
            ("中石化", "加油停车", "中石化"),
            ("中石油", "加油停车", "中石油"),
            ("壳牌", "加油停车", "壳牌"),
            ("中国国际航空", "航空铁路", "国航"),
            ("中国东方航空", "航空铁路", "东航"),
            ("中国南方航空", "航空铁路", "南航"),
            ("铁路", "航空铁路", None),
            ("高铁", "航空铁路", None),
            ("12306", "航空铁路", None),
            ("携程", "航空铁路", "携程"),
            ("去哪儿", "航空铁路", "去哪儿"),
        ],
        "购物": [
            ("淘宝", "电商", "淘宝"),
            ("天猫", "电商", "天猫"),
            ("京东", "电商", "京东"),
            ("拼多多", "电商", "拼多多"),
            ("苏宁易购", "电商", "苏宁"),
            ("唯品会", "电商", "唯品会"),
            ("网易严选", "电商", "网易严选"),
            ("小米商城", "电商", "小米"),
            ("华为商城", "电商", "华为"),
            ("沃尔玛", "超市", "沃尔玛"),
            ("家乐福", "超市", "家乐福"),
            ("永辉超市", "超市", "永辉"),
            ("物美", "超市", "物美"),
            ("盒马鲜生", "超市", "盒马"),
            ("大润发", "超市", "大润发"),
            ("华润万家", "超市", "华润万家"),
            ("优衣库", "服饰", "优衣库"),
            ("ZARA", "服饰", "ZARA"),
            ("H&M", "服饰", "H&M"),
            ("耐克", "服饰", "耐克"),
            ("阿迪达斯", "服饰", "阿迪达斯"),
            ("李宁", "服饰", "李宁"),
            ("安踏", "服饰", "安踏"),
        ],
        "娱乐": [
            ("万达电影", "影视", "万达"),
            ("横店影视", "影视", "横店"),
            ("金逸影城", "影视", "金逸"),
            ("猫眼电影", "影视", "猫眼"),
            ("淘票票", "影视", "淘票票"),
            ("爱奇艺", "影视", "爱奇艺"),
            ("腾讯视频", "影视", "腾讯视频"),
            ("优酷", "影视", "优酷"),
            ("芒果TV", "影视", "芒果TV"),
            ("哔哩哔哩", "影视", "B站"),
            ("QQ音乐", "影视", "QQ音乐"),
            ("网易云音乐", "影视", "网易云"),
            ("KTV", None, None),
            ("唱吧", None, "唱吧"),
            ("健身房", "健身", None),
            ("健身", "健身", None),
            ("瑜伽", "健身", None),
            ("迪士尼", None, "迪士尼"),
            ("环球影城", None, "环球影城"),
            ("欢乐谷", None, "欢乐谷"),
        ],
        "医疗": [
            ("协和医院", "医院", "协和"),
            ("301医院", "医院", "301"),
            ("华西医院", "医院", "华西"),
            ("湘雅医院", "医院", "湘雅"),
            ("瑞金医院", "医院", "瑞金"),
            ("同济医院", "医院", "同济"),
            ("华山医院", "医院", "华山"),
            ("医院", "医院", None),
            ("诊所", "医院", None),
            ("卫生院", "医院", None),
            ("门诊部", "医院", None),
            ("同仁堂", "药店", "同仁堂"),
            ("药房", "药店", None),
            ("药店", "药店", None),
            ("大药房", "药店", None),
            ("体检中心", "体检", None),
            ("体检", "体检", None),
            ("平安好医生", None, "平安好医生"),
            ("阿里健康", None, "阿里健康"),
            ("京东健康", None, "京东健康"),
            ("微医", None, "微医"),
            ("春雨医生", None, "春雨医生"),
            ("丁香医生", None, "丁香医生"),
        ]
    }
    
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆"]
    
    for category, merchant_list in default_data.items():
        for name, sub_category, brand in merchant_list:
            merchants.append(MerchantInfo(
                name=name,
                category=category,
                sub_category=sub_category,
                brand=brand,
                keywords=[name]
            ))
            
            for city in cities[:3]:
                merchants.append(MerchantInfo(
                    name=f"{name}({city}店)",
                    category=category,
                    sub_category=sub_category,
                    city=city,
                    brand=brand or name,
                    keywords=[name, city]
                ))
    
    return merchants

class MerchantDatabase:
    def __init__(self, db_path: str = "data/merchants.json"):
        self.db_path = db_path
        self.merchants: List[MerchantInfo] = []
        self.merchant_index: Dict[str, List[MerchantInfo]] = defaultdict(list)
        self._load_database()
    
    def _load_database(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.merchants = [MerchantInfo(**m) for m in data]
            except Exception:
                self.merchants = _create_default_merchants()
                self._save_database()
        else:
            self.merchants = _create_default_merchants()
            self._save_database()
        
        self._build_index()
    
    def _build_index(self):
        self.merchant_index = defaultdict(list)
        for merchant in self.merchants:
            self.merchant_index[merchant.name.lower()].append(merchant)
            if merchant.brand:
                self.merchant_index[merchant.brand.lower()].append(merchant)
    
    def _save_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        data = [m.to_dict() for m in self.merchants]
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_merchant(self, merchant_info: MerchantInfo) -> bool:
        for m in self.merchants:
            if m.name == merchant_info.name and m.city == merchant_info.city:
                return False
        self.merchants.append(merchant_info)
        self._build_index()
        self._save_database()
        return True
    
    def remove_merchant(self, merchant_name: str, city: Optional[str] = None) -> bool:
        original_len = len(self.merchants)
        if city:
            self.merchants = [
                m for m in self.merchants 
                if not (m.name == merchant_name and m.city == city)
            ]
        else:
            self.merchants = [m for m in self.merchants if m.name != merchant_name]
        
        if len(self.merchants) < original_len:
            self._build_index()
            self._save_database()
            return True
        return False
    
    def _get_parent_category(self, sub_category: str) -> Optional[str]:
        for cat, info in CATEGORY_HIERARCHY.items():
            if info["children"] and sub_category in info["children"]:
                return cat
        return None
    
    def fuzzy_match(
        self, 
        merchant_name: str, 
        location: Optional[str] = None,
        threshold: int = 70
    ) -> Tuple[Optional[str], int, Optional[MerchantInfo]]:
        best_match = None
        best_score = 0
        best_merchant = None
        
        all_merchant_names = [m.name for m in self.merchants]
        
        match = process.extractOne(
            merchant_name,
            all_merchant_names,
            scorer=fuzz.partial_ratio,
            score_cutoff=threshold
        )
        
        if match:
            matched_name, score = match[0], match[1]
            candidates = [m for m in self.merchants if m.name == matched_name]
            
            if location and len(candidates) > 1:
                for candidate in candidates:
                    if candidate.city and candidate.city in location:
                        best_merchant = candidate
                        best_score = score + 10
                        best_match = candidate.category
                        break
            
            if not best_merchant and candidates:
                best_merchant = candidates[0]
                best_score = score
                best_match = candidates[0].category
        
        return best_match, best_score, best_merchant
    
    def exact_match(
        self, 
        merchant_name: str, 
        location: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[MerchantInfo]]:
        candidates = self.merchant_index.get(merchant_name.lower(), [])
        
        if location and len(candidates) > 1:
            for candidate in candidates:
                if candidate.city and candidate.city in location:
                    return candidate.category, candidate
        
        if candidates:
            return candidates[0].category, candidates[0]
        
        return None, None
    
    def parent_category_fallback(self, merchant_name: str) -> Optional[str]:
        merchant_lower = merchant_name.lower()
        
        for parent_cat, info in CATEGORY_HIERARCHY.items():
            if info["parent"] is None:
                for keyword in info["keywords"]:
                    if keyword.lower() in merchant_lower:
                        return parent_cat
                
                if info["children"]:
                    for child in info["children"]:
                        child_info = CATEGORY_HIERARCHY.get(child, {})
                        for keyword in child_info.get("keywords", []):
                            if keyword.lower() in merchant_lower:
                                return parent_cat
        
        return None
    
    def cold_start_classify(self, merchant_name: str) -> Optional[str]:
        result = self.parent_category_fallback(merchant_name)
        
        if not result:
            if any(kw in merchant_name for kw in ["餐", "饭", "食", "吃", "喝", "茶", "咖啡"]):
                return "餐饮"
        
        return result
    
    def get_all_merchants(self) -> List[MerchantInfo]:
        return self.merchants
    
    def get_merchants_by_category(self, category: str) -> List[MerchantInfo]:
        return [m for m in self.merchants if m.category == category]
    
    def get_merchants_by_city(self, city: str) -> List[MerchantInfo]:
        return [m for m in self.merchants if m.city == city]
    
    def search_merchants(self, keyword: str) -> List[MerchantInfo]:
        keyword_lower = keyword.lower()
        results = []
        seen = set()
        
        for merchant in self.merchants:
            key = (merchant.name, merchant.city)
            if key in seen:
                continue
            
            if (keyword_lower in merchant.name.lower() or
                (merchant.brand and keyword_lower in merchant.brand.lower()) or
                (merchant.city and keyword_lower in merchant.city.lower())):
                results.append(merchant)
                seen.add(key)
        
        return results
    
    def get_category_hierarchy(self) -> Dict[str, Any]:
        return CATEGORY_HIERARCHY
