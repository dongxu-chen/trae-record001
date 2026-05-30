import os
import sys
import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir, get_feature_embedding_dims


class TeacherStudentDistiller:
    """教师-学生模型蒸馏器"""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("ModelDistiller", self.config)
        self.teacher_model = None
        self.student_model = None
        self.distillation_history = {}

    def set_teacher(self, teacher_model):
        """设置教师模型"""
        self.teacher_model = teacher_model
        self.logger.info("Teacher model set")

    def create_student_model(self, feature_info: Dict, 
                              compression_ratio: float = 0.25,
                              model_type: str = "deepfm") -> tf.keras.Model:
        """
        创建压缩的学生模型
        
        Args:
            feature_info: 特征信息
            compression_ratio: 压缩比 (学生/教师参数比)
            model_type: 模型类型 ("deepfm" 或 "simple_dnn")
        
        Returns:
            学生模型
        """
        if model_type == "deepfm":
            return self._create_compressed_deepfm(feature_info, compression_ratio)
        else:
            return self._create_simple_dnn(feature_info, compression_ratio)

    def _create_compressed_deepfm(self, feature_info: Dict, 
                                    compression_ratio: float) -> tf.keras.Model:
        """创建压缩版DeepFM学生模型"""
        original_config = self.config.copy()
        original_hidden = original_config["models"]["deepfm"]["hidden_units"]
        original_emb_dim = original_config["models"]["deepfm"]["embedding_dim"]

        compressed_hidden = [max(8, int(u * compression_ratio)) for u in original_hidden]
        compressed_emb_dim = max(4, int(original_emb_dim * compression_ratio))

        compressed_config = original_config.copy()
        compressed_config["models"]["deepfm"]["hidden_units"] = compressed_hidden
        compressed_config["models"]["deepfm"]["embedding_dim"] = compressed_emb_dim

        from models.deepfm import DeepFM
        student = DeepFM(feature_info, compressed_config, use_adaptive_embedding=True)

        self.logger.info(f"Student DeepFM: hidden={compressed_hidden}, emb_dim={compressed_emb_dim}")
        return student

    def _create_simple_dnn(self, feature_info: Dict, 
                             compression_ratio: float) -> tf.keras.Model:
        """创建简单DNN学生模型（极简版）"""
        numerical_features = feature_info["feature_names"]["numerical"]
        categorical_features = feature_info["feature_names"]["categorical"]
        vocab_sizes = feature_info.get("vocab_sizes", {})

        embedding_dims = get_feature_embedding_dims(vocab_sizes, min_dim=2, max_dim=16)
        total_emb_dim = sum(embedding_dims.values()) if embedding_dims else 0
        total_input_dim = len(numerical_features) + total_emb_dim

        hidden_units = [max(8, int(64 * compression_ratio)), max(4, int(32 * compression_ratio))]

        inputs = {}
        emb_layers = []
        emb_flat_parts = []

        for feat in categorical_features:
            inp = tf.keras.Input(shape=(), name=feat, dtype=tf.float32)
            inputs[feat] = inp
            emb_dim = embedding_dims.get(feat, 4)
            emb = tf.keras.layers.Embedding(
                input_dim=vocab_sizes.get(feat, 100),
                output_dim=emb_dim,
                name=f"emb_{feat}"
            )(inp)
            emb_flat_parts.append(tf.reshape(emb, [-1, emb_dim]))

        for feat in numerical_features:
            inp = tf.keras.Input(shape=(), name=feat, dtype=tf.float32)
            inputs[feat] = inp
            emb_flat_parts.append(tf.expand_dims(inp, axis=-1))

        if emb_flat_parts:
            concat = tf.concat(emb_flat_parts, axis=1)
        else:
            concat = tf.zeros((1, 1))

        x = concat
        for i, units in enumerate(hidden_units):
            x = tf.keras.layers.Dense(units, activation="relu", name=f"dense_{i}")(x)
            x = tf.keras.layers.BatchNormalization(name=f"bn_{i}")(x)
            x = tf.keras.layers.Dropout(0.1, name=f"dropout_{i}")(x)

        output = tf.keras.layers.Dense(1, activation="sigmoid", name="output")(x)

        student = tf.keras.Model(inputs=inputs, outputs=output, name="SimpleDNN")
        student.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss=tf.keras.losses.BinaryCrossentropy(),
            metrics=[tf.keras.metrics.AUC(name="auc")]
        )

        self.logger.info(f"Simple DNN student: hidden={hidden_units}, total_input={total_input_dim}")
        return student

    def distill(self, X_train: pd.DataFrame, X_val: pd.DataFrame,
                y_train: np.ndarray, y_val: np.ndarray,
                temperature: float = 5.0, alpha: float = 0.3,
                epochs: int = 10, batch_size: int = 1024) -> Tuple[tf.keras.Model, Dict]:
        """
        执行知识蒸馏训练
        
        Args:
            X_train: 训练特征
            X_val: 验证特征
            y_train: 训练标签
            y_val: 验证标签
            temperature: 蒸馏温度 (越高越软)
            alpha: 蒸馏损失权重 (0-1, 越大越依赖教师)
            epochs: 训练轮数
            batch_size: 批大小
        
        Returns:
            (学生模型, 训练历史)
        """
        if self.teacher_model is None:
            raise ValueError("Teacher model not set")

        self.logger.info(f"Starting distillation: T={temperature}, alpha={alpha}")

        train_dataset = self._prepare_dataset(X_train, y_train, batch_size, shuffle=True)
        val_dataset = self._prepare_dataset(X_val, y_val, batch_size, shuffle=False)

        teacher_preds_train = self._get_teacher_predictions(X_train, batch_size)
        teacher_preds_val = self._get_teacher_predictions(X_val, batch_size)

        history = {"train_loss": [], "val_loss": [], "val_auc": [],
                   "distill_loss": [], "hard_loss": []}

        best_val_auc = 0
        best_weights = None

        for epoch in range(epochs):
            epoch_losses = {"total": [], "distill": [], "hard": []}

            for step, (x_batch, y_batch) in enumerate(train_dataset):
                batch_idx = step * batch_size
                teacher_batch = teacher_preds_train[batch_idx:batch_idx + batch_size]
                if len(teacher_batch) < len(y_batch):
                    teacher_batch = np.pad(teacher_batch, (0, len(y_batch) - len(teacher_batch)), 
                                           constant_values=0.5)

                losses = self._train_step(x_batch, y_batch, teacher_batch, 
                                           temperature, alpha)
                epoch_losses["total"].append(float(losses["total"]))
                epoch_losses["distill"].append(float(losses["distill"]))
                epoch_losses["hard"].append(float(losses["hard"]))

            val_metrics = self.student_model.evaluate(val_dataset, verbose=0, return_dict=True)
            val_loss = val_metrics.get("loss", 0)
            val_auc = val_metrics.get("auc", 0)

            history["train_loss"].append(np.mean(epoch_losses["total"]))
            history["distill_loss"].append(np.mean(epoch_losses["distill"]))
            history["hard_loss"].append(np.mean(epoch_losses["hard"]))
            history["val_loss"].append(val_loss)
            history["val_auc"].append(val_auc)

            if val_auc > best_val_auc:
                best_val_auc = val_auc
                best_weights = self.student_model.get_weights()

            self.logger.info(
                f"Epoch {epoch+1}/{epochs} - "
                f"loss: {np.mean(epoch_losses['total']):.4f} - "
                f"distill_loss: {np.mean(epoch_losses['distill']):.4f} - "
                f"val_auc: {val_auc:.4f}"
            )

        if best_weights is not None:
            self.student_model.set_weights(best_weights)

        self.distillation_history = history
        self.logger.info(f"Distillation complete! Best val AUC: {best_val_auc:.4f}")
        return self.student_model, history

    def _train_step(self, x_batch, y_batch, teacher_preds, 
                     temperature: float, alpha: float) -> Dict[str, float]:
        """单步蒸馏训练"""
        with tf.GradientTape() as tape:
            student_preds = self.student_model(x_batch, training=True)

            if isinstance(student_preds, dict):
                student_preds = student_preds.get("click", student_preds.get("output", 
                                              list(student_preds.values())[0]))

            if student_preds.shape.rank > 1 and student_preds.shape[-1] == 1:
                student_preds = tf.squeeze(student_preds, axis=-1)

            hard_loss = tf.keras.losses.binary_crossentropy(y_batch, student_preds)

            teacher_logits = tf.math.log(teacher_preds + 1e-10) / temperature
            student_logits = tf.math.log(student_preds + 1e-10) / temperature

            soft_teacher = tf.nn.softmax(teacher_logits * temperature)
            soft_student = tf.nn.softmax(student_logits * temperature)

            distill_loss = tf.keras.losses.KLDivergence()(soft_teacher, soft_student)

            total_loss = alpha * tf.reduce_mean(distill_loss) + (1 - alpha) * tf.reduce_mean(hard_loss)

        gradients = tape.gradient(total_loss, self.student_model.trainable_variables)
        self.student_model.optimizer.apply_gradients(
            zip(gradients, self.student_model.trainable_variables)
        )

        return {
            "total": total_loss,
            "distill": tf.reduce_mean(distill_loss),
            "hard": tf.reduce_mean(hard_loss)
        }

    def _get_teacher_predictions(self, X: pd.DataFrame, batch_size: int) -> np.ndarray:
        """获取教师模型预测（软标签）"""
        dataset = self._prepare_dataset(X, np.zeros(len(X)), batch_size, shuffle=False)
        all_preds = []

        for x_batch, _ in dataset:
            preds = self.teacher_model(x_batch, training=False)
            if isinstance(preds, dict):
                preds = preds.get("click", preds.get("output", list(preds.values())[0]))
            all_preds.append(preds.numpy().flatten())

        return np.concatenate(all_preds)

    def _prepare_dataset(self, X: pd.DataFrame, y: np.ndarray, 
                          batch_size: int, shuffle: bool) -> tf.data.Dataset:
        """准备tf.data.Dataset"""
        feature_dict = {col: X[col].values.astype(np.float32) for col in X.columns}
        dataset = tf.data.Dataset.from_tensor_slices((feature_dict, y.astype(np.float32)))
        if shuffle:
            dataset = dataset.shuffle(buffer_size=len(X))
        dataset = dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
        return dataset

    def benchmark_inference_speed(self, X: pd.DataFrame, 
                                    batch_size: int = 1024,
                                    warmup: int = 3,
                                    num_runs: int = 10) -> Dict:
        """
        对比教师和学生模型的推理速度
        
        Returns:
            推理速度对比结果
        """
        feature_dict = {col: X[col].values.astype(np.float32) for col in X.columns}
        dataset = tf.data.Dataset.from_tensor_slices(feature_dict).batch(batch_size)

        def benchmark_model(model, name):
            for _ in range(warmup):
                for batch in dataset:
                    if isinstance(model, tf.keras.Model):
                        _ = model(batch, training=False)

            start_time = time.time()
            total_samples = 0
            for _ in range(num_runs):
                for batch in dataset:
                    if isinstance(model, tf.keras.Model):
                        preds = model(batch, training=False)
                    total_samples += batch_size

            total_time = time.time() - start_time
            throughput = total_samples / total_time
            avg_latency = total_time / total_samples * 1000

            return {
                "model": name,
                "total_time_s": total_time,
                "throughput_samples_per_sec": throughput,
                "avg_latency_ms": avg_latency,
                "num_samples": total_samples
            }

        teacher_result = benchmark_model(self.teacher_model, "teacher") if self.teacher_model else None
        student_result = benchmark_model(self.student_model, "student") if self.student_model else None

        result = {
            "teacher": teacher_result,
            "student": student_result,
            "timestamp": datetime.now().isoformat()
        }

        if teacher_result and student_result:
            speedup = student_result["throughput_samples_per_sec"] / max(teacher_result["throughput_samples_per_sec"], 1)
            latency_reduction = (1 - student_result["avg_latency_ms"] / max(teacher_result["avg_latency_ms"], 1e-10)) * 100
            result["speedup"] = speedup
            result["latency_reduction_pct"] = latency_reduction

            self.logger.info(f"Speedup: {speedup:.2f}x, Latency reduction: {latency_reduction:.1f}%")

        return result

    def get_model_size_comparison(self) -> Dict:
        """对比教师和学生模型的参数量"""
        def count_params(model):
            if model is None:
                return 0
            return sum(np.prod(v.shape) for v in model.trainable_variables)

        teacher_params = count_params(self.teacher_model)
        student_params = count_params(self.student_model)

        return {
            "teacher_params": int(teacher_params),
            "student_params": int(student_params),
            "compression_ratio": student_params / max(teacher_params, 1),
            "param_reduction": (1 - student_params / max(teacher_params, 1)) * 100 if teacher_params > 0 else 0
        }

    def save_student_model(self, path: str = "models/saved/student"):
        """保存学生模型"""
        ensure_dir(path)
        if self.student_model:
            self.student_model.save(path)
            self.logger.info(f"Student model saved to {path}")


def main():
    print("Model Distillation Module")
    print("Use this module to distill large models into smaller ones")


if __name__ == "__main__":
    main()
