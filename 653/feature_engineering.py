import pandas as pd
import numpy as np
import re
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.decomposition import TruncatedSVD
from scipy import sparse
from typing import Dict, List, Tuple
import joblib
import os

LOCATIONS = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉",
             "西安", "南京", "苏州", "重庆", "天津"]
COMPANY_SIZES = ["少于50人", "50-150人", "150-500人", "500-1000人", "1000人以上"]
EDUCATION_LEVELS = ["大专", "本科", "硕士", "博士"]

COMPANY_SIZE_MAP = {
    "少于50人": 1,
    "50-150人": 2,
    "150-500人": 3,
    "500-1000人": 4,
    "1000人以上": 5
}

EDUCATION_MAP = {
    "大专": 1,
    "本科": 2,
    "硕士": 3,
    "博士": 4
}

LOCATION_MAP = {
    "北京": 1.3, "上海": 1.28, "深圳": 1.25, "广州": 1.1,
    "杭州": 1.15, "成都": 0.9, "武汉": 0.85, "西安": 0.82,
    "南京": 0.95, "苏州": 0.92, "重庆": 0.8, "天津": 0.88
}

HIGH_SALARY_KEYWORDS = [
    "架构", "资深", "高级", "专家", "总监", "经理", "科学家", "算法",
    "机器学习", "深度学习", "AI", "人工智能", "数据", "量化"
]

TECH_KEYWORDS = [
    "Python", "Java", "C++", "Go", "Rust", "TypeScript", "React", "Vue",
    "机器学习", "深度学习", "TensorFlow", "PyTorch", "大数据", "Spark",
    "云原生", "K8s", "Docker", "微服务", "分布式", "高并发"
]

STOP_WORDS = set([
    "的", "了", "和", "是", "就", "都", "而", "及", "与", "着",
    "或", "一个", "我们", "你们", "他们", "它们", "这个", "那个",
    "这些", "那些", "以及", "等等", "进行", "负责", "参与", "要求",
    "熟悉", "具备", "良好", "能力", "相关", "技术", "工作", "经验"
])


def extract_title_features(title: str) -> Dict[str, int]:
    features = {}
    
    features["is_senior"] = 1 if any(k in title for k in ["高级", "资深", "专家", "架构"]) else 0
    features["is_manager"] = 1 if any(k in title for k in ["经理", "总监", "主管"]) else 0
    features["is_tech"] = 1 if any(k in title for k in ["开发", "工程师", "算法", "数据", "运维", "测试"]) else 0
    features["is_data"] = 1 if any(k in title for k in ["数据", "算法", "科学"]) else 0
    
    for kw in HIGH_SALARY_KEYWORDS:
        features[f"title_has_{kw}"] = 1 if kw in title else 0
    
    return features


def extract_desc_features(desc: str) -> Dict[str, int]:
    features = {}
    desc_lower = desc.lower()
    
    tech_count = sum(1 for kw in TECH_KEYWORDS if kw.lower() in desc_lower)
    features["tech_keyword_count"] = tech_count
    
    features["has_master_kw"] = 1 if "硕士" in desc else 0
    features["has_phd_kw"] = 1 if "博士" in desc else 0
    features["has_experience_kw"] = 1 if any(k in desc for k in ["经验", "年以上", "工作经验"]) else 0
    
    desc_len = len(desc)
    features["desc_length"] = desc_len
    
    return features


def tokenize_chinese(text: str) -> List[str]:
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
    words = jieba.lcut(text)
    words = [w for w in words if w.strip() and w not in STOP_WORDS and len(w) > 1]
    return words


