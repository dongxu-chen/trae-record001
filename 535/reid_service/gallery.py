from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from config import GalleryConfig
from reid_service.search_engine import FaissSearchEngine
from reid_service.st_ranker import SpatioTemporalRanker, TrackRecord, RankedResult

logger = logging.getLogger(__name__)


@dataclass
class GalleryItem:
    item_id: str
    track_id: str
    camera_id: str
    timestamp: float
    feature: list[float]
    bbox: list[int] | None = None
    image_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    last_access_time: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "track_id": self.track_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "feature": self.feature,
            "bbox": self.bbox,
            "image_path": self.image_path,
            "metadata": self.metadata,
            "last_access_time": self.last_access_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GalleryItem:
        return cls(
            item_id=data["item_id"],
            track_id=data["track_id"],
            camera_id=data["camera_id"],
            timestamp=data["timestamp"],
            feature=data["feature"],
            bbox=data.get("bbox"),
            image_path=data.get("image_path"),
            metadata=data.get("metadata", {}),
            last_access_time=data.get("last_access_time", time.time()),
        )


@dataclass
class SearchResult:
    item_id: str
    track_id: str
    camera_id: str
    timestamp: float
    visual_score: float
    spatial_score: float
    temporal_score: float
    combined_score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "track_id": self.track_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "visual_score": round(self.visual_score, 6),
            "spatial_score": round(self.spatial_score, 6),
            "temporal_score": round(self.temporal_score, 6),
            "combined_score": round(self.combined_score, 6),
            "metadata": self.metadata,
        }


