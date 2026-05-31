import cv2
import numpy as np
import torch
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class Keypoint:
    x: float
    y: float
    confidence: float
    part_name: Optional[str] = None


@dataclass
class PersonDetection:
    keypoints: List[Optional[Keypoint]]
    bbox: Tuple[int, int, int, int]
    confidence: float
    person_id: Optional[int] = None


@dataclass
class HandDetection:
    keypoints: List[Optional[Keypoint]]
    bbox: Tuple[int, int, int, int]
    hand_side: str
    confidence: float


class OpenPoseDetector:
    def __init__(self, proto_path: str, weights_path: str, 
                 hand_proto_path: Optional[str] = None,
                 hand_weights_path: Optional[str] = None,
                 net_input_size: Tuple[int, int] = (368, 368),
                 threshold: float = 0.1,
                 device: str = 'cpu'):
        
        self.device = device
        self.threshold = threshold
        self.net_input_size = net_input_size
        
        self.body_net = self._load_network(proto_path, weights_path)
        self.hand_net = None
        
        if hand_proto_path and hand_weights_path:
            self.hand_net = self._load_network(hand_proto_path, hand_weights_path)
        
        self.BODY_PARTS = {
            "Nose": 0, "Neck": 1, "RShoulder": 2, "RElbow": 3, "RWrist": 4,
            "LShoulder": 5, "LElbow": 6, "LWrist": 7, "RHip": 8, "RKnee": 9,
            "RAnkle": 10, "LHip": 11, "LKnee": 12, "LAnkle": 13, "REye": 14,
            "LEye": 15, "REar": 16, "LEar": 17, "Background": 18
        }
        
        self.POSE_PAIRS = [
            ["Neck", "RShoulder"], ["Neck", "LShoulder"], ["RShoulder", "RElbow"],
            ["RElbow", "RWrist"], ["LShoulder", "LElbow"], ["LElbow", "LWrist"],
            ["Neck", "RHip"], ["RHip", "RKnee"], ["RKnee", "RAnkle"],
            ["Neck", "LHip"], ["LHip", "LKnee"], ["LKnee", "LAnkle"],
            ["Neck", "Nose"], ["Nose", "REye"], ["REye", "REar"],
            ["Nose", "LEye"], ["LEye", "LEar"]
        ]
        
        self.HAND_PARTS = {
            "Wrist": 0, "Thumb1": 1, "Thumb2": 2, "Thumb3": 3, "Thumb4": 4,
            "Index1": 5, "Index2": 6, "Index3": 7, "Index4": 8,
            "Middle1": 9, "Middle2": 10, "Middle3": 11, "Middle4": 12,
            "Ring1": 13, "Ring2": 14, "Ring3": 15, "Ring4": 16,
            "Pinky1": 17, "Pinky2": 18, "Pinky3": 19, "Pinky4": 20
        }
        
        self.HAND_PAIRS = [
            ["Wrist", "Thumb1"], ["Thumb1", "Thumb2"], ["Thumb2", "Thumb3"], ["Thumb3", "Thumb4"],
            ["Wrist", "Index1"], ["Index1", "Index2"], ["Index2", "Index3"], ["Index3", "Index4"],
            ["Wrist", "Middle1"], ["Middle1", "Middle2"], ["Middle2", "Middle3"], ["Middle3", "Middle4"],
            ["Wrist", "Ring1"], ["Ring1", "Ring2"], ["Ring2", "Ring3"], ["Ring3", "Ring4"],
            ["Wrist", "Pinky1"], ["Pinky1", "Pinky2"], ["Pinky2", "Pinky3"], ["Pinky3", "Pinky4"]
        ]
    
    def _load_network(self, proto_path: str, weights_path: str):
        try:
            net = cv2.dnn.readNetFromCaffe(proto_path, weights_path)
            
            if self.device == 'cuda' and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            
            return net
        except Exception as e:
            print(f"Warning: Could not load network from {proto_path} and {weights_path}: {e}")
            return None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        blob = cv2.dnn.blobFromImage(
            image, 1.0 / 255, self.net_input_size,
            (0, 0, 0), swapRB=False, crop=False
        )
        return blob
    
    def detect_keypoints(self, image: np.ndarray) -> List[PersonDetection]:
        if self.body_net is None:
            return []
        
        blob = self._preprocess_image(image)
        self.body_net.setInput(blob)
        output = self.body_net.forward()
        
        height, width = image.shape[:2]
        output_height, output_width = output.shape[2:]
        
        detected_keypoints = self._parse_body_keypoints(output, width, height, output_width, output_height)
        person_detections = self._group_keypoints(detected_keypoints, width, height)
        
        return person_detections
    
    def _parse_body_keypoints(self, output: np.ndarray, 
                               image_width: int, image_height: int,
                               output_width: int, output_height: int) -> List[List[Optional[Keypoint]]]:
        keypoints_list = []
        
        for part_idx in range(len(self.BODY_PARTS) - 1):
            prob_map = output[0, part_idx, :, :]
            
            map_smooth = cv2.GaussianBlur(prob_map, (3, 3), 0, 0)
            
            _, prob_map = cv2.dnn.blobFromImage(map_smooth)
            prob_map = prob_map[0, 0]
            
            keypoints = []
            for y in range(output_height):
                for x in range(output_width):
                    prob = prob_map[y, x]
                    if prob > self.threshold:
                        x_coord = (x * image_width) / output_width
                        y_coord = (y * image_height) / output_height
                        keypoints.append(Keypoint(x_coord, y_coord, float(prob), 
                                       list(self.BODY_PARTS.keys())[part_idx]))
            
            if len(keypoints) > 0:
                keypoints = sorted(keypoints, key=lambda k: k.confidence, reverse=True)
                keypoints = self._nms_keypoints(keypoints)
            else:
                keypoints = [None]
            
            keypoints_list.append(keypoints)
        
        return keypoints_list
    
    def _nms_keypoints(self, keypoints: List[Keypoint], 
                        dist_threshold: float = 10.0) -> List[Keypoint]:
        if len(keypoints) == 0:
            return []
        
        suppressed = [False] * len(keypoints)
        selected = []
        
        for i, kp in enumerate(keypoints):
            if suppressed[i]:
                continue
            selected.append(kp)
            for j in range(i + 1, len(keypoints)):
                if suppressed[j]:
                    continue
                dist = np.sqrt((keypoints[j].x - kp.x) ** 2 + (keypoints[j].y - kp.y) ** 2)
                if dist < dist_threshold:
                    suppressed[j] = True
        
        return selected
    
    def _group_keypoints(self, detected_keypoints: List[List[Optional[Keypoint]]],
                        image_width: int, image_height: int) -> List[PersonDetection]:
        personwise_keypoints = []
        personwise_scores = []
        person_bboxes = []
        
        pair_wise = self._compute_pair_wise_scores(detected_keypoints)
        
        max_persons = self._greedy_grouping(detected_keypoints, pair_wise, 
                                          self.POSE_PAIRS, self.BODY_PARTS)
        
        for person_keypoints, person_score in max_persons:
            person_dict = {}
            for part_name, kp_idx in self.BODY_PARTS.items():
                if kp_idx < len(person_keypoints) and person_keypoints[kp_idx] != -1:
                    person_dict[part_name] = detected_keypoints[kp_idx][person_keypoints[kp_idx]]
            
            person_final = [person_dict.get(name) if name in person_dict else None 
                        for name in self.BODY_PARTS]
            
            bbox = self._compute_bbox(person_final, image_width, image_height)
            
            if bbox is not None:
                personwise_keypoints.append(person_final)
                personwise_scores.append(person_score)
                person_bboxes.append(bbox)
        
        detections = []
        for keypoints, bbox, score in zip(personwise_keypoints, person_bboxes, personwise_scores):
            detections.append(PersonDetection(
                keypoints=keypoints, bbox=bbox, confidence=float(score)))
        
        return detections
    
    def _compute_pair_wise_scores(self, detected_keypoints: List[List[Optional[Keypoint]]]) -> List[np.ndarray]:
        num_pairs = len(self.POSE_PAIRS)
        pair_wise_scores = []
        
        for pair_idx, pair in enumerate(self.POSE_PAIRS):
            part_a = pair[0]
            part_b = pair[1]
            
            idx_a = self.BODY_PARTS[part_a]
            idx_b = self.BODY_PARTS[part_b]
            
            candidates_a = detected_keypoints[idx_a]
            candidates_b = detected_keypoints[idx_b]
            
            num_candidates_a = len([k for k in candidates_a if k is not None])
            num_candidates_b = len([k for k in candidates_b if k is not None])
            
            if num_candidates_a == 0 or num_candidates_b == 0:
                pair_wise_scores.append(np.zeros((0, 0)))
                continue
            
            valid_a = [k for k in candidates_a if k is not None]
            valid_b = [k for k in candidates_b if k is not None]
            
            scores = np.zeros((len(valid_a), len(valid_b)))
            
            for i, kp_a in enumerate(valid_a):
                for j, kp_b in enumerate(valid_b):
                    scores[i, j] = self._compute_pair_score(kp_a, kp_b)
            
            pair_wise_scores.append(scores)
        
        return pair_wise_scores
    
    def _compute_pair_score(self, kp_a: Keypoint, kp_b: Keypoint,
                         dist_weight: float = 0.5) -> float:
        dist = np.sqrt((kp_a.x - kp_b.x) ** 2 + (kp_a.y - kp_b.y) ** 2)
        conf_score = (kp_a.confidence + kp_b.confidence) / 2.0
        
        max_dist = 100.0
        dist_score = max(0, 1 - dist / max_dist)
        
        score = dist_weight * dist_score + (1 - dist_weight) * conf_score
        
        return score
    
    def _greedy_grouping(self, detected_keypoints: List[List[Optional[Keypoint]]],
                         pair_wise_scores: List[np.ndarray],
                         pose_pairs: List[List[str]],
                         body_parts: Dict[str, int],
                         min_score: float = 0.3) -> List[Tuple[List[int], float]]:
        
        persons = []
        
        for pair_idx, pair in enumerate(pose_pairs):
            part_a = pair[0]
            part_b = pair[1]
            
            idx_a = body_parts[part_a]
            idx_b = body_parts[part_b]
            
            scores = pair_wise_scores[pair_idx]
            if scores.size == 0:
                continue
            
            valid_a = [i for i, k in enumerate(detected_keypoints[idx_a]) if k is not None]
            valid_b = [i for i, k in enumerate(detected_keypoints[idx_b]) if k is not None]
            
            for i in range(scores.shape[0]):
                for j in range(scores.shape[1]):
                    if scores[i, j] > min_score:
                        self._merge_into_persons(persons, idx_a, idx_b, valid_a[i], valid_b[j], 
                                             scores[i, j])
        
        return persons
    
    def _merge_into_persons(self, persons: List[Tuple[List[int], float]],
                         part_a_idx: int, part_b_idx: int,
                         kp_a_idx: int, kp_b_idx: int,
                         score: float):
        found_existing = False
        
        for person_idx, (person_keypoints, person_score) in enumerate(persons):
            if person_keypoints[part_a_idx] == kp_a_idx and person_keypoints[part_b_idx] == -1:
                person_keypoints[part_b_idx] = kp_b_idx
                persons[person_idx] = (person_keypoints, person_score + score)
                found_existing = True
                break
            elif person_keypoints[part_b_idx] == kp_b_idx and person_keypoints[part_a_idx] == -1:
                person_keypoints[part_a_idx] = kp_a_idx
                persons[person_idx] = (person_keypoints, person_score + score)
                found_existing = True
                break
        
        if not found_existing:
            new_person = [-1] * (len(self.BODY_PARTS) - 1)
            new_person[part_a_idx] = kp_a_idx
            new_person[part_b_idx] = kp_b_idx
            persons.append((new_person, score))
    
    def _compute_bbox(self, keypoints: List[Optional[Keypoint]],
                       image_width: int, image_height: int,
                       padding: int = 20) -> Optional[Tuple[int, int, int, int]]:
        valid_keypoints = [kp for kp in keypoints if kp is not None]
        
        if len(valid_keypoints) < 5:
            return None
        
        x_coords = [kp.x for kp in valid_keypoints]
        y_coords = [kp.y for kp in valid_keypoints]
        
        x_min = int(max(0, min(x_coords) - padding))
        y_min = int(max(0, min(y_coords) - padding))
        x_max = int(min(image_width, max(x_coords) + padding))
        y_max = int(min(image_height, max(y_coords) + padding))
        
        if x_max <= x_min or y_max <= y_min:
            return None
        
        return (x_min, y_min, x_max - x_min, y_max - y_min)
    
    def detect_hands(self, image: np.ndarray,
                    person_detections: List[PersonDetection]
                    ) -> List[HandDetection]:
        if self.hand_net is None or len(person_detections) == 0:
            return []
        
        hand_detections = []
        
        for person in person_detections:
            r_wrist = person.keypoints[self.BODY_PARTS["RWrist"]]
            l_wrist = person.keypoints[self.BODY_PARTS["LWrist"]]
            r_elbow = person.keypoints[self.BODY_PARTS["RElbow"]]
            l_elbow = person.keypoints[self.BODY_PARTS["LElbow"]]
            
            if r_wrist is not None and r_elbow is not None:
                hand = self._detect_single_hand(image, r_wrist, r_elbow, "right")
                if hand is not None:
                    hand_detections.append(hand)
            
            if l_wrist is not None and l_elbow is not None:
                hand = self._detect_single_hand(image, l_wrist, l_elbow, "left")
                if hand is not None:
                    hand_detections.append(hand)
        
        return hand_detections
    
    def _detect_single_hand(self, image: np.ndarray,
                             wrist: Keypoint,
                             elbow: Keypoint,
                             hand_side: str,
                             bbox_size: int = 200) -> Optional[HandDetection]:
        x, y = int(wrist.x), int(wrist.y)
        
        dx = wrist.x - elbow.x
        dy = wrist.y - elbow.y
        length = np.sqrt(dx*dx + dy*dy)
        
        bbox_size = int(length * 2.5)
        x_min = max(0, x - bbox_size // 2)
        y_min = max(0, y - bbox_size // 2)
        x_max = min(image.shape[1], x + bbox_size // 2)
        y_max = min(image.shape[0], y + bbox_size // 2)
        
        if x_max <= x_min or y_max <= y_min:
            return None
        
        hand_roi = image[y_min:y_max, x_min:x_max]
        
        if hand_roi.size == 0:
            return None
        
        blob = cv2.dnn.blobFromImage(
            hand_roi, 1.0 / 255, (368, 368),
            (0, 0, 0), swapRB=False, crop=False
        )
        
        self.hand_net.setInput(blob)
        output = self.hand_net.forward()
        
        hand_keypoints = self._parse_hand_keypoints(output, x_min, y_min,
                                                 hand_roi.shape[1], hand_roi.shape[0])
        
        bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
        
        valid_kps = [kp.confidence for kp in hand_keypoints if kp is not None]
        if len(valid_kps) > 0:
            confidence = float(np.mean(valid_kps))
        else:
            confidence = 0.0
        
        return HandDetection(
            keypoints=hand_keypoints,
            bbox=bbox,
            hand_side=hand_side,
            confidence=float(confidence)
        )
    
    def _parse_hand_keypoints(self, output: np.ndarray,
                           offset_x: int, offset_y: int,
                           roi_width: int, roi_height: int) -> List[Optional[Keypoint]]:
        keypoints = []
        output_height, output_width = output.shape[2:]
        
        for part_idx in range(len(self.HAND_PARTS)):
            prob_map = output[0, part_idx, :, :]
            
            flat_idx = np.argmax(prob_map)
            y_idx, x_idx = np.unravel_index(flat_idx, prob_map.shape)
            prob = prob_map[y_idx, x_idx]
            
            if prob > self.threshold:
                x_coord = (x_idx * roi_width) / output_width + offset_x
                y_coord = (y_idx * roi_height) / output_height + offset_y
                
                part_name = list(self.HAND_PARTS.keys())[part_idx]
                keypoints.append(Keypoint(x_coord, y_coord, float(prob), part_name))
            else:
                keypoints.append(None)
        
        return keypoints
    
    def visualize(self, image: np.ndarray,
                  persons: List[PersonDetection],
                  hands: Optional[List[HandDetection]] = None) -> np.ndarray:
        vis_image = image.copy()
        
        for person in persons:
            vis_image = self._draw_person(vis_image, person)
        
        if hands is not None:
            for hand in hands:
                vis_image = self._draw_hand(vis_image, hand)
        
        return vis_image
    
    def _draw_person(self, image: np.ndarray, person: PersonDetection) -> np.ndarray:
        for pair in self.POSE_PAIRS:
            part_a = pair[0]
            part_b = pair[1]
            
            idx_a = self.BODY_PARTS[part_a]
            idx_b = self.BODY_PARTS[part_b]
            
            if idx_a < len(person.keypoints) and idx_b < len(person.keypoints):
                kp_a = person.keypoints[idx_a]
                kp_b = person.keypoints[idx_b]
                
                if kp_a is not None and kp_b is not None:
                    cv2.line(image,
                              (int(kp_a.x), int(kp_a.y)),
                              (int(kp_b.x), int(kp_b.y)),
                              (0, 255, 0), 2)
        
        for kp in person.keypoints:
            if kp is not None:
                cv2.circle(image, (int(kp.x), int(kp.y)), 5, (0, 0, 255), -1)
        
        x, y, w, h = person.bbox
        cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)
        
        if person.person_id is not None:
            cv2.putText(image, f'ID: {person.person_id}',
                         (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                         0.5, (255, 0, 0), 2)
        
        return image
    
    def _draw_hand(self, image: np.ndarray, hand: HandDetection) -> np.ndarray:
        color = (0, 255, 255) if hand.hand_side == "right" else (255, 0, 255)
        
        for pair in self.HAND_PAIRS:
            part_a = pair[0]
            part_b = pair[1]
            
            idx_a = self.HAND_PARTS[part_a]
            idx_b = self.HAND_PARTS[part_b]
            
            if idx_a < len(hand.keypoints) and idx_b < len(hand.keypoints):
                kp_a = hand.keypoints[idx_a]
                kp_b = hand.keypoints[idx_b]
                
                if kp_a is not None and kp_b is not None:
                    cv2.line(image,
                              (int(kp_a.x), int(kp_a.y)),
                              (int(kp_b.x), int(kp_b.y)),
                              color, 2)
        
        for kp in hand.keypoints:
            if kp is not None:
                cv2.circle(image, (int(kp.x), int(kp.y)), 3, color, -1)
        
        return image