class FeatureEngineer:
    def __init__(self, save_dir: str = "models"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        self.title_tfidf = None
        self.desc_tfidf = None
        self.title_svd = None
        self.desc_svd = None
        self.location_encoder = None
        self.feature_names = []
        
    def fit_transform(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        features_list = []
        self.feature_names = []
        
        title_features = df["岗位标题"].apply(extract_title_features).apply(pd.Series)
        features_list.append(title_features.values)
        self.feature_names.extend(title_features.columns.tolist())
        
        desc_features = df["岗位描述"].apply(extract_desc_features).apply(pd.Series)
        features_list.append(desc_features.values)
        self.feature_names.extend(desc_features.columns.tolist())
        
        company_size_ord = df["公司规模"].map(COMPANY_SIZE_MAP).values.reshape(-1, 1)
        features_list.append(company_size_ord)
        self.feature_names.append("公司规模_序数")
        
        education_ord = df["学历要求"].map(EDUCATION_MAP).values.reshape(-1, 1)
        features_list.append(education_ord)
        self.feature_names.append("学历要求_序数")
        
        location_score = df["地区"].map(LOCATION_MAP).values.reshape(-1, 1)
        features_list.append(location_score)
        self.feature_names.append("地区_经济系数")
        
        self.location_encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        location_onehot = self.location_encoder.fit_transform(df[["地区"]])
        features_list.append(location_onehot)
        loc_cats = self.location_encoder.categories_[0]
        self.feature_names.extend([f"地区_{cat}" for cat in loc_cats])
        
        company_onehot = pd.get_dummies(df["公司规模"], prefix="公司规模")
        features_list.append(company_onehot.values)
        self.feature_names.extend(company_onehot.columns.tolist())
        
        edu_onehot = pd.get_dummies(df["学历要求"], prefix="学历要求")
        features_list.append(edu_onehot.values)
        self.feature_names.extend(edu_onehot.columns.tolist())
        
        size_edu_interaction = (df["公司规模"].map(COMPANY_SIZE_MAP) * df["学历要求"].map(EDUCATION_MAP)).values.reshape(-1, 1)
        features_list.append(size_edu_interaction)
        self.feature_names.append("规模_学历_交互")
        
        loc_size_interaction = (df["地区"].map(LOCATION_MAP) * df["公司规模"].map(COMPANY_SIZE_MAP)).values.reshape(-1, 1)
        features_list.append(loc_size_interaction)
        self.feature_names.append("地区_规模_交互")
        
        self.title_tfidf = TfidfVectorizer(
            tokenizer=tokenize_chinese,
            max_features=100,
            ngram_range=(1, 2)
        )
        title_tfidf_mat = self.title_tfidf.fit_transform(df["岗位标题"])
        
        self.title_svd = TruncatedSVD(n_components=10, random_state=42)
        title_svd = self.title_svd.fit_transform(title_tfidf_mat)
        features_list.append(title_svd)
        self.feature_names.extend([f"标题_SVD_{i}" for i in range(10)])
        
        self.desc_tfidf = TfidfVectorizer(
            tokenizer=tokenize_chinese,
            max_features=200,
            ngram_range=(1, 2)
        )
        desc_tfidf_mat = self.desc_tfidf.fit_transform(df["岗位描述"])
        
        self.desc_svd = TruncatedSVD(n_components=20, random_state=42)
        desc_svd = self.desc_svd.fit_transform(desc_tfidf_mat)
        features_list.append(desc_svd)
        self.feature_names.extend([f"描述_SVD_{i}" for i in range(20)])
        
        X = np.hstack(features_list)
        
        self.save()
        
        return X, self.feature_names
    
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        features_list = []
        
        title_features = df["岗位标题"].apply(extract_title_features).apply(pd.Series)
        features_list.append(title_features.values)
        
        desc_features = df["岗位描述"].apply(extract_desc_features).apply(pd.Series)
        features_list.append(desc_features.values)
        
        company_size_ord = df["公司规模"].map(COMPANY_SIZE_MAP).values.reshape(-1, 1)
        features_list.append(company_size_ord)
        
        education_ord = df["学历要求"].map(EDUCATION_MAP).values.reshape(-1, 1)
        features_list.append(education_ord)
        
        location_score = df["地区"].map(LOCATION_MAP).values.reshape(-1, 1)
        features_list.append(location_score)
        
        location_onehot = self.location_encoder.transform(df[["地区"]])
        features_list.append(location_onehot)
        
        company_onehot = pd.get_dummies(df["公司规模"], prefix="公司规模")
        for col in [f"公司规模_{size}" for size in COMPANY_SIZES]:
            if col not in company_onehot.columns:
                company_onehot[col] = 0
        company_onehot = company_onehot[[f"公司规模_{size}" for size in COMPANY_SIZES]]
        features_list.append(company_onehot.values)
        
        edu_onehot = pd.get_dummies(df["学历要求"], prefix="学历要求")
        for col in [f"学历要求_{edu}" for edu in EDUCATION_LEVELS]:
            if col not in edu_onehot.columns:
                edu_onehot[col] = 0
        edu_onehot = edu_onehot[[f"学历要求_{edu}" for edu in EDUCATION_LEVELS]]
        features_list.append(edu_onehot.values)
        
        size_edu_interaction = (df["公司规模"].map(COMPANY_SIZE_MAP) * df["学历要求"].map(EDUCATION_MAP)).values.reshape(-1, 1)
        features_list.append(size_edu_interaction)
        
        loc_size_interaction = (df["地区"].map(LOCATION_MAP) * df["公司规模"].map(COMPANY_SIZE_MAP)).values.reshape(-1, 1)
        features_list.append(loc_size_interaction)
        
        title_tfidf_mat = self.title_tfidf.transform(df["岗位标题"])
        title_svd = self.title_svd.transform(title_tfidf_mat)
        features_list.append(title_svd)
        
        desc_tfidf_mat = self.desc_tfidf.transform(df["岗位描述"])
        desc_svd = self.desc_svd.transform(desc_tfidf_mat)
        features_list.append(desc_svd)
        
        X = np.hstack(features_list)
        
        return X
    
    def save(self):
        joblib.dump(self.title_tfidf, os.path.join(self.save_dir, "title_tfidf.pkl"))
        joblib.dump(self.desc_tfidf, os.path.join(self.save_dir, "desc_tfidf.pkl"))
        joblib.dump(self.title_svd, os.path.join(self.save_dir, "title_svd.pkl"))
        joblib.dump(self.desc_svd, os.path.join(self.save_dir, "desc_svd.pkl"))
        joblib.dump(self.location_encoder, os.path.join(self.save_dir, "location_encoder.pkl"))
        joblib.dump(self.feature_names, os.path.join(self.save_dir, "feature_names.pkl"))
    
    def load(self):
        self.title_tfidf = joblib.load(os.path.join(self.save_dir, "title_tfidf.pkl"))
        self.desc_tfidf = joblib.load(os.path.join(self.save_dir, "desc_tfidf.pkl"))
        self.title_svd = joblib.load(os.path.join(self.save_dir, "title_svd.pkl"))
        self.desc_svd = joblib.load(os.path.join(self.save_dir, "desc_svd.pkl"))
        self.location_encoder = joblib.load(os.path.join(self.save_dir, "location_encoder.pkl"))
        self.feature_names = joblib.load(os.path.join(self.save_dir, "feature_names.pkl"))


if __name__ == "__main__":
    df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
    print(f"加载数据: {len(df)} 条")
    
    fe = FeatureEngineer()
    X, feature_names = fe.fit_transform(df)
    
    print(f"\n特征矩阵形状: {X.shape}")
    print(f"特征数量: {len(feature_names)}")
    print(f"\n前10个特征名称: {feature_names[:10]}")
    print(f"\n特征矩阵统计:")
    print(f"  均值: {X.mean():.4f}")
    print(f"  标准差: {X.std():.4f}")
    print(f"  非零比例: {(X != 0).sum() / X.size:.2%}")