class GalleryManager:
    def __init__(
        self,
        search_engine: FaissSearchEngine,
        ranker: SpatioTemporalRanker,
        config: GalleryConfig | None = None,
    ):
        self.config = config or GalleryConfig()
        self.search_engine = search_engine
        self.ranker = ranker
        self._items: dict[str, GalleryItem] = {}
        self._lru_order: OrderedDict[str, None] = OrderedDict()
        self._next_id: int = 0
        self._persist_path = Path(self.config.persist_path)
        self._persist_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self._cleanup_thread: threading.Thread | None = None
        self._cleanup_stop_event = threading.Event()
        if self.config.enable_lru and self.config.cleanup_interval_seconds > 0:
            self._start_cleanup_thread()

    def _generate_item_id(self) -> str:
        self._next_id += 1
        return f"gal_{self._next_id:08d}"

    def _touch_item(self, item_id: str) -> None:
        with self._lock:
            if item_id in self._items:
                self._items[item_id].last_access_time = time.time()
                if item_id in self._lru_order:
                    self._lru_order.move_to_end(item_id)

    def _evict_lru(self, count: int = 1) -> int:
        evicted = 0
        with self._lock:
            while self._lru_order and evicted < count:
                oldest_id, _ = self._lru_order.popitem(last=False)
                if oldest_id in self._items:
                    self._items.pop(oldest_id, None)
                    self.search_engine.remove(oldest_id)
                    evicted += 1
        if evicted > 0:
            logger.info(f"LRU evicted {evicted} oldest items")
        return evicted

    def _evict_expired(self, current_time: float | None = None) -> int:
        if self.config.lru_ttl_seconds <= 0:
            return 0

        current_time = current_time or time.time()
        expiry_threshold = current_time - self.config.lru_ttl_seconds
        evicted_ids = []

        with self._lock:
            for item_id, item in list(self._items.items()):
                if item.last_access_time < expiry_threshold:
                    evicted_ids.append(item_id)

            for item_id in evicted_ids:
                self._items.pop(item_id, None)
                self._lru_order.pop(item_id, None)
                self.search_engine.remove(item_id)

        if evicted_ids:
            logger.info(f"Expired {len(evicted_ids)} items (TTL exceeded)")
        return len(evicted_ids)

    def _start_cleanup_thread(self) -> None:
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        self._cleanup_stop_event.clear()

        def cleanup_loop():
            logger.info("LRU cleanup thread started")
            while not self._cleanup_stop_event.is_set():
                try:
                    self._cleanup_stop_event.wait(self.config.cleanup_interval_seconds)
                    if self._cleanup_stop_event.is_set():
                        break
                    self.perform_cleanup()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
            logger.info("LRU cleanup thread stopped")

        self._cleanup_thread = threading.Thread(
            target=cleanup_loop, daemon=True, name="gallery-cleanup"
        )
        self._cleanup_thread.start()

    def _stop_cleanup_thread(self) -> None:
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_stop_event.set()
            self._cleanup_thread.join(timeout=5.0)
            self._cleanup_thread = None

    def perform_cleanup(self) -> dict[str, int]:
        results = {"expired_removed": 0, "lru_evicted": 0}
        results["expired_removed"] = self._evict_expired()

        with self._lock:
            excess = max(0, len(self._items) - self.config.max_gallery_size)
            if excess > 0:
                results["lru_evicted"] = self._evict_lru(excess)

        if results["expired_removed"] > 0 or results["lru_evicted"] > 0:
            logger.info(
                f"Cleanup complete: expired={results['expired_removed']}, "
                f"evicted={results['lru_evicted']}, total={self.size()}"
            )
        return results

    def add(
        self,
        feature: np.ndarray,
        track_id: str,
        camera_id: str,
        timestamp: float,
        bbox: list[int] | None = None,
        image_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GalleryItem:
        with self._lock:
            if len(self._items) >= self.config.max_gallery_size:
                self._evict_lru(1)

            item_id = self._generate_item_id()
            item = GalleryItem(
                item_id=item_id,
                track_id=track_id,
                camera_id=camera_id,
                timestamp=timestamp,
                feature=feature.tolist(),
                bbox=bbox,
                image_path=image_path,
                metadata=metadata or {},
            )

            self._items[item_id] = item
            self._lru_order[item_id] = None
            self.search_engine.add(feature, item_id)

        logger.info(
            f"Added gallery item {item_id}: track={track_id}, "
            f"cam={camera_id}, t={timestamp}"
        )
        return item

    def add_batch(
        self,
        features: np.ndarray,
        track_ids: list[str],
        camera_ids: list[str],
        timestamps: list[float],
        bboxes: list[list[int] | None] | None = None,
        image_paths: list[str | None] | None = None,
        metadata_list: list[dict[str, Any] | None] | None = None,
    ) -> list[GalleryItem]:
        n = len(track_ids)
        items = []

        with self._lock:
            excess = max(0, len(self._items) + n - self.config.max_gallery_size)
            if excess > 0:
                self._evict_lru(excess)

            item_ids = []
            for i in range(n):
                item_id = self._generate_item_id()
                item = GalleryItem(
                    item_id=item_id,
                    track_id=track_ids[i],
                    camera_id=camera_ids[i],
                    timestamp=timestamps[i],
                    feature=features[i].tolist(),
                    bbox=bboxes[i] if bboxes else None,
                    image_path=image_paths[i] if image_paths else None,
                    metadata=metadata_list[i] if metadata_list else {},
                )
                self._items[item_id] = item
                self._lru_order[item_id] = None
                items.append(item)
                item_ids.append(item_id)

            self.search_engine.add_batch(features, item_ids)

        logger.info(f"Added batch of {n} items to gallery")
        return items

    def remove(self, item_id: str) -> bool:
        with self._lock:
            if item_id not in self._items:
                return False
            self._items.pop(item_id)
            self._lru_order.pop(item_id, None)
            self.search_engine.remove(item_id)
        logger.info(f"Removed gallery item {item_id}")
        return True

    def get(self, item_id: str, touch: bool = True) -> GalleryItem | None:
        with self._lock:
            item = self._items.get(item_id)
            if item and touch:
                self._touch_item(item_id)
        return item

    def query(
        self,
        query_feature: np.ndarray,
        query_camera_id: str,
        query_timestamp: float,
        top_k: int = 10,
        use_spatial_temporal: bool = True,
        cross_camera_only: bool = False,
        allowed_cameras: set[str] | None = None,
        excluded_cameras: set[str] | None = None,
    ) -> list[SearchResult]:
        search_k = min(top_k * 5, self.search_engine.size())
        if search_k == 0:
            return []

        raw_results = self.search_engine.search(query_feature, search_k)

        if not raw_results:
            return []

        candidates = []
        visual_scores = []
        with self._lock:
            for item_id, vis_score in raw_results:
                item = self._items.get(item_id)
                if item is None:
                    continue
                self._touch_item(item_id)
                candidates.append(item)
                visual_scores.append(vis_score)

        if not use_spatial_temporal:
            results = []
            for item, vis_score in zip(candidates, visual_scores):
                results.append(
                    SearchResult(
                        item_id=item.item_id,
                        track_id=item.track_id,
                        camera_id=item.camera_id,
                        timestamp=item.timestamp,
                        visual_score=vis_score,
                        spatial_score=0.0,
                        temporal_score=0.0,
                        combined_score=vis_score,
                        metadata=item.metadata,
                    )
                )
            results.sort(key=lambda x: x.combined_score, reverse=True)
            return results[:top_k]

        query_record = TrackRecord(
            track_id="query",
            camera_id=query_camera_id,
            timestamp=query_timestamp,
        )

        candidate_records = [
            TrackRecord(
                track_id=item.track_id,
                camera_id=item.camera_id,
                timestamp=item.timestamp,
                metadata=item.metadata,
            )
            for item in candidates
        ]

        if cross_camera_only:
            ranked = self.ranker.rank_cross_camera(
                query_record, candidate_records, visual_scores, top_k
            )
        elif allowed_cameras or excluded_cameras:
            ranked = self.ranker.rank_with_camera_filter(
                query_record,
                candidate_records,
                visual_scores,
                top_k,
                allowed_cameras,
                excluded_cameras,
            )
        else:
            ranked = self.ranker.rank(
                query_record, candidate_records, visual_scores, top_k
            )

        id_to_item = {item.item_id: item for item in candidates}
        results = []
        for r in ranked:
            item = id_to_item.get(r.track_id)
            if item is None:
                for cand_item in candidates:
                    if cand_item.track_id == r.track_id:
                        item = cand_item
                        break
            if item is None:
                continue
            results.append(
                SearchResult(
                    item_id=item.item_id,
                    track_id=item.track_id,
                    camera_id=r.camera_id,
                    timestamp=r.timestamp,
                    visual_score=r.visual_score,
                    spatial_score=r.spatial_score,
                    temporal_score=r.temporal_score,
                    combined_score=r.combined_score,
                    metadata=item.metadata,
                )
            )
        return results

    def query_by_image(
        self,
        feature_extractor,
        image,
        query_camera_id: str,
        query_timestamp: float,
        bbox: list[int] | None = None,
        top_k: int = 10,
        use_spatial_temporal: bool = True,
        cross_camera_only: bool = False,
    ) -> list[SearchResult]:
        if bbox is not None:
            feature = feature_extractor.extract_from_video_frame(image, tuple(bbox))
        else:
            feature = feature_extractor.extract(image)
        return self.query(
            query_feature=feature,
            query_camera_id=query_camera_id,
            query_timestamp=query_timestamp,
            top_k=top_k,
            use_spatial_temporal=use_spatial_temporal,
            cross_camera_only=cross_camera_only,
        )

    def get_items_by_camera(self, camera_id: str, touch: bool = False) -> list[GalleryItem]:
        with self._lock:
            items = [
                item for item in self._items.values() if item.camera_id == camera_id
            ]
            if touch:
                for item in items:
                    self._touch_item(item.item_id)
        return items

    def get_items_by_track(self, track_id: str, touch: bool = False) -> list[GalleryItem]:
        with self._lock:
            items = [
                item for item in self._items.values() if item.track_id == track_id
            ]
            if touch:
                for item in items:
                    self._touch_item(item.item_id)
        return items

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._lru_order.clear()
            self._next_id = 0
            self.search_engine.clear()
        logger.info("Cleared gallery")

    def get_camera_list(self) -> list[str]:
        with self._lock:
            return list({item.camera_id for item in self._items.values()})

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            camera_counts: dict[str, int] = {}
            for item in self._items.values():
                camera_counts[item.camera_id] = camera_counts.get(item.camera_id, 0) + 1
            return {
                "total_items": len(self._items),
                "index_size": self.search_engine.size(),
                "cameras": camera_counts,
                "max_size": self.config.max_gallery_size,
                "lru_enabled": self.config.enable_lru,
                "lru_ttl_seconds": self.config.lru_ttl_seconds,
                "cleanup_interval_seconds": self.config.cleanup_interval_seconds,
            }

    def save(self) -> None:
        with self._lock:
            items_data = {k: v.to_dict() for k, v in self._items.items()}
        items_path = self._persist_path / "gallery_items.json"
        with open(items_path, "w", encoding="utf-8") as f:
            json.dump(items_data, f, ensure_ascii=False, indent=2)

        index_path = str(self._persist_path / "faiss_index.bin")
        self.search_engine.save(index_path)

        meta_path = self._persist_path / "gallery_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"next_id": self._next_id}, f)
        logger.info(f"Saved gallery with {len(items_data)} items")

    def load(self) -> None:
        items_path = self._persist_path / "gallery_items.json"
        if items_path.exists():
            with open(items_path, "r", encoding="utf-8") as f:
                items_data = json.load(f)
            with self._lock:
                for k, v in items_data.items():
                    item = GalleryItem.from_dict(v)
                    self._items[k] = item
                    self._lru_order[k] = None

        index_path = str(self._persist_path / "faiss_index.bin")
        index_file = Path(index_path)
        if index_file.exists():
            self.search_engine.load(index_path)

        meta_path = self._persist_path / "gallery_meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self._next_id = meta.get("next_id", 0)
        logger.info(f"Loaded gallery with {len(self._items)} items")

    def __del__(self):
        self._stop_cleanup_thread()
