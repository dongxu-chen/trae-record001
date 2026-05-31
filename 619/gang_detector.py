import networkx as nx
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime


class GangDetector:
    def __init__(self, users_df, orders_df, devices_df, ip_records_df, addresses_df, graph_features):
        self.users_df = users_df
        self.orders_df = orders_df
        self.devices_df = devices_df
        self.ip_records_df = ip_records_df
        self.addresses_df = addresses_df
        self.graph_features = graph_features
        self.gangs = []
        self.gang_analysis = {}

    def detect_gangs(self, min_size=3, max_size=50):
        user_links = defaultdict(set)

        for user_id, gf in self.graph_features.items():
            for key in ["shared_device_users", "shared_ip_users", "shared_address_users"]:
                for linked_user in gf.get(key, []):
                    user_links[user_id].add(linked_user)
                    user_links[linked_user].add(user_id)

        visited = set()
        for user_id in user_links:
            if user_id not in visited:
                gang = self._dfs_collect(user_id, user_links, visited)
                if min_size <= len(gang) <= max_size:
                    self.gangs.append(list(gang))

        self._analyze_gangs()
        return self.gangs

    def _dfs_collect(self, start, user_links, visited):
        stack = [start]
        gang = set()
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                gang.add(node)
                for neighbor in user_links[node]:
                    if neighbor not in visited:
                        stack.append(neighbor)
        return gang

    def _analyze_gangs(self):
        for i, gang in enumerate(self.gangs):
            gang_users = self.users_df[self.users_df["user_id"].isin(gang)]
            gang_orders = self.orders_df[self.orders_df["user_id"].isin(gang)]

            device_set = set()
            ip_set = set()
            addr_set = set()

            for user_id in gang:
                user_devices = self.devices_df[self.devices_df["user_id"] == user_id]["device_hash"].unique()
                user_ips = self.ip_records_df[self.ip_records_df["user_id"] == user_id]["ip_address"].unique()
                user_addrs = self.addresses_df[self.addresses_df["user_id"] == user_id]["full_address"].unique()
                device_set.update(user_devices)
                ip_set.update(user_ips)
                addr_set.update(user_addrs)

            shared_devices = self._count_shared_resources(gang, "device")
            shared_ips = self._count_shared_resources(gang, "ip")
            shared_addrs = self._count_shared_resources(gang, "address")

            avg_score = np.mean([
                self.graph_features.get(u, {}).get("total_linked_users", 0) for u in gang
            ]) if gang else 0

            fraud_ratio = gang_users["is_fraud"].mean() if len(gang_users) > 0 else 0

            order_dates = pd.to_datetime(gang_orders["order_time"])
            if len(order_dates) > 1:
                date_range = (order_dates.max() - order_dates.min()).days
                order_density = len(gang_orders) / max(date_range, 1)
            else:
                date_range = 0
                order_density = len(gang_orders)

            same_product_ratio = 0
            if len(gang_orders) > 0:
                product_counts = gang_orders["product_name"].value_counts()
                same_product_ratio = product_counts.max() / len(gang_orders) if len(product_counts) > 0 else 0

            gang_score = self._calculate_gang_score(
                len(gang), fraud_ratio, len(shared_devices),
                len(shared_ips), len(shared_addrs), order_density, same_product_ratio
            )

            modus_operandi = self._identify_modus_operandi(
                shared_devices, shared_ips, shared_addrs,
                order_density, same_product_ratio, gang_users
            )

            self.gang_analysis[f"gang_{i+1}"] = {
                "gang_id": i + 1,
                "members": gang,
                "member_count": len(gang),
                "fraud_ratio": fraud_ratio,
                "fraud_count": (gang_users["is_fraud"] == True).sum(),
                "normal_count": (gang_users["is_fraud"] == False).sum(),
                "total_orders": len(gang_orders),
                "total_amount": round(gang_orders["amount"].sum(), 2) if len(gang_orders) > 0 else 0,
                "avg_order_amount": round(gang_orders["amount"].mean(), 2) if len(gang_orders) > 0 else 0,
                "device_count": len(device_set),
                "ip_count": len(ip_set),
                "address_count": len(addr_set),
                "shared_device_count": len(shared_devices),
                "shared_ip_count": len(shared_ips),
                "shared_address_count": len(shared_addrs),
                "avg_linked_users": round(avg_score, 1),
                "order_density": round(order_density, 2),
                "same_product_ratio": round(same_product_ratio, 2),
                "date_range_days": date_range,
                "gang_score": gang_score,
                "risk_level": self._get_gang_risk_level(gang_score),
                "modus_operandi": modus_operandi,
                "key_members": self._identify_key_members(gang),
                "first_seen": order_dates.min().strftime("%Y-%m-%d") if len(order_dates) > 0 else None,
                "last_seen": order_dates.max().strftime("%Y-%m-%d") if len(order_dates) > 0 else None,
            }

    def _count_shared_resources(self, gang, resource_type):
        resource_users = defaultdict(list)
        for user_id in gang:
            if resource_type == "device":
                resources = self.devices_df[self.devices_df["user_id"] == user_id]["device_hash"].unique()
            elif resource_type == "ip":
                resources = self.ip_records_df[self.ip_records_df["user_id"] == user_id]["ip_address"].unique()
            else:
                resources = self.addresses_df[self.addresses_df["user_id"] == user_id]["full_address"].unique()
            for r in resources:
                resource_users[r].append(user_id)
        return {r: users for r, users in resource_users.items() if len(users) > 1}

    def _calculate_gang_score(self, size, fraud_ratio, shared_dev, shared_ip, shared_addr, density, product_ratio):
        score = 0
        score += min(size * 5, 25)
        score += fraud_ratio * 30
        score += min(shared_dev * 5, 15)
        score += min(shared_ip * 4, 12)
        score += min(shared_addr * 6, 18)
        score += min(density * 2, 15)
        score += product_ratio * 20
        return min(score, 100)

    def _get_gang_risk_level(self, score):
        if score >= 70:
            return "🔴 高危团伙"
        elif score >= 45:
            return "🟠 中危团伙"
        elif score >= 25:
            return "🟡 低危团伙"
        else:
            return "🟢 正常群体"

    def _identify_modus_operandi(self, shared_dev, shared_ip, shared_addr, density, product_ratio, gang_users):
        mo = []

        if len(shared_dev) >= 2:
            mo.append("多账号共用设备")
        elif len(shared_dev) == 1:
            mo.append("设备关联")

        if len(shared_ip) >= 3:
            mo.append("IP高度集中（机房/VPN）")
        elif len(shared_ip) >= 1:
            mo.append("IP关联")

        if len(shared_addr) >= 2:
            mo.append("收货地址高度集中")
        elif len(shared_addr) == 1:
            mo.append("同一收货地址")

        if density >= 10:
            mo.append("爆发式下单")
        elif density >= 3:
            mo.append("高频下单")

        if product_ratio >= 0.7:
            mo.append("集中刷单一商品")
        elif product_ratio >= 0.4:
            mo.append("集中刷单类商品")

        new_accounts = gang_users[gang_users["account_age_days"] < 60].shape[0]
        if new_accounts / len(gang_users) >= 0.6:
            mo.append("新账号军团")

        return mo

    def _identify_key_members(self, gang, top_n=3):
        member_scores = {}
        for user_id in gang:
            gf = self.graph_features.get(user_id, {})
            score = (
                gf.get("shared_device_count", 0) * 3 +
                gf.get("shared_ip_count", 0) * 2 +
                gf.get("shared_address_count", 0) * 4 +
                gf.get("total_linked_users", 0)
            )
            member_scores[user_id] = score

        sorted_members = sorted(member_scores.items(), key=lambda x: x[1], reverse=True)
        return [u for u, s in sorted_members[:top_n]]

    def get_gang_network_data(self, gang_id):
        gang_key = f"gang_{gang_id}"
        if gang_key not in self.gang_analysis:
            return None

        gang = self.gang_analysis[gang_key]
        members = gang["members"]

        edges = []
        for i, u1 in enumerate(members):
            for u2 in members[i+1:]:
                gf1 = self.graph_features.get(u1, {})
                shared = False
                rel_type = []
                if u2 in gf1.get("shared_device_users", []):
                    shared = True
                    rel_type.append("共享设备")
                if u2 in gf1.get("shared_ip_users", []):
                    shared = True
                    rel_type.append("共享IP")
                if u2 in gf1.get("shared_address_users", []):
                    shared = True
                    rel_type.append("共享地址")
                if shared:
                    edges.append((u1, u2, ", ".join(rel_type)))

        return {
            "members": members,
            "edges": edges,
            "analysis": gang
        }

    def get_gang_summary(self):
        return list(self.gang_analysis.values())
