import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


@dataclass
class Defect3D:
    id: int
    class_id: int
    class_name: str
    confidence: float
    center_3d: Tuple[float, float, float]
    size_3d: Tuple[float, float, float]
    volume: float
    depth: float
    orientation: Tuple[float, float, float]
    views_detected: List[int] = field(default_factory=list)
    bbox_2d: Dict[int, Tuple[float, float, float, float]] = field(default_factory=dict)


@dataclass
class CameraParams:
    angle: float
    distance: float
    source_to_detector: float
    pixel_size: float
    intrinsic: Tuple[float, float] = (0.2, 0.2)
    rotation_axis: Tuple[float, float, float] = (0, 1, 0)


class MultiViewImageReg:
    def __init__(self, num_views: int = 3, angular_range: float = 30.0, camera_distance: float = 1000.0):
        self.num_views = num_views
        self.angular_range = angular_range
        self.camera_distance = camera_distance
        self.camera_params = self._generate_camera_params()

    def _generate_camera_params(self) -> List[CameraParams]:
        params = []
        angles = np.linspace(-self.angular_range / 2, self.angular_range / 2, self.num_views)
        for angle in angles:
            params.append(CameraParams(
                angle=angle,
                distance=self.camera_distance,
                source_to_detector=self.camera_distance * 2,
                pixel_size=0.2
            ))
        return params

    def register_images(self, images: List[np.ndarray],
                        reference_idx: int = 0) -> List[np.ndarray]:
        if len(images) != self.num_views:
            raise ValueError(f"Expected {self.num_views} images, got {len(images)}")

        registered = []
        ref_img = images[reference_idx]

        for i, img in enumerate(images):
            if i == reference_idx:
                registered.append(img.copy())
                continue

            try:
                aligned = self._register_pair(ref_img, img)
                registered.append(aligned)
            except Exception as e:
                print(f"Warning: Failed to register view {i}, using original: {e}")
                registered.append(img.copy())

        return registered

    def _register_pair(self, ref_img: np.ndarray, img: np.ndarray) -> np.ndarray:
        if len(ref_img.shape) == 3:
            ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
        else:
            ref_gray = ref_img.copy()

        if len(img.shape) == 3:
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = img.copy()

        orb = cv2.ORB_create(nfeatures=2000)
        kp1, des1 = orb.detectAndCompute(ref_gray, None)
        kp2, des2 = orb.detectAndCompute(img_gray, None)

        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            return img.copy()

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        if len(matches) < 10:
            return img.copy()

        matches = sorted(matches, key=lambda x: x.distance)
        good_matches = matches[:min(100, len(matches))]

        src_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        if H is None:
            return img.copy()

        h, w = ref_gray.shape
        aligned = cv2.warpPerspective(img, H, (w, h))

        return aligned


