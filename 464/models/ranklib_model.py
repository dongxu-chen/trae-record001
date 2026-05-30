import os
import subprocess
import tempfile
import numpy as np


def _write_libsvm_format(X, y, groups, filepath):
    with open(filepath, "w") as f:
        idx = 0
        for group_size in groups:
            for _ in range(group_size):
                label = int(y[idx])
                features = X[idx]
                feat_str = " ".join(f"{j + 1}:{v:.6f}" for j, v in enumerate(features))
                f.write(f"{label} {feat_str}\n")
                idx += 1


def _read_ranklib_scores(filepath):
    scores = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    scores.append(float(line))
                except ValueError:
                    continue
    return np.array(scores)


class RankLibRanker:
    SUPPORTED_METHODS = ["6", "LAMBDA"]

    def __init__(self, method="LAMBDA", ranklib_jar=None):
        self.method = method
        self.ranklib_jar = ranklib_jar
        self.model_file = None

    def train(self, X_train, y_train, group_train, X_val=None, y_val=None, group_val=None, model_output=None):
        if self.ranklib_jar is None or not os.path.exists(self.ranklib_jar):
            raise FileNotFoundError(
                "RankLib JAR not found. Set ranklib_jar path. "
                "Download from https://sourceforge.net/projects/lemur/"
            )

        tmp_dir = tempfile.mkdtemp()
        train_file = os.path.join(tmp_dir, "train.txt")
        _write_libsvm_format(X_train, y_train, group_train, train_file)

        cmd = [
            "java", "-jar", self.ranklib_jar,
            "-train", train_file,
            "-ranker", self.method,
            "-metric2t", "NDCG@10",
        ]

        if X_val is not None and y_val is not None and group_val is not None:
            val_file = os.path.join(tmp_dir, "val.txt")
            _write_libsvm_format(X_val, y_val, group_val, val_file)
            cmd.extend(["-validate", val_file])

        if model_output:
            cmd.extend(["-save", model_output])
            self.model_file = model_output
        else:
            model_path = os.path.join(tmp_dir, "model.txt")
            cmd.extend(["-save", model_path])
            self.model_file = model_path

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"RankLib training failed: {result.stderr}")
        return result.stdout

    def predict(self, X, scores_file=None):
        if self.model_file is None:
            raise ValueError("Model not trained yet")
        if not os.path.exists(self.model_file):
            raise FileNotFoundError("Model file not found")

        tmp_dir = tempfile.mkdtemp()
        test_file = os.path.join(tmp_dir, "test.txt")
        dummy_labels = np.zeros(len(X))
        dummy_groups = [len(X)]
        _write_libsvm_format(X, dummy_labels, dummy_groups, test_file)

        if scores_file is None:
            scores_file = os.path.join(tmp_dir, "scores.txt")

        cmd = [
            "java", "-jar", self.ranklib_jar,
            "-load", self.model_file,
            "-rank", test_file,
            "-score", scores_file,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"RankLib prediction failed: {result.stderr}")

        return _read_ranklib_scores(scores_file)
