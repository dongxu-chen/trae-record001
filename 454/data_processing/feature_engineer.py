import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, load_feature_config, setup_logger


class FeatureEngineer:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.feature_config = load_feature_config()
        self.logger = setup_logger("FeatureEngineer", self.config)
        self.feature_stats = {}
        self.vocabularies = {}

    def normalize_numerical_features(self, df: pd.DataFrame, features: List[str], fit: bool = True) -> pd.DataFrame:
        df = df.copy()
        for feat in features:
            if feat not in df.columns:
                continue
            if fit:
                mean = df[feat].mean()
                std = df[feat].std()
                self.feature_stats[feat] = {"mean": mean, "std": std}
            else:
                mean = self.feature_stats.get(feat, {}).get("mean", 0)
                std = self.feature_stats.get(feat, {}).get("std", 1)
            df[feat] = (df[feat] - mean) / (std + 1e-8)
        return df

    def build_vocabulary(self, df: pd.DataFrame, categorical_features: List[str]) -> Dict[str, Dict]:
        vocabs = {}
        for feat in categorical_features:
            if feat not in df.columns:
                continue
            unique_vals = sorted(df[feat].unique())
            vocabs[feat] = {val: idx for idx, val in enumerate(unique_vals)}
        return vocabs

    def encode_categorical_features(self, df: pd.DataFrame, features: List[str], fit: bool = True) -> pd.DataFrame:
        df = df.copy()
        if fit:
            self.vocabularies = self.build_vocabulary(df, features)

        for feat in features:
            if feat not in df.columns or feat not in self.vocabularies:
                continue
            vocab = self.vocabularies[feat]
            df[feat] = df[feat].map(lambda x: vocab.get(x, 0))
        return df

    def create_cross_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        cross_features = self.feature_config.get("cross_features", [])

        for cross_feat in cross_features:
            name = cross_feat["name"]
            feat1, feat2 = cross_feat["features"]
            if feat1 in df.columns and feat2 in df.columns:
                df[name] = df[feat1].astype(str) + "_" + df[feat2].astype(str)
        return df

    def get_feature_names(self) -> Dict[str, List[str]]:
        feat_config = self.feature_config
        user_feats = [f["name"] for f in feat_config["user_features"]["features"]]
        ad_feats = [f["name"] for f in feat_config["ad_features"]["features"]]
        context_feats = [f["name"] for f in feat_config["context_features"]["features"]]
        cross_feats = [f["name"] for f in feat_config.get("cross_features", [])]

        numerical_features = ["user_ctr_7d", "ad_ctr_history", "ad_price",
                              "user_click_count_7d", "user_impression_count_7d",
                              "ad_click_count_7d", "ad_impression_count_7d",
                              "user_registration_days", "user_active_days_7d"]
        numerical_features = [f for f in numerical_features if f in user_feats + ad_feats]

        categorical_features = [f for f in user_feats + ad_feats + context_feats
                                if f not in numerical_features]
        categorical_features += cross_feats

        return {
            "numerical": numerical_features,
            "categorical": categorical_features,
            "all": numerical_features + categorical_features
        }

    def transform(self, df: pd.DataFrame, fit: bool = True) -> Tuple[pd.DataFrame, Dict]:
        self.logger.info(f"Transforming data with shape: {df.shape}")

        feat_names = self.get_feature_names()

        df = self.create_cross_features(df)
        df = self.normalize_numerical_features(df, feat_names["numerical"], fit=fit)
        df = self.encode_categorical_features(df, feat_names["categorical"] + [f["name"] for f in self.feature_config.get("cross_features", [])], fit=fit)

        feature_info = {
            "feature_names": feat_names,
            "vocab_sizes": {k: len(v) for k, v in self.vocabularies.items()},
            "feature_stats": self.feature_stats
        }

        self.logger.info(f"Feature transformation complete")
        return df, feature_info

    def save_artifacts(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        artifacts = {
            "feature_stats": self.feature_stats,
            "vocabularies": self.vocabularies
        }
        with open(path, "wb") as f:
            pickle.dump(artifacts, f)
        self.logger.info(f"Feature artifacts saved to {path}")

    def load_artifacts(self, path: str):
        with open(path, "rb") as f:
            artifacts = pickle.load(f)
        self.feature_stats = artifacts["feature_stats"]
        self.vocabularies = artifacts["vocabularies"]
        self.logger.info(f"Feature artifacts loaded from {path}")
