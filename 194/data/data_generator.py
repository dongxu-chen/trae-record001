import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NUM_ROADS, RANDOM_SEED, DATA_DIR

np.random.seed(RANDOM_SEED)


def generate_traffic_data(start_date, days=30):
    dates = []
    current = start_date
    while current < start_date + timedelta(days=days):
        dates.append(current)
        current += timedelta(minutes=5)

    n_samples = len(dates)
    data = []

    for road_id in range(NUM_ROADS):
        road_base_speed = np.random.uniform(40, 80)
        road_base_flow = np.random.uniform(200, 800)
        road_base_occ = np.random.uniform(0.1, 0.4)

        for i, dt in enumerate(dates):
            hour = dt.hour
            weekday = dt.weekday()

            is_weekend = 1 if weekday >= 5 else 0
            morning_peak = 1 if 7 <= hour <= 9 else 0
            evening_peak = 1 if 17 <= hour <= 19 else 0
            peak_factor = 0.6 if morning_peak or evening_peak else 1.0
            weekend_factor = 1.3 if is_weekend else 1.0

            speed = road_base_speed * peak_factor * weekend_factor
            speed += np.random.normal(0, 5)
            speed = max(5, min(120, speed))

            flow = road_base_flow / peak_factor / weekend_factor
            flow += np.random.normal(0, 50)
            flow = max(0, min(2000, flow))

            occ = road_base_occ / peak_factor / weekend_factor
            occ += np.random.normal(0, 0.05)
            occ = max(0, min(1, occ))

            congestion = calculate_congestion_index(speed, flow, occ, road_base_speed)

            data.append({
                "timestamp": dt,
                "road_id": road_id,
                "speed": speed,
                "flow": flow,
                "occupancy": occ,
                "congestion_index": congestion,
                "hour": hour,
                "minute": dt.minute,
                "weekday": weekday,
                "is_weekend": is_weekend,
                "morning_peak": morning_peak,
                "evening_peak": evening_peak,
                "day_of_year": dt.timetuple().tm_yday,
                "month": dt.month,
            })

    df = pd.DataFrame(data)
    return df


def calculate_congestion_index(speed, flow, occ, base_speed):
    speed_ratio = speed / base_speed
    flow_norm = flow / 2000

    if speed_ratio > 0.9:
        level = 0
    elif speed_ratio > 0.7:
        level = 2
    elif speed_ratio > 0.5:
        level = 4
    elif speed_ratio > 0.3:
        level = 6
    else:
        level = 8

    congestion = level + (1 - speed_ratio) * 2.0 + flow_norm * 1.0 + occ * 0.5
    return max(0, min(10, congestion))


def generate_weather_data(start_date, days=30):
    dates = []
    current = start_date
    while current < start_date + timedelta(days=days):
        dates.append(current)
        current += timedelta(hours=1)

    weather_data = []
    for dt in dates:
        month = dt.month
        base_temp = 10 + 15 * np.sin(2 * np.pi * (month - 3) / 12)

        weather_data.append({
            "timestamp": dt,
            "temperature": base_temp + np.random.normal(0, 3),
            "rainfall": max(0, np.random.exponential(0.5) if np.random.random() < 0.2 else 0),
            "visibility": np.random.uniform(5, 20) if np.random.random() < 0.9 else np.random.uniform(0.5, 5),
            "weather_type": np.random.choice([0, 1, 2, 3], p=[0.6, 0.2, 0.15, 0.05]),
        })

    df = pd.DataFrame(weather_data)
    return df


def generate_event_data(start_date, days=30):
    events = []
    current = start_date
    end_date = start_date + timedelta(days=days)

    while current < end_date:
        if np.random.random() < 0.05:
            road_id = np.random.randint(0, NUM_ROADS)
            event_type = np.random.choice([1, 2, 3])
            duration_hours = np.random.uniform(0.5, 4)

            events.append({
                "start_time": current,
                "end_time": current + timedelta(hours=duration_hours),
                "road_id": road_id,
                "event_type": event_type,
                "severity": np.random.randint(1, 4),
            })

        current += timedelta(minutes=30)

    df = pd.DataFrame(events)
    return df


