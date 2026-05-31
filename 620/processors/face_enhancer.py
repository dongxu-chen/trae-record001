import numpy as np
import cv2
from collections import deque
from config import FACE_ENHANCE_CONFIG


class FaceEnhancer:
    def __init__(self, config=None, device=None):
        self.config = config or FACE_ENHANCE_CONFIG
        self.enable = self.config.get('enable', False)
        self.face_scale = self.config.get('face_scale', 8)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        self.margin = self.config.get('margin', 0.2)
        self.blend_alpha = self.config.get('blend_alpha', 0.8)
        self.tracking = self.config.get('tracking', True)
        self.track_window = self.config.get('track_window', 5)
        
        self.device = device
        self.face_cascade = None
        self.net = None
        self.tracked_faces = deque(maxlen=self.track_window)
        
        self._init_detector()

    def _init_detector(self):
        try:
            model_file = "haarcascade_frontalface_default.xml"
            cascade_path = cv2.data.haarcascades + model_file
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except:
            self.face_cascade = None
        
        try:
            self.net = cv2.dnn.readNetFromCaffe(
                "deploy.prototxt",
                "res10_300x300_ssd_iter_140000_fp16.caffemodel"
            )
        except:
            try:
                self.net = cv2.dnn.readNetFromTensorflow(
                    "opencv_face_detector.pbtxt",
                    "opencv_face_detector_uint8.pb"
                )
            except:
                self.net = None

    def reset(self):
        self.tracked_faces.clear()

    def detect_faces_haar(self, frame):
        if self.face_cascade is None:
            return []
        
        gray = cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        
        return faces

    def detect_faces_dnn(self, frame):
        if self.net is None:
            return []
        
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            (frame * 255).astype(np.uint8), 1.0, (300, 300), (104.0, 177.0, 123.0), False, False
        )
        
        self.net.setInput(blob)
        detections = self.net.forward()
        
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > self.confidence_threshold:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x1, y1, x2, y2) = box.astype("int")
                faces.append((x1, y1, x2, y2, confidence))
        
        return faces

    def detect_faces(self, frame):
        faces = []
        
        if self.net is not None:
            faces = self.detect_faces_dnn(frame)
        elif self.face_cascade is not None:
            faces = self.detect_faces_haar(frame)
            faces = [(x, y, x + w, y + h, 0.9) for (x, y, w, h) in faces]
        
        if self.tracking and len(faces) == 0 and len(self.tracked_faces) > 0:
            faces = self._track_faces()
        
        if len(faces) > 0:
            self.tracked_faces.append(faces)
        
        return faces

    def _track_faces(self):
        if len(self.tracked_faces) == 0:
            return []
        
        last_faces = self.tracked_faces[-1]
        
        smoothed_faces = []
        for face in last_faces:
            x1, y1, x2, y2, conf = face
            smoothed_faces.append((x1, y1, x2, y2, conf * 0.8))
        
        return smoothed_faces

    def _expand_roi(self, frame, face):
        h, w = frame.shape[:2]
        x1, y1, x2, y2, conf = face
        
        face_w = x2 - x1
        face_h = y2 - y1
        
        margin_w = int(face_w * self.margin)
        margin_h = int(face_h * self.margin)
        
        x1 = max(0, x1 - margin_w)
        y1 = max(0, y1 - margin_h)
        x2 = min(w, x2 + margin_w)
        y2 = min(h, y2 + margin_h)
        
        return x1, y1, x2, y2

    def _sharpen_face(self, face_img, amount=1.5):
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]], dtype=np.float32) * (amount / 9.0)
        sharpened = cv2.filter2D(face_img, -1, kernel)
        return np.clip(sharpened, 0, 1)

    def _super_resolve_face(self, face_img, scale):
        h, w = face_img.shape[:2]
        new_size = (int(w * scale), int(h * scale))
        
        face_upsampled = cv2.resize(
            (face_img * 255).astype(np.uint8),
            new_size,
            interpolation=cv2.INTER_CUBIC
        ).astype(np.float32) / 255.0
        
        sharpened = self._sharpen_face(face_upsampled, amount=1.2)
        
        return sharpened

    def _blend_face(self, full_frame, enhanced_face, x1, y1, x2, y2):
        h, w = full_frame.shape[:2]
        
        roi_h = y2 - y1
        roi_w = x2 - x1
        
        enhanced_resized = cv2.resize(
            enhanced_face,
            (roi_w, roi_h),
            interpolation=cv2.INTER_AREA
        )
        
        mask = np.zeros_like(full_frame, dtype=np.float32)
        
        center = (x1 + roi_w // 2, y1 + roi_h // 2)
        axes = (roi_w // 2, roi_h // 2)
        cv2.ellipse(mask, center, axes, 0, 0, 360, (1, 1, 1), -1)
        
        mask = cv2.GaussianBlur(mask, (51, 51), 0)
        
        blended = (
            full_frame.astype(np.float32) * (1 - mask * self.blend_alpha) +
            enhanced_resized * mask * self.blend_alpha
        )
        
        return np.clip(blended, 0, 1).astype(np.float32)

    def enhance_faces(self, frame, sr_func=None):
        if not self.enable:
            return frame, []
        
        faces = self.detect_faces(frame)
        if len(faces) == 0:
            return frame, []
        
        enhanced_frame = frame.copy()
        enhanced_faces = []
        
        for face in faces:
            x1, y1, x2, y2, conf = face
            x1, y1, x2, y2 = self._expand_roi(frame, face)
            
            face_roi = frame[y1:y2, x1:x2]
            
            if sr_func is not None:
                enhanced_face = sr_func(face_roi)
            else:
                enhanced_face = self._super_resolve_face(face_roi, scale=self.face_scale)
            
            enhanced_frame = self._blend_face(enhanced_frame, enhanced_face, x1, y1, x2, y2)
            
            enhanced_faces.append({
                'bbox': (x1, y1, x2, y2),
                'confidence': conf,
            })
        
        return enhanced_frame, enhanced_faces

    def process(self, frame, sr_func=None):
        return self.enhance_faces(frame, sr_func)


def detect_faces_in_frame(frame, method='haar'):
    try:
        if method == 'haar':
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.1, 5)
            return [(x, y, x + w, y + h) for (x, y, w, h) in faces]
    except:
        return []


def align_face(face_img):
    try:
        eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        gray = cv2.cvtColor((face_img * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        eyes = eye_cascade.detectMultiScale(gray, 1.1, 5)
        
        if len(eyes) >= 2:
            (ex1, ey1, ew1, eh1) = eyes[0]
            (ex2, ey2, ew2, eh2) = eyes[1]
            
            eye1_center = (ex1 + ew1 // 2, ey1 + eh1 // 2)
            eye2_center = (ex2 + ew2 // 2, ey2 + eh2 // 2)
            
            if eye1_center[0] > eye2_center[0]:
                eye1_center, eye2_center = eye2_center, eye1_center
            
            dx = eye2_center[0] - eye1_center[0]
            dy = eye2_center[1] - eye1_center[1]
            angle = np.degrees(np.arctan2(dy, dx))
            
            h, w = face_img.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            aligned = cv2.warpAffine((face_img * 255).astype(np.uint8), M, (w, h))
            return aligned.astype(np.float32) / 255.0
    except:
        pass
    return face_img
