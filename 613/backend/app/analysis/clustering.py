import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import hstack, csr_matrix
from collections import defaultdict
import hashlib

from app.models.alert import Alert, AlertCluster


class AlertClustering:
    def __init__(
        self,
        eps_time: float = 300.0,
        min_samples: int = 5,
        service_weight: float = 0.3,
        endpoint_weight: float = 0.2,
        instance_weight: float = 0.15,
        message_weight: float = 0.25,
        time_weight: float = 0.1,
    ):
        self.eps_time = eps_time
        self.min_samples = min_samples
        self.service_weight = service_weight
        self.endpoint_weight = endpoint_weight
        self.instance_weight = instance_weight
        self.message_weight = message_weight
        self.time_weight = time_weight

    def _extract_features(self, alerts: List[Alert]) -> pd.DataFrame:
        data = []
        for alert in alerts:
            data.append({
                "id": alert.id,
                "rule_name": alert.rule_name,
                "service": alert.service,
                "scope": alert.scope,
                "priority": alert.priority,
                "start_time": alert.start_time,
                "message": alert.alarm_message,
                "endpoint": alert.endpoint_name or "",
                "instance": alert.service_instance or "",
            })
        return pd.DataFrame(data)

    def _encode_categorical_features(
        self, df: pd.DataFrame
    ) -> csr_matrix:
        categorical_cols = ["service", "endpoint", "instance"]
        encoder = OneHotEncoder(
            sparse_output=True, handle_unknown="ignore", min_frequency=2
        )

        features = []
        for col in categorical_cols:
            col_data = df[col].fillna("").astype(str)
            encoded = encoder.fit_transform(col_data.values.reshape(-1, 1))

            weight = {
                "service": self.service_weight,
                "endpoint": self.endpoint_weight,
                "instance": self.instance_weight,
            }.get(col, 1.0)

            features.append(encoded * weight)

        if features:
            return hstack(features)
        return csr_matrix((len(df), 0))

    def _encode_text_features(
        self, df: pd.DataFrame, max_features: int = 100
    ) -> csr_matrix:
        messages = df["message"].fillna("").astype(str)

        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=max_features,
            ngram_range=(1, 2),
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(messages)
            return tfidf_matrix * self.message_weight
        except Exception:
            return csr_matrix((len(df), 0))

    def _encode_time_features(
        self, df: pd.DataFrame
    ) -> np.ndarray:
        times = df["start_time"].values / 1000.0
        time_diff = times - times.min()

        scaler = StandardScaler()
        time_scaled = scaler.fit_transform(time_diff.reshape(-1, 1))

        return time_scaled * self.time_weight

    def _multidimensional_clustering(
        self, df: pd.DataFrame, rule_name: str
    ) -> Dict[int, List[str]]:
        rule_df = df[df["rule_name"] == rule_name].copy()
        if len(rule_df) < self.min_samples:
            return {}

        rule_df = rule_df.reset_index(drop=True)

        cat_features = self._encode_categorical_features(rule_df)
        text_features = self._encode_text_features(rule_df)
        time_features = self._encode_time_features(rule_df)

        all_features = []
        if cat_features.shape[1] > 0:
            all_features.append(cat_features)
        if text_features.shape[1] > 0:
            all_features.append(text_features)
        if time_features.shape[1] > 0:
            all_features.append(csr_matrix(time_features))

        if not all_features:
            return self._time_only_clustering(rule_df)

        combined_features = hstack(all_features)

        if combined_features.shape[1] > 50:
            svd = TruncatedSVD(n_components=min(50, combined_features.shape[1] - 1))
            combined_features = svd.fit_transform(combined_features)
        else:
            combined_features = combined_features.toarray()

        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(combined_features)

        eps = self._estimate_optimal_eps(features_scaled)

        dbscan = DBSCAN(eps=eps, min_samples=self.min_samples, metric="euclidean")
        labels = dbscan.fit_predict(features_scaled)

        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:
                alert_id = rule_df.iloc[idx]["id"]
                clusters[label].append(alert_id)

        return dict(clusters)

    def _time_only_clustering(
        self, rule_df: pd.DataFrame
    ) -> Dict[int, List[str]]:
        times = rule_df["start_time"].values.reshape(-1, 1) / 1000.0
        scaler = StandardScaler()
        times_scaled = scaler.fit_transform(times)

        eps_scaled = self.eps_time / (times.std() if times.std() > 0 else 1)
        dbscan = DBSCAN(eps=max(eps_scaled, 0.1), min_samples=self.min_samples)
        labels = dbscan.fit_predict(times_scaled)

        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:
                alert_id = rule_df.iloc[idx]["id"]
                clusters[label].append(alert_id)

        return dict(clusters)

    def _estimate_optimal_eps(
        self, features: np.ndarray, k: int = None
    ) -> float:
        from sklearn.neighbors import NearestNeighbors

        if k is None:
            k = self.min_samples

        if len(features) < k:
            return 0.5

        nn = NearestNeighbors(n_neighbors=k)
        nn.fit(features)
        distances, _ = nn.kneighbors(features)

        k_distances = np.sort(distances[:, -1])

        second_derivative = np.diff(np.diff(k_distances))
        if len(second_derivative) > 0:
            elbow_idx = np.argmax(second_derivative) + 2
            eps = k_distances[min(elbow_idx, len(k_distances) - 1)]
        else:
            eps = np.percentile(k_distances, 75)

        return max(eps, 0.1)

    def _time_based_clustering(
        self, df: pd.DataFrame, rule_name: str
    ) -> Dict[int, List[str]]:
        return self._multidimensional_clustering(df, rule_name)

    def _content_similarity(
        self, alerts: List[Alert], threshold: float = 0.7
    ) -> List[Tuple[str, str, float]]:
        if len(alerts) < 2:
            return []

        messages = [alert.alarm_message for alert in alerts]
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(messages)
        similarity_matrix = cosine_similarity(tfidf_matrix)

        similar_pairs = []
        for i in range(len(alerts)):
            for j in range(i + 1, len(alerts)):
                sim = similarity_matrix[i][j]
                if sim >= threshold:
                    similar_pairs.append((alerts[i].id, alerts[j].id, float(sim)))

        return similar_pairs

    def _generate_cluster_id(self, rule_name: str, cluster_idx: int) -> str:
        raw = f"{rule_name}_{cluster_idx}_{datetime.now().timestamp()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _analyze_pattern(
        self, alerts: List[Alert]
    ) -> Dict[str, Any]:
        if not alerts:
            return {}

        df = self._extract_features(alerts)

        time_intervals = np.diff(sorted(df["start_time"].values)) / 1000.0
        avg_interval = float(np.mean(time_intervals)) if len(time_intervals) > 0 else 0

        service_counts = df["service"].value_counts().to_dict()
        priority_counts = df["priority"].value_counts().to_dict()
        scope_counts = df["scope"].value_counts().to_dict()
        endpoint_counts = df["endpoint"].fillna("").value_counts().to_dict()
        instance_counts = df["instance"].fillna("").value_counts().to_dict()

        peak_hours = defaultdict(int)
        for ts in df["start_time"].values:
            hour = datetime.fromtimestamp(ts / 1000).hour
            peak_hours[hour] += 1

        peak_hour = max(peak_hours.items(), key=lambda x: x[1])[0] if peak_hours else 0

        unique_services = df["service"].nunique()
        unique_endpoints = df["endpoint"].fillna("").nunique()
        unique_instances = df["instance"].fillna("").nunique()

        service_concentration = max(service_counts.values()) / len(alerts) if service_counts else 0
        endpoint_concentration = max(endpoint_counts.values()) / len(alerts) if endpoint_counts else 0

        return {
            "alert_count": len(alerts),
            "avg_interval_seconds": round(avg_interval, 2),
            "service_distribution": service_counts,
            "endpoint_distribution": endpoint_counts,
            "instance_distribution": instance_counts,
            "priority_distribution": priority_counts,
            "scope_distribution": scope_counts,
            "unique_services": unique_services,
            "unique_endpoints": unique_endpoints,
            "unique_instances": unique_instances,
            "service_concentration": round(service_concentration, 4),
            "endpoint_concentration": round(endpoint_concentration, 4),
            "peak_hour": peak_hour,
            "hourly_distribution": dict(peak_hours),
            "is_periodic": avg_interval > 0 and (
                np.std(time_intervals) / avg_interval < 0.5 if len(time_intervals) > 1 else False
            ),
            "periodicity_cv": round(
                np.std(time_intervals) / avg_interval if avg_interval > 0 and len(time_intervals) > 1 else 0,
                4,
            ),
            "duration_minutes": round(
                (df["start_time"].max() - df["start_time"].min()) / 60000, 2
            ),
            "dimensional_weights": {
                "service_weight": self.service_weight,
                "endpoint_weight": self.endpoint_weight,
                "instance_weight": self.instance_weight,
                "message_weight": self.message_weight,
                "time_weight": self.time_weight,
            },
        }

    def cluster_alerts(
        self, alerts: List[Alert]
    ) -> List[AlertCluster]:
        if not alerts:
            return []

        df = self._extract_features(alerts)
        rule_names = df["rule_name"].unique()

        alert_map = {alert.id: alert for alert in alerts}
        clusters = []

        for rule_name in rule_names:
            rule_alerts = [a for a in alerts if a.rule_name == rule_name]
            time_clusters = self._time_based_clustering(df, rule_name)

            if not time_clusters:
                if len(rule_alerts) >= self.min_samples:
                    pattern = self._analyze_pattern(rule_alerts)
                    cluster = AlertCluster(
                        cluster_id=self._generate_cluster_id(rule_name, 0),
                        rule_name=rule_name,
                        alert_count=len(rule_alerts),
                        services=list(df[df["rule_name"] == rule_name]["service"].unique()),
                        time_span={
                            "start": int(df[df["rule_name"] == rule_name]["start_time"].min()),
                            "end": int(df[df["rule_name"] == rule_name]["start_time"].max()),
                        },
                        priority_distribution=df[df["rule_name"] == rule_name]["priority"].value_counts().to_dict(),
                        sample_alerts=rule_alerts[:10],
                        pattern_features=pattern,
                    )
                    clusters.append(cluster)
                continue

            for cluster_idx, alert_ids in time_clusters.items():
                cluster_alerts = [alert_map[aid] for aid in alert_ids if aid in alert_map]
                if len(cluster_alerts) < self.min_samples:
                    continue

                pattern = self._analyze_pattern(cluster_alerts)
                cluster_df = df[df["id"].isin(alert_ids)]

                cluster = AlertCluster(
                    cluster_id=self._generate_cluster_id(rule_name, cluster_idx),
                    rule_name=rule_name,
                    alert_count=len(cluster_alerts),
                    services=list(cluster_df["service"].unique()),
                    time_span={
                        "start": int(cluster_df["start_time"].min()),
                        "end": int(cluster_df["start_time"].max()),
                    },
                    priority_distribution=cluster_df["priority"].value_counts().to_dict(),
                    sample_alerts=cluster_alerts[:10],
                    pattern_features=pattern,
                )
                clusters.append(cluster)

        return sorted(clusters, key=lambda c: c.alert_count, reverse=True)

    def find_similar_clusters(
        self, clusters: List[AlertCluster], threshold: float = 0.6
    ) -> List[Tuple[str, str, float]]:
        if len(clusters) < 2:
            return []

        texts = []
        for cluster in clusters:
            messages = " ".join([a.alarm_message for a in cluster.sample_alerts])
            text = f"{cluster.rule_name} {cluster.services} {messages}"
            texts.append(text)

        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(texts)
        similarity_matrix = cosine_similarity(tfidf_matrix)

        similar_pairs = []
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                sim = similarity_matrix[i][j]
                if sim >= threshold:
                    similar_pairs.append(
                        (clusters[i].cluster_id, clusters[j].cluster_id, float(sim))
                    )

        return similar_pairs

    def get_cluster_summary(
        self, clusters: List[AlertCluster]
    ) -> Dict[str, Any]:
        if not clusters:
            return {"total_clusters": 0}

        total_alerts = sum(c.alert_count for c in clusters)
        avg_size = total_alerts / len(clusters)

        rule_dist = defaultdict(int)
        for c in clusters:
            rule_dist[c.rule_name] += c.alert_count

        priority_dist = defaultdict(int)
        for c in clusters:
            for priority, count in c.priority_distribution.items():
                priority_dist[priority] += count

        periodic_count = sum(
            1 for c in clusters if c.pattern_features.get("is_periodic", False)
        )

        return {
            "total_clusters": len(clusters),
            "total_alerts_in_clusters": total_alerts,
            "avg_cluster_size": round(avg_size, 2),
            "max_cluster_size": max(c.alert_count for c in clusters),
            "min_cluster_size": min(c.alert_count for c in clusters),
            "rule_distribution": dict(rule_dist),
            "priority_distribution": dict(priority_dist),
            "periodic_clusters": periodic_count,
            "periodic_percentage": round(periodic_count / len(clusters) * 100, 2),
        }


alert_clustering = AlertClustering()
