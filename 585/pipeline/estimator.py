import os
import numpy as np
import torch
import torchvision.transforms as transforms
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
import cv2
from PIL import Image

from utils.config import config
from models.smpl import SMPL
from models.hmr import HMR, WeakPerspectiveCamera
from detectors.openpose import OpenPoseDetector, PersonDetection, HandDetection
from utils.tracking import MultiPersonTracker, TrackedPerson
from utils.smoothing import PoseSmoother, SmoothedPose
from utils.keypoints import KeypointFusion
from utils.visualization import PoseVisualizer3D
from utils.occlusion import TemporalPoseCompleter, SymmetryAwareCompleter
from utils.hand_alignment import GlobalHandAligner, TemporalHandAligner, HandAlignmentResult
from utils.action_recognition import ActionRecognizer, ActionRecognitionResult
from utils.avatar import AvatarAnimationFrame, RealTimeAvatarDriver
from utils.pose_scoring import PoseScorer, PoseScoreResult


@dataclass
class PersonResult:
    track_id: int
    joints_3d: np.ndarray
    betas: np.ndarray
    pose: np.ndarray
    camera: np.ndarray
    reprojection_error: float
    bbox: Tuple[int, int, int, int]
    vertices: Optional[np.ndarray] = None
    hand_joints: Optional[np.ndarray] = None
    right_hand_result: Optional[HandAlignmentResult] = None
    left_hand_result: Optional[HandAlignmentResult] = None
    occlusion_mask: Optional[np.ndarray] = None
    completion_confidence: Optional[np.ndarray] = None
    adaptive_alpha: Optional[float] = None
    is_large_motion: Optional[bool] = None
    action_result: Optional[ActionRecognitionResult] = None
    avatar_frame: Optional[AvatarAnimationFrame] = None
    pose_score: Optional[PoseScoreResult] = None


@dataclass
class FrameResult:
    frame_id: int
    persons: List[PersonResult]
    image_with_2d: np.ndarray
    image_with_3d: Optional[np.ndarray]
    raw_image: np.ndarray


