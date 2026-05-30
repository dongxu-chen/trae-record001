from __future__ import annotations

import logging
from typing import Any

import faiss
import numpy as np

from config import FaissConfig

logger = logging.getLogger(__name__)


class FaissSearchEngine:
    def __init__(
        self,
        dimension: int = 512,
        config: FaissConfig | None = None,
    ):
        self.dimension = dimension
        self.config = config or FaissConfig()
        self.index: faiss.Index | None = None
        self.id_map: dict[int, Any] = {}
        self._reverse_map: dict[Any, int] = {}
        self._next_internal_id: int = 0
        self._build_index()

    def _build_index(self) -> None:
        if self.config.index_type == "FlatIP":
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIDMap(self.index)
            logger.info("Built Faiss IndexFlatIP (exact inner product search)")
        elif self.config.index_type == "IVFFlat":
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(
                quantizer,
                self.dimension,
                self.config.nlist,
                faiss.METRIC_INNER_PRODUCT,
            )
            self.index.nprobe = self.config.nprobe
            logger.info(
                f"Built Faiss IVFFlat index (nlist={self.config.nlist}, "
                f"nprobe={self.config.nprobe})"
            )
        else:
            raise ValueError(f"Unsupported index type: {self.config.index_type}")

    def add(self, feature: np.ndarray, external_id: Any) -> None:
        if feature.shape[0] != self.dimension:
            raise ValueError(
                f"Feature dimension mismatch: expected {self.dimension}, "
                f"got {feature.shape[0]}"
            )
        if external_id in self._reverse_map:
            self.remove(external_id)

        internal_id = self._next_internal_id
        self._next_internal_id += 1

        self.id_map[internal_id] = external_id
        self._reverse_map[external_id] = internal_id

        feature_norm = np.linalg.norm(feature)
        if feature_norm > 0:
            feature = feature / feature_norm

        vec = feature.reshape(1, -1).astype(np.float32)
        ids = np.array([internal_id], dtype=np.int64)

        self._add_to_index(vec, ids)
        logger.debug(f"Added feature with external_id={external_id}")

    def add_batch(
        self, features: np.ndarray, external_ids: list[Any]
    ) -> None:
        if len(features) != len(external_ids):
            raise ValueError("Features and IDs must have the same length")

        internal_ids = []
        for ext_id in external_ids:
            if ext_id in self._reverse_map:
                self.remove(ext_id)
            int_id = self._next_internal_id
            self._next_internal_id += 1
            self.id_map[int_id] = ext_id
            self._reverse_map[ext_id] = int_id
            internal_ids.append(int_id)

        norms = np.linalg.norm(features, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        features = features / norms

        vecs = features.astype(np.float32)
        ids = np.array(internal_ids, dtype=np.int64)

        self._add_to_index(vecs, ids)
        logger.info(f"Added batch of {len(external_ids)} features")

    def _add_to_index(self, vecs: np.ndarray, ids: np.ndarray) -> None:
        if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
            if vecs.shape[0] >= self.config.nlist:
                self.index.train(vecs)
                logger.info("Trained IVF index")
            else:
                self.index = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIDMap(self.index)
                logger.warning(
                    "Not enough vectors to train IVF; falling back to FlatIP"
                )
        self.index.add_with_ids(vecs, ids)

    def search(
        self, query: np.ndarray, top_k: int = 10
    ) -> list[tuple[Any, float]]:
        if self.index.ntotal == 0:
            return []

        query_norm = np.linalg.norm(query)
        if query_norm > 0:
            query = query / query_norm
        query_vec = query.reshape(1, -1).astype(np.float32)

        distances, indices = self.index.search(query_vec, min(top_k, self.index.ntotal))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            external_id = self.id_map.get(int(idx))
            if external_id is not None:
                results.append((external_id, float(dist)))
        return results

    def search_batch(
        self, queries: np.ndarray, top_k: int = 10
    ) -> list[list[tuple[Any, float]]]:
        if self.index.ntotal == 0:
            return [[] for _ in range(len(queries))]

        norms = np.linalg.norm(queries, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        queries = queries / norms
        query_vecs = queries.astype(np.float32)

        distances, indices = self.index.search(
            query_vecs, min(top_k, self.index.ntotal)
        )

        all_results = []
        for i in range(len(queries)):
            results = []
            for dist, idx in zip(distances[i], indices[i]):
                if idx < 0:
                    continue
                external_id = self.id_map.get(int(idx))
                if external_id is not None:
                    results.append((external_id, float(dist)))
            all_results.append(results)
        return all_results

    def remove(self, external_id: Any) -> bool:
        if external_id not in self._reverse_map:
            return False
        internal_id = self._reverse_map.pop(external_id)
        self.id_map.pop(internal_id, None)
        try:
            self.index.remove_ids(np.array([internal_id], dtype=np.int64))
        except Exception:
            logger.warning(f"Could not remove id={internal_id} from Faiss index")
        return True

    def size(self) -> int:
        return self.index.ntotal

    def clear(self) -> None:
        self.id_map.clear()
        self._reverse_map.clear()
        self._next_internal_id = 0
        self._build_index()
        logger.info("Cleared search engine index")

    def save(self, path: str) -> None:
        faiss.write_index(self.index, path)
        import pickle

        meta_path = path + ".meta"
        meta = {
            "id_map": self.id_map,
            "reverse_map": self._reverse_map,
            "next_internal_id": self._next_internal_id,
        }
        with open(meta_path, "wb") as f:
            pickle.dump(meta, f)
        logger.info(f"Saved index to {path}")

    def load(self, path: str) -> None:
        self.index = faiss.read_index(path)
        import pickle

        meta_path = path + ".meta"
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        self.id_map = meta["id_map"]
        self._reverse_map = meta["reverse_map"]
        self._next_internal_id = meta["next_internal_id"]
        logger.info(f"Loaded index from {path} with {self.index.ntotal} vectors")
