import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN


class MLDetector:
    def __init__(self, users_df, orders_df, graph_features):
        self.users_df = users_df
        self.orders_df = orders_df
        self.graph_features = graph_features
        self.user_features_df = None
        self.scaler = StandardScaler()
        self.iso_forest = None
        self.ml_scores = {}

    def extract_features(self):
        features_list = []
        user_orders = self.orders_df.groupby("user_id")

        for _, user_row in self.users_df.iterrows():
            user_id = user_row["user_id"]
            gf = self.graph_features.get(user_id, {})
            orders = user_orders.get_group(user_id) if user_id in user_orders.groups else pd.DataFrame()

            n_orders = len(orders)
            total_amount = orders["amount"].sum() if n_orders > 0 else 0
            avg_amount = orders["amount"].mean() if n_orders > 0 else 0
            std_amount = orders["amount"].std() if n_orders > 1 else 0
            max_amount = orders["amount"].max() if n_orders > 0 else 0
            min_amount = orders["amount"].min() if n_orders > 0 else 0

            n_products = orders["product_name"].nunique() if n_orders > 0 else 0
            n_categories = orders["category"].nunique() if n_orders > 0 else 0

            if n_orders > 1:
                times = pd.to_datetime(orders["order_time"]).sort_values()
                diffs = times.diff().dropna().dt.total_seconds() / 3600
                avg_interval = diffs.mean()
                min_interval = diffs.min()
            else:
                avg_interval = 999
                min_interval = 999

            night_ratio = 0
            if n_orders > 0:
                night_orders = orders[(orders["order_hour"] >= 0) & (orders["order_hour"] <= 5)]
                night_ratio = len(night_orders) / n_orders

            same_product_ratio = 0
            if n_orders > 0:
                product_counts = orders["product_name"].value_counts()
                same_product_ratio = product_counts.max() / n_orders

            features_list.append({
                "user_id": user_id,
                "account_age_days": user_row["account_age_days"],
                "n_orders": n_orders,
                "total_amount": total_amount,
                "avg_amount": avg_amount,
                "std_amount": std_amount,
                "max_amount": max_amount,
                "min_amount": min_amount,
                "amount_range": max_amount - min_amount,
                "n_products": n_products,
                "n_categories": n_categories,
                "avg_order_interval_h": avg_interval,
                "min_order_interval_h": min_interval,
                "night_order_ratio": night_ratio,
                "same_product_ratio": same_product_ratio,
                "shared_device_count": gf.get("shared_device_count", 0),
                "shared_ip_count": gf.get("shared_ip_count", 0),
                "shared_address_count": gf.get("shared_address_count", 0),
                "total_linked_users": gf.get("total_linked_users", 0),
                "degree": gf.get("degree", 0),
                "clustering_coefficient": gf.get("clustering_coefficient", 0),
                "is_fraud": user_row["is_fraud"]
            })

        self.user_features_df = pd.DataFrame(features_list)
        return self.user_features_df

    def train_isolation_forest(self, contamination=0.15):
        if self.user_features_df is None:
            self.extract_features()

        feature_cols = [
            "account_age_days", "n_orders", "total_amount", "avg_amount",
            "std_amount", "amount_range", "n_products", "n_categories",
            "avg_order_interval_h", "min_order_interval_h",
            "night_order_ratio", "same_product_ratio",
            "shared_device_count", "shared_ip_count", "shared_address_count",
            "total_linked_users", "degree"
        ]

        X = self.user_features_df[feature_cols].fillna(0)
        X_scaled = self.scaler.fit_transform(X)

        self.iso_forest = IsolationForest(
            contamination=contamination,
            n_estimators=200,
            max_samples="auto",
            random_state=42,
            n_jobs=-1
        )
        self.iso_forest.fit(X_scaled)

        predictions = self.iso_forest.predict(X_scaled)
        scores = self.iso_forest.score_samples(X_scaled)

        self.user_features_df["iso_prediction"] = predictions
        self.user_features_df["iso_raw_score"] = scores

        min_score = scores.min()
        max_score = scores.max()
        if max_score > min_score:
            normalized = (scores - min_score) / (max_score - min_score)
        else:
            normalized = np.zeros_like(scores)

        self.user_features_df["ml_anomaly_score"] = (1 - normalized) * 100

        for _, row in self.user_features_df.iterrows():
            self.ml_scores[row["user_id"]] = {
                "ml_anomaly_score": row["ml_anomaly_score"],
                "iso_prediction": row["iso_prediction"],
                "iso_raw_score": row["iso_raw_score"]
            }

        return self.ml_scores

    def cluster_users(self, eps=1.5, min_samples=3):
        if self.user_features_df is None:
            self.extract_features()

        feature_cols = [
            "n_orders", "avg_amount", "avg_order_interval_h",
            "night_order_ratio", "same_product_ratio",
            "shared_device_count", "shared_ip_count", "shared_address_count"
        ]

        X = self.user_features_df[feature_cols].fillna(0)
        X_scaled = self.scaler.fit_transform(X)

        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(X_scaled)

        self.user_features_df["cluster_label"] = labels

        cluster_stats = {}
        for label in set(labels):
            if label == -1:
                continue
            mask = labels == label
            cluster_users = self.user_features_df[mask]
            fraud_ratio = cluster_users["is_fraud"].mean()
            cluster_stats[label] = {
                "size": mask.sum(),
                "fraud_ratio": fraud_ratio,
                "avg_orders": cluster_users["n_orders"].mean(),
                "avg_amount": cluster_users["avg_amount"].mean(),
                "avg_shared_devices": cluster_users["shared_device_count"].mean(),
                "members": cluster_users["user_id"].tolist()
            }

        return cluster_stats

    def get_feature_importance(self):
        if self.iso_forest is None:
            return None

        feature_cols = [
            "account_age_days", "n_orders", "total_amount", "avg_amount",
            "std_amount", "amount_range", "n_products", "n_categories",
            "avg_order_interval_h", "min_order_interval_h",
            "night_order_ratio", "same_product_ratio",
            "shared_device_count", "shared_ip_count", "shared_address_count",
            "total_linked_users", "degree"
        ]

        importances = self.iso_forest.decision_function(
            self.scaler.transform(self.user_features_df[feature_cols].fillna(0))
        )

        return dict(zip(feature_cols, np.abs(importances).mean(axis=0) if importances.ndim > 1 else np.abs(importances)))
