import numpy as np
from typing import List, Tuple, Optional
from scipy.spatial.transform import Slerp, Rotation


class TrajectoryPlanner:
    def __init__(self, robot_kinematics):
        self.robot = robot_kinematics

    def linear_interpolation(
        self,
        start_pose: np.ndarray,
        end_pose: np.ndarray,
        num_waypoints: int = 100,
    ) -> np.ndarray:
        start_pose = np.asarray(start_pose, dtype=float)
        end_pose = np.asarray(end_pose, dtype=float)

        if start_pose.shape != (4, 4) or end_pose.shape != (4, 4):
            raise ValueError("Poses must be 4x4 homogeneous matrices")

        poses = np.zeros((num_waypoints, 4, 4))
        for i in range(num_waypoints):
            alpha = i / (num_waypoints - 1)
            poses[i] = self._interpolate_pose(start_pose, end_pose, alpha)
        return poses

    def _interpolate_pose(
        self,
        pose1: np.ndarray,
        pose2: np.ndarray,
        alpha: float,
    ) -> np.ndarray:
        result = np.eye(4)
        result[:3, 3] = (1 - alpha) * pose1[:3, 3] + alpha * pose2[:3, 3]

        R1 = Rotation.from_matrix(pose1[:3, :3])
        R2 = Rotation.from_matrix(pose2[:3, :3])
        slerp = Slerp([0, 1], Rotation.concatenate([R1, R2]))
        result[:3, :3] = slerp(alpha).as_matrix()

        return result

    def circular_arc(
        self,
        center: np.ndarray,
        radius: float,
        start_angle: float,
        end_angle: float,
        num_waypoints: int = 100,
        normal: np.ndarray = None,
        orientation: np.ndarray = None,
    ) -> np.ndarray:
        center = np.asarray(center, dtype=float)
        if normal is None:
            normal = np.array([0, 0, 1])
        else:
            normal = np.asarray(normal, dtype=float)
            normal = normal / np.linalg.norm(normal)

        if orientation is None:
            R_orient = np.eye(3)
        else:
            orientation = np.asarray(orientation, dtype=float)
            if orientation.shape == (3, 3):
                R_orient = orientation
            else:
                R_orient = np.eye(3)

        v1 = np.array([1, 0, 0])
        if abs(np.dot(v1, normal)) > 0.9:
            v1 = np.array([0, 1, 0])
        v1 = v1 - np.dot(v1, normal) * normal
        v1 = v1 / np.linalg.norm(v1)
        v2 = np.cross(normal, v1)

        angles = np.linspace(start_angle, end_angle, num_waypoints)
        poses = np.zeros((num_waypoints, 4, 4))

        for i, theta in enumerate(angles):
            pos = center + radius * (np.cos(theta) * v1 + np.sin(theta) * v2)
            poses[i, :3, 3] = pos
            poses[i, :3, :3] = R_orient
            poses[i, 3, 3] = 1.0

        return poses

    def three_point_arc(
        self,
        point1: np.ndarray,
        point2: np.ndarray,
        point3: np.ndarray,
        num_waypoints: int = 100,
        orientation: np.ndarray = None,
    ) -> np.ndarray:
        point1 = np.asarray(point1, dtype=float)
        point2 = np.asarray(point2, dtype=float)
        point3 = np.asarray(point3, dtype=float)

        center, radius, normal = self._circle_from_three_points(
            point1, point2, point3
        )

        v1 = point1 - center
        v2 = point2 - center
        start_angle = 0
        angle_diff = np.arccos(
            np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1, 1)
        )
        cross = np.cross(v1, v2)
        if np.dot(cross, normal) < 0:
            angle_diff = -angle_diff
        end_angle = 2 * angle_diff

        return self.circular_arc(
            center, radius, start_angle, end_angle, num_waypoints, normal, orientation
        )

    def _circle_from_three_points(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        p3: np.ndarray,
    ) -> Tuple[np.ndarray, float, np.ndarray]:
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        normal = normal / np.linalg.norm(normal)

        v1_perp = np.cross(v1, normal)
        v2_perp = np.cross(v2, normal)

        mid1 = (p1 + p2) / 2
        mid2 = (p1 + p3) / 2

        A = np.column_stack([v1_perp, -v2_perp])
        b = mid2 - mid1
        b = b - np.dot(b, normal) * normal

        A_proj = np.column_stack([v1_perp, v2_perp])
        t, s = np.linalg.lstsq(A_proj, b, rcond=None)[0]

        center = mid1 + t * v1_perp
        radius = np.linalg.norm(p1 - center)

        return center, radius, normal

    def quintic_trajectory(
        self,
        q_start: np.ndarray,
        q_end: np.ndarray,
        duration: float,
        num_waypoints: int = 100,
        dq_start: np.ndarray = None,
        dq_end: np.ndarray = None,
        ddq_start: np.ndarray = None,
        ddq_end: np.ndarray = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        q_start = np.asarray(q_start, dtype=float)
        q_end = np.asarray(q_end, dtype=float)
        n = len(q_start)

        if dq_start is None:
            dq_start = np.zeros(n)
        if dq_end is None:
            dq_end = np.zeros(n)
        if ddq_start is None:
            ddq_start = np.zeros(n)
        if ddq_end is None:
            ddq_end = np.zeros(n)

        time_steps = np.linspace(0, duration, num_waypoints)
        q_traj = np.zeros((num_waypoints, n))
        dq_traj = np.zeros((num_waypoints, n))
        ddq_traj = np.zeros((num_waypoints, n))

        for i, t in enumerate(time_steps):
            tau = t / duration
            h0 = 1 - 10 * tau**3 + 15 * tau**4 - 6 * tau**5
            h1 = tau - 6 * tau**3 + 8 * tau**4 - 3 * tau**5
            h2 = 0.5 * (tau**2 - 3 * tau**3 + 3 * tau**4 - tau**5)
            h3 = -10 * tau**2 + 30 * tau**3 - 24 * tau**4 + 4 * tau**5
            h4 = -3 * tau**2 + 14 * tau**3 - 15 * tau**4 + 4 * tau**5
            h5 = tau**2 - 2 * tau**3 + tau**4

            q_traj[i] = (
                h0 * q_start
                + h1 * dq_start * duration
                + h2 * ddq_start * duration**2
                + (1 - h0) * q_end
                + h3 * dq_end * duration
                + h4 * ddq_end * duration**2
            )

            dh0 = 30 * (tau**4 - tau**3)
            dh1 = 1 - 18 * tau**2 + 32 * tau**3 - 15 * tau**4
            dh2 = tau - 4.5 * tau**2 + 6 * tau**3 - 2.5 * tau**4
            dh3 = -20 * tau + 90 * tau**2 - 96 * tau**3 + 20 * tau**4
            dh4 = -6 * tau + 42 * tau**2 - 60 * tau**3 + 20 * tau**4
            dh5 = 2 * tau - 6 * tau**2 + 4 * tau**3

            dq_traj[i] = (
                dh0 * q_start
                + dh1 * dq_start
                + dh2 * ddq_start * duration
                + -dh0 * q_end
                + dh3 * dq_end
                + dh4 * ddq_end * duration
            ) / duration

            ddh0 = 120 * tau**3 - 90 * tau**2
            ddh1 = -36 * tau + 96 * tau**2 - 60 * tau**3
            ddh2 = 1 - 9 * tau + 18 * tau**2 - 10 * tau**3
            ddh3 = -20 + 180 * tau - 288 * tau**2 + 80 * tau**3
            ddh4 = -6 + 84 * tau - 180 * tau**2 + 80 * tau**3
            ddh5 = 2 - 12 * tau + 12 * tau**2

            ddq_traj[i] = (
                ddh0 * q_start
                + ddh1 * dq_start / duration
                + ddh2 * ddq_start
                + -ddh0 * q_end
                + ddh3 * dq_end / duration
                + ddh4 * ddq_end
            ) / duration**2

        return time_steps, q_traj, dq_traj, ddq_traj

    def cartesian_to_joint_trajectory(
        self,
        cartesian_trajectory: np.ndarray,
        initial_guess: np.ndarray = None,
        max_iter: int = 200,
        tolerance: float = 1e-4,
    ) -> Tuple[np.ndarray, np.ndarray]:
        num_waypoints = cartesian_trajectory.shape[0]
        n_joints = self.robot.model.nq

        q_traj = np.zeros((num_waypoints, n_joints))
        success_mask = np.zeros(num_waypoints, dtype=bool)

        if initial_guess is None:
            q_guess = self.robot.random_configuration()
        else:
            q_guess = np.asarray(initial_guess, dtype=float)

        for i in range(num_waypoints):
            target_pose = cartesian_trajectory[i]
            q_sol, success, error = self.robot.inverse_kinematics(
                target_pose,
                initial_guess=q_guess,
                max_iter=max_iter,
                tolerance=tolerance
            )

            q_traj[i] = q_sol
            success_mask[i] = success
            q_guess = q_sol

        return q_traj, success_mask

    def cartesian_position_trajectory(
        self,
        start_position: np.ndarray,
        end_position: np.ndarray,
        num_waypoints: int = 100,
    ) -> np.ndarray:
        start_position = np.asarray(start_position, dtype=float)
        end_position = np.asarray(end_position, dtype=float)

        positions = np.zeros((num_waypoints, 3))
        for i in range(num_waypoints):
            alpha = i / (num_waypoints - 1)
            positions[i] = (1 - alpha) * start_position + alpha * end_position

        return positions

    def generate_straight_line(
        self,
        start_pos: np.ndarray,
        end_pos: np.ndarray,
        orientation: np.ndarray = None,
        num_waypoints: int = 100,
    ) -> np.ndarray:
        start_pos = np.asarray(start_pos, dtype=float)
        end_pos = np.asarray(end_pos, dtype=float)

        if orientation is None:
            R = np.eye(3)
        else:
            R = np.asarray(orientation, dtype=float)

        poses = np.zeros((num_waypoints, 4, 4))
        for i in range(num_waypoints):
            alpha = i / (num_waypoints - 1)
            poses[i, :3, 3] = (1 - alpha) * start_pos + alpha * end_pos
            poses[i, :3, :3] = R
            poses[i, 3, 3] = 1.0

        return poses

    def blend_trajectories(
        self,
        trajectory_segments: List[np.ndarray],
        blend_radius: float = 0.05,
    ) -> np.ndarray:
        if len(trajectory_segments) == 1:
            return trajectory_segments[0]

        blended = [trajectory_segments[0][:-1]]
        for i in range(1, len(trajectory_segments)):
            prev_seg = trajectory_segments[i - 1]
            curr_seg = trajectory_segments[i]

            blended.append(curr_seg[1:])

        return np.vstack(blended)

    def get_trajectory_velocities(
        self,
        positions: np.ndarray,
        time_step: float,
    ) -> np.ndarray:
        velocities = np.diff(positions, axis=0) / time_step
        velocities = np.vstack([velocities, velocities[-1:]])
        return velocities

    def get_trajectory_accelerations(
        self,
        velocities: np.ndarray,
        time_step: float,
    ) -> np.ndarray:
        accelerations = np.diff(velocities, axis=0) / time_step
        accelerations = np.vstack([accelerations, accelerations[-1:]])
        return accelerations

    def resample_trajectory(
        self,
        trajectory: np.ndarray,
        original_dt: float,
        target_dt: float,
    ) -> np.ndarray:
        n = trajectory.shape[0]
        total_time = (n - 1) * original_dt
        target_n = int(total_time / target_dt) + 1

        if trajectory.ndim == 2 and trajectory.shape[1] == 4 and trajectory.shape[2] == 4:
            resampled = np.zeros((target_n, 4, 4))
            for i in range(target_n):
                alpha = i / (target_n - 1)
                idx = alpha * (n - 1)
                idx0 = int(np.floor(idx))
                idx1 = min(idx0 + 1, n - 1)
                a = idx - idx0
                resampled[i] = self._interpolate_pose(
                    trajectory[idx0], trajectory[idx1], a
                )
        else:
            resampled = np.zeros((target_n, trajectory.shape[1]))
            for i in range(target_n):
                alpha = i / (target_n - 1)
                idx = alpha * (n - 1)
                idx0 = int(np.floor(idx))
                idx1 = min(idx0 + 1, n - 1)
                a = idx - idx0
                resampled[i] = (1 - a) * trajectory[idx0] + a * trajectory[idx1]

        return resampled

    def minimum_jerk_trajectory(
        self,
        q_start: np.ndarray,
        q_end: np.ndarray,
        duration: float,
        num_waypoints: int = 100,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        q_start = np.asarray(q_start, dtype=float)
        q_end = np.asarray(q_end, dtype=float)
        n = len(q_start)

        time_steps = np.linspace(0, duration, num_waypoints)
        q_traj = np.zeros((num_waypoints, n))
        dq_traj = np.zeros((num_waypoints, n))
        ddq_traj = np.zeros((num_waypoints, n))

        for i, t in enumerate(time_steps):
            tau = t / duration
            q_traj[i] = q_start + (q_end - q_start) * (
                10 * tau**3 - 15 * tau**4 + 6 * tau**5
            )
            dq_traj[i] = (q_end - q_start) * (
                30 * tau**2 - 60 * tau**3 + 30 * tau**4
            ) / duration
            ddq_traj[i] = (q_end - q_start) * (
                60 * tau - 180 * tau**2 + 120 * tau**3
            ) / duration**2

        return time_steps, q_traj, dq_traj, ddq_traj

    def check_trajectory_smoothness(
        self,
        q_trajectory: np.ndarray,
        max_joint_velocity: float = np.pi,
        max_joint_acceleration: float = 4 * np.pi,
    ) -> Tuple[bool, dict]:
        dt = 1.0
        velocities = np.diff(q_trajectory, axis=0) / dt
        accelerations = np.diff(velocities, axis=0) / dt

        max_vel = np.max(np.abs(velocities))
        max_acc = np.max(np.abs(accelerations))

        is_smooth = max_vel <= max_joint_velocity and max_acc <= max_joint_acceleration

        info = {
            'max_velocity': max_vel,
            'max_acceleration': max_acc,
            'velocity_limit': max_joint_velocity,
            'acceleration_limit': max_joint_acceleration,
            'velocity_violation': max_vel > max_joint_velocity,
            'acceleration_violation': max_acc > max_joint_acceleration,
        }

        return is_smooth, info
