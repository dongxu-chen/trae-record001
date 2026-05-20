import numpy as np
import sys
import os
from sklearn.metrics import mean_squared_error, mean_absolute_error

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FUSION_PARAMS, MODEL_DIR, NUM_ROADS, PRED_HORIZONS
from models.lightgbm_model import LightGBMPredictor, prepare_features_for_lgb
from models.gnn_model import GNNPredictor


class FusionPredictor:
    def __init__(self, gnn_input_dim, gnn_params=None, lgb_params=None, fusion_params=None):
        self.gnn_input_dim = gnn_input_dim
        self.gnn_params = gnn_params
        self.lgb_params = lgb_params
        self.fusion_params = fusion_params if fusion_params else FUSION_PARAMS

        self.gnn_predictor = GNNPredictor(gnn_input_dim, gnn_params)
        self.lgb_predictor = LightGBMPredictor(lgb_params)

    def set_graph(self, g):
        self.gnn_predictor.set_graph(g)

    def train(self, train_sequences, train_targets, train_road_ids,
              val_sequences=None, val_targets=None, val_road_ids=None):
        print("\n" + "=" * 50)
        print("Training LightGBM Model...")
        print("=" * 50)
        X_train_lgb = prepare_features_for_lgb(train_sequences, train_road_ids)
        X_val_lgb = None
        if val_sequences is not None:
            X_val_lgb = prepare_features_for_lgb(val_sequences, val_road_ids)

        self.lgb_predictor.train(X_train_lgb, train_targets, X_val_lgb, val_targets)
        self.lgb_predictor.save()

        print("\n" + "=" * 50)
        print("Training GNN Model...")
        print("=" * 50)
        self.gnn_predictor.train(
            train_sequences, train_targets, train_road_ids,
            val_sequences, val_targets, val_road_ids
        )

        print("\n" + "=" * 50)
        print("Training Complete!")
        print("=" * 50)

    def predict(self, sequences, road_ids):
        print("Generating LightGBM predictions...")
        X_lgb = prepare_features_for_lgb(sequences, road_ids)
        lgb_preds = self.lgb_predictor.predict(X_lgb)

        print("Generating GNN predictions...")
        gnn_preds = self.gnn_predictor.predict(sequences, road_ids)

        print("Fusing predictions...")
        fused_preds = (
            self.fusion_params["gnn_weight"] * gnn_preds +
            self.fusion_params["lgb_weight"] * lgb_preds
        )

        return fused_preds, lgb_preds, gnn_preds

    def evaluate(self, sequences, targets, road_ids):
        fused_preds, lgb_preds, gnn_preds = self.predict(sequences, road_ids)

        print("\n" + "=" * 50)
        print("Model Evaluation Results")
        print("=" * 50)

        lgb_mse = mean_squared_error(targets, lgb_preds)
        lgb_mae = mean_absolute_error(targets, lgb_preds)
        print(f"LightGBM - MSE: {lgb_mse:.4f}, MAE: {lgb_mae:.4f}")

        gnn_mse = mean_squared_error(targets, gnn_preds)
        gnn_mae = mean_absolute_error(targets, gnn_preds)
        print(f"GNN       - MSE: {gnn_mse:.4f}, MAE: {gnn_mae:.4f}")

        fused_mse = mean_squared_error(targets, fused_preds)
        fused_mae = mean_absolute_error(targets, fused_preds)
        print(f"Fusion    - MSE: {fused_mse:.4f}, MAE: {fused_mae:.4f}")

        for i, horizon in enumerate(PRED_HORIZONS):
            lgb_mse_h = mean_squared_error(targets[:, i], lgb_preds[:, i])
            gnn_mse_h = mean_squared_error(targets[:, i], gnn_preds[:, i])
            fused_mse_h = mean_squared_error(targets[:, i], fused_preds[:, i])
            print(f"\nHorizon {horizon}min:")
            print(f"  LightGBM MSE: {lgb_mse_h:.4f}")
            print(f"  GNN       MSE: {gnn_mse_h:.4f}")
            print(f"  Fusion    MSE: {fused_mse_h:.4f}")

        return {
            "lgb": {"mse": lgb_mse, "mae": lgb_mae},
            "gnn": {"mse": gnn_mse, "mae": gnn_mae},
            "fused": {"mse": fused_mse, "mae": fused_mae},
            "predictions": {
                "lgb": lgb_preds,
                "gnn": gnn_preds,
                "fused": fused_preds
            }
        }

    def save(self, model_dir=MODEL_DIR):
        self.lgb_predictor.save(os.path.join(model_dir, "lgb_models"))
        self.gnn_predictor.save(os.path.join(model_dir, "gnn_model.pt"))
        print(f"Saved all models to {model_dir}")

    def load(self, model_dir=MODEL_DIR):
        self.lgb_predictor.load(os.path.join(model_dir, "lgb_models"))
        self.gnn_predictor.load(os.path.join(model_dir, "gnn_model.pt"))
        print(f"Loaded all models from {model_dir}")
