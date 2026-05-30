import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque
from scipy.optimize import linear_sum_assignment


HAND_COLORS = [
    (0, 255, 0),
    (255, 0, 0),
    (0, 0, 255),
    (255, 255, 0),
]

LANDMARK_NAMES = [
    "手腕", "拇指CMC", "拇指MCP", "拇指IP", "拇指指尖",
    "食指MCP", "食指PIP", "食指DIP", "食指指尖",
    "中指MCP", "中指PIP", "中指DIP", "中指指尖",
    "无名指MCP", "无名指PIP", "无名指DIP", "无名指指尖",
    "小指MCP", "小指PIP", "小指DIP", "小指指尖",
]

FINGER_JOINTS = {
    "拇指": [(1, 2), (2, 3), (3, 4)],
    "食指": [(5, 6), (6, 7), (7, 8)],
    "中指": [(9, 10), (10, 11), (11, 12)],
    "无名指": [(13, 14), (14, 15), (15, 16)],
    "小指": [(17, 18), (18, 19), (19, 20)],
}


class HandTracker:
    def __init__(self, hand_id, handedness, initial_pos, max_history=60):
        self.hand_id = hand_id
        self.handedness = handedness
        self.center = initial_pos
        self.history = deque(maxlen=max_history)
        self.history_3d = deque(maxlen=max_history)
        self.history.append(initial_pos)
        self.lost_frames = 0
        self.velocity = (0, 0)
        self.speed = 0.0
        self.velocity_3d = (0, 0, 0)
        self.speed_3d = 0.0

    def update(self, center, center_3d=None, dt=1.0):
        if len(self.history) > 0:
            prev_center = self.history[-1]
            dx = center[0] - prev_center[0]
            dy = center[1] - prev_center[1]
            self.velocity = (dx / max(dt, 1e-6), dy / max(dt, 1e-6))
            self.speed = np.sqrt(self.velocity[0] ** 2 + self.velocity[1] ** 2)

            if center_3d is not None and len(self.history_3d) > 0:
                prev_3d = self.history_3d[-1]
                dx3d = center_3d[0] - prev_3d[0]
                dy3d = center_3d[1] - prev_3d[1]
                dz3d = center_3d[2] - prev_3d[2]
                self.velocity_3d = (dx3d, dy3d, dz3d)
                self.speed_3d = np.sqrt(dx3d ** 2 + dy3d ** 2 + dz3d ** 2)

        self.center = center
        self.history.append(center)
        if center_3d is not None:
            self.history_3d.append(center_3d)
        self.lost_frames = 0


class HandPose3D:
    def __init__(self):
        self.finger_angles = {}
        self.hand_normal = None
        self.palm_direction = None
        self.hand_size_3d = 0.0
        self.depth_scale = 1.0

    def compute_pose(self, landmarks_3d):
        wrist = np.array(landmarks_3d[0][2:5])
        thumb_tip = np.array(landmarks_3d[4][2:5])
        index_mcp = np.array(landmarks_3d[5][2:5])
        middle_mcp = np.array(landmarks_3d[9][2:5])
        ring_mcp = np.array(landmarks_3d[13][2:5])
        pinky_mcp = np.array(landmarks_3d[17][2:5])
        middle_tip = np.array(landmarks_3d[12][2:5])

        palm_center = (index_mcp + ring_mcp + pinky_mcp) / 3
        self.palm_direction = palm_center - wrist

        v1 = index_mcp - wrist
        v2 = pinky_mcp - wrist
        self.hand_normal = np.cross(v1, v2)
        norm_mag = np.linalg.norm(self.hand_normal)
        if norm_mag > 0:
            self.hand_normal = self.hand_normal / norm_mag

        self.hand_size_3d = np.linalg.norm(middle_tip - wrist)
        if self.hand_size_3d > 0:
            self.depth_scale = 1.0 / self.hand_size_3d

        for finger_name, joints in FINGER_JOINTS.items():
            self.finger_angles[finger_name] = []
            for idx, (j1, j2) in enumerate(joints):
                p1 = np.array(landmarks_3d[j1][2:5])
                p2 = np.array(landmarks_3d[j2][2:5])
                angle = self._compute_joint_angle(p1, p2, wrist)
                self.finger_angles[finger_name].append(angle)

        return self

    def _compute_joint_angle(self, p1, p2, wrist):
        v1 = p1 - wrist
        v2 = p2 - p1
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 > 0 and norm2 > 0:
            cos_theta = dot / (norm1 * norm2)
            cos_theta = np.clip(cos_theta, -1.0, 1.0)
            return np.degrees(np.arccos(cos_theta))
        return 0.0

    def get_finger_total_angle(self, finger_name):
        if finger_name in self.finger_angles:
            return sum(self.finger_angles[finger_name])
        return 0.0

    def get_hand_orientation(self):
        if self.hand_normal is not None:
            pitch = np.degrees(np.arctan2(self.hand_normal[1], self.hand_normal[2]))
            yaw = np.degrees(np.arctan2(self.hand_normal[0], self.hand_normal[2]))
            return {"pitch": pitch, "yaw": yaw}
        return {"pitch": 0, "yaw": 0}