class HumanPoseEstimator3D:
    def __init__(self, config_obj=config):
        self.config = config_obj
        self.device = config_obj.DEVICE
        
        print(f"Initializing 3D Human Pose Estimator on {self.device}...")
        
        self._init_transforms()
        self._init_models()
        self._init_detector()
        self._init_tracker()
        self._init_smoother()
        self._init_fusion()
        self._init_occlusion_handler()
        self._init_hand_aligner()
        self._init_visualizer()
        self._init_action_recognizer()
        self._init_avatar_driver()
        self._init_pose_scorer()
        
        self.frame_count = 0
        
        print("Initialization complete!")
    
    def _init_transforms(self):
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((self.config.hmr.IMAGE_SIZE, self.config.hmr.IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=self.config.hmr.MEAN, std=self.config.hmr.STD)
        ])
    
    def _init_models(self):
        print("Loading SMPL model...")
        try:
            self.smpl = SMPL(self.config.hmr.SMPL_MODEL_PATH, device=self.device)
        except Exception as e:
            print(f"Warning: Could not load SMPL model: {e}")
            self.smpl = None
        
        print("Loading HMR model...")
        self.hmr = HMR(
            num_shape_params=self.config.hmr.SMPL_NUM_SHAPE_PARAMS,
            num_pose_params=self.config.hmr.SMPL_NUM_POSE_PARAMS,
            num_iterations=3,
            pretrained_backbone=True
        )
        self.hmr.to(self.device)
        self.hmr.eval()
        
        if os.path.exists(self.config.hmr.HMR_CHECKPOINT_PATH):
            self.hmr.load_pretrained(self.config.hmr.HMR_CHECKPOINT_PATH, self.device)
        
        self.camera = WeakPerspectiveCamera()
    
    def _init_detector(self):
        print("Loading OpenPose detector...")
        hand_proto = self.config.openpose.HAND_PROTO_PATH if self.config.ENABLE_HAND else None
        hand_weights = self.config.openpose.HAND_WEIGHTS_PATH if self.config.ENABLE_HAND else None
        
        self.openpose = OpenPoseDetector(
            proto_path=self.config.openpose.PROTO_PATH,
            weights_path=self.config.openpose.WEIGHTS_PATH,
            hand_proto_path=hand_proto,
            hand_weights_path=hand_weights,
            net_input_size=self.config.openpose.NET_INPUT_SIZE,
            threshold=self.config.openpose.THRESHOLD,
            device=self.device
        )
    
    def _init_tracker(self):
        print("Initializing multi-person tracker...")
        self.tracker = MultiPersonTracker(
            max_age=self.config.tracking.MAX_AGE,
            min_hits=self.config.tracking.MIN_HITS,
            iou_threshold=self.config.tracking.IOU_THRESHOLD,
            use_kalman=self.config.tracking.USE_KALMAN
        )
    
    def _init_smoother(self):
        print("Initializing temporal smoother...")
        self.smoother = PoseSmoother(
            method=self.config.smoothing.METHOD,
            alpha=self.config.smoothing.ALPHA,
            process_noise=self.config.smoothing.PROCESS_NOISE,
            measurement_noise=self.config.smoothing.MEASUREMENT_NOISE,
            num_joints=self.config.hmr.SMPL_NUM_JOINTS
        )
    
    def _init_fusion(self):
        print("Initializing keypoint fusion module...")
        self.fusion = KeypointFusion(
            num_body_joints=self.config.hmr.SMPL_NUM_JOINTS,
            device=self.device
        )
    
    def _init_occlusion_handler(self):
        print("Initializing occlusion reasoning module...")
        self.occlusion_completer = TemporalPoseCompleter(
            num_joints=self.config.hmr.SMPL_NUM_JOINTS,
            device=self.device
        )
        self.symmetry_completer = SymmetryAwareCompleter(
            num_joints=self.config.hmr.SMPL_NUM_JOINTS
        )
    
    def _init_hand_aligner(self):
        print("Initializing global hand alignment module...")
        self.hand_aligner = GlobalHandAligner(
            num_body_joints=self.config.hmr.SMPL_NUM_JOINTS
        )
        self.temporal_hand_aligner = TemporalHandAligner()
    
    def _init_visualizer(self):
        print("Initializing visualizer...")
        self.visualizer = PoseVisualizer3D(
            joint_size=self.config.visualization.JOINT_SIZE,
            line_width=self.config.visualization.LINE_WIDTH,
            figure_size=self.config.visualization.FIGURE_SIZE,
            enable_mesh=self.config.visualization.ENABLE_MESH
        )
    
    def _init_action_recognizer(self):
        print("Initializing action recognition module...")
        self.action_recognizer = ActionRecognizer(
            num_joints=self.config.hmr.SMPL_NUM_JOINTS,
            num_classes=15,
            sequence_length=60,
            overlap=30,
            device=self.device
        )
    
    def _init_avatar_driver(self):
        print("Initializing avatar driver module...")
        self.avatar_drivers = {}
        self._avatar_smpl_faces = None
    
    def _init_pose_scorer(self):
        print("Initializing pose scoring module...")
        self.pose_scorers = {}
    
    def _get_or_create_avatar_driver(self, track_id: int) -> RealTimeAvatarDriver:
        if track_id not in self.avatar_drivers:
            self.avatar_drivers[track_id] = RealTimeAvatarDriver(
                num_joints=self.config.hmr.SMPL_NUM_JOINTS,
                device=self.device
            )
        return self.avatar_drivers[track_id]
    
    def _get_or_create_pose_scorer(self, track_id: int) -> PoseScorer:
        if track_id not in self.pose_scorers:
            self.pose_scorers[track_id] = PoseScorer()
        return self.pose_scorers[track_id]
    
    def _crop_person(self, image: np.ndarray, bbox: Tuple[int, int, int, int],
                     padding: int = 20) -> Tuple[np.ndarray, torch.Tensor, Tuple[int, int, int, int]]:
        x, y, w, h = bbox
        
        x_min = max(0, x - padding)
        y_min = max(0, y - padding)
        x_max = min(image.shape[1], x + w + padding)
        y_max = min(image.shape[0], y + h + padding)
        
        person_crop = image[y_min:y_max, x_min:x_max]
        
        if person_crop.size == 0:
            return image, self.transform(image), (0, 0, image.shape[1], image.shape[0])
        
        person_tensor = self.transform(person_crop)
        
        new_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
        
        return person_crop, person_tensor, new_bbox
    
    def _estimate_single_person(self, person_image: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        with torch.no_grad():
            if person_image.ndim == 3:
                person_image = person_image.unsqueeze(0)
            
            person_image = person_image.to(self.device)
            
            betas, pose, camera = self.hmr(person_image)
            
            if self.smpl is not None:
                vertices, joints_3d = self.smpl(betas, pose)
            else:
                batch_size = betas.shape[0]
                joints_3d = torch.zeros(batch_size, self.config.hmr.SMPL_NUM_JOINTS, 3, device=self.device)
                vertices = None
            
            joints_2d = self.camera.project(joints_3d, camera)
        
        return joints_3d, joints_2d, vertices, betas, pose, camera
    
    def process_frame(self, image: np.ndarray, frame_id: Optional[int] = None) -> FrameResult:
        if frame_id is None:
            frame_id = self.frame_count
            self.frame_count += 1
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        person_detections = self.openpose.detect_keypoints(image_rgb)
        
        hand_detections = []
        if self.config.ENABLE_HAND:
            hand_detections = self.openpose.detect_hands(image_rgb, person_detections)
        
        image_with_2d = self.openpose.visualize(image, person_detections, hand_detections)
        
        tracked_persons = self.tracker.update(person_detections)
        
        for i, track in enumerate(tracked_persons):
            if track.track_id < len(person_detections):
                person_detections[i].person_id = track.track_id
        
        results = []
        for track in tracked_persons:
            person_crop, person_tensor, new_bbox = self._crop_person(image_rgb, track.bbox)
            
            joints_3d, joints_2d, vertices, betas, pose, camera = self._estimate_single_person(person_tensor)
            
            adaptive_alpha = None
            is_large_motion = None
            
            if self.config.ENABLE_TEMPORAL_SMOOTHING:
                smoothed = self.smoother.smooth(
                    track.track_id, joints_3d, betas, pose, camera
                )
                joints_3d = smoothed.joints_3d
                betas = smoothed.betas
                pose = smoothed.pose
                camera = smoothed.camera
                adaptive_alpha = smoothed.adaptive_alpha
                
                if self.smoother.use_adaptive and hasattr(self.smoother, 'motion_analyzer'):
                    is_large_motion = hasattr(self.smoother.motion_analyzer, 'motion_threshold')
                
                if self.smpl is not None:
                    betas_t = torch.tensor(betas, dtype=torch.float32, device=self.device).unsqueeze(0)
                    pose_t = torch.tensor(pose, dtype=torch.float32, device=self.device).unsqueeze(0)
                    vertices, _ = self.smpl(betas_t, pose_t)
                    vertices = vertices.detach().cpu().numpy()[0]
            else:
                joints_3d = joints_3d.detach().cpu().numpy()[0]
                betas = betas.detach().cpu().numpy()[0]
                pose = pose.detach().cpu().numpy()[0]
                camera = camera.detach().cpu().numpy()[0]
                if vertices is not None:
                    vertices = vertices.detach().cpu().numpy()[0]
            
            occlusion_mask = None
            completion_confidence = None
            if hasattr(self, 'occlusion_completer'):
                completion_result = self.occlusion_completer.process_frame(
                    track.track_id, joints_3d, track.keypoints
                )
                joints_3d[:self.config.hmr.SMPL_NUM_JOINTS] = completion_result.joints_3d
                occlusion_mask = completion_result.occlusion_mask
                completion_confidence = completion_result.completion_confidence
                
                joints_3d[:self.config.hmr.SMPL_NUM_JOINTS] = self.symmetry_completer.apply_symmetry(
                    joints_3d[:self.config.hmr.SMPL_NUM_JOINTS], occlusion_mask
                )
            
            hand_joints_3d = None
            right_hand_result = None
            left_hand_result = None
            
            if self.config.ENABLE_HAND and len(hand_detections) > 0:
                person_hands = [h for h in hand_detections if self._is_hand_matching(h, track.bbox)]
                
                if len(person_hands) > 0:
                    right_hand = None
                    left_hand = None
                    for hand in person_hands:
                        if hand.hand_side == 'right':
                            right_hand = hand
                        else:
                            left_hand = hand
                    
                    if right_hand is not None:
                        right_hand_result = self.hand_aligner.align_hand_to_body(
                            right_hand.keypoints, joints_3d, camera, 'right'
                        )
                        if hasattr(self, 'temporal_hand_aligner'):
                            right_hand_result = self.temporal_hand_aligner.update(
                                track.track_id, 'right', right_hand_result
                            )
                    
                    if left_hand is not None:
                        left_hand_result = self.hand_aligner.align_hand_to_body(
                            left_hand.keypoints, joints_3d, camera, 'left'
                        )
                        if hasattr(self, 'temporal_hand_aligner'):
                            left_hand_result = self.temporal_hand_aligner.update(
                                track.track_id, 'left', left_hand_result
                            )
                    
                    joints_3d = self.hand_aligner.merge_hands_with_body(
                        joints_3d[:self.config.hmr.SMPL_NUM_JOINTS],
                        right_hand_result,
                        left_hand_result
                    )
                    hand_joints_3d = joints_3d[self.config.hmr.SMPL_NUM_JOINTS:]
            
            reprojection_error = self.fusion.compute_reprojection_error(
                joints_3d, track.keypoints, camera
            )
            
            action_result = None
            if hasattr(self, 'action_recognizer'):
                action_result = self.action_recognizer.update_pose(
                    track.track_id, joints_3d[:self.config.hmr.SMPL_NUM_JOINTS]
                )
            
            avatar_frame = None
            if hasattr(self, 'avatar_drivers'):
                avatar_driver = self._get_or_create_avatar_driver(track.track_id)
                action_name = action_result.action_name if action_result else None
                
                if self._avatar_smpl_faces is None and vertices is not None:
                    self._avatar_smpl_faces = self.get_smpl_faces()
                
                avatar_frame = avatar_driver.update(
                    joints_3d,
                    mesh_vertices=vertices,
                    mesh_faces=self._avatar_smpl_faces,
                    action_name=action_name
                )
            
            pose_score = None
            if hasattr(self, 'pose_scorers'):
                try:
                    pose_scorer = self._get_or_create_pose_scorer(track.track_id)
                    action_name = action_result.action_name if action_result else None
                    pose_score = pose_scorer.score_pose(
                        joints_3d[:self.config.hmr.SMPL_NUM_JOINTS],
                        action_name=action_name
                    )
                except Exception as e:
                    print(f"Pose scoring error: {e}")
            
            result = PersonResult(
                track_id=track.track_id,
                joints_3d=joints_3d,
                vertices=vertices,
                betas=betas,
                pose=pose,
                camera=camera,
                hand_joints=hand_joints_3d,
                right_hand_result=right_hand_result,
                left_hand_result=left_hand_result,
                reprojection_error=reprojection_error,
                bbox=new_bbox,
                occlusion_mask=occlusion_mask,
                completion_confidence=completion_confidence,
                adaptive_alpha=adaptive_alpha,
                is_large_motion=is_large_motion,
                action_result=action_result,
                avatar_frame=avatar_frame,
                pose_score=pose_score
            )
            results.append(result)
        
        image_with_3d = None
        if len(results) > 0:
            image_with_3d = self._visualize_results(image, results)
        
        return FrameResult(
            frame_id=frame_id,
            persons=results,
            image_with_2d=image_with_2d,
            image_with_3d=image_with_3d,
            raw_image=image
        )
    
    def _is_hand_matching(self, hand: HandDetection, bbox: Tuple[int, int, int, int]) -> bool:
        hx, hy, hw, hh = hand.bbox
        px, py, pw, ph = bbox
        
        hand_center = (hx + hw / 2, hy + hh / 2)
        person_center = (px + pw / 2, py + ph / 2)
        
        dist = np.sqrt((hand_center[0] - person_center[0]) ** 2 + 
                      (hand_center[1] - person_center[1]) ** 2)
        
        return dist < max(pw, ph) * 0.8
    
    def _visualize_results(self, image: np.ndarray, results: List[PersonResult]) -> np.ndarray:
        if len(results) == 0:
            return image
        
        if len(results) == 1:
            result = results[0]
            return self.visualizer.visualize_with_image(
                image, result.joints_3d,
                hand_joints=result.hand_joints,
                title=f"Person {result.track_id}"
            )
        else:
            all_joints = [r.joints_3d for r in results]
            track_ids = [r.track_id for r in results]
            fig = self.visualizer.plot_multiple_poses(all_joints, track_ids)
            img_3d = self.visualizer.figure_to_image(fig)
            
            h1, w1 = image.shape[:2]
            h2, w2 = img_3d.shape[:2]
            target_height = max(h1, h2)
            image_resized = cv2.resize(image, (int(w1 * target_height / h1), target_height))
            img_3d_resized = cv2.resize(img_3d, (int(w2 * target_height / h2), target_height))
            
            return np.hstack([image_resized, img_3d_resized])
    
    def process_video(self, video_path: str, output_path: Optional[str] = None,
                       max_frames: Optional[int] = None) -> List[FrameResult]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        results = []
        frame_idx = 0
        
        if output_path is not None:
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 2)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if max_frames is not None and frame_idx >= max_frames:
                    break
                
                result = self.process_frame(frame, frame_idx)
                results.append(result)
                
                if output_path is not None and result.image_with_3d is not None:
                    writer.write(result.image_with_3d)
                
                frame_idx += 1
                
                if frame_idx % 10 == 0:
                    print(f"Processed {frame_idx} frames...")
        
        finally:
            cap.release()
            if output_path is not None:
                writer.release()
        
        print(f"Processed {len(results)} frames total.")
        return results
    
    def process_image_file(self, image_path: str) -> FrameResult:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        return self.process_frame(image)
    
    def reset(self):
        self.tracker.reset()
        self.smoother.reset()
        if hasattr(self, 'occlusion_completer'):
            self.occlusion_completer.reset()
        if hasattr(self, 'temporal_hand_aligner'):
            self.temporal_hand_aligner.reset()
        if hasattr(self, 'action_recognizer'):
            self.action_recognizer.reset()
        if hasattr(self, 'avatar_drivers'):
            for driver in self.avatar_drivers.values():
                driver.close()
                driver.reset()
            self.avatar_drivers.clear()
            self._avatar_smpl_faces = None
        if hasattr(self, 'pose_scorers'):
            for scorer in self.pose_scorers.values():
                scorer.reset()
            self.pose_scorers.clear()
        self.frame_count = 0
    
    def get_smpl_faces(self) -> Optional[np.ndarray]:
        if self.smpl is not None:
            return self.smpl.get_faces()
        return None
