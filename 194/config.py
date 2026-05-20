import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
VIS_DIR = os.path.join(BASE_DIR, "visualization")

NUM_ROADS = 20
HISTORY_LEN = 12
PRED_LEN = 3
PRED_HORIZONS = [15, 30, 60]

CONGESTION_MIN = 0
CONGESTION_MAX = 10

RANDOM_SEED = 42
TEST_SIZE = 0.2
VAL_SIZE = 0.1

LIGHTGBM_PARAMS = {
    "objective": "regression",
    "metric": "mse",
    "num_leaves": 63,
    "learning_rate": 0.05,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "num_threads": 4,
}

GNN_PARAMS = {
    "hidden_dim": 64,
    "num_layers": 2,
    "dropout": 0.2,
    "lr": 0.001,
    "epochs": 50,
    "batch_size": 32,
}

FUSION_PARAMS = {
    "gnn_weight": 0.6,
    "lgb_weight": 0.4,
}