class Defect3DReconstructor:
    def __init__(self, num_views: int = 3, angular_range: float = 30.0,
                 camera_distance: float = 1000.0, pixel_size: float = 0.2):
        self.num_views = num_views
        self.angular_range = angular_range
        self.camera_distance = camera_distance
        self.pixel_size = pixel_size

        self.image_reg = MultiViewImageReg(num_views, angular_range, camera_distance)
        self.camera_params = self.image_reg.camera_params

    def _project_3d_to_2d(self, point_3d: Tuple[float, float, float],
                           camera_param: CameraParams) -> Tuple[float, float]:
        angle_rad = np.radians(camera_param.angle)

        R = np.array([
            [np.cos(angle_rad), 0, np.sin(angle_rad)],
            [0, 1, 0],
            [-np.sin(angle_rad), 0, np.cos(angle_rad)]
        ])

        point_rotated = R @ np.array(point_3d)

        z = point_rotated[2] + camera_param.distance
        if z <= 0:
            return (0, 0)

        scale = camera_param.source_to_detector / z

        x_2d = point_rotated[0] * scale / self.pixel_size
        y_2d = point_rotated[1] * scale / self.pixel_size

        return (x_2d, y_2d)

    def _back_project_2d_to_3d(self, point_2d: Tuple[float, float],
                             camera_param: CameraParams,
                             estimated_depth: float) -> Tuple[float, float, float]:
        angle_rad = np.radians(camera_param.angle)

        z = camera_param.distance + estimated_depth

        scale = z / camera_param.source_to_detector

        x_3d = point_2d[0] * self.pixel_size * scale
        y_3d = point_2d[1] * self.pixel_size * scale

        point_rotated = np.array([x_3d, y_3d, estimated_depth])

        R_inv = np.array([
            [np.cos(angle_rad), 0, -np.sin(angle_rad)],
            [0, 1, 0],
            [np.sin(angle_rad), 0, np.cos(angle_rad)]
        ])

        point_3d = R_inv @ point_rotated
        return tuple(point_3d)

    def _estimate_depth_from_parallax(self, points_2d: List[Tuple[float, float]],
                                    camera_params: List[CameraParams]) -> float:
        if len(points_2d) < 2:
            return 0.0

        disparities = []
        for i in range(len(points_2d)):
            for j in range(i + 1, len(points_2d)):
                dx = points_2d[i][0] - points_2d[j][0]
                dy = points_2d[i][1] - points_2d[j][1]
                disparity = np.sqrt(dx * dx + dy * dy)

                angle_diff = abs(camera_params[i].angle - camera_params[j].angle)
                if angle_diff > 0:
                    depth = (disparity * self.pixel_size * camera_params[i].source_to_detector) / (
                        2 * np.tan(np.radians(angle_diff / 2))
                    )
                    disparities.append(depth)

        return float(np.mean(disparities)) if disparities else 0.0

    def _match_defects_across_views(self, detections_per_view: List[List[Dict[str, Any]]],
                                     registered_images: List[np.ndarray]) -> List[Defect3D]:
        if len(detections_per_view) < 2:
            return []

        matched_defects = []
        defect_id_counter = 0

        for view_idx, detections in enumerate(detections_per_view):
            for det in detections:
                center_2d = (det['bbox']['center_x'], det['bbox']['center_y'])
                size_2d = (det['bbox']['width'], det['bbox']['height'])

                matched = False
                for existing_defect in matched_defects:
                    existing_points = [existing_defect.bbox_2d[v] for v in existing_defect.bbox_2d
                                    if v < view_idx]

                    if len(existing_points) >= 1:
                        last_view = max(existing_defect.bbox_2d.keys())
                        last_center = (
                            existing_defect.bbox_2d[last_view][0] + existing_defect.bbox_2d[last_view][2]) / 2, \
                            (existing_defect.bbox_2d[last_view][1] + existing_defect.bbox_2d[last_view][3]) / 2

                        dist = np.sqrt((center_2d[0] - last_center[0]) ** 2 + \
                               (center_2d[1] - last_center[1]) ** 2)

                        max_dist = max(size_2d[0], size_2d[1],
                                       existing_defect.bbox_2d[last_view][2] - existing_defect.bbox_2d[last_view][0],
                                       existing_defect.bbox_2d[last_view][3] - existing_defect.bbox_2d[last_view][1])

                        if dist < max_dist * 1.5 and det['class_id'] == existing_defect.class_id:
                            existing_defect.bbox_2d[view_idx] = (det['bbox']['x1'], det['bbox']['y1'],
                                                                det['bbox']['x2'], det['bbox']['y2'])
                            existing_defect.views_detected.append(view_idx)
                            if det['confidence'] > existing_defect.confidence:
                                existing_defect.confidence = det['confidence']
                            matched = True
                            break

                if not matched:
                    new_defect = Defect3D(
                        id=defect_id_counter,
                        class_id=det['class_id'],
                        class_name=det['class_name'],
                        confidence=det['confidence'],
                        center_3d=(0.0, 0.0, 0.0),
                        size_3d=(0.0, 0.0, 0.0),
                        volume=0.0,
                        depth=0.0,
                        orientation=(0.0, 0.0, 0.0),
                        views_detected=[view_idx],
                        bbox_2d={view_idx: (det['bbox']['x1'], det['bbox']['y1'],
                                              det['bbox']['x2'], det['bbox']['y2'])}
                    )
                    matched_defects.append(new_defect)
                    defect_id_counter += 1

        return matched_defects

    def reconstruct_3d(self, images: List[np.ndarray],
                      detections_per_view: List[List[Dict[str, Any]]]) -> List[Defect3D]:
        if len(images) != self.num_views:
            raise ValueError(f"Expected {self.num_views} images, got {len(images)}")

        if len(detections_per_view) != self.num_views:
            raise ValueError(f"Expected {self.num_views} detection lists, got {len(detections_per_view)}")

        print("\n" + "=" * 60)
        print("3D Defect Reconstruction")
        print("=" * 60)
        print(f"Number of views: {self.num_views}")
        print(f"Angular range: ±{self.angular_range / 2}°")
        print(f"Camera distance: {self.camera_distance} mm")
        print("=" * 60 + "\n")

        print("Registering multi-view images...")
        registered_images = self.image_reg.register_images(images)
        print("Image registration complete.")

        print("Matching defects across views...")
        matched_defects = self._match_defects_across_views(detections_per_view, registered_images)
        print(f"Found {len(matched_defects)} unique defects across views.")

        print("Reconstructing 3D positions...")
        for defect in matched_defects:
            if len(defect.views_detected) >= 2:
                centers_2d = []
                sizes_2d = []
                camera_params_used = []

                for view_idx in defect.views_detected:
                    bbox = defect.bbox_2d[view_idx]
                    center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                    size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
                    centers_2d.append(center)
                    sizes_2d.append(size)
                    camera_params_used.append(self.camera_params[view_idx])

                depth = self._estimate_depth_from_parallax(centers_2d, camera_params_used)

                points_3d = []
                for center, size, cam_param in zip(centers_2d, sizes_2d, camera_params_used):
                    pt3d = self._back_project_2d_to_3d(center, cam_param, depth)
                    points_3d.append(pt3d)

                if points_3d:
                    center_3d = tuple(np.mean(points_3d, axis=0))

                    sizes_3d_x = []
                    sizes_3d_y = []
                    sizes_3d_z = []

                    for (w, h), cam_param in zip(sizes_2d, camera_params_used):
                        pt1 = self._back_project_2d_to_3d(
                            (centers_2d[0][0] - w / 2, centers_2d[0][1]), cam_param, depth)
                        pt2 = self._back_project_2d_to_3d(
                            (centers_2d[0][0] + w / 2, centers_2d[0][1]), cam_param, depth)
                        pt3 = self._back_project_2d_to_3d(
                            (centers_2d[0][0], centers_2d[0][1] - h / 2), cam_param, depth)
                        pt4 = self._back_project_2d_to_3d(
                            (centers_2d[0][0], centers_2d[0][1] + h / 2), cam_param, depth)

                        sizes_3d_x.append(np.linalg.norm(np.array(pt1) - np.array(pt2)))
                        sizes_3d_y.append(np.linalg.norm(np.array(pt3) - np.array(pt4)))

                    size_x = float(np.mean(sizes_3d_x)) if sizes_3d_x else 0.0
                    size_y = float(np.mean(sizes_3d_y)) if sizes_3d_y else 0.0
                    size_z = size_x * 0.5

                    volume = size_x * size_y * size_z * np.pi / 6

                    defect.center_3d = center_3d
                    defect.size_3d = (size_x, size_y, size_z)
                    defect.volume = volume
                    defect.depth = depth

                    if len(points_3d) >= 2:
                        vec = np.array(points_3d[-1]) - np.array(points_3d[0])
                        if np.linalg.norm(vec) > 0:
                            vec = vec / np.linalg.norm(vec)
                            defect.orientation = tuple(vec)

        print(f"3D reconstruction complete for {len(matched_defects)} defects.")

        return matched_defects

    def visualize_3d(self, defects: List[Defect3D], output_path: Optional[str] = None):
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        class_colors = {
            0: 'green',
            1: 'red',
            2: 'blue'
        }

        for defect in defects:
            color = class_colors.get(defect.class_id, 'gray')

            ax.scatter(defect.center_3d[0], defect.center_3d[1], defect.center_3d[2],
                        c=color, s=100, marker='o', alpha=0.8,
                        label=f"{defect.class_name} (ID:{defect.id})")

            size = max(defect.size_3d) if defect.size_3d[0] > 0 else 5
            ax.scatter(defect.center_3d[0], defect.center_3d[1], defect.center_3d[2],
                        c=color, s=size * 10, marker='^', alpha=0.3)

        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('3D Defect Reconstruction')

        ax.set_box_aspect([1, 1, 1])

        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='green', label='Porosity'),
                         Patch(facecolor='red', label='Crack'),
                         Patch(facecolor='blue', label='Slag Inclusion')]
        ax.legend(handles=legend_elements, loc='upper right')

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"3D visualization saved to: {output_path}")

        plt.close()

    def save_3d_results(self, defects: List[Defect3D], output_path: str):
        results = []
        for defect in defects:
            results.append({
                'id': defect.id,
                'class_id': defect.class_id,
                'class_name': defect.class_name,
                'confidence': defect.confidence,
                'center_3d': {
                    'x': defect.center_3d[0],
                    'y': defect.center_3d[1],
                    'z': defect.center_3d[2]
                },
                'size_3d': {
                    'x': defect.size_3d[0],
                    'y': defect.size_3d[1],
                    'z': defect.size_3d[2]
                },
                'volume': defect.volume,
                'depth': defect.depth,
                'orientation': {
                    'x': defect.orientation[0],
                    'y': defect.orientation[1],
                    'z': defect.orientation[2]
                },
                'views_detected': defect.views_detected,
                'bbox_2d': {str(k): list(v) for k, v in defect.bbox_2d.items()}
            })

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"3D results saved to: {output_path}")


