import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import networkx as nx
import sys
import os
from datetime import datetime
from collections import OrderedDict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NUM_ROADS, PRED_HORIZONS, VIS_DIR, CONGESTION_MIN, CONGESTION_MAX
from models.graph_builder import build_adjacency_matrix


class TileCache:
    def __init__(self, max_size=100):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()


class TileBasedHeatmap:
    def __init__(self, data, tile_size=64, levels=5, cmap=None):
        self.data = data
        self.tile_size = tile_size
        self.levels = levels
        self.cmap = cmap if cmap else self._create_traffic_cmap()
        self.norm = mcolors.Normalize(vmin=CONGESTION_MIN, vmax=CONGESTION_MAX)
        self.cache = TileCache(max_size=200)

        self.n_rows, self.n_cols = data.shape
        self.n_tiles_x = int(np.ceil(self.n_cols / tile_size))
        self.n_tiles_y = int(np.ceil(self.n_rows / tile_size))

        self._build_pyramid()

    def _create_traffic_cmap(self):
        colors = [
            "#00ff00",
            "#7fff00",
            "#ffff00",
            "#ffcc00",
            "#ff9900",
            "#ff6600",
            "#ff3300",
            "#cc0000",
            "#990000",
            "#660000",
        ]
        return mcolors.LinearSegmentedColormap.from_list("traffic", colors, N=256)

    def _build_pyramid(self):
        self.pyramid = [self.data]
        current = self.data
        for level in range(1, self.levels):
            scale = 2 ** level
            new_rows = max(1, self.n_rows // scale)
            new_cols = max(1, self.n_cols // scale)

            if current.shape[0] < 2 or current.shape[1] < 2:
                break

            downsampled = np.zeros((new_rows, new_cols))
            for i in range(new_rows):
                for j in range(new_cols):
                    src_i_start = i * scale
                    src_i_end = min((i + 1) * scale, current.shape[0])
                    src_j_start = j * scale
                    src_j_end = min((j + 1) * scale, current.shape[1])
                    downsampled[i, j] = np.mean(current[src_i_start:src_i_end, src_j_start:src_j_end])

            self.pyramid.append(downsampled)
            current = downsampled

    def get_tile(self, level, tile_y, tile_x):
        key = (level, tile_y, tile_x)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        if level >= len(self.pyramid):
            level = len(self.pyramid) - 1

        data = self.pyramid[level]
        scale = 2 ** level
        tile_h = min(self.tile_size, data.shape[0] - tile_y * self.tile_size)
        tile_w = min(self.tile_size, data.shape[1] - tile_x * self.tile_size)

        if tile_h <= 0 or tile_w <= 0:
            tile = np.zeros((self.tile_size, self.tile_size, 4), dtype=np.uint8)
        else:
            y_start = tile_y * self.tile_size
            y_end = y_start + tile_h
            x_start = tile_x * self.tile_size
            x_end = x_start + tile_w

            tile_data = data[y_start:y_end, x_start:x_end]
            rgba = self.cmap(self.norm(tile_data))
            rgba = (rgba * 255).astype(np.uint8)

            tile = np.zeros((self.tile_size, self.tile_size, 4), dtype=np.uint8)
            tile[:tile_h, :tile_w] = rgba

        self.cache.set(key, tile)
        return tile

    def render_heatmap(self, ax, target_level=None):
        if target_level is None:
            target_level = min(2, len(self.pyramid) - 1)

        data = self.pyramid[target_level]
        im = ax.imshow(data, cmap=self.cmap, norm=self.norm, aspect="auto", origin="lower")
        return im

    def get_visible_tiles(self, view_y_range, view_x_range, level):
        tiles = []
        y_start, y_end = view_y_range
        x_start, x_end = view_x_range

        tile_y_start = max(0, int(y_start // self.tile_size))
        tile_y_end = min(self.n_tiles_y, int(np.ceil(y_end / self.tile_size)) + 1)
        tile_x_start = max(0, int(x_start // self.tile_size))
        tile_x_end = min(self.n_tiles_x, int(np.ceil(x_end / self.tile_size)) + 1)

        for ty in range(tile_y_start, tile_y_end):
            for tx in range(tile_x_start, tile_x_end):
                tile = self.get_tile(level, ty, tx)
                tiles.append((ty, tx, tile))

        return tiles


class TrafficVisualizer:
    def __init__(self):
        self.cmap = mcolors.LinearSegmentedColormap.from_list(
            "traffic",
            ["#00ff00", "#7fff00", "#ffff00", "#ffcc00", "#ff9900", "#ff6600", "#ff3300", "#cc0000", "#990000"],
            N=256
        )
        self.norm = mcolors.Normalize(vmin=CONGESTION_MIN, vmax=CONGESTION_MAX)
        self.congestion_labels = [
            "Extremely Smooth",
            "Very Smooth",
            "Smooth",
            "Minor",
            "Moderate",
            "Moderate Heavy",
            "Heavy",
            "Very Heavy",
            "Severe",
            "Extremely Severe"
        ]

    def _prepare_heatmap_data(self, predictions, road_ids, timestamps, horizon_idx):
        unique_times = sorted(list(set(timestamps)))
        n_times = len(unique_times)
        n_roads = NUM_ROADS

        heatmap_data = np.zeros((n_roads, n_times))

        for i, t in enumerate(unique_times):
            mask = timestamps == t
            roads = road_ids[mask]
            preds = predictions[mask, horizon_idx]
            for r, p in zip(roads, preds):
                heatmap_data[int(r), i] = p

        return heatmap_data, unique_times

    def plot_congestion_heatmap(self, predictions, road_ids, timestamps, horizon_idx=0, save_path=None,
                                 use_tiled=True, tile_size=64):
        horizon = PRED_HORIZONS[horizon_idx]
        heatmap_data, unique_times = self._prepare_heatmap_data(predictions, road_ids, timestamps, horizon_idx)

        fig, ax = plt.subplots(figsize=(15, 8))

        if use_tiled:
            tile_heatmap = TileBasedHeatmap(heatmap_data, tile_size=tile_size)
            im = tile_heatmap.render_heatmap(ax)
            print(f"Tiled heatmap: {tile_heatmap.n_tiles_y}x{tile_heatmap.n_tiles_x} tiles, "
                  f"{len(tile_heatmap.pyramid)} pyramid levels")
        else:
            im = ax.imshow(heatmap_data, aspect="auto", cmap=self.cmap, norm=self.norm, origin="lower")

        ax.set_xlabel("Time")
        ax.set_ylabel("Road ID")
        ax.set_title(f"Traffic Congestion Heatmap - {horizon}min Prediction")

        time_ticks = np.linspace(0, len(unique_times) - 1, min(10, len(unique_times))).astype(int)
        ax.set_xticks(time_ticks)
        ax.set_xticklabels([unique_times[i].strftime("%H:%M") for i in time_ticks], rotation=45, ha="right")

        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Congestion Index")
        tick_positions = np.linspace(CONGESTION_MIN, CONGESTION_MAX, 10)
        cbar.set_ticks(tick_positions)
        cbar.set_ticklabels(self.congestion_labels)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Saved heatmap to {save_path}")

        plt.close()
        return fig

    def plot_road_network(self, predictions, road_ids, timestamp_idx=0, horizon_idx=0, save_path=None):
        horizon = PRED_HORIZONS[horizon_idx]
        adj = build_adjacency_matrix()
        G = nx.from_numpy_array(adj, create_using=nx.DiGraph)

        unique_times = sorted(list(set(timestamps)))
        t = unique_times[min(timestamp_idx, len(unique_times) - 1)]

        t_mask = timestamps == t
        preds_at_t = predictions[t_mask, horizon_idx]
        roads_at_t = road_ids[t_mask]

        node_colors = []
        for node in G.nodes():
            r_mask = roads_at_t == node
            if np.any(r_mask):
                node_colors.append(preds_at_t[r_mask][0])
            else:
                node_colors.append(CONGESTION_MIN)

        pos = nx.spring_layout(G, seed=42)

        fig, ax = plt.subplots(figsize=(12, 10))

        nx.draw_networkx_nodes(
            G, pos,
            node_color=node_colors,
            cmap=self.cmap,
            vmin=CONGESTION_MIN, vmax=CONGESTION_MAX,
            node_size=500,
            ax=ax
        )

        nx.draw_networkx_edges(G, pos, alpha=0.3, ax=ax, arrowstyle="->", arrowsize=15)
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold", ax=ax)

        sm = plt.cm.ScalarMappable(cmap=self.cmap, norm=self.norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label("Congestion Index")
        tick_positions = np.linspace(CONGESTION_MIN, CONGESTION_MAX, 10)
        cbar.set_ticks(tick_positions)
        cbar.set_ticklabels(self.congestion_labels)

        ax.set_title(f"Road Network Congestion - {t.strftime('%Y-%m-%d %H:%M')}\n{horizon}min Prediction")
        ax.axis("off")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Saved network plot to {save_path}")

        plt.close()
        return fig

    def plot_prediction_comparison(self, y_true, y_pred, road_ids, horizon_idx=0, road_id=0, save_path=None):
        horizon = PRED_HORIZONS[horizon_idx]

        mask = road_ids == road_id
        y_true_road = y_true[mask, horizon_idx]
        y_pred_road = y_pred[mask, horizon_idx]

        fig, ax = plt.subplots(figsize=(15, 6))

        x = np.arange(len(y_true_road))
        ax.plot(x, y_true_road, label="Ground Truth", color="#1f77b4", linewidth=2)
        ax.plot(x, y_pred_road, label="Prediction", color="#ff7f0e", linewidth=2, alpha=0.8)

        level_ranges = [
            (0, 2, "green", "Smooth"),
            (2, 4, "yellow", "Minor"),
            (4, 6, "orange", "Moderate"),
            (6, 8, "red", "Heavy"),
            (8, 10, "darkred", "Severe"),
        ]
        for start, end, color, label in level_ranges:
            ax.fill_between(x, start, end, alpha=0.1, color=color, label=label)

        ax.set_xlabel("Time Step")
        ax.set_ylabel("Congestion Index")
        ax.set_title(f"Road {road_id} - {horizon}min Prediction vs Ground Truth")
        ax.set_ylim([CONGESTION_MIN - 0.5, CONGESTION_MAX + 0.5])
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Saved comparison plot to {save_path}")

        plt.close()
        return fig

    def plot_horizon_comparison(self, predictions, road_ids, timestamps, road_id=0, save_path=None):
        mask = road_ids == road_id
        unique_times = sorted(list(set(timestamps[mask])))

        preds_by_horizon = []
        for h_idx, horizon in enumerate(PRED_HORIZONS):
            horizon_preds = []
            for t in unique_times:
                t_mask = (timestamps == t) & mask
                if np.any(t_mask):
                    horizon_preds.append(predictions[t_mask, h_idx][0])
                else:
                    horizon_preds.append(np.nan)
            preds_by_horizon.append(horizon_preds)

        fig, ax = plt.subplots(figsize=(15, 6))

        colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
        for h_idx, horizon in enumerate(PRED_HORIZONS):
            ax.plot(unique_times, preds_by_horizon[h_idx],
                    label=f"{horizon}min Prediction",
                    color=colors[h_idx],
                    linewidth=2)

        ax.set_xlabel("Time")
        ax.set_ylabel("Congestion Index")
        ax.set_title(f"Road {road_id} - Multi-Horizon Predictions")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim([CONGESTION_MIN - 0.5, CONGESTION_MAX + 0.5])

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Saved horizon comparison plot to {save_path}")

        plt.close()
        return fig

    def plot_model_comparison(self, lgb_preds, gnn_preds, fused_preds, y_true, road_ids,
                              horizon_idx=0, road_id=0, save_path=None):
        horizon = PRED_HORIZONS[horizon_idx]
        mask = road_ids == road_id

        fig, ax = plt.subplots(figsize=(15, 6))

        x = np.arange(len(y_true[mask, horizon_idx]))
        ax.plot(x, y_true[mask, horizon_idx], label="Ground Truth", color="black", linewidth=2, linestyle="--")
        ax.plot(x, lgb_preds[mask, horizon_idx], label="LightGBM", color="#1f77b4", linewidth=1.5, alpha=0.8)
        ax.plot(x, gnn_preds[mask, horizon_idx], label="GNN", color="#ff7f0e", linewidth=1.5, alpha=0.8)
        ax.plot(x, fused_preds[mask, horizon_idx], label="Fusion", color="#2ca02c", linewidth=2)

        ax.set_xlabel("Time Step")
        ax.set_ylabel("Congestion Index")
        ax.set_title(f"Road {road_id} - Model Comparison ({horizon}min)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim([CONGESTION_MIN - 0.5, CONGESTION_MAX + 0.5])

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Saved model comparison plot to {save_path}")

        plt.close()
        return fig

    def generate_tiled_heatmap_pyramid(self, predictions, road_ids, timestamps, output_dir, tile_size=256):
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print("\n" + "=" * 50)
        print("Generating Tiled Heatmap Pyramid...")
        print("=" * 50)

        for h_idx in range(len(PRED_HORIZONS)):
            horizon = PRED_HORIZONS[h_idx]
            heatmap_data, unique_times = self._prepare_heatmap_data(predictions, road_ids, timestamps, h_idx)

            tile_heatmap = TileBasedHeatmap(heatmap_data, tile_size=tile_size)

            horizon_dir = os.path.join(output_dir, f"heatmap_{horizon}min_{timestamp}")
            os.makedirs(horizon_dir, exist_ok=True)

            for level in range(len(tile_heatmap.pyramid)):
                level_dir = os.path.join(horizon_dir, f"level_{level}")
                os.makedirs(level_dir, exist_ok=True)

                n_tiles_y = max(1, int(np.ceil(tile_heatmap.pyramid[level].shape[0] / tile_size)))
                n_tiles_x = max(1, int(np.ceil(tile_heatmap.pyramid[level].shape[1] / tile_size)))

                for ty in range(n_tiles_y):
                    for tx in range(n_tiles_x):
                        tile = tile_heatmap.get_tile(level, ty, tx)
                        tile_path = os.path.join(level_dir, f"tile_{ty}_{tx}.png")
                        plt.imsave(tile_path, tile)

            print(f"  Horizon {horizon}min: {len(tile_heatmap.pyramid)} levels, "
                  f"{sum(max(1, int(np.ceil(tile_heatmap.pyramid[l].shape[0] / tile_size)) * "
                  f"max(1, int(np.ceil(tile_heatmap.pyramid[l].shape[1] / tile_size)))) "
                  f"for l in range(len(tile_heatmap.pyramid)))} total tiles")

        print("Tiled heatmap pyramid generated!")

    def generate_all_visualizations(self, predictions, y_true, road_ids, timestamps, output_dir=VIS_DIR,
                                     generate_tiles=False):
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print("\n" + "=" * 50)
        print("Generating Visualizations...")
        print("=" * 50)

        for h_idx in range(len(PRED_HORIZONS)):
            self.plot_congestion_heatmap(
                predictions, road_ids, timestamps, horizon_idx=h_idx,
                save_path=os.path.join(output_dir, f"heatmap_{PRED_HORIZONS[h_idx]}min_{timestamp}.png"),
                use_tiled=True
            )

        self.plot_road_network(
            predictions, road_ids, timestamps,
            timestamp_idx=0, horizon_idx=0,
            save_path=os.path.join(output_dir, f"network_{timestamp}.png")
        )

        sample_roads = [0, NUM_ROADS // 2, NUM_ROADS - 1]
        for road_id in sample_roads:
            if road_id < NUM_ROADS:
                for h_idx in range(len(PRED_HORIZONS)):
                    self.plot_prediction_comparison(
                        y_true, predictions, road_ids,
                        horizon_idx=h_idx, road_id=road_id,
                        save_path=os.path.join(output_dir, f"comparison_road{road_id}_{PRED_HORIZONS[h_idx]}min_{timestamp}.png")
                    )

        self.plot_horizon_comparison(
            predictions, road_ids, timestamps, road_id=0,
            save_path=os.path.join(output_dir, f"horizon_comparison_{timestamp}.png")
        )

        if generate_tiles:
            self.generate_tiled_heatmap_pyramid(
                predictions, road_ids, timestamps,
                output_dir=os.path.join(output_dir, f"tiles_{timestamp}")
            )

        print("All visualizations generated!")
