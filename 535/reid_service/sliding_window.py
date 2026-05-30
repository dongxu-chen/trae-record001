from __future__ import annotations

import logging
import threading
import time
from collections import deque, OrderedDict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from config import SlidingWindowConfig
from reid_service.gallery import GalleryManager, SearchResult
from reid_service.search_engine import FaissSearchEngine

logger = logging.getLogger(__name__)


@dataclass
class WindowItem:
    item_id: str
    feature: np.ndarray
    camera_id: str
    timestamp: float
    track_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    added_time: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "feature": self.feature.tolist(),
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "track_id": self.track_id,
            "metadata": self.metadata,
            "added_time": self.added_time,
        }


@dataclass
class RealtimeMatchResult:
    query_timestamp: float
    results: list[tuple[str, float]]
    window_size: int
    processing_time_ms: float
    cache_hit: bool = False

    def to_dict(self) -> dict:
        return {
            "query_timestamp": self.query_timestamp,
            "results": [
                {"item_id": item_id, "score": round(score, 6)}
                for item_id, score in self.results
            ],
            "window_size": self.window_size,
            "processing_time_ms": round(self.processing_time_ms, 2),
            "cache_hit": self.cache_hit,
        }


@dataclass
class CacheEntry:
    query_hash: str
    results: list[tuple[str, float]]
    timestamp: float
    access_count: int = 0


