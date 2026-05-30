import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from collections import deque
from dataclasses import dataclass, field

from config import Config


@dataclass
class CameraTrack:
    track_id: int
    camera_id: str
    feature: np.ndarray
    bbox: np.ndarray
    class_id: int
    confidence: float
    position: Tuple[float, float]
    timestamp: float
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2))
    trail: List[Tuple[float, float]] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)


@dataclass
class GlobalIdentity:
    global_id: int
    features: deque = field(default_factory=lambda: deque(maxlen=50))
    camera_tracks: Dict[str, int] = field(default_factory=dict)
    last_camera: str = ""
    last_position: Tuple[float, float] = (0.0, 0.0)
    last_seen: float = 0.0
    class_id: int = -1
    confidence: float = 0.0
    active: bool = True
    transfer_count: int = 0


class CrossCameraTracker:
    def __init__(
        self,
        feature_threshold: Optional[float] = None,
        time_window: Optional[float] = None,
        iou_threshold: Optional[float] = None,
    ):
        self.feature_threshold = feature_threshold or Config.CROSS_CAMERA_FEATURE_THRESHOLD
        self.time_window = time_window or Config.CROSS_CAMERA_TIME_WINDOW
        self.iou_threshold = iou_threshold or Config.CROSS_CAMERA_IOU_THRESHOLD

        self.global_identities: Dict[int, GlobalIdentity] = {}
        self.next_global_id = 0
        self.camera_tracks: Dict[str, Dict[int, CameraTrack]] = {}
        self.recent_transfers: deque = deque(maxlen=100)
        self.active_global_ids: Set[int] = set()

    def register_camera(self, camera_id: str):
        if camera_id not in self.camera_tracks:
            self.camera_tracks[camera_id] = {}

    def update(
        self,
        camera_id: str,
        tracks: List[Dict],
        features: Optional[np.ndarray] = None,
    ) -> List[Dict]:
        if camera_id not in self.camera_tracks:
            self.register_camera(camera_id)

        current_camera_tracks = {}
        updated_tracks = []

        for i, track in enumerate(tracks):
            track_id = track["id"]
            feature = features[i] if features is not None and i < len(features) else np.zeros(128, dtype=np.float32)
            bbox = np.array(track["bbox"])
            position = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            velocity = np.zeros(2)
            if "velocity" in track:
                velocity = np.array(track["velocity"])
            trail = track.get("trail", [])

            cam_track = CameraTrack(
                track_id=track_id,
                camera_id=camera_id,
                feature=feature,
                bbox=bbox,
                class_id=track["class_id"],
                confidence=track["confidence"],
                position=position,
                timestamp=time.time(),
                velocity=velocity,
                trail=trail,
            )
            current_camera_tracks[track_id] = cam_track

            global_id = self._assign_global_id(cam_track)

            track["global_id"] = global_id
            track["camera_id"] = camera_id
            track["is_cross_camera"] = self._is_cross_camera_track(global_id)
            updated_tracks.append(track)

        old_track_ids = set(self.camera_tracks[camera_id].keys())
        new_track_ids = set(current_camera_tracks.keys())
        lost_ids = old_track_ids - new_track_ids

        for lost_id in lost_ids:
            old_track = self.camera_tracks[camera_id][lost_id]
            self._handle_lost_track(old_track)

        self.camera_tracks[camera_id] = current_camera_tracks
        self._update_active_ids()

        return updated_tracks

    def _assign_global_id(self, cam_track: CameraTrack) -> int:
        best_global_id = -1
        best_score = -1.0

        same_camera_match = self._find_match_same_camera(cam_track)
        if same_camera_match is not None:
            return same_camera_match

        for gid, identity in self.global_identities.items():
            if not identity.active:
                continue

            if identity.class_id >= 0 and identity.class_id != cam_track.class_id:
                continue

            time_diff = time.time() - identity.last_seen
            if time_diff > self.time_window:
                continue

            if cam_track.camera_id == identity.last_camera:
                continue

            feature_score = self._compute_feature_similarity(cam_track.feature, identity.features)
            spatial_score = self._compute_spatial_feasibility(cam_track, identity)
            combined_score = 0.7 * feature_score + 0.3 * spatial_score

            if combined_score > best_score and combined_score > self.feature_threshold:
                best_score = combined_score
                best_global_id = gid

        if best_global_id >= 0:
            identity = self.global_identities[best_global_id]
            identity.features.append(cam_track.feature)
            identity.camera_tracks[cam_track.camera_id] = cam_track.track_id
            identity.last_camera = cam_track.camera_id
            identity.last_position = cam_track.position
            identity.last_seen = time.time()
            identity.confidence = cam_track.confidence
            identity.transfer_count += 1

            self.recent_transfers.append({
                "global_id": best_global_id,
                "from_camera": identity.last_camera,
                "to_camera": cam_track.camera_id,
                "score": round(best_score, 3),
                "timestamp": time.time(),
            })

            return best_global_id

        global_id = self._create_global_identity(cam_track)
        return global_id

    def _find_match_same_camera(self, cam_track: CameraTrack) -> Optional[int]:
        for gid, identity in self.global_identities.items():
            if not identity.active:
                continue
            if cam_track.camera_id in identity.camera_tracks:
                if identity.camera_tracks[cam_track.camera_id] == cam_track.track_id:
                    identity.features.append(cam_track.feature)
                    identity.last_position = cam_track.position
                    identity.last_seen = time.time()
                    identity.confidence = cam_track.confidence
                    return gid
        return None

    def _compute_feature_similarity(
        self,
        feature: np.ndarray,
        history_features: deque,
    ) -> float:
        if len(history_features) == 0:
            return 0.0

        feat = feature.flatten()
        feat_norm = feat / (np.linalg.norm(feat) + 1e-6)

        similarities = []
        for hist_feat in history_features:
            hf = hist_feat.flatten()
            hf_norm = hf / (np.linalg.norm(hf) + 1e-6)
            sim = np.dot(feat_norm, hf_norm)
            similarities.append(sim)

        return float(np.max(similarities))

    def _compute_spatial_feasibility(
        self,
        cam_track: CameraTrack,
        identity: GlobalIdentity,
    ) -> float:
        pos_diff = np.sqrt(
            (cam_track.position[0] - identity.last_position[0]) ** 2
            + (cam_track.position[1] - identity.last_position[1]) ** 2
        )

        spatial_score = np.exp(-pos_diff / 500.0)

        time_diff = time.time() - identity.last_seen
        time_factor = np.exp(-time_diff / self.time_window)

        return spatial_score * time_factor

    def _create_global_identity(self, cam_track: CameraTrack) -> int:
        global_id = self.next_global_id
        self.next_global_id += 1

        identity = GlobalIdentity(
            global_id=global_id,
            features=deque([cam_track.feature], maxlen=50),
            camera_tracks={cam_track.camera_id: cam_track.track_id},
            last_camera=cam_track.camera_id,
            last_position=cam_track.position,
            last_seen=time.time(),
            class_id=cam_track.class_id,
            confidence=cam_track.confidence,
        )
        self.global_identities[global_id] = identity
        return global_id

    def _handle_lost_track(self, cam_track: CameraTrack):
        for gid, identity in self.global_identities.items():
            if cam_track.camera_id in identity.camera_tracks:
                if identity.camera_tracks[cam_track.camera_id] == cam_track.track_id:
                    del identity.camera_tracks[cam_track.camera_id]
                    if not identity.camera_tracks:
                        identity.active = False
                    break

    def _is_cross_camera_track(self, global_id: int) -> bool:
        identity = self.global_identities.get(global_id)
        if identity is None:
            return False
        return identity.transfer_count > 0

    def _update_active_ids(self):
        self.active_global_ids = {
            gid for gid, identity in self.global_identities.items()
            if identity.active
        }

    def get_transfer_history(self, n: int = 20) -> List[Dict]:
        transfers = list(self.recent_transfers)[-n:]
        return transfers

    def get_active_global_ids(self) -> Set[int]:
        return self.active_global_ids.copy()

    def get_identity_info(self, global_id: int) -> Optional[Dict]:
        identity = self.global_identities.get(global_id)
        if identity is None:
            return None
        return {
            "global_id": identity.global_id,
            "class_id": identity.class_id,
            "last_camera": identity.last_camera,
            "camera_history": dict(identity.camera_tracks),
            "transfer_count": identity.transfer_count,
            "active": identity.active,
        }

    def reset(self):
        self.global_identities.clear()
        self.next_global_id = 0
        self.camera_tracks.clear()
        self.recent_transfers.clear()
        self.active_global_ids.clear()
