import cv2
import numpy as np
import torch
import config


class FaceDetector:
    def __init__(self):
        self.face_cascade = self._load_haar_cascade()
    
    def _load_haar_cascade(self):
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        return face_cascade
    
    def detect(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return faces
    
    def align_face(self, image, face_box, output_size=224):
        x, y, w, h = face_box
        
        center_x = x + w // 2
        center_y = y + h // 2
        
        size = max(w, h)
        size = int(size * 1.1)
        
        x1 = max(0, center_x - size // 2)
        y1 = max(0, center_y - size // 2)
        x2 = min(image.shape[1], center_x + size // 2)
        y2 = min(image.shape[0], center_y + size // 2)
        
        face_crop = image[y1:y2, x1:x2]
        face_aligned = cv2.resize(face_crop, (output_size, output_size))
        
        return face_aligned, (x1, y1, x2, y2)


class LandmarkDetector:
    def __init__(self):
        self.predictor = None
        self._init_dlib_predictor()
    
    def _init_dlib_predictor(self):
        try:
            import dlib
            predictor_path = "shape_predictor_68_face_landmarks.dat"
            self.predictor = dlib.shape_predictor(predictor_path)
            self.dlib = dlib
        except:
            print("Warning: dlib not available, using synthetic landmarks")
            self.predictor = None
    
    def detect_landmarks(self, image, face_box):
        if self.predictor is not None:
            return self._detect_landmarks_dlib(image, face_box)
        else:
            return self._detect_landmarks_synthetic(image, face_box)
    
    def _detect_landmarks_dlib(self, image, face_box):
        x, y, w, h = face_box
        rect = self.dlib.rectangle(int(x), int(y), int(x + w), int(y + h))
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        shape = self.predictor(gray, rect)
        
        landmarks = np.zeros((68, 2), dtype=np.float32)
        for i in range(68):
            landmarks[i, 0] = shape.part(i).x
            landmarks[i, 1] = shape.part(i).y
        
        return landmarks
    
    def _detect_landmarks_synthetic(self, image, face_box):
        x, y, w, h = face_box
        
        landmarks = np.zeros((68, 2), dtype=np.float32)
        
        center_x = x + w / 2
        center_y = y + h / 2
        
        jaw_x = np.linspace(x + w * 0.1, x + w * 0.9, 17)
        jaw_y = y + h * 0.7 + np.sin(np.linspace(0, np.pi, 17)) * h * 0.1
        for i in range(17):
            landmarks[i] = [jaw_x[i], jaw_y[i]]
        
        brow_y = y + h * 0.35
        for i in range(5):
            landmarks[17 + i] = [x + w * (0.25 + i * 0.06), brow_y]
            landmarks[22 + i] = [x + w * (0.45 + i * 0.06), brow_y]
        
        nose_center_x = center_x
        nose_center_y = y + h * 0.55
        for i in range(4):
            landmarks[27 + i] = [nose_center_x, y + h * (0.35 + i * 0.05)]
        for i in range(5):
            landmarks[31 + i] = [nose_center_x + (i - 2) * w * 0.04, nose_center_y]
        
        eye_y = y + h * 0.4
        left_eye_x = x + w * 0.35
        right_eye_x = x + w * 0.65
        eye_radius = w * 0.06
        
        landmarks[36] = [left_eye_x - eye_radius, eye_y]
        landmarks[37] = [left_eye_x - eye_radius * 0.5, eye_y - eye_radius * 0.5]
        landmarks[38] = [left_eye_x + eye_radius * 0.5, eye_y - eye_radius * 0.5]
        landmarks[39] = [left_eye_x + eye_radius, eye_y]
        landmarks[40] = [left_eye_x + eye_radius * 0.5, eye_y + eye_radius * 0.5]
        landmarks[41] = [left_eye_x - eye_radius * 0.5, eye_y + eye_radius * 0.5]
        
        landmarks[42] = [right_eye_x - eye_radius, eye_y]
        landmarks[43] = [right_eye_x - eye_radius * 0.5, eye_y - eye_radius * 0.5]
        landmarks[44] = [right_eye_x + eye_radius * 0.5, eye_y - eye_radius * 0.5]
        landmarks[45] = [right_eye_x + eye_radius, eye_y]
        landmarks[46] = [right_eye_x + eye_radius * 0.5, eye_y + eye_radius * 0.5]
        landmarks[47] = [right_eye_x - eye_radius * 0.5, eye_y + eye_radius * 0.5]
        
        mouth_center_y = y + h * 0.75
        mouth_width = w * 0.3
        mouth_height = h * 0.08
        
        landmarks[48] = [center_x - mouth_width / 2, mouth_center_y]
        landmarks[49] = [center_x - mouth_width * 0.3, mouth_center_y - mouth_height * 0.3]
        landmarks[50] = [center_x - mouth_width * 0.1, mouth_center_y - mouth_height * 0.5]
        landmarks[51] = [center_x, mouth_center_y - mouth_height * 0.5]
        landmarks[52] = [center_x + mouth_width * 0.1, mouth_center_y - mouth_height * 0.5]
        landmarks[53] = [center_x + mouth_width * 0.3, mouth_center_y - mouth_height * 0.3]
        landmarks[54] = [center_x + mouth_width / 2, mouth_center_y]
        landmarks[55] = [center_x + mouth_width * 0.3, mouth_center_y + mouth_height * 0.3]
        landmarks[56] = [center_x + mouth_width * 0.1, mouth_center_y + mouth_height * 0.5]
        landmarks[57] = [center_x, mouth_center_y + mouth_height * 0.5]
        landmarks[58] = [center_x - mouth_width * 0.1, mouth_center_y + mouth_height * 0.5]
        landmarks[59] = [center_x - mouth_width * 0.3, mouth_center_y + mouth_height * 0.3]
        
        landmarks[60] = [center_x - mouth_width * 0.2, mouth_center_y]
        landmarks[61] = [center_x - mouth_width * 0.1, mouth_center_y - mouth_height * 0.2]
        landmarks[62] = [center_x, mouth_center_y - mouth_height * 0.2]
        landmarks[63] = [center_x + mouth_width * 0.1, mouth_center_y - mouth_height * 0.2]
        landmarks[64] = [center_x + mouth_width * 0.2, mouth_center_y]
        landmarks[65] = [center_x + mouth_width * 0.1, mouth_center_y + mouth_height * 0.2]
        landmarks[66] = [center_x, mouth_center_y + mouth_height * 0.2]
        landmarks[67] = [center_x - mouth_width * 0.1, mouth_center_y + mouth_height * 0.2]
        
        return landmarks
    
    def normalize_landmarks(self, landmarks, image_size):
        landmarks_normalized = landmarks.copy()
        landmarks_normalized[:, 0] = landmarks_normalized[:, 0] / image_size
        landmarks_normalized[:, 1] = landmarks_normalized[:, 1] / image_size
        return landmarks_normalized


def draw_landmarks(image, landmarks, color=(0, 255, 0), radius=2):
    img = image.copy()
    for i, (x, y) in enumerate(landmarks):
        cv2.circle(img, (int(x), int(y)), radius, color, -1)
    return img


def draw_face_box(image, face_box, color=(255, 0, 0), thickness=2):
    x, y, w, h = face_box
    img = cv2.rectangle(image.copy(), (x, y), (x + w, y + h), color, thickness)
    return img
