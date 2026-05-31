import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score


FEATURE_COLUMNS = [
    "cart_value",
    "cart_items",
    "shipping_fee",
    "price_sensitivity_score",
    "has_coupon",
    "cart_page_time_sec",
    "scroll_depth",
    "mouse_leave_count",
    "tab_switch_count",
    "cart_page_visits",
    "hover_checkout_btn_sec",
    "price_page_dwell_sec",
    "hesitation_score",
    "has_lower_competitor",
    "price_diff_pct_vs_lowest",
    "n_competitors_checked",
]

CATEGORICAL_MAPS = {
    "user_segment": {"新用户": 0, "回访用户": 1, "活跃用户": 2, "沉睡用户": 3, "VIP用户": 4},
    "device": {"移动端": 0, "PC端": 1, "平板": 2},
}


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    cart_df["has_coupon"] = cart_df["has_coupon"].astype(int)
    cart_df["has_lower_competitor"] = cart_df["has_lower_competitor"].astype(int)

    for col, mapping in CATEGORICAL_MAPS.items():
        cart_df[f"{col}_encoded"] = cart_df[col].map(mapping).fillna(-1)

    feature_cols = FEATURE_COLUMNS + [f"{col}_encoded" for col in CATEGORICAL_MAPS.keys()]

    return cart_df, feature_cols


def train_risk_model(df: pd.DataFrame):
    cart_df, feature_cols = prepare_features(df)

    X = cart_df[feature_cols].fillna(0).values
    y = cart_df["completed"].astype(int).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    model.fit(X_scaled, y)

    y_pred_proba = model.predict_proba(X_scaled)[:, 1]
    y_pred = model.predict(X_scaled)

    auc = roc_auc_score(y, y_pred_proba)

    cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring="roc_auc")

    feature_importance = pd.DataFrame({
        "feature": feature_cols,
        "coefficient": model.coef_[0],
        "abs_coefficient": np.abs(model.coef_[0]),
    }).sort_values("abs_coefficient", ascending=False)

    cart_df["risk_score"] = 1 - y_pred_proba
    cart_df["predicted_abandon"] = (cart_df["risk_score"] > 0.5).astype(int)

    risk_bins = [0, 0.3, 0.6, 1.01]
    risk_labels = ["低风险", "中风险", "高风险"]
    cart_df["risk_level"] = pd.cut(cart_df["risk_score"], bins=risk_bins, labels=risk_labels)

    return {
        "model": model,
        "scaler": scaler,
        "feature_cols": feature_cols,
        "auc": round(auc, 4),
        "cv_auc_mean": round(cv_scores.mean(), 4),
        "cv_auc_std": round(cv_scores.std(), 4),
        "feature_importance": feature_importance,
        "predictions": cart_df,
    }


def predict_risk_for_user(df: pd.DataFrame, model_result: dict) -> pd.DataFrame:
    cart_df, feature_cols = prepare_features(df)

    X = cart_df[feature_cols].fillna(0).values
    X_scaled = model_result["scaler"].transform(X)

    risk_scores = 1 - model_result["model"].predict_proba(X_scaled)[:, 1]

    cart_df["risk_score"] = np.round(risk_scores, 4)

    bins = [0, 0.3, 0.6, 1.01]
    labels = ["低风险", "中风险", "高风险"]
    cart_df["risk_level"] = pd.cut(cart_df["risk_score"], bins=bins, labels=labels)

    return cart_df


def compute_risk_distribution(df: pd.DataFrame, model_result: dict) -> pd.DataFrame:
    predictions = model_result["predictions"]
    predictions["actual_abandon"] = (~predictions["completed"]).astype(int)

    risk_dist = predictions.groupby("risk_level", observed=False).agg(
        count=("session_id", "count"),
        actual_abandon_rate=("actual_abandon", "mean"),
        avg_risk_score=("risk_score", "mean"),
        avg_cart_value=("cart_value", "mean"),
    ).reset_index()

    risk_dist["actual_abandon_rate"] = (risk_dist["actual_abandon_rate"] * 100).round(2)
    risk_dist["avg_risk_score"] = risk_dist["avg_risk_score"].round(4)
    risk_dist["avg_cart_value"] = risk_dist["avg_cart_value"].round(2)

    return risk_dist


def compute_risk_by_segment(df: pd.DataFrame, model_result: dict) -> pd.DataFrame:
    predictions = model_result["predictions"]
    predictions["actual_abandon"] = (~predictions["completed"]).astype(int)
    predictions["is_high_risk"] = (predictions["risk_level"] == "高风险").astype(int)

    seg_risk = predictions.groupby("user_segment").agg(
        avg_risk_score=("risk_score", "mean"),
        high_risk_pct=("is_high_risk", "mean"),
        actual_abandon_rate=("actual_abandon", "mean"),
    ).reset_index()

    seg_risk["avg_risk_score"] = seg_risk["avg_risk_score"].round(4)
    seg_risk["high_risk_pct"] = (seg_risk["high_risk_pct"] * 100).round(2)
    seg_risk["actual_abandon_rate"] = (seg_risk["actual_abandon_rate"] * 100).round(2)

    return seg_risk


def simulate_realtime_prediction(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    cart_df["has_coupon"] = cart_df["has_coupon"].astype(int)
    cart_df["has_lower_competitor"] = cart_df["has_lower_competitor"].astype(int)

    risk_signals = []
    for _, row in cart_df.iterrows():
        signals = 0
        if row["hesitation_score"] >= 5:
            signals += 3
        elif row["hesitation_score"] >= 3:
            signals += 2
        elif row["hesitation_score"] >= 1:
            signals += 1

        if row["price_sensitivity_score"] > 0.5:
            signals += 2
        elif row["price_sensitivity_score"] > 0.2:
            signals += 1

        if row["has_lower_competitor"]:
            signals += 2

        if row["shipping_fee"] > 0 and row["cart_value"] < 99:
            signals += 1

        if row["user_segment"] == "新用户":
            signals += 1

        if row["mouse_leave_count"] > 2:
            signals += 1

        risk_pct = min(signals / 10, 1.0)

        if risk_pct > 0.6:
            risk_level = "高风险"
        elif risk_pct > 0.3:
            risk_level = "中风险"
        else:
            risk_level = "低风险"

        risk_signals.append({
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "realtime_risk_score": round(risk_pct, 4),
            "realtime_risk_level": risk_level,
            "completed": row["completed"],
        })

    return pd.DataFrame(risk_signals)
