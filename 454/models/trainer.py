import os
import sys
import pandas as pd
import numpy as np
import tensorflow as tf
from typing import Dict, List, Tuple
import json
from datetime import datetime
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir
from deepfm import DeepFM
from mmoe import MMoE


class ModelTrainer:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("ModelTrainer", self.config)
        self.models = {}
        self.history = {}
        self.feature_info = None

    def prepare_tf_dataset(self, X: pd.DataFrame, y: np.ndarray, 
                             batch_size: int = 1024, shuffle: bool = True) -> tf.data.Dataset:
        feature_dict = {col: X[col].values.astype(np.float32) for col in X.columns}

        if isinstance(y, dict):
            dataset = tf.data.Dataset.from_tensor_slices((feature_dict, y))
        else:
            dataset = tf.data.Dataset.from_tensor_slices((feature_dict, y))

        if shuffle:
            dataset = dataset.shuffle(buffer_size=len(X))

        dataset = dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
        return dataset

    def train_deepfm(self, X_train: pd.DataFrame, y_train: np.ndarray,
                     X_val: pd.DataFrame, y_val: np.ndarray,
                     feature_info: Dict) -> Tuple[DeepFM, Dict]:
        self.logger.info("Starting DeepFM training...")
        self.feature_info = feature_info

        model_config = self.config["models"]["deepfm"]
        batch_size = model_config["batch_size"]
        epochs = model_config["epochs"]

        train_dataset = self.prepare_tf_dataset(X_train, y_train, batch_size=batch_size)
        val_dataset = self.prepare_tf_dataset(X_val, y_val, batch_size=batch_size, shuffle=False)

        model = DeepFM(feature_info, self.config)

        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor="val_auc",
            patience=3,
            mode="max",
            restore_best_weights=True
        )

        history = model.fit(
            train_dataset,
            validation_data=val_dataset,
            epochs=epochs,
            callbacks=[early_stopping]
        )

        self.models["deepfm"] = model
        self.history["deepfm"] = history.history

        self.logger.info("DeepFM training complete!")
        return model, history.history

    def train_mmoe(self, X_train: pd.DataFrame, y_click_train: np.ndarray,
                     y_conv_train: np.ndarray,
                     X_val: pd.DataFrame, y_click_val: np.ndarray,
                     y_conv_val: np.ndarray,
                     feature_info: Dict) -> Tuple[MMoE, Dict]:
        self.logger.info("Starting MMoE training...")
        self.feature_info = feature_info

        model_config = self.config["models"]["mmoe"]
        batch_size = model_config["batch_size"]
        epochs = model_config["epochs"]

        y_train_dict = {"click": y_click_train, "conversion": y_conv_train}
        y_val_dict = {"click": y_click_val, "conversion": y_conv_val}

        train_dataset = self.prepare_tf_dataset(X_train, y_train_dict, batch_size=batch_size)
        val_dataset = self.prepare_tf_dataset(X_val, y_val_dict, batch_size=batch_size, shuffle=False)

        model = MMoE(feature_info, self.config)

        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor="val_click_auc",
            patience=3,
            mode="max",
            restore_best_weights=True
        )

        history = model.fit(
            train_dataset,
            validation_data=val_dataset,
            epochs=epochs,
            callbacks=[early_stopping]
        )

        self.models["mmoe"] = model
        self.history["mmoe"] = history.history

        self.logger.info("MMoE training complete!")
        return model, history.history

    def evaluate_model(self, model_name: str, X_test: pd.DataFrame, y_test: np.ndarray) -> Dict[str, float]:
        self.logger.info(f"Evaluating {model_name}...")
        model = self.models.get(model_name)
        if model is None:
            raise ValueError(f"Model {model_name} not found")

        test_dataset = self.prepare_tf_dataset(X_test, y_test, batch_size=1024, shuffle=False)
        results = model.evaluate(test_dataset, verbose=0)

        if isinstance(results, dict):
            return results
        else:
            metric_names = model.metrics_names
            return dict(zip(metric_names, results))

    def save_models(self, output_dir: str = "models/saved"):
        ensure_dir(output_dir)

        for model_name, model in self.models.items():
            model_path = os.path.join(output_dir, model_name)
            model.save(model_path)
            self.logger.info(f"Saved {model_name} to {model_path}")

        history_path = os.path.join(output_dir, "training_history.json")
        serializable_history = {}
        for model_name, hist in self.history.items():
            serializable_history[model_name] = {}
            for metric_name, values in hist.items():
                serializable_history[model_name][metric_name] = [float(v) if isinstance(v, (int, float, np.floating)) else v for v in values]
        with open(history_path, "w") as f:
            json.dump(serializable_history, f, indent=2)

        if self.feature_info:
            feature_info_path = os.path.join(output_dir, "feature_info.pkl")
            with open(feature_info_path, "wb") as f:
                pickle.dump(self.feature_info, f)

        self.logger.info("All models saved successfully!")

    def get_training_history(self) -> Dict:
        return self.history


def main():
    print("Model Trainer module")
    print("Use this module to train DeepFM and MMoE models")


if __name__ == "__main__":
    main()