class MultiViewDefectDetector:
    def __init__(self, detector, num_views: int = 3,
                 angular_range: float = 30.0, camera_distance: float = 1000.0):
        self.detector = detector
        self.reconstructor = Defect3DReconstructor(
            num_views=num_views,
            angular_range=angular_range,
            camera_distance=camera_distance
        )
        self.num_views = num_views

    def detect_multi_view(self, image_paths: List[str],
                         output_dir: str = None,
                         visualize: bool = True) -> Dict[str, Any]:
        if len(image_paths) != self.num_views:
            raise ValueError(f"Expected {self.num_views} image paths, got {len(image_paths)}")

        images = []
        detections_per_view = []

        print("\n" + "=" * 60)
        print("Multi-View Defect Detection with 3D Reconstruction")
        print("=" * 60)

        for i, path in enumerate(image_paths):
            print(f"\nProcessing view {i + 1}/{self.num_views}: {Path(path).name}")

            img = cv2.imread(path)
            if img is None:
                raise ValueError(f"Failed to load image: {path}")

            images.append(img)

            detections, _ = self.detector.detect(img, verbose=False)
            detections_per_view.append(detections)

            print(f"  Found {len(detections)} defects")

        print("\nReconstructing 3D defect positions...")
        defects_3d = self.reconstructor.reconstruct_3d(images, detections_per_view)

        result = {
            'num_views': self.num_views,
            'image_paths': image_paths,
            'detections_per_view': detections_per_view,
            'defects_3d': defects_3d,
            'num_defects_3d': len(defects_3d)
        }

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

            json_path = os.path.join(output_dir, 'defects_3d.json')
            self.reconstructor.save_3d_results(defects_3d, json_path)
            result['json_path'] = json_path

            if visualize:
                vis_path = os.path.join(output_dir, 'defects_3d_visualization.png')
                self.reconstructor.visualize_3d(defects_3d, vis_path)
                result['visualization_path'] = vis_path

            for i, (img, dets) in enumerate(zip(images, detections_per_view)):
                vis_img = self.detector.visualize(img, dets)
                vis_path = os.path.join(output_dir, f'view_{i}_result.jpg')
                cv2.imwrite(vis_path, vis_img)

        print("\n" + "=" * 60)
        print("3D Reconstruction Summary")
        print("=" * 60)
        print(f"Total defects reconstructed: {len(defects_3d)}")
        for defect in defects_3d:
            print(f"\nDefect {defect.id} - {defect.class_name}")
            print(f"  Confidence: {defect.confidence:.3f}")
            print(f"  3D Center: ({defect.center_3d[0]:.2f}, {defect.center_3d[1]:.2f}, {defect.center_3d[2]:.2f}) mm")
            print(f"  Size: {defect.size_3d[0]:.2f} x {defect.size_3d[1]:.2f} x {defect.size_3d[2]:.2f} mm")
            print(f"  Volume: {defect.volume:.2f} mm³")
            print(f"  Depth: {defect.depth:.2f} mm")
            print(f"  Views detected: {defect.views_detected}")
        print("=" * 60 + "\n")

        return result
