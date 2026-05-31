import networkx as nx
import pandas as pd
import numpy as np
from collections import defaultdict


class GraphAnalyzer:
    def __init__(self, users_df, devices_df, ip_records_df, addresses_df, orders_df,
                 use_sampling=True, max_nodes=5000, sampling_ratio=0.3, random_seed=42):
        self.users_df = users_df
        self.devices_df = devices_df
        self.ip_records_df = ip_records_df
        self.addresses_df = addresses_df
        self.orders_df = orders_df
        self.graph = nx.Graph()
        self.communities = []
        self.user_risk_scores = {}
        self.use_sampling = use_sampling
        self.max_nodes = max_nodes
        self.sampling_ratio = sampling_ratio
        self.random_seed = random_seed
        self.sampling_stats = {}

    def build_graph(self):
        user_nodes = self._sample_users_if_needed()
        self._add_user_nodes(user_nodes)
        self._add_device_edges(user_nodes)
        self._add_ip_edges(user_nodes)
        self._add_address_edges(user_nodes)
        return self.graph

    def _sample_users_if_needed(self):
        total_users = len(self.users_df)
        if not self.use_sampling or total_users <= self.max_nodes:
            self.sampling_stats = {
                "sampled": False,
                "original_users": total_users,
                "sampled_users": total_users
            }
            return set(self.users_df["user_id"])

        np.random.seed(self.random_seed)
        n_sample = min(self.max_nodes, int(total_users * self.sampling_ratio))

        fraud_users = self.users_df[self.users_df["is_fraud"]]
        normal_users = self.users_df[~self.users_df["is_fraud"]]

        n_fraud_sample = min(len(fraud_users), int(n_sample * 0.4))
        n_normal_sample = n_sample - n_fraud_sample

        sampled_fraud = fraud_users.sample(n=min(n_fraud_sample, len(fraud_users)), random_state=self.random_seed)["user_id"].tolist()
        sampled_normal = normal_users.sample(n=min(n_normal_sample, len(normal_users)), random_state=self.random_seed)["user_id"].tolist()

        sampled = set(sampled_fraud + sampled_normal)

        self.sampling_stats = {
            "sampled": True,
            "original_users": total_users,
            "sampled_users": len(sampled),
            "sampling_ratio": self.sampling_ratio,
            "fraud_in_sample": len(sampled_fraud),
            "normal_in_sample": len(sampled_normal)
        }

        return sampled

    def _add_user_nodes(self, user_set):
        for _, row in self.users_df.iterrows():
            user_id = row["user_id"]
            if user_id in user_set:
                self.graph.add_node(
                    user_id,
                    type="user",
                    username=row["username"],
                    register_date=row["register_date"],
                    account_age_days=row["account_age_days"]
                )

    def _add_device_edges(self, user_set):
        device_users = defaultdict(list)
        for _, row in self.devices_df.iterrows():
            if row["user_id"] in user_set:
                device_users[row["device_hash"]].append(row["user_id"])

        for device_hash, users in device_users.items():
            if len(users) >= 1:
                device_node = f"device_{device_hash}"
                self.graph.add_node(device_node, type="device", device_hash=device_hash)
                for user_id in users:
                    self.graph.add_edge(user_id, device_node, relation="uses_device")

    def _add_ip_edges(self, user_set):
        ip_users = defaultdict(list)
        for _, row in self.ip_records_df.iterrows():
            if row["user_id"] in user_set:
                ip_users[row["ip_address"]].append(row["user_id"])

        for ip_address, users in ip_users.items():
            if len(users) >= 1:
                ip_node = f"ip_{ip_address}"
                self.graph.add_node(ip_node, type="ip", ip_address=ip_address)
                for user_id in users:
                    self.graph.add_edge(user_id, ip_node, relation="uses_ip")

    def _add_address_edges(self, user_set):
        addr_users = defaultdict(list)
        for _, row in self.addresses_df.iterrows():
            if row["user_id"] in user_set:
                addr_users[row["full_address"]].append(row["user_id"])

        for address, users in addr_users.items():
            if len(users) >= 1:
                addr_node = f"addr_{address}"
                self.graph.add_node(addr_node, type="address", address=address)
                for user_id in users:
                    self.graph.add_edge(user_id, addr_node, relation="ships_to")

    def detect_communities(self):
        user_nodes = set(n for n, d in self.graph.nodes(data=True) if d.get("type") == "user")
        if not user_nodes:
            self.communities = []
            return self.communities

        projection = nx.Graph()
        projection.add_nodes_from(user_nodes)

        for node, data in self.graph.nodes(data=True):
            if data.get("type") in ("device", "ip", "address"):
                neighbor_users = [n for n in self.graph.neighbors(node) if n in user_nodes]
                for i in range(len(neighbor_users)):
                    for j in range(i + 1, len(neighbor_users)):
                        if projection.has_edge(neighbor_users[i], neighbor_users[j]):
                            projection[neighbor_users[i]][neighbor_users[j]]["weight"] += 1
                        else:
                            projection.add_edge(neighbor_users[i], neighbor_users[j], weight=1)

        if len(projection.edges()) == 0:
            self.communities = []
            return self.communities

        components = list(nx.connected_components(projection))

        self.communities = []
        for comp in components:
            if len(comp) >= 2:
                self.communities.append(list(comp))

        return self.communities

    def compute_user_graph_features(self):
        features = {}
        user_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "user"]

        all_users = set(self.users_df["user_id"])
        sampled_users = set(user_nodes)
        unsampled_users = all_users - sampled_users

        for user_id in user_nodes:
            neighbors = list(self.graph.neighbors(user_id))
            device_neighbors = [n for n in neighbors if self.graph.nodes[n].get("type") == "device"]
            ip_neighbors = [n for n in neighbors if self.graph.nodes[n].get("type") == "ip"]
            addr_neighbors = [n for n in neighbors if self.graph.nodes[n].get("type") == "address"]

            shared_device_users = set()
            shared_ip_users = set()
            shared_addr_users = set()

            for dev in device_neighbors:
                for neighbor in self.graph.neighbors(dev):
                    if neighbor != user_id and self.graph.nodes[neighbor].get("type") == "user":
                        shared_device_users.add(neighbor)

            for ip in ip_neighbors:
                for neighbor in self.graph.neighbors(ip):
                    if neighbor != user_id and self.graph.nodes[neighbor].get("type") == "user":
                        shared_ip_users.add(neighbor)

            for addr in addr_neighbors:
                for neighbor in self.graph.neighbors(addr):
                    if neighbor != user_id and self.graph.nodes[neighbor].get("type") == "user":
                        shared_addr_users.add(neighbor)

            degree = self.graph.degree(user_id)
            clustering = nx.clustering(self.graph, user_id) if degree > 0 else 0

            all_linked_users = shared_device_users | shared_ip_users | shared_addr_users

            features[user_id] = {
                "shared_device_count": len(shared_device_users),
                "shared_ip_count": len(shared_ip_users),
                "shared_address_count": len(shared_addr_users),
                "total_linked_users": len(all_linked_users),
                "degree": degree,
                "clustering_coefficient": clustering,
                "device_count": len(device_neighbors),
                "ip_count": len(ip_neighbors),
                "address_count": len(addr_neighbors),
                "shared_device_users": list(shared_device_users),
                "shared_ip_users": list(shared_ip_users),
                "shared_address_users": list(shared_addr_users),
                "is_sampled": True,
            }

        for user_id in unsampled_users:
            user_devices = set(self.devices_df[self.devices_df["user_id"] == user_id]["device_hash"].tolist())
            user_ips = set(self.ip_records_df[self.ip_records_df["user_id"] == user_id]["ip_address"].tolist())
            user_addrs = set(self.addresses_df[self.addresses_df["user_id"] == user_id]["full_address"].tolist())

            device_shared = self.devices_df[
                (self.devices_df["device_hash"].isin(user_devices)) &
                (self.devices_df["user_id"] != user_id)
            ]["user_id"].unique().tolist()

            ip_shared = self.ip_records_df[
                (self.ip_records_df["ip_address"].isin(user_ips)) &
                (self.ip_records_df["user_id"] != user_id)
            ]["user_id"].unique().tolist()

            addr_shared = self.addresses_df[
                (self.addresses_df["full_address"].isin(user_addrs)) &
                (self.addresses_df["user_id"] != user_id)
            ]["user_id"].unique().tolist()

            all_linked = set(device_shared) | set(ip_shared) | set(addr_shared)

            features[user_id] = {
                "shared_device_count": len(device_shared),
                "shared_ip_count": len(ip_shared),
                "shared_address_count": len(addr_shared),
                "total_linked_users": len(all_linked),
                "degree": len(user_devices) + len(user_ips) + len(user_addrs),
                "clustering_coefficient": 0,
                "device_count": len(user_devices),
                "ip_count": len(user_ips),
                "address_count": len(user_addrs),
                "shared_device_users": device_shared,
                "shared_ip_users": ip_shared,
                "shared_address_users": addr_shared,
                "is_sampled": False,
            }

        return features

    def get_subgraph_for_user(self, user_id, depth=2):
        if not self.graph.has_node(user_id):
            return nx.Graph()
        nodes = set([user_id])
        frontier = set([user_id])
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                if self.graph.has_node(node):
                    for neighbor in self.graph.neighbors(node):
                        if neighbor not in nodes:
                            next_frontier.add(neighbor)
            nodes |= next_frontier
            frontier = next_frontier
        return self.graph.subgraph(nodes).copy()

    def get_community_stats(self):
        stats = []
        for i, community in enumerate(self.communities):
            user_rows = self.users_df[self.users_df["user_id"].isin(community)]
            order_rows = self.orders_df[self.orders_df["user_id"].isin(community)]
            stats.append({
                "community_id": i + 1,
                "member_count": len(community),
                "members": community,
                "total_orders": len(order_rows),
                "total_amount": order_rows["amount"].sum() if len(order_rows) > 0 else 0,
                "fraud_ratio": user_rows["is_fraud"].mean() if len(user_rows) > 0 else 0,
                "avg_account_age": user_rows["account_age_days"].mean() if len(user_rows) > 0 else 0,
            })
        return stats

    def get_sampling_stats(self):
        return self.sampling_stats
