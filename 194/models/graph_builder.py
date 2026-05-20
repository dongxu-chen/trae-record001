import numpy as np
import dgl
import torch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NUM_ROADS, RANDOM_SEED

np.random.seed(RANDOM_SEED)


def build_directed_road_network(one_way_ratio=0.3):
    num_nodes = NUM_ROADS
    grid_size = int(np.ceil(np.sqrt(num_nodes)))

    src = []
    dst = []
    edge_weights = []
    edge_directions = []
    edge_capacities = []

    roads = []
    for i in range(num_nodes):
        row = i // grid_size
        col = i % grid_size

        if col < grid_size - 1 and (i + 1) < num_nodes:
            roads.append((i, i + 1, "horizontal"))
        if row < grid_size - 1 and (i + grid_size) < num_nodes:
            roads.append((i, i + grid_size, "vertical"))

    for u, v, road_type in roads:
        is_one_way = np.random.random() < one_way_ratio
        capacity = np.random.uniform(500, 2000)

        if is_one_way:
            direction = np.random.choice([0, 1])
            if direction == 0:
                src.append(u)
                dst.append(v)
                edge_weights.append(1.0)
                edge_directions.append(1)
                edge_capacities.append(capacity)
            else:
                src.append(v)
                dst.append(u)
                edge_weights.append(1.0)
                edge_directions.append(-1)
                edge_capacities.append(capacity)
        else:
            src.append(u)
            dst.append(v)
            edge_weights.append(1.0)
            edge_directions.append(1)
            edge_capacities.append(capacity)

            src.append(v)
            dst.append(u)
            edge_weights.append(1.0)
            edge_directions.append(1)
            edge_capacities.append(capacity)

    src = torch.tensor(src, dtype=torch.long)
    dst = torch.tensor(dst, dtype=torch.long)
    edge_weights = torch.tensor(edge_weights, dtype=torch.float32)
    edge_directions = torch.tensor(edge_directions, dtype=torch.float32)
    edge_capacities = torch.tensor(edge_capacities, dtype=torch.float32)

    g = dgl.graph((src, dst), num_nodes=num_nodes)
    g.edata["weight"] = edge_weights
    g.edata["direction"] = edge_directions
    g.edata["capacity"] = edge_capacities

    self_src = torch.arange(num_nodes, dtype=torch.long)
    self_dst = torch.arange(num_nodes, dtype=torch.long)
    self_weights = torch.ones(num_nodes, dtype=torch.float32)
    self_directions = torch.zeros(num_nodes, dtype=torch.float32)
    self_capacities = torch.full((num_nodes,), float("inf"), dtype=torch.float32)

    g.add_edges(self_src, self_dst, {
        "weight": self_weights,
        "direction": self_directions,
        "capacity": self_capacities
    })

    return g


def build_road_network():
    return build_directed_road_network()


def build_adjacency_matrix(num_nodes=None):
    if num_nodes is None:
        num_nodes = NUM_ROADS

    grid_size = int(np.ceil(np.sqrt(num_nodes)))
    adj = np.zeros((num_nodes, num_nodes), dtype=np.float32)

    for i in range(num_nodes):
        row = i // grid_size
        col = i % grid_size

        neighbors = []
        if col > 0:
            neighbors.append(i - 1)
        if col < grid_size - 1 and (i + 1) < num_nodes:
            neighbors.append(i + 1)
        if row > 0:
            neighbors.append(i - grid_size)
        if row < grid_size - 1 and (i + grid_size) < num_nodes:
            neighbors.append(i + grid_size)

        for neighbor in neighbors:
            adj[i, neighbor] = 1.0

    adj = adj + np.eye(num_nodes)
    return adj


def normalize_adj(adj):
    rowsum = np.array(adj.sum(1))
    d_inv_sqrt = np.power(rowsum, -0.5).flatten()
    d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.0
    d_mat_inv_sqrt = np.diag(d_inv_sqrt)
    return adj.dot(d_mat_inv_sqrt).transpose().dot(d_mat_inv_sqrt)


if __name__ == "__main__":
    print("Building road network graph...")
    g = build_road_network()
    print(f"Graph: {g}")
    print(f"Number of nodes: {g.num_nodes()}")
    print(f"Number of edges: {g.num_edges()}")

    adj = build_adjacency_matrix()
    print(f"Adjacency matrix shape: {adj.shape}")
    print(f"Adjacency matrix density: {adj.sum() / (adj.shape[0] * adj.shape[1]):.4f}")

    norm_adj = normalize_adj(adj)
    print(f"Normalized adjacency matrix shape: {norm_adj.shape}")
