import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import ensure_dir


def generate_user_data(num_users: int = 10000, start_date: datetime = None, days: int = 30) -> pd.DataFrame:
    if start_date is None:
        start_date = datetime.now() - timedelta(days=days)

    np.random.seed(42)
    data = []

    for day in range(days):
        event_timestamp = start_date + timedelta(days=day)
        for user_id in range(num_users):
            row = {
                "user_id": f"user_{user_id}",
                "event_timestamp": event_timestamp,
                "created": event_timestamp,
                "user_age": np.random.randint(18, 65),
                "user_gender": np.random.choice([0, 1, 2], p=[0.05, 0.5, 0.45]),
                "user_level": np.random.randint(1, 10),
                "user_consumption_level": np.random.randint(1, 6),
                "user_active_days_7d": np.random.randint(0, 8),
                "user_click_count_7d": np.random.poisson(15),
                "user_impression_count_7d": np.random.poisson(100),
                "user_category_preference": np.random.randint(1, 20),
                "user_city_level": np.random.randint(1, 5),
                "user_device_type": np.random.choice([1, 2, 3], p=[0.4, 0.5, 0.1]),
                "user_registration_days": np.random.randint(1, 1000),
            }
            row["user_ctr_7d"] = np.clip(
                row["user_click_count_7d"] / max(row["user_impression_count_7d"], 1), 0, 1
            ).astype(np.float32)
            data.append(row)

    df = pd.DataFrame(data)
    return df


def generate_ad_data(num_ads: int = 5000, start_date: datetime = None, days: int = 30) -> pd.DataFrame:
    if start_date is None:
        start_date = datetime.now() - timedelta(days=days)

    np.random.seed(43)
    data = []

    for day in range(days):
        event_timestamp = start_date + timedelta(days=day)
        for ad_id in range(num_ads):
            row = {
                "ad_id": f"ad_{ad_id}",
                "event_timestamp": event_timestamp,
                "created": event_timestamp,
                "ad_category": np.random.randint(1, 20),
                "ad_campaign_id": np.random.randint(1, 500),
                "ad_advertiser_id": np.random.randint(1, 200),
                "ad_click_count_7d": np.random.poisson(50),
                "ad_impression_count_7d": np.random.poisson(500),
                "ad_price": np.random.uniform(0.1, 10.0).astype(np.float32),
                "ad_position": np.random.randint(1, 10),
                "ad_creative_type": np.random.randint(1, 6),
                "ad_is_new": np.random.choice([0, 1], p=[0.9, 0.1]),
            }
            row["ad_ctr_history"] = np.clip(
                row["ad_click_count_7d"] / max(row["ad_impression_count_7d"], 1), 0, 1
            ).astype(np.float32)
            data.append(row)

    df = pd.DataFrame(data)
    return df


def generate_context_data(num_contexts: int = 20000, start_date: datetime = None, days: int = 30) -> pd.DataFrame:
    if start_date is None:
        start_date = datetime.now() - timedelta(days=days)

    np.random.seed(44)
    data = []
    context_id = 0

    for day in range(days):
        base_date = start_date + timedelta(days=day)
        day_of_week = base_date.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0

        for _ in range(num_contexts // days):
            hour = np.random.randint(0, 24)
            event_timestamp = base_date + timedelta(hours=hour)
            row = {
                "context_id": f"context_{context_id}",
                "event_timestamp": event_timestamp,
                "created": event_timestamp,
                "context_hour": hour,
                "context_day_of_week": day_of_week,
                "context_is_weekend": is_weekend,
                "context_traffic_source": np.random.randint(1, 10),
                "context_network_type": np.random.choice([1, 2, 3], p=[0.5, 0.4, 0.1]),
                "context_app_version": np.random.randint(1, 20),
                "context_scene_id": np.random.randint(1, 50),
                "context_page_id": np.random.randint(1, 100),
            }
            data.append(row)
            context_id += 1

    df = pd.DataFrame(data)
    return df


def generate_training_data(num_samples: int = 100000) -> pd.DataFrame:
    np.random.seed(45)
    data = []

    for i in range(num_samples):
        user_id = f"user_{np.random.randint(0, 10000)}"
        ad_id = f"ad_{np.random.randint(0, 5000)}"
        context_id = f"context_{np.random.randint(0, 20000)}"

        user_ctr = np.random.beta(2, 20)
        ad_ctr = np.random.beta(3, 25)
        context_bias = 0.5 + 0.1 * np.sin(np.random.randint(0, 24) * np.pi / 12)

        click_prob = 0.02 + 0.3 * user_ctr + 0.4 * ad_ctr + 0.1 * context_bias
        click_prob = np.clip(click_prob, 0.001, 0.8)

        click_label = np.random.binomial(1, click_prob)
        conversion_label = click_label * np.random.binomial(1, 0.3)

        data.append({
            "user_id": user_id,
            "ad_id": ad_id,
            "context_id": context_id,
            "click": click_label,
            "conversion": conversion_label,
            "timestamp": datetime.now() - timedelta(minutes=np.random.randint(0, 1440 * 30)),
        })

    df = pd.DataFrame(data)
    return df


def main():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    ensure_dir(data_dir)

    print("Generating user data...")
    user_df = generate_user_data(num_users=1000, days=7)
    user_df.to_parquet(os.path.join(data_dir, "user_stats.parquet"))
    print(f"User data shape: {user_df.shape}")

    print("Generating ad data...")
    ad_df = generate_ad_data(num_ads=500, days=7)
    ad_df.to_parquet(os.path.join(data_dir, "ad_stats.parquet"))
    print(f"Ad data shape: {ad_df.shape}")

    print("Generating context data...")
    context_df = generate_context_data(num_contexts=2000, days=7)
    context_df.to_parquet(os.path.join(data_dir, "context_stats.parquet"))
    print(f"Context data shape: {context_df.shape}")

    print("Generating training data...")
    train_df = generate_training_data(num_samples=50000)
    train_df.to_parquet(os.path.join(data_dir, "training_data.parquet"))
    print(f"Training data shape: {train_df.shape}")

    print("Data generation complete!")


if __name__ == "__main__":
    main()
