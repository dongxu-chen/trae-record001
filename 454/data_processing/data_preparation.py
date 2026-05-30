import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from sklearn.model_selection import train_test_split
from feast import FeatureStore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger
from feature_engineer import FeatureEngineer


class DataPreparation:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("DataPreparation", self.config)
        self.feature_engineer = FeatureEngineer(config_path)
        self.feast_repo_path = self.config["feature_store"]["repo_path"]

    def load_raw_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        data_dir = os.path.join(self.feast_repo_path, "data")

        user_df = pd.read_parquet(os.path.join(data_dir, "user_stats.parquet"))
        ad_df = pd.read_parquet(os.path.join(data_dir, "ad_stats.parquet"))
        context_df = pd.read_parquet(os.path.join(data_dir, "context_stats.parquet"))
        train_df = pd.read_parquet(os.path.join(data_dir, "training_data.parquet"))

        self.logger.info(f"Loaded user data shape: {user_df.shape}")
        self.logger.info(f"Loaded ad data shape: {ad_df.shape}")
        self.logger.info(f"Loaded context data shape: {context_df.shape}")
        self.logger.info(f"Loaded training data shape: {train_df.shape}")

        return user_df, ad_df, context_df, train_df

    def get_latest_snapshot(self, df: pd.DataFrame, entity_key: str) -> pd.DataFrame:
        df = df.sort_values("event_timestamp").groupby(entity_key).last().reset_index()
        return df

    def merge_features(self, train_df: pd.DataFrame, user_df: pd.DataFrame,
                      ad_df: pd.DataFrame, context_df: pd.DataFrame) -> pd.DataFrame:
        user_latest = self.get_latest_snapshot(user_df, "user_id")
        ad_latest = self.get_latest_snapshot(ad_df, "ad_id")
        context_latest = self.get_latest_snapshot(context_df, "context_id")

        merged_df = train_df.merge(user_latest, on="user_id", how="left", suffixes=("", "_user"))
        merged_df = merged_df.merge(ad_latest, on="ad_id", suffixes=("", "_ad"))
        if "context_id" in merged_df.columns:
            merged_df = merged_df.merge(context_latest, on="context_id", how="left", suffixes=("", "_context"))

        merged_df = merged_df.drop(columns=["event_timestamp", "created"], errors="ignore")

        self.logger.info(f"Merged data shape: {merged_df.shape}")
        return merged_df

    def prepare_training_data(self, test_size: float = 0.2, val_size: float = 0.1) -> Dict:
        user_df, ad_df, context_df, train_df = self.load_raw_data()

        merged_df = self.merge_features(train_df, user_df, ad_df, context_df)

        merged_df, feature_info = self.feature_engineer.transform(merged_df, fit=True)

        feat_names = self.feature_engineer.get_feature_names()
        feature_cols = feat_names["all"]

        X = merged_df[feature_cols].fillna(0)
        y_click = merged_df["click"].values
        y_conversion = merged_df["conversion"].values

        X_train_val, X_test, y_click_train_val, y_click_test, y_conv_train_val, y_conv_test = train_test_split(
            X, y_click, y_conversion, test_size=test_size, random_state=42, stratify=y_click
        )

        val_size_adjusted = val_size / (1 - test_size)
        X_train, X_val, y_click_train, y_click_val, y_conv_train, y_conv_val = train_test_split(
            X_train_val, y_click_train_val, y_conv_train_val, test_size=val_size_adjusted,
            random_state=42, stratify=y_click_train_val
        )

        self.logger.info(f"Train shape: {X_train.shape}")
        self.logger.info(f"Validation shape: {X_val.shape}")
        self.logger.info(f"Test shape: {X_test.shape}")

        artifact_path = os.path.join("data", "processed", "feature_artifacts.pkl")
        self.feature_engineer.save_artifacts(artifact_path)

        return {
            "train": (X_train, y_click_train, y_conv_train),
            "val": (X_val, y_click_val, y_conv_val),
            "test": (X_test, y_click_test, y_conv_test),
            "feature_info": feature_info
        }


def main():
    data_prep = DataPreparation()
    data = data_prep.prepare_training_data()

    output_dir = os.path.join("data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    import pickle
    with open(os.path.join(output_dir, "training_data.pkl"), "wb") as f:
        pickle.dump(data, f)

    print("Data preparation complete!")


if __name__ == "__main__":
    main()
