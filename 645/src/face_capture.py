import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Tuple, Optional


class FaceCapture:
    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.drawing_spec = self.mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
        
        self.focal_length = None
        self.camera_matrix = None
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        
        self._3d_face_model = self._get_3d_face_model()

    def _get_3d_face_model(self) -> np.ndarray:
        return np.array([
            [0.0, 0.0, 0.0],
            [0.0, -330.0, -65.0],
            [-225.0, 170.0, -135.0],
            [225.0, 170.0, -135.0],
            [-150.0, -150.0, -125.0],
            [150.0, -150.0, -125.0]
        ], dtype=np.float64)

    def _get_2d_landmarks(self, landmarks: list, image_shape: Tuple[int, int]) -> np.ndarray:
        h, w = image_shape[:2]
        face_2d = np.array([
            [landmarks[1].x * w, landmarks[1].y * h],
            [landmarks[152].x * w, landmarks[152].y * h],
            [landmarks[226].x * w, landmarks[226].y * h],
            [landmarks[446].x * w, landmarks[446].y * h],
            [landmarks[57].x * w, landmarks[57].y * h],
            [landmarks[287].x * w, landmarks[287].y * h]
        ], dtype=np.float64)
        return face_2d

    def _init_camera_matrix(self, image_shape: Tuple[int, int]):
        h, w = image_shape[:2]
        self.focal_length = w
        self.camera_matrix = np.array([
            [self.focal_length, 0, w / 2],
            [0, self.focal_length, h / 2],
            [0, 0, 1]
        ], dtype=np.float64)

    def estimate_head_pose(self, landmarks: list, image_shape: Tuple[int, int]) -> Dict[str, float]:
        if self.camera_matrix is None:
            self._init_camera_matrix(image_shape)
        
        face_2d = self._get_2d_landmarks(landmarks, image_shape)
        
        success, rotation_vec, translation_vec = cv2.solvePnP(
            self._3d_face_model,
            face_2d,
            self.camera_matrix,
            self.dist_coeffs
        )
        
        if not success:
            return {'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0}
        
        rotation_mat, _ = cv2.Rodrigues(rotation_vec)
        pose_mat = cv2.hconcat((rotation_mat, translation_vec))
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)
        
        pitch, yaw, roll = euler_angles.flatten()
        
        return {
            'pitch': float(pitch),
            'yaw': float(yaw),
            'roll': float(roll)
        }

    def get_all_landmarks(self, landmarks: list, image_shape: Tuple[int, int]) -> np.ndarray:
        h, w = image_shape[:2]
        points = np.array([[lm.x * w, lm.y * h, lm.z] for lm in landmarks], dtype=np.float32)
        return points

    def process_frame(self, frame: np.ndarray) -> Tuple[Optional[list], Optional[Dict], np.ndarray]:
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.face_mesh.process(image)
        image.flags.writeable = True
        
        landmarks = None
        head_pose = None
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            head_pose = self.estimate_head_pose(landmarks, frame.shape)
        
        return landmarks, head_pose, image

    def draw_landmarks(self, image: np.ndarray, landmarks: list) -> np.ndarray:
        if landmarks:
            face_landmarks = mp.solutions.face_mesh.NamedFaceLandmarks
            self.mp_drawing.draw_landmarks(
                image=image,
                landmark_list=landmarks,
                connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
            )
        return image

    def release(self):
        self.face_mesh.close()