def merge_data(traffic_df, weather_df, event_df):
    traffic_df = traffic_df.sort_values(["road_id", "timestamp"]).reset_index(drop=True)

    weather_df["hour_timestamp"] = weather_df["timestamp"].dt.floor("H")
    traffic_df["hour_timestamp"] = traffic_df["timestamp"].dt.floor("H")

    df = pd.merge(
        traffic_df,
        weather_df.drop(columns=["timestamp"]),
        on="hour_timestamp",
        how="left"
    )
    df = df.drop(columns=["hour_timestamp"])

    df["has_event"] = 0
    df["event_type"] = 0
    df["event_severity"] = 0

    for _, event in event_df.iterrows():
        mask = (
            (df["road_id"] == event["road_id"]) &
            (df["timestamp"] >= event["start_time"]) &
            (df["timestamp"] <= event["end_time"])
        )
        df.loc[mask, "has_event"] = 1
        df.loc[mask, "event_type"] = event["event_type"]
        df.loc[mask, "event_severity"] = event["severity"]

    return df


def create_sequences(df, history_len=12, pred_len=3):
    feature_cols = [
        "speed", "flow", "occupancy",
        "hour", "minute", "weekday", "is_weekend",
        "morning_peak", "evening_peak", "day_of_year", "month",
        "temperature", "rainfall", "visibility", "weather_type",
        "has_event", "event_type", "event_severity"
    ]

    sequences = []
    targets = []
    road_ids = []
    timestamps = []

    for road_id in range(NUM_ROADS):
        road_data = df[df["road_id"] == road_id].sort_values("timestamp")
        values = road_data[feature_cols].values
        target_values = road_data["congestion_index"].values
        time_values = road_data["timestamp"].values

        for i in range(len(road_data) - history_len - pred_len + 1):
            seq = values[i:i + history_len]
            target = target_values[i + history_len:i + history_len + pred_len]

            sequences.append(seq)
            targets.append(target)
            road_ids.append(road_id)
            timestamps.append(time_values[i + history_len])

    return np.array(sequences), np.array(targets), np.array(road_ids), np.array(timestamps)


if __name__ == "__main__":
    start_date = datetime(2024, 1, 1)
    print("Generating traffic data...")
    traffic_df = generate_traffic_data(start_date, days=30)
    print(f"Traffic data shape: {traffic_df.shape}")

    print("Generating weather data...")
    weather_df = generate_weather_data(start_date, days=30)
    print(f"Weather data shape: {weather_df.shape}")

    print("Generating event data...")
    event_df = generate_event_data(start_date, days=30)
    print(f"Event data shape: {event_df.shape}")

    print("Merging data...")
    merged_df = merge_data(traffic_df, weather_df, event_df)
    print(f"Merged data shape: {merged_df.shape}")

    os.makedirs(DATA_DIR, exist_ok=True)
    merged_df.to_pickle(os.path.join(DATA_DIR, "traffic_data.pkl"))
    print(f"Saved merged data to {os.path.join(DATA_DIR, 'traffic_data.pkl')}")

    print("Creating sequences...")
    sequences, targets, road_ids, timestamps = create_sequences(merged_df)
    print(f"Sequences shape: {sequences.shape}")
    print(f"Targets shape: {targets.shape}")

    np.save(os.path.join(DATA_DIR, "sequences.npy"), sequences)
    np.save(os.path.join(DATA_DIR, "targets.npy"), targets)
    np.save(os.path.join(DATA_DIR, "road_ids.npy"), road_ids)
    np.save(os.path.join(DATA_DIR, "timestamps.npy"), timestamps)
    print("Saved sequence data.")
