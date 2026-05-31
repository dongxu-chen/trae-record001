import pandas as pd
import numpy as np
import re
import jieba
import os
import joblib
from typing import Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.decomposition import TruncatedSVD
from sklearn.decomposition import PCA

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

JOB_LEVEL_MAP = {
    "实习生": 1, "助理": 2, "专员": 3, "工程师": 4,
    "高级工程师": 5, "资深工程师": 6, "主管": 6,
    "经理": 7, "高级经理": 8, "总监": 9, "专家": 8
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


class BERTEncoder:
    def __init__(self, model_name: str = "paraphrase-MiniLM-L6-v2", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.output_dim = 384
        self._initialized = False
    
    def _initialize(self):
        if self._initialized:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self._initialized = True
            print(f"✓ BERT模型加载成功: {self.model_name} (输出维度: {self.output_dim})")
        except Exception as e:
            print(f"⚠️  BERT模型加载失败，使用模拟编码: {e}")
            self._initialized = False
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        self._initialize()
        
        if self._initialized and self.model is not None:
            embeddings = self.model.encode(
                texts, 
                batch_size=batch_size, 
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return embeddings
        else:
            return self._simulate_bert_encoding(texts)
    
    def _simulate_bert_encoding(self, texts: List[str]) -> np.ndarray:
        np.random.seed(42)
        n = len(texts)
        base_embeddings = np.random.randn(n, self.output_dim) * 0.1
        
        for i, text in enumerate(texts):
            text_lower = text.lower()
            
            for j, kw in enumerate(TECH_KEYWORDS[:self.output_dim]):
                if kw.lower() in text_lower:
                    base_embeddings[i, j % self.output_dim] += 0.3
            
            for j, kw in enumerate(HIGH_SALARY_KEYWORDS[:self.output_dim]):
                if kw in text:
                    base_embeddings[i, (j + 10) % self.output_dim] += 0.2
        
        return base_embeddings


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


def get_job_level(title: str) -> int:
    for level_name, level_value in sorted(JOB_LEVEL_MAP.items(), key=lambda x: -x[1]):
        if level_name in title:
            return level_value
    return 4


def tokenize_chinese(text: str) -> List[str]:
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
    words = jieba.lcut(text)
    words = [w for w in words if w.strip() and w not in STOP_WORDS and len(w) > 1]
    return words


class FeatureEngineerV2:
    def __init__(self, save_dir: str = "models", use_bert: bool = True):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        self.use_bert = use_bert
        self.bert_encoder = BERTEncoder() if use_bert else None
        
        self.title_tfidf = None
        self.desc_tfidf = None
        self.title_svd = None
        self.desc_svd = None
        self.location_encoder = None
        self.pca = None
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
        
        job_level = df["岗位标题"].apply(get_job_level).values.reshape(-1, 1)
        features_list.append(job_level)
        self.feature_names.append("岗位层级")
        
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
        
        level_edu_interaction = (df["岗位标题"].apply(get_job_level) * df["学历要求"].map(EDUCATION_MAP)).values.reshape(-1, 1)
        features_list.append(level_edu_interaction)
        self.feature_names.append("层级_学历_交互")
        
        if self.use_bert:
            print("正在进行BERT语义编码（岗位描述）...")
            desc_bert = self.bert_encoder.encode(df["岗位描述"].tolist())
            features_list.append(desc_bert)
            self.feature_names.extend([f"desc_bert_{i}" for i in range(384)])
            
            print("正在进行BERT语义编码（岗位标题）...")
            title_bert = self.bert_encoder.encode(df["岗位标题"].tolist())
            features_list.append(title_bert)
            self.feature_names.extend([f"title_bert_{i}" for i in range(384)])
        
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
        
        self.desc_svd = TruncatedSVD(n_components=15, random_state=42)
        desc_svd = self.desc_svd.fit_transform(desc_tfidf_mat)
        features_list.append(desc_svd)
        self.feature_names.extend([f"描述_SVD_{i}" for i in range(15)])
        
        X = np.hstack(features_list)
        
        if X.shape[1] > 500:
            print(f"特征维度较高 ({X.shape[1]})，正在进行PCA降维...")
            self.pca = PCA(n_components=min(X.shape[1] - 10, 500), random_state=42)
            X = self.pca.fit_transform(X)
            print(f"降维后维度: {X.shape[1]}")
            self.feature_names = [f"pca_{i}" for i in range(X.shape[1])]
        
        self.save()
        
        return X, self.feature_names
    
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        features_list = []
        
        title_features = df["岗位标题"].apply(extract_title_features).apply(pd.Series)
        features_list.append(title_features.values)
        
        desc_features = df["岗位描述"].apply(extract_desc_features).apply(pd.Series)
        features_list.append(desc_features.values)
        
        job_level = df["岗位标题"].apply(get_job_level).values.reshape(-1, 1)
        features_list.append(job_level)
        
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
        
        level_edu_interaction = (df["岗位标题"].apply(get_job_level) * df["学历要求"].map(EDUCATION_MAP)).values.reshape(-1, 1)
        features_list.append(level_edu_interaction)
        
        if self.use_bert:
            desc_bert = self.bert_encoder.encode(df["岗位描述"].tolist())
            features_list.append(desc_bert)
            
            title_bert = self.bert_encoder.encode(df["岗位标题"].tolist())
            features_list.append(title_bert)
        
        title_tfidf_mat = self.title_tfidf.transform(df["岗位标题"])
        title_svd = self.title_svd.transform(title_tfidf_mat)
        features_list.append(title_svd)
        
        desc_tfidf_mat = self.desc_tfidf.transform(df["岗位描述"])
        desc_svd = self.desc_svd.transform(desc_tfidf_mat)
        features_list.append(desc_svd)
        
        X = np.hstack(features_list)
        
        if self.pca is not None:
            X = self.pca.transform(X)
        
        return X
    
    def save(self):
        joblib.dump(self.title_tfidf, os.path.join(self.save_dir, "title_tfidf_v2.pkl"))
        joblib.dump(self.desc_tfidf, os.path.join(self.save_dir, "desc_tfidf_v2.pkl"))
        joblib.dump(self.title_svd, os.path.join(self.save_dir, "title_svd_v2.pkl"))
        joblib.dump(self.desc_svd, os.path.join(self.save_dir, "desc_svd_v2.pkl"))
        joblib.dump(self.location_encoder, os.path.join(self.save_dir, "location_encoder_v2.pkl"))
        joblib.dump(self.feature_names, os.path.join(self.save_dir, "feature_names_v2.pkl"))
        if self.pca is not None:
            joblib.dump(self.pca, os.path.join(self.save_dir, "pca_v2.pkl"))
    
    def load(self):
        self.title_tfidf = joblib.load(os.path.join(self.save_dir, "title_tfidf_v2.pkl"))
        self.desc_tfidf = joblib.load(os.path.join(self.save_dir, "desc_tfidf_v2.pkl"))
        self.title_svd = joblib.load(os.path.join(self.save_dir, "title_svd_v2.pkl"))
        self.desc_svd = joblib.load(os.path.join(self.save_dir, "desc_svd_v2.pkl"))
        self.location_encoder = joblib.load(os.path.join(self.save_dir, "location_encoder_v2.pkl"))
        self.feature_names = joblib.load(os.path.join(self.save_dir, "feature_names_v2.pkl"))
        pca_path = os.path.join(self.save_dir, "pca_v2.pkl")
        if os.path.exists(pca_path):
            self.pca = joblib.load(pca_path)
        else:
            self.pca = None


if __name__ == "__main__":
    df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig").head(100)
    print(f"加载数据: {len(df)} 条")
    
    fe = FeatureEngineerV2(use_bert=True)
    X, feature_names = fe.fit_transform(df)
    
    print(f"\n特征矩阵形状: {X.shape}")
    print(f"特征数量: {len(feature_names)}")
    print(f"\nBERT编码维度: 384 (岗位描述) + 384 (岗位标题) = 768维")