class SlidingWindowEngine:
    def __init__(
        self,
        gallery_manager: GalleryManager,
        config: SlidingWindowConfig | None = None,
    ):
        self.config = config or SlidingWindowConfig()
        self.gallery_manager = gallery_manager
        self._window: deque[WindowItem] = deque(maxlen=self.config.window_size)
        self._window_index: dict[str, WindowItem] = {}
        self._lock = threading.RLock()

        self._window_index: FaissSearchEngine | None = None
        self._rebuild_index_interval: float = 5.0
        self._last_rebuild_time: float = 0.0

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._cache_lock = threading.RLock()
        self._max_cache_size: int = 1000

        self._real_time_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pending_queries: deque[tuple[np.ndarray, str, float, int]] = deque()
        self._query_results: dict[str, RealtimeMatchResult] = {}

        if self.config.enable_real_time_search:
            self._start_real_time_thread()

        self._build_window_index()

        logger.info(
            f"SlidingWindowEngine initialized: window_size={self.config.window_size}, "
            f"overlap={self.config.window_overlap}, real_time={self.config.enable_real_time_search}"
        )

    def _compute_hash(self, feature: np.ndarray) -> str:
        return hash(feature.tobytes()).to_bytes(8, "big", signed=True).hex()

    def _build_window_index(self) -> None:
        if len(self._window) == 0:
            self._window_index = None
            return

        dimension = self.config.warmup_samples or 512
        self._window_index = FaissSearchEngine(
            dimension=dimension,
            config=self.gallery_manager.search_engine.config,
        )

        features = []
        item_ids = []
        for item in self._window:
            features.append(item.feature)
            item_ids.append(item.item_id)

        if features:
            self._window_index.add_batch(np.stack(features), item_ids)

        self._last_rebuild_time = time.time()
        logger.debug(f"Rebuilt window index with {len(features)} items")

    def _maybe_rebuild_index(self) -> None:
        current_time = time.time()
        if current_time - self._last_rebuild_time > self._rebuild_index_interval:
            self._build_window_index()

    def add(self, item: WindowItem) -> None:
        with self._lock:
            if item.item_id in self._window_index:
                return

            self._window.append(item)
            self._window_index[item.item_id] = item

            if self._window_index is None:
                self._build_window_index()
            else:
                try:
                    self._window_index.add(item.feature, item.item_id)
                except Exception:
                    self._build_window_index()

            if len(self._window) > self.config.window_size:
                removed = self._window.popleft()
                self._window_index.pop(removed.item_id, None)
                try:
                    self.gallery_manager.search_engine.remove(removed.item_id)
                except Exception:
                    pass

            self._maybe_rebuild_index()

        self._clear_cache()

    def add_batch(self, items: list[WindowItem]) -> None:
        with self._lock:
            new_features = []
            new_ids = []

            for item in items:
                if item.item_id in self._window_index:
                    continue
                self._window.append(item)
                self._window_index[item.item_id] = item
                new_features.append(item.feature)
                new_ids.append(item.item_id)

            while len(self._window) > self.config.window_size:
                removed = self._window.popleft()
                self._window_index.pop(removed.item_id, None)

            if new_features:
                if self._window_index is None:
                    self._build_window_index()
                else:
                    try:
                        self._window_index.add_batch(np.stack(new_features), new_ids)
                    except Exception:
                        self._build_window_index()

            self._maybe_rebuild_index()

        self._clear_cache()

    def _get_cache(self, query_hash: str) -> CacheEntry | None:
        with self._cache_lock:
            entry = self._cache.get(query_hash)
            if entry:
                current_time = time.time()
                if current_time - entry.timestamp > self.config.cache_ttl_seconds:
                    self._cache.pop(query_hash, None)
                    return None
                entry.access_count += 1
                self._cache.move_to_end(query_hash)
                return entry
            return None

    def _put_cache(
        self,
        query_hash: str,
        results: list[tuple[str, float]],
    ) -> None:
        with self._cache_lock:
            while len(self._cache) >= self._max_cache_size:
                self._cache.popitem(last=False)
            self._cache[query_hash] = CacheEntry(
                query_hash=query_hash,
                results=results,
                timestamp=time.time(),
            )

    def _clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()

    def search(
        self,
        query_feature: np.ndarray,
        top_k: int = 10,
        use_cache: bool = True,
    ) -> RealtimeMatchResult:
        start_time = time.time()
        query_hash = self._compute_hash(query_feature)

        if use_cache:
            cached = self._get_cache(query_hash)
            if cached:
                return RealtimeMatchResult(
                    query_timestamp=start_time,
                    results=cached.results[:top_k],
                    window_size=len(self._window),
                    processing_time_ms=(time.time() - start_time) * 1000,
                    cache_hit=True,
                )

        with self._lock:
            if self._window_index is None or self._window_index.size() == 0:
                return RealtimeMatchResult(
                    query_timestamp=start_time,
                    results=[],
                    window_size=0,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    cache_hit=False,
                )

            results = self._window_index.search(query_feature, top_k)

        proc_time = (time.time() - start_time) * 1000

        if use_cache:
            self._put_cache(query_hash, results)

        return RealtimeMatchResult(
            query_timestamp=start_time,
            results=results,
            window_size=len(self._window),
            processing_time_ms=proc_time,
            cache_hit=False,
        )

    def _start_real_time_thread(self) -> None:
        if self._real_time_thread and self._real_time_thread.is_alive():
            return

        self._stop_event.clear()

        def process_loop():
            logger.info("Real-time search thread started")
            while not self._stop_event.is_set():
                try:
                    batch = []
                    with self._lock:
                        while (
                            self._pending_queries
                            and len(batch) < self.config.real_time_batch_size
                        ):
                            batch.append(self._pending_queries.popleft())

                    if batch:
                        self._process_batch_queries(batch)
                    else:
                        time.sleep(self.config.real_time_interval)

                except Exception as e:
                    logger.error(f"Error in real-time processing: {e}")
                    time.sleep(0.1)
            logger.info("Real-time search thread stopped")

        self._real_time_thread = threading.Thread(
            target=process_loop, daemon=True, name="realtime-search"
        )
        self._real_time_thread.start()

    def _stop_real_time_thread(self) -> None:
        if self._real_time_thread and self._real_time_thread.is_alive():
            self._stop_event.set()
            self._real_time_thread.join(timeout=5.0)
            self._real_time_thread = None

    def _process_batch_queries(
        self, batch: list[tuple[np.ndarray, str, float, int]]
    ) -> None:
        queries = np.stack([q[0] for q in batch])
        top_ks = [q[3] for q in batch]
        max_top_k = max(top_ks)

        all_results = self.search_batch(queries, max_top_k, use_cache=False)

        for i, (query, query_id, timestamp, top_k) in enumerate(batch):
            results = all_results[i][:top_k]
            self._query_results[query_id] = RealtimeMatchResult(
                query_timestamp=timestamp,
                results=results,
                window_size=len(self._window),
                processing_time_ms=0.0,
                cache_hit=False,
            )

    def search_batch(
        self,
        query_features: np.ndarray,
        top_k: int = 10,
        use_cache: bool = True,
    ) -> list[list[tuple[str, float]]]:
        with self._lock:
            if self._window_index is None or self._window_index.size() == 0:
                return [[] for _ in range(len(query_features))]

            return self._window_index.search_batch(query_features, top_k)

    def async_search(
        self,
        query_feature: np.ndarray,
        query_id: str,
        timestamp: float | None = None,
        top_k: int = 10,
    ) -> None:
        timestamp = timestamp or time.time()
        with self._lock:
            self._pending_queries.append((query_feature, query_id, timestamp, top_k))

    def get_async_result(self, query_id: str) -> RealtimeMatchResult | None:
        return self._query_results.pop(query_id, None)

    def hybrid_search(
        self,
        query_feature: np.ndarray,
        query_camera_id: str,
        query_timestamp: float,
        top_k: int = 10,
        use_spatial_temporal: bool = True,
    ) -> list[SearchResult]:
        window_results = self.search(query_feature, top_k * 2, use_cache=True)

        window_item_ids = {r[0] for r in window_results.results}

        gallery_results = self.gallery_manager.query(
            query_feature=query_feature,
            query_camera_id=query_camera_id,
            query_timestamp=query_timestamp,
            top_k=top_k,
            use_spatial_temporal=use_spatial_temporal,
        )

        gallery_ids = {r.item_id for r in gallery_results}

        combined = []
        seen_ids = set()

        for r in window_results.results[:top_k]:
            if r[0] not in gallery_ids and r[0] not in seen_ids:
                item = self.gallery_manager.get(r[0], touch=False)
                if item:
                    combined.append(
                        SearchResult(
                            item_id=item.item_id,
                            track_id=item.track_id,
                            camera_id=item.camera_id,
                            timestamp=item.timestamp,
                            visual_score=r[1],
                            spatial_score=0.0,
                            temporal_score=0.0,
                            combined_score=r[1],
                            metadata=item.metadata,
                        )
                    )
                    seen_ids.add(r[0])

        for r in gallery_results:
            if r.item_id not in seen_ids:
                combined.append(r)
                seen_ids.add(r.item_id)

        combined.sort(key=lambda x: x.combined_score, reverse=True)
        return combined[:top_k]

    def get_window_items(
        self, camera_id: str | None = None
    ) -> list[WindowItem]:
        with self._lock:
            items = list(self._window)
            if camera_id:
                items = [it for it in items if it.camera_id == camera_id]
            return items

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "window_size": len(self._window),
                "window_capacity": self.config.window_size,
                "index_size": self._window_index.size() if self._window_index else 0,
                "cache_size": len(self._cache),
                "pending_queries": len(self._pending_queries),
                "real_time_enabled": self.config.enable_real_time_search,
                "last_rebuild_seconds": time.time() - self._last_rebuild_time,
            }

    def clear(self) -> None:
        with self._lock:
            self._window.clear()
            self._window_index.clear() if self._window_index else None
            self._window_index = None
            self._build_window_index()
            with self._cache_lock:
                self._cache.clear()
            self._pending_queries.clear()
            self._query_results.clear()

        logger.info("Cleared sliding window engine")

    def __del__(self):
        self._stop_real_time_thread()
