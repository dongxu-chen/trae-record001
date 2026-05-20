import numpy as np
from typing import Optional, Tuple, List
from scipy.ndimage import median_filter, gaussian_filter


class WorkspaceAnalyzer:
    def __init__(self, robot_kinematics):
        self.robot = robot_kinematics

    def sample_workspace(
        self,
        num_samples: int = 10000,
        joint_limits: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        filter_singular: bool = False,
        singular_threshold: float = 1e-3,
        remove_outliers: bool = False,
        outlier_threshold: float = 3.0,
    ) -> np.ndarray:
        if joint_limits is None:
            lower, upper = self.robot.get_joint_limits()
        else:
            lower, upper = joint_limits

        lower = np.asarray(lower, dtype=float)
        upper = np.asarray(upper, dtype=float)

        n_joints = self.robot.model.nq
        target_samples = num_samples
        positions = []
        joint_configs = []

        while len(positions) < target_samples:
            batch_size = min(1000, target_samples - len(positions))
            joint_batch = np.random.uniform(
                lower, upper, size=(batch_size, n_joints)
            )

            for q in joint_batch:
                if filter_singular and self.robot.is_singular(q, singular_threshold):
                    continue

                pos = self.robot.get_frame_position(
                    q, self.robot.end_effector_name
                )

                if np.any(np.isnan(pos)) or np.any(np.isinf(pos)):
                    continue

                positions.append(pos)
                joint_configs.append(q)

                if len(positions) >= target_samples:
                    break

        positions = np.array(positions)

        if remove_outliers and len(positions) > 10:
            positions = self._remove_outliers(positions, outlier_threshold)

        return positions

    def _remove_outliers(self, positions: np.ndarray, threshold: float) -> np.ndarray:
        mean = np.mean(positions, axis=0)
        std = np.std(positions, axis=0)

        std_safe = np.where(std < 1e-10, 1.0, std)
        z_scores = np.abs((positions - mean) / std_safe)

        valid = np.all(z_scores < threshold, axis=1)
        return positions[valid]

    def sample_workspace_with_info(
        self,
        num_samples: int = 10000,
        joint_limits: Optional[Tuple[np.ndarray, np.ndarray]] = None,
    ) -> dict:
        if joint_limits is None:
            lower, upper = self.robot.get_joint_limits()
        else:
            lower, upper = joint_limits

        lower = np.asarray(lower, dtype=float)
        upper = np.asarray(upper, dtype=float)

        n_joints = self.robot.model.nq
        joint_samples = np.random.uniform(
            lower, upper, size=(num_samples, n_joints)
        )

        positions = np.zeros((num_samples, 3))
        manipulability = np.zeros(num_samples)
        condition_numbers = np.zeros(num_samples)
        is_singular = np.zeros(num_samples, dtype=bool)

        for i in range(num_samples):
            q = joint_samples[i]
            positions[i] = self.robot.get_frame_position(
                q, self.robot.end_effector_name
            )
            manipulability[i] = self.robot.manipulability(q)
            condition_numbers[i] = self.robot.condition_number(q)
            is_singular[i] = self.robot.is_singular(q)

        return {
            'positions': positions,
            'joint_configs': joint_samples,
            'manipulability': manipulability,
            'condition_numbers': condition_numbers,
            'is_singular': is_singular,
        }

    def filter_singular_configurations(
        self,
        joint_configs: np.ndarray,
        singular_threshold: float = 1e-3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        valid_mask = np.array([
            not self.robot.is_singular(q, singular_threshold)
            for q in joint_configs
        ])
        return joint_configs[valid_mask], valid_mask

    def smooth_trajectory(
        self,
        waypoints: np.ndarray,
        method: str = 'gaussian',
        sigma: float = 1.0,
        kernel_size: int = 5,
    ) -> np.ndarray:
        waypoints = np.asarray(waypoints, dtype=float)

        if method == 'gaussian':
            smoothed = np.zeros_like(waypoints)
            for i in range(3):
                smoothed[:, i] = gaussian_filter(waypoints[:, i], sigma=sigma)
        elif method == 'median':
            smoothed = np.zeros_like(waypoints)
            for i in range(3):
                smoothed[:, i] = median_filter(
                    waypoints[:, i], size=kernel_size
                )
        elif method == 'savgol':
            from scipy.signal import savgol_filter
            smoothed = np.zeros_like(waypoints)
            window_length = min(kernel_size, len(waypoints) // 2 * 2 + 1)
            if window_length < 5:
                window_length = 5
            polyorder = min(2, window_length - 1)
            for i in range(3):
                smoothed[:, i] = savgol_filter(
                    waypoints[:, i], window_length=window_length,
                    polyorder=polyorder
                )
        elif method == 'moving_average':
            kernel = np.ones(kernel_size) / kernel_size
            smoothed = np.zeros_like(waypoints)
            for i in range(3):
                smoothed[:, i] = np.convolve(
                    waypoints[:, i], kernel, mode='same'
                )
        else:
            raise ValueError(f"Unknown smoothing method: {method}")

        return smoothed

    def compute_workspace_bounds(
        self,
        num_samples: int = 10000,
        filter_outliers: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        positions = self.sample_workspace(num_samples, remove_outliers=filter_outliers)
        min_bound = np.min(positions, axis=0)
        max_bound = np.max(positions, axis=0)
        return min_bound, max_bound

    def voxelize_workspace(
        self,
        resolution: float = 0.05,
        num_samples: int = 50000,
        bounds: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        filter_singular: bool = False,
        smooth_voxels: bool = False,
        smooth_sigma: float = 1.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        positions = self.sample_workspace(
            num_samples,
            filter_singular=filter_singular,
            remove_outliers=True
        )

        if bounds is None:
            min_bound, max_bound = self.compute_workspace_bounds(num_samples)
        else:
            min_bound, max_bound = bounds

        min_bound = np.asarray(min_bound, dtype=float)
        max_bound = np.asarray(max_bound, dtype=float)

        dims = np.ceil((max_bound - min_bound) / resolution).astype(int)
        voxel_grid = np.zeros(dims, dtype=float)

        for pos in positions:
            idx = np.floor((pos - min_bound) / resolution).astype(int)
            if np.all(idx >= 0) and np.all(idx < dims):
                voxel_grid[tuple(idx)] += 1

        if smooth_voxels and np.all(dims > 3):
            voxel_grid = gaussian_filter(voxel_grid, sigma=smooth_sigma)

        return voxel_grid > 0, min_bound, max_bound

    def compute_manipulability_map(
        self,
        resolution: float = 0.1,
        num_samples_per_voxel: int = 10,
        bounds: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        filter_singular: bool = True,
        smooth_map: bool = True,
        smooth_sigma: float = 1.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        info = self.sample_workspace_with_info(num_samples_per_voxel * 10000)
        positions = info['positions']
        manipulability_vals = info['manipulability']
        is_singular = info['is_singular']

        if filter_singular:
            valid = ~is_singular
            positions = positions[valid]
            manipulability_vals = manipulability_vals[valid]

        if bounds is None:
            min_bound, max_bound = self.compute_workspace_bounds()
        else:
            min_bound, max_bound = bounds

        min_bound = np.asarray(min_bound, dtype=float)
        max_bound = np.asarray(max_bound, dtype=float)

        dims = np.ceil((max_bound - min_bound) / resolution).astype(int)
        manipulability_map = np.zeros(dims, dtype=float)
        voxel_counts = np.zeros(dims, dtype=int)

        for pos, manip in zip(positions, manipulability_vals):
            idx = np.floor((pos - min_bound) / resolution).astype(int)
            if np.all(idx >= 0) and np.all(idx < dims):
                voxel_idx = tuple(idx)
                manipulability_map[voxel_idx] += manip
                voxel_counts[voxel_idx] += 1

        with np.errstate(divide='ignore', invalid='ignore'):
            average_manipulability = np.where(
                voxel_counts > 0,
                manipulability_map / voxel_counts,
                0
            )

        if smooth_map and np.all(dims > 3):
            average_manipulability = gaussian_filter(
                average_manipulability, sigma=smooth_sigma
            )

        return average_manipulability, voxel_counts > 0, min_bound, max_bound

    def get_reachable_positions(
        self,
        positions: np.ndarray,
        tolerance: float = 0.02,
        avoid_singular: bool = False,
    ) -> np.ndarray:
        positions = np.asarray(positions, dtype=float)
        reachable = np.zeros(positions.shape[0], dtype=bool)

        for i, pos in enumerate(positions):
            q, success, error = self.robot.inverse_kinematics_position(
                pos, max_iter=200, tolerance=tolerance
            )
            if success and error < tolerance:
                if avoid_singular and self.robot.is_singular(q):
                    reachable[i] = False
                else:
                    reachable[i] = True

        return reachable

    def compute_workspace_volume(
        self,
        resolution: float = 0.05,
        num_samples: int = 50000,
        filter_singular: bool = False,
    ) -> float:
        voxel_grid, min_bound, max_bound = self.voxelize_workspace(
            resolution, num_samples, filter_singular=filter_singular
        )
        voxel_volume = resolution ** 3
        num_voxels = np.sum(voxel_grid)
        return num_voxels * voxel_volume

    def visualize_workspace(
        self,
        visualizer,
        num_samples: int = 5000,
        color: str = 'blue',
        point_size: float = 0.005,
        filter_singular: bool = False,
        color_by_manipulability: bool = False,
    ):
        if color_by_manipulability:
            info = self.sample_workspace_with_info(num_samples)
            positions = info['positions']
            manip = info['manipulability']

            if filter_singular:
                valid = ~info['is_singular']
                positions = positions[valid]
                manip = manip[valid]

            colors = np.zeros_like(positions)
            max_manip = np.max(manip) if len(manip) > 0 else 1.0
            normalized = manip / max_manip if max_manip > 0 else manip
            colors[:, 0] = normalized
            colors[:, 2] = 1 - normalized
        else:
            positions = self.sample_workspace(
                num_samples, filter_singular=filter_singular
            )

            color_map = {
                'blue': np.array([0, 0, 1.0]),
                'red': np.array([1.0, 0, 0]),
                'green': np.array([0, 1.0, 0]),
                'heat': None
            }

            if color == 'heat':
                colors = np.zeros_like(positions)
                norms = np.linalg.norm(positions, axis=1)
                max_norm = np.max(norms)
                normalized = norms / max_norm if max_norm > 0 else norms
                colors[:, 0] = normalized
                colors[:, 2] = 1 - normalized
            else:
                colors = np.tile(
                    color_map.get(color, color_map['blue']),
                    (positions.shape[0], 1)
                )

        visualizer.draw_point_cloud('workspace', positions, colors, point_size)

    def check_position_reachability(
        self,
        position: np.ndarray,
        tolerance: float = 0.02,
        avoid_singular: bool = False,
    ) -> bool:
        position = np.asarray(position, dtype=float)
        q, success, error = self.robot.inverse_kinematics_position(
            position, max_iter=200, tolerance=tolerance
        )
        if not (success and error < tolerance):
            return False
        if avoid_singular and self.robot.is_singular(q):
            return False
        return True

    def find_singular_regions(
        self,
        num_samples: int = 20000,
        singular_threshold: float = 1e-3,
    ) -> dict:
        info = self.sample_workspace_with_info(num_samples)
        singular_mask = info['is_singular']

        singular_positions = info['positions'][singular_mask]
        singular_configs = info['joint_configs'][singular_mask]

        return {
            'singular_positions': singular_positions,
            'singular_configs': singular_configs,
            'num_singular': len(singular_positions),
            'total_samples': num_samples,
            'singular_ratio': len(singular_positions) / num_samples,
        }

    def smooth_point_cloud(
        self,
        points: np.ndarray,
        method: str = 'gaussian',
        sigma: float = 1.0,
        radius: float = 0.05,
    ) -> np.ndarray:
        points = np.asarray(points, dtype=float)
        smoothed = np.copy(points)

        if method == 'gaussian':
            smoothed = gaussian_filter(points, sigma=sigma)
        elif method == 'moving_average':
            for i, p in enumerate(points):
                distances = np.linalg.norm(points - p, axis=1)
                neighbors = points[distances < radius]
                if len(neighbors) > 0:
                    smoothed[i] = np.mean(neighbors, axis=0)
        elif method == 'median':
            smoothed = median_filter(points, size=3)

        return smoothed

    def get_condition_number_map(
        self,
        resolution: float = 0.1,
        num_samples: int = 10000,
        bounds: Optional[Tuple[np.ndarray, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        info = self.sample_workspace_with_info(num_samples)
        positions = info['positions']
        cond_numbers = np.minimum(info['condition_numbers'], 1000)

        if bounds is None:
            min_bound, max_bound = self.compute_workspace_bounds(num_samples)
        else:
            min_bound, max_bound = bounds

        min_bound = np.asarray(min_bound, dtype=float)
        max_bound = np.asarray(max_bound, dtype=float)

        dims = np.ceil((max_bound - min_bound) / resolution).astype(int)
        cond_map = np.zeros(dims, dtype=float)
        voxel_counts = np.zeros(dims, dtype=int)

        for pos, cond in zip(positions, cond_numbers):
            idx = np.floor((pos - min_bound) / resolution).astype(int)
            if np.all(idx >= 0) and np.all(idx < dims):
                voxel_idx = tuple(idx)
                cond_map[voxel_idx] += cond
                voxel_counts[voxel_idx] += 1

        with np.errstate(divide='ignore', invalid='ignore'):
            average_cond = np.where(
                voxel_counts > 0,
                cond_map / voxel_counts,
                0
            )

        return average_cond, voxel_counts > 0, min_bound, max_bound
