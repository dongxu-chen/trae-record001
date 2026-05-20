import numpy as np
import argparse
import sys
import os
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import (
    DATA_DIR, OUTPUT_DIR, RANDOM_SEED, TEST_SIZE, VAL_SIZE,
    NUM_ROADS, HISTORY_LEN, PRED_LEN, PRED_HORIZONS
)
from data.data_generator import generate_traffic_data, generate_weather_data, generate_event_data, merge_data, create_sequences
from models.graph_builder import build_road_network
from models.fusion_model import FusionPredictor
from models.event_simulator import EventSimulator, TrafficEvent
from models.path_planner import PathPlanner
from models.traffic_broadcaster import TrafficBroadcaster
from visualization.visualizer import TrafficVisualizer

np.random.seed(RANDOM_SEED)


def load_or_generate_data():
    os.makedirs(DATA_DIR, exist_ok=True)

    seq_path = os.path.join(DATA_DIR, "sequences.npy")
    target_path = os.path.join(DATA_DIR, "targets.npy")
    road_path = os.path.join(DATA_DIR, "road_ids.npy")
    time_path = os.path.join(DATA_DIR, "timestamps.npy")

    if os.path.exists(seq_path) and os.path.exists(target_path):
        print("Loading existing data...")
        sequences = np.load(seq_path)
        targets = np.load(target_path)
        road_ids = np.load(road_path)
        timestamps = np.load(time_path, allow_pickle=True)
        print(f"Loaded sequences shape: {sequences.shape}")
        print(f"Loaded targets shape: {targets.shape}")
    else:
        print("Generating new data...")
        start_date = datetime(2024, 1, 1)

        traffic_df = generate_traffic_data(start_date, days=30)
        weather_df = generate_weather_data(start_date, days=30)
        event_df = generate_event_data(start_date, days=30)

        merged_df = merge_data(traffic_df, weather_df, event_df)
        sequences, targets, road_ids, timestamps = create_sequences(merged_df)

        np.save(seq_path, sequences)
        np.save(target_path, targets)
        np.save(road_path, road_ids)
        np.save(time_path, timestamps)

        merged_df.to_pickle(os.path.join(DATA_DIR, "traffic_data.pkl"))
        print(f"Generated sequences shape: {sequences.shape}")
        print(f"Generated targets shape: {targets.shape}")

    return sequences, targets, road_ids, timestamps


def prepare_data(sequences, targets, road_ids, timestamps):
    n_samples = sequences.shape[0]
    n_features = sequences.shape[2]

    sequences_reshaped = sequences.reshape(n_samples, -1)

    scaler = StandardScaler()
    sequences_scaled = scaler.fit_transform(sequences_reshaped)
    sequences_scaled = sequences_scaled.reshape(n_samples, HISTORY_LEN, n_features)

    unique_times = sorted(list(set(timestamps)))
    n_time_points = len(unique_times)
    time_to_idx = {t: i for i, t in enumerate(unique_times)}

    test_start_idx = int(n_time_points * (1 - TEST_SIZE))
    val_start_idx = int(n_time_points * (1 - TEST_SIZE - VAL_SIZE))

    train_mask = np.array([time_to_idx[t] < val_start_idx for t in timestamps])
    val_mask = np.array([val_start_idx <= time_to_idx[t] < test_start_idx for t in timestamps])
    test_mask = np.array([time_to_idx[t] >= test_start_idx for t in timestamps])

    X_train = sequences_scaled[train_mask]
    y_train = targets[train_mask]
    road_train = road_ids[train_mask]
    time_train = timestamps[train_mask]

    X_val = sequences_scaled[val_mask]
    y_val = targets[val_mask]
    road_val = road_ids[val_mask]
    time_val = timestamps[val_mask]

    X_test = sequences_scaled[test_mask]
    y_test = targets[test_mask]
    road_test = road_ids[test_mask]
    time_test = timestamps[test_mask]

    print(f"Train samples: {len(X_train)} ({len(X_train) / n_samples * 100:.1f}%)")
    print(f"Val samples: {len(X_val)} ({len(X_val) / n_samples * 100:.1f}%)")
    print(f"Test samples: {len(X_test)} ({len(X_test) / n_samples * 100:.1f}%)")

    return (X_train, y_train, road_train, time_train), \
           (X_val, y_val, road_val, time_val), \
           (X_test, y_test, road_test, time_test), scaler


