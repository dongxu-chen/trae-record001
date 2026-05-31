import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import mediapipe as mp


class FaceAnalyzer:
    def __init__(self, min_detection_confidence: float = 0.5):
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=min_detection_confidence
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=5,
            min_detection_confidence=min_detection_confidence
        )

    def detect_faces(self, image: np.ndarray) -> List[Dict]:
        results = self.face_detection.process(image)
        faces = []
        
        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                h, w, _ = image.shape
                
                face_data = {
                    "bbox": {
                        "xmin": int(bbox.xmin * w),
                        "ymin": int(bbox.ymin * h),
                        "width": int(bbox.width * w),
                        "height": int(bbox.height * h)
                    },
                    "confidence": detection.score[0],
                    "landmarks": []
                }
                
                for landmark in detection.location_data.relative_keypoints:
                    face_data["landmarks"].append({
                        "x": landmark.x * w,
                        "y": landmark.y * h
                    })
                
                faces.append(face_data)
        
        return faces

    def analyze_expression(self, image: np.ndarray, face_bbox: Dict) -> Dict:
        h, w, _ = image.shape
        x, y = face_bbox["xmin"], face_bbox["ymin"]
        width, height = face_bbox["width"], face_bbox["height"]
        
        padding = int(0.1 * max(width, height))
        x = max(0, x - padding)
        y = max(0, y - padding)
        x2 = min(w, x + width + 2 * padding)
        y2 = min(h, y + height + 2 * padding)
        
        face_img = image[y:y2, x:x2]
        if face_img.size == 0:
            return {"expression": "unknown", "scores": {}, "intensity": 0}
        
        results = self.face_mesh.process(face_img)
        
        if not results.multi_face_landmarks:
            return {"expression": "unknown", "scores": {}, "intensity": 0}
        
        landmarks = results.multi_face_landmarks[0].landmark
        
        left_eye_open = self._calculate_eye_openness(landmarks, 33, 159, 158, 153, 145, 144)
        right_eye_open = self._calculate_eye_openness(landmarks, 362, 386, 385, 398, 374, 373)
        mouth_open = self._calculate_mouth_openness(landmarks)
        smile_intensity = self._calculate_smile(landmarks)
        eyebrow_raise = self._calculate_eyebrow_raise(landmarks)
        
        expression_scores = {
            "happy": min(1.0, smile_intensity * 1.5),
            "surprised": min(1.0, (left_eye_open + right_eye_open) / 2 * mouth_open * 2),
            "neutral": 0.5,
            "excited": min(1.0, eyebrow_raise * mouth_open * 1.5)
        }
        
        expressions = ["happy", "surprised", "neutral", "excited"]
        main_expression = max(expressions, key=lambda e: expression_scores[e])
        
        return {
            "expression": main_expression,
            "scores": expression_scores,
            "intensity": max(expression_scores.values()),
            "eye_openness": (left_eye_open + right_eye_open) / 2,
            "mouth_openness": mouth_open,
            "smile_intensity": smile_intensity
        }

    def _calculate_eye_openness(self, landmarks, *indices) -> float:
        if len(indices) < 6:
            return 0.5
        
        points = [np.array([landmarks[i].x, landmarks[i].y]) for i in indices]
        
        eye_width = np.linalg.norm(points[0] - points[3])
        eye_height = (np.linalg.norm(points[1] - points[5]) + np.linalg.norm(points[2] - points[4])) / 2
        
        if eye_width == 0:
            return 0.5
        
        ratio = eye_height / eye_width
        return min(1.0, ratio * 5)

    def _calculate_mouth_openness(self, landmarks) -> float:
        upper_lip = np.array([landmarks[13].x, landmarks[13].y])
        lower_lip = np.array([landmarks[14].x, landmarks[14].y])
        mouth_left = np.array([landmarks[78].x, landmarks[78].y])
        mouth_right = np.array([landmarks[308].x, landmarks[308].y])
        
        mouth_height = np.linalg.norm(upper_lip - lower_lip)
        mouth_width = np.linalg.norm(mouth_left - mouth_right)
        
        if mouth_width == 0:
            return 0
        
        return min(1.0, mouth_height / mouth_width * 2)

    def _calculate_smile(self, landmarks) -> float:
        left_corner = np.array([landmarks[61].x, landmarks[61].y])
        right_corner = np.array([landmarks[291].x, landmarks[291].y])
        upper_lip = np.array([landmarks[13].x, landmarks[13].y])
        
        mouth_width = np.linalg.norm(left_corner - right_corner)
        avg_y = (left_corner[1] + right_corner[1]) / 2
        
        curvature = avg_y - upper_lip[1]
        
        if mouth_width == 0:
            return 0.5
        
        return max(0, min(1.0, curvature / mouth_width * 10 + 0.5))

    def _calculate_eyebrow_raise(self, landmarks) -> float:
        left_eyebrow = np.array([landmarks[105].x, landmarks[105].y])
        right_eyebrow = np.array([landmarks[334].x, landmarks[334].y])
        left_eye = np.array([landmarks[159].x, landmarks[159].y])
        right_eye = np.array([landmarks[386].x, landmarks[386].y])
        
        left_dist = np.linalg.norm(left_eyebrow - left_eye)
        right_dist = np.linalg.norm(right_eyebrow - right_eye)
        
        return min(1.0, (left_dist + right_dist) / 2 * 10)

    def analyze_frame(self, image: np.ndarray) -> Dict:
        faces = self.detect_faces(image)
        
        if not faces:
            return {
                "has_face": False,
                "num_faces": 0,
                "faces": [],
                "face_score": 0,
                "expression_score": 0
            }
        
        expressions = []
        for face in faces:
            expr = self.analyze_expression(image, face["bbox"])
            face["expression"] = expr
            expressions.append(expr)
        
        avg_intensity = np.mean([e["intensity"] for e in expressions]) if expressions else 0
        max_confidence = max([f["confidence"] for f in faces]) if faces else 0
        num_face_score = min(1.0, len(faces) / 3)
        
        face_score = num_face_score * 0.3 + max_confidence * 0.4 + avg_intensity * 0.3
        
        return {
            "has_face": True,
            "num_faces": len(faces),
            "faces": faces,
            "face_score": face_score,
            "expression_score": avg_intensity,
            "main_expression": max(
                ["happy", "surprised", "neutral", "excited"],
                key=lambda e: np.mean([exp["scores"].get(e, 0) for exp in expressions]) if expressions else 0
            )
        }

    def draw_faces(self, image: np.ndarray, analysis_result: Dict) -> np.ndarray:
        img_copy = image.copy()
        
        for face in analysis_result.get("faces", []):
            bbox = face["bbox"]
            confidence = face["confidence"]
            expression = face.get("expression", {}).get("expression", "unknown")
            
            cv2.rectangle(
                img_copy,
                (bbox["xmin"], bbox["ymin"]),
                (bbox["xmin"] + bbox["width"], bbox["ymin"] + bbox["height"]),
                (0, 255, 0),
                2
            )
            
            label = f"{expression} ({confidence:.2f})"
            cv2.putText(
                img_copy,
                label,
                (bbox["xmin"], bbox["ymin"] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
        
        return img_copy

    def close(self):
        self.face_detection.close()
        self.face_mesh.close()

    def __del__(self):
        try:
            self.close()
        except:
            pass