class HandDetector:
    def __init__(
        self,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        iou_threshold=0.3,
        max_lost_frames=10,
    ):
        self.max_num_hands = max_num_hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.fps_time = time.time()
        self.fps = 0.0
        self.trackers = {}
        self.next_hand_id = 0
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.last_frame_time = time.time()
        self.frame_count = 0

    def _compute_iou(self, bbox1, bbox2):
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2

        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)

        if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
            return 0.0

        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = area1 + area2 - inter_area

        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    def _compute_cost_matrix(self, detections):
        tracker_ids = list(self.trackers.keys())
        cost_matrix = np.zeros((len(tracker_ids), len(detections)))

        for t_idx, tid in enumerate(tracker_ids):
            tracker = self.trackers[tid]
            for d_idx, det in enumerate(detections):
                if det["handedness"] != tracker.handedness:
                    cost_matrix[t_idx, d_idx] = 1e9
                else:
                    dist = np.sqrt(
                        (det["center"][0] - tracker.center[0]) ** 2 +
                        (det["center"][1] - tracker.center[1]) ** 2
                    )
                    cost_matrix[t_idx, d_idx] = dist

        return tracker_ids, cost_matrix

    def _associate_hands(self, detections):
        if not self.trackers:
            return {}, list(range(len(detections)))

        tracker_ids, cost_matrix = self._compute_cost_matrix(detections)

        if len(tracker_ids) == 0 or len(detections) == 0:
            return {}, list(range(len(detections)))

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matched = {}
        unmatched_detections = set(range(len(detections)))

        for t_idx, d_idx in zip(row_ind, col_ind):
            tid = tracker_ids[t_idx]
            det = detections[d_idx]
            tracker = self.trackers[tid]
            if det["handedness"] == tracker.handedness:
                if cost_matrix[t_idx, d_idx] < 150:
                    matched[tid] = d_idx
                    unmatched_detections.discard(d_idx)

        return matched, list(unmatched_detections)

    def _compute_3d_pose(self, landmarks):
        pose3d = HandPose3D()
        return pose3d.compute_pose(landmarks)

    def find_hands(self, img, draw=True, use_tracking=True, compute_3d=True):
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)
        h, w, _ = img.shape
        detections = []

        if self.results.multi_hand_landmarks:
            for hand_idx, hand_lms in enumerate(self.results.multi_hand_landmarks):
                handedness = self.results.multi_handedness[hand_idx]
                label = handedness.classification[0].label
                score = handedness.classification[0].score

                lm_list = []
                for lm in hand_lms.landmark:
                    px, py = int(lm.x * w), int(lm.y * h)
                    lm_list.append((px, py, lm.x, lm.y, lm.z))

                x_coords = [p[0] for p in lm_list]
                y_coords = [p[1] for p in lm_list]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                bbox = (x_min, y_min, x_max, y_max)

                center_x = (x_min + x_max) // 2
                center_y = (y_min + y_max) // 2

                pose_3d = None
                center_3d = None
                if compute_3d:
                    pose_3d = self._compute_3d_pose(lm_list)
                    wrist_3d = lm_list[0][2:5]
                    center_3d = (wrist_3d[0], wrist_3d[1], wrist_3d[2])

                detection = {
                    "landmarks": lm_list,
                    "bbox": bbox,
                    "center": (center_x, center_y),
                    "center_3d": center_3d,
                    "handedness": label,
                    "confidence": score,
                    "raw_lms": hand_lms,
                    "pose_3d": pose_3d,
                }
                detections.append(detection)

        matched, unmatched = self._associate_hands(detections) if use_tracking else ({}, list(range(len(detections))))

        all_hands = []

        for tid, d_idx in matched.items():
            det = detections[d_idx]
            tracker = self.trackers[tid]
            tracker.update(det["center"], det.get("center_3d"), dt)

            hand_info = {
                "hand_id": tid,
                "tracker": tracker,
                "landmarks": det["landmarks"],
                "bbox": det["bbox"],
                "center": det["center"],
                "center_3d": det.get("center_3d"),
                "handedness": det["handedness"],
                "confidence": det["confidence"],
                "speed": tracker.speed,
                "velocity": tracker.velocity,
                "speed_3d": tracker.speed_3d,
                "velocity_3d": tracker.velocity_3d,
                "pose_3d": det.get("pose_3d"),
            }
            all_hands.append(hand_info)

            if draw:
                color = HAND_COLORS[tid % len(HAND_COLORS)]
                handedness_label = "右手" if det["handedness"] == "Right" else "左手"
                cv2.putText(img, f"ID:{tid} {handedness_label}", (det["bbox"][0], det["bbox"][1] - 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                self.mp_drawing.draw_landmarks(
                    img,
                    det["raw_lms"],
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=color, thickness=2),
                )

        for d_idx in unmatched:
            det = detections[d_idx]
            new_tid = self.next_hand_id
            self.next_hand_id += 1
            tracker = HandTracker(new_tid, det["handedness"], det["center"])
            self.trackers[new_tid] = tracker

            hand_info = {
                "hand_id": new_tid,
                "tracker": tracker,
                "landmarks": det["landmarks"],
                "bbox": det["bbox"],
                "center": det["center"],
                "center_3d": det.get("center_3d"),
                "handedness": det["handedness"],
                "confidence": det["confidence"],
                "speed": 0.0,
                "velocity": (0, 0),
                "speed_3d": 0.0,
                "velocity_3d": (0, 0, 0),
                "pose_3d": det.get("pose_3d"),
            }
            all_hands.append(hand_info)

            if draw:
                color = HAND_COLORS[new_tid % len(HAND_COLORS)]
                handedness_label = "右手" if det["handedness"] == "Right" else "左手"
                cv2.putText(img, f"ID:{new_tid} {handedness_label}", (det["bbox"][0], det["bbox"][1] - 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                self.mp_drawing.draw_landmarks(
                    img,
                    det["raw_lms"],
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=color, thickness=2),
                )

        lost_ids = []
        for tid in self.trackers:
            if tid not in matched:
                self.trackers[tid].lost_frames += 1
                if self.trackers[tid].lost_frames > self.max_lost_frames:
                    lost_ids.append(tid)
        for tid in lost_ids:
            del self.trackers[tid]

        self.frame_count += 1
        dt_fps = now - self.fps_time
        self.fps_time = now
        if dt_fps > 0:
            self.fps = 0.95 * self.fps + 0.05 * (1.0 / dt_fps)

        return img, all_hands

    def get_landmark_array(self, hand_info):
        lm = hand_info["landmarks"]
        arr = np.array([[p[2], p[3]] for p in lm], dtype=np.float32)
        wrist = arr[0]
        arr = arr - wrist
        max_dist = np.max(np.linalg.norm(arr, axis=1))
        if max_dist > 0:
            arr = arr / max_dist
        return arr.flatten()

    def get_landmark_array_3d(self, hand_info):
        lm = hand_info["landmarks"]
        arr = np.array([[p[2], p[3], p[4]] for p in lm], dtype=np.float32)
        wrist = arr[0]
        arr = arr - wrist
        max_dist = np.max(np.linalg.norm(arr, axis=1))
        if max_dist > 0:
            arr = arr / max_dist
        return arr.flatten()

    def get_finger_states(self, hand_info):
        lm = hand_info["landmarks"]
        handedness = hand_info["handedness"]
        is_right = handedness == "Right"

        thumb_tip = lm[4]
        thumb_ip = lm[3]
        thumb_mcp = lm[2]

        if is_right:
            thumb_up = thumb_tip[0] < thumb_ip[0]
        else:
            thumb_up = thumb_tip[0] > thumb_ip[0]

        finger_tips = [lm[8], lm[12], lm[16], lm[20]]
        finger_pips = [lm[6], lm[10], lm[14], lm[18]]
        fingers_up = [thumb_up]
        for tip, pip in zip(finger_tips, finger_pips):
            fingers_up.append(tip[1] < pip[1])

        return fingers_up

    def release(self):
        self.hands.close()