def main():
    parser = argparse.ArgumentParser(description="Traffic Congestion Prediction")
    parser.add_argument("--mode", type=str, default="train", choices=["train", "predict", "both"],
                        help="Mode: train, predict, or both")
    parser.add_argument("--generate_data", action="store_true", help="Regenerate data")
    parser.add_argument("--generate_tiles", action="store_true", help="Generate tiled heatmap pyramid")
    parser.add_argument("--simulate_event", action="store_true", help="Run event impact simulation")
    parser.add_argument("--plan_route", action="store_true", help="Run route planning")
    parser.add_argument("--broadcast", action="store_true", help="Generate traffic broadcast")
    parser.add_argument("--start_road", type=int, default=0, help="Start road for route planning")
    parser.add_argument("--end_road", type=int, default=15, help="End road for route planning")
    args = parser.parse_args()

    if args.generate_data:
        for f in ["sequences.npy", "targets.npy", "road_ids.npy", "timestamps.npy", "traffic_data.pkl"]:
            fp = os.path.join(DATA_DIR, f)
            if os.path.exists(fp):
                os.remove(fp)

    print("\n" + "=" * 60)
    print("TRAFFIC CONGESTION PREDICTION SYSTEM")
    print("=" * 60)
    print(f"Prediction horizons: {PRED_HORIZONS} minutes")
    print(f"Number of roads: {NUM_ROADS}")
    print(f"History length: {HISTORY_LEN} time steps")
    print(f"Prediction length: {PRED_LEN} time steps")

    print("\n1. Loading/Generating data...")
    sequences, targets, road_ids, timestamps = load_or_generate_data()

    print("\n2. Preparing data splits...")
    (X_train, y_train, road_train, time_train), \
    (X_val, y_val, road_val, time_val), \
    (X_test, y_test, road_test, time_test), scaler = prepare_data(sequences, targets, road_ids, timestamps)

    print("\n3. Building road network graph...")
    g = build_road_network()
    print(f"Graph: {g}")
    print(f"Nodes: {g.num_nodes()}, Edges: {g.num_edges()}")

    input_dim = X_train.shape[2]
    print(f"\nInput feature dimension: {input_dim}")

    print("\n4. Initializing fusion predictor...")
    predictor = FusionPredictor(gnn_input_dim=input_dim)
    predictor.set_graph(g)

    if args.mode in ["train", "both"]:
        print("\n" + "=" * 60)
        print("TRAINING PHASE")
        print("=" * 60)
        predictor.train(
            X_train, y_train, road_train,
            X_val, y_val, road_val
        )

    if args.mode in ["predict", "both"]:
        print("\n" + "=" * 60)
        print("PREDICTION PHASE")
        print("=" * 60)

        if args.mode == "predict":
            predictor.load()

        print("\nEvaluating on test set...")
        results = predictor.evaluate(X_test, y_test, road_test)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        np.save(os.path.join(OUTPUT_DIR, "test_predictions.npy"), results["predictions"]["fused"])
        np.save(os.path.join(OUTPUT_DIR, "test_targets.npy"), y_test)
        np.save(os.path.join(OUTPUT_DIR, "test_road_ids.npy"), road_test)
        np.save(os.path.join(OUTPUT_DIR, "test_timestamps.npy"), time_test)
        print(f"Saved predictions to {OUTPUT_DIR}")

        print("\n5. Generating visualizations...")
        visualizer = TrafficVisualizer()
        visualizer.generate_all_visualizations(
            results["predictions"]["fused"],
            y_test,
            road_test,
            time_test,
            generate_tiles=args.generate_tiles
        )

        sample_road = 0
        for h_idx in range(len(PRED_HORIZONS)):
            visualizer.plot_model_comparison(
                results["predictions"]["lgb"],
                results["predictions"]["gnn"],
                results["predictions"]["fused"],
                y_test, road_test,
                horizon_idx=h_idx,
                road_id=sample_road,
                save_path=os.path.join(OUTPUT_DIR, f"model_comparison_road{sample_road}_{PRED_HORIZONS[h_idx]}min.png")
            )

        if args.simulate_event:
            print("\n" + "=" * 60)
            print("EVENT IMPACT SIMULATION")
            print("=" * 60)

            simulator = EventSimulator()
            current_time = time_test[0] if len(time_test) > 0 else datetime.now()

            base_congestion = np.mean(y_test, axis=1)[:NUM_ROADS]

            test_event = TrafficEvent(
                event_type="accident",
                road_id=5,
                start_time=current_time,
                duration_minutes=90,
                severity=2
            )

            simulator.add_event(test_event)
            report, prediction = simulator.generate_event_report(test_event, base_congestion)
            print(report)

            event_report_path = os.path.join(OUTPUT_DIR, f"event_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(event_report_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Saved event report to {event_report_path}")

        if args.plan_route:
            print("\n" + "=" * 60)
            print("ROUTE PLANNING")
            print("=" * 60)

            planner = PathPlanner()
            current_time = time_test[0] if len(time_test) > 0 else datetime.now()

            predictions_reshaped = results["predictions"]["fused"][:NUM_ROADS] if len(results["predictions"]["fused"]) >= NUM_ROADS else results["predictions"]["fused"]

            guidance, route_results = planner.generate_route_guidance(
                args.start_road, args.end_road, predictions_reshaped, current_time
            )
            print(guidance)

            route_report_path = os.path.join(OUTPUT_DIR, f"route_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(route_report_path, "w", encoding="utf-8") as f:
                f.write(guidance)
            print(f"Saved route report to {route_report_path}")

        if args.broadcast:
            print("\n" + "=" * 60)
            print("TRAFFIC BROADCAST")
            print("=" * 60)

            broadcaster = TrafficBroadcaster()
            current_time = time_test[0] if len(time_test) > 0 else datetime.now()

            predictions_for_broadcast = results["predictions"]["fused"][:NUM_ROADS] if len(results["predictions"]["fused"]) >= NUM_ROADS else results["predictions"]["fused"]
            timestamps_for_broadcast = time_test[:NUM_ROADS] if len(time_test) >= NUM_ROADS else time_test
            roads_for_broadcast = road_test[:NUM_ROADS] if len(road_test) >= NUM_ROADS else road_test

            hourly_broadcast = broadcaster.generate_hourly_broadcast(
                predictions_for_broadcast, timestamps_for_broadcast, roads_for_broadcast, current_time
            )
            print(hourly_broadcast)

            voice_text = broadcaster.generate_voice_broadcast_text(
                predictions_for_broadcast, timestamps_for_broadcast, roads_for_broadcast, current_time
            )
            print("\n语音播报文本:")
            print(voice_text)

            broadcast_path = os.path.join(OUTPUT_DIR, f"broadcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            broadcaster.save_broadcast_to_file(hourly_broadcast + "\n\n" + voice_text, OUTPUT_DIR)

            notifications = broadcaster.generate_push_notification(
                predictions_for_broadcast, timestamps_for_broadcast, roads_for_broadcast,
                user_route=(args.start_road, args.end_road)
            )
            print("\nAPP推送通知:")
            for notif in notifications:
                print(f"  [{notif['priority'].upper()}] {notif['title']}: {notif['body']}")

    print("\n" + "=" * 60)
    print("PROCESS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
