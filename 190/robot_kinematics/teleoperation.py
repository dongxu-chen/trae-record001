import numpy as np
import pinocchio as pin
from typing import Optional, Tuple, List, Callable
from scipy.spatial.transform import Rotation, Slerp


class DragTeach:
    def __init__(self, robot_kinematics, visualizer=None):
        self.robot = robot_kinematics
        self.viz = visualizer

        self.is_dragging = False
        self.drag_start_pose = None
        self.drag_start_q = None
        self.target_pose = None

        self.recorded_positions = []
        self.recorded_orientations = []
        self.recorded_joint_angles = []
        self.recorded_timestamps = []

        self.gain_position = 1.0
        self.gain_orientation = 0.5
        self.nullspace_gain = 0.1

        self.max_iter = 20
        self.tolerance = 1e-3

    def start_drag(self, current_q: np.ndarray):
        current_q = np.asarray(current_q, dtype=float)
        self.is_dragging = True
        self.drag_start_q = current_q.copy()
        self.drag_start_pose = self.robot.forward_kinematics(current_q)
        self.target_pose = self.drag_start_pose.copy()

        self.recorded_positions = []
        self.recorded_orientations = []
        self.recorded_joint_angles = []
        self.recorded_timestamps = []

    def update_target_pose(
        self,
        delta_position: np.ndarray = None,
        delta_rotation: np.ndarray = None,
        absolute_position: np.ndarray = None,
        absolute_rotation: np.ndarray = None,
    ):
        if not self.is_dragging:
            return

        if absolute_position is not None:
            self.target_pose[:3, 3] = np.asarray(absolute_position, dtype=float)
        elif delta_position is not None:
            self.target_pose[:3, 3] += np.asarray(delta_position, dtype=float)

        if absolute_rotation is not None:
            self.target_pose[:3, :3] = np.asarray(absolute_rotation, dtype=float)
        elif delta_rotation is not None:
            delta_rot = np.asarray(delta_rotation, dtype=float)
            if delta_rot.shape == (3, 3):
                self.target_pose[:3, :3] = delta_rot @ self.target_pose[:3, :3]
            elif delta_rot.shape == (3,):
                R = Rotation.from_rotvec(delta_rot).as_matrix()
                self.target_pose[:3, :3] = R @ self.target_pose[:3, :3]

    def step(self, current_q: np.ndarray, dt: float = 0.01) -> np.ndarray:
        if not self.is_dragging or self.target_pose is None:
            return current_q

        current_q = np.asarray(current_q, dtype=float)
        q = current_q.copy()

        for _ in range(self.max_iter):
            current_pose = self.robot.forward_kinematics(q)
            current_se3 = pin.SE3(current_pose[:3, :3], current_pose[:3, 3])
            target_se3 = pin.SE3(self.target_pose[:3, :3], self.target_pose[:3, 3])

            error = pin.log6(current_se3.inverse() * target_se3).vector
            error_norm = np.linalg.norm(error)

            if error_norm < self.tolerance:
                break

            J = self.robot.jacobian_geometric(q)
            damping = 1e-3
            JJT = J @ J.T + damping**2 * np.eye(6)
            v = J.T @ np.linalg.solve(JJT, error)

            q_null = np.zeros_like(q)
            J_pinv = np.linalg.pinv(J)
            nullspace_projector = np.eye(len(q)) - J_pinv @ J
            q_nominal = np.zeros_like(q)
            q_null = nullspace_projector @ (q_nominal - q)

            v_total = v + self.nullspace_gain * q_null

            q = pin.integrate(self.robot.model, q, v_total * dt)

            lower = self.robot.model.lowerPositionLimit
            upper = self.robot.model.upperPositionLimit
            q = np.clip(q, lower, upper)

        return q

    def record_point(self, q: np.ndarray, timestamp: float = None):
        if timestamp is None:
            timestamp = len(self.recorded_timestamps) * 0.01

        pose = self.robot.forward_kinematics(q)
        self.recorded_positions.append(pose[:3, 3].copy())
        self.recorded_orientations.append(pose[:3, :3].copy())
        self.recorded_joint_angles.append(q.copy())
        self.recorded_timestamps.append(timestamp)

    def stop_drag(self) -> dict:
        self.is_dragging = False

        trajectory = {
            'positions': np.array(self.recorded_positions),
            'orientations': np.array(self.recorded_orientations),
            'joint_angles': np.array(self.recorded_joint_angles),
            'timestamps': np.array(self.recorded_timestamps),
        }

        return trajectory

    def get_drag_target_pose(self) -> Optional[np.ndarray]:
        return self.target_pose.copy() if self.target_pose is not None else None

    def simulate_drag_along_path(
        self,
        waypoints: np.ndarray,
        q_start: np.ndarray,
        num_steps_per_segment: int = 50,
    ) -> Tuple[np.ndarray, np.ndarray]:
        q_start = np.asarray(q_start, dtype=float)
        waypoints = np.asarray(waypoints, dtype=float)

        all_q = [q_start.copy()]
        current_q = q_start.copy()

        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]

            for j in range(num_steps_per_segment):
                alpha = (j + 1) / num_steps_per_segment
                target_pos = (1 - alpha) * start + alpha * end

                self.target_pose = np.eye(4)
                self.target_pose[:3, 3] = target_pos

                current_q = self.step(current_q)
                all_q.append(current_q.copy())

        return np.array(all_q), waypoints

    def generate_trajectory_from_demonstration(
        self,
        recorded_trajectory: dict = None,
        smoothing: bool = True,
        smooth_method: str = 'gaussian',
        smooth_sigma: float = 2.0,
    ) -> dict:
        if recorded_trajectory is None:
            recorded_trajectory = {
                'positions': np.array(self.recorded_positions),
                'orientations': np.array(self.recorded_orientations),
                'joint_angles': np.array(self.recorded_joint_angles),
                'timestamps': np.array(self.recorded_timestamps),
            }

        positions = recorded_trajectory['positions']
        joint_angles = recorded_trajectory['joint_angles']
        timestamps = recorded_trajectory['timestamps']

        if smoothing and len(positions) > 5:
            from scipy.ndimage import gaussian_filter1d

            smoothed_positions = np.zeros_like(positions)
            for i in range(3):
                smoothed_positions[:, i] = gaussian_filter1d(
                    positions[:, i], sigma=smooth_sigma
                )

            smoothed_joints = np.zeros_like(joint_angles)
            for i in range(joint_angles.shape[1]):
                smoothed_joints[:, i] = gaussian_filter1d(
                    joint_angles[:, i], sigma=smooth_sigma
                )
        else:
            smoothed_positions = positions
            smoothed_joints = joint_angles

        dt = np.mean(np.diff(timestamps)) if len(timestamps) > 1 else 0.01
        velocities = np.diff(smoothed_positions, axis=0) / dt
        velocities = np.vstack([velocities, velocities[-1:]])

        accelerations = np.diff(velocities, axis=0) / dt
        accelerations = np.vstack([accelerations, accelerations[-1:]])

        return {
            'positions': smoothed_positions,
            'joint_angles': smoothed_joints,
            'timestamps': timestamps,
            'velocities': velocities,
            'accelerations': accelerations,
            'original_positions': positions,
            'original_joint_angles': joint_angles,
        }

    def replay_trajectory(
        self,
        trajectory: dict,
        speed_factor: float = 1.0,
        callback: Optional[Callable[[int, np.ndarray, np.ndarray], None]] = None,
    ) -> np.ndarray:
        joint_angles = trajectory['joint_angles']
        num_steps = len(joint_angles)

        for i in range(num_steps):
            q = joint_angles[i]
            pos = trajectory['positions'][i]

            if callback is not None:
                callback(i, q, pos)

            time.sleep(0.01 / speed_factor)

        return joint_angles

    def save_trajectory(self, filepath: str, trajectory: dict = None):
        if trajectory is None:
            trajectory = self.generate_trajectory_from_demonstration()

        np.savez(
            filepath,
            positions=trajectory['positions'],
            joint_angles=trajectory['joint_angles'],
            timestamps=trajectory['timestamps'],
            velocities=trajectory['velocities'],
            accelerations=trajectory['accelerations'],
        )

    def load_trajectory(self, filepath: str) -> dict:
        data = np.load(filepath)
        return {
            'positions': data['positions'],
            'joint_angles': data['joint_angles'],
            'timestamps': data['timestamps'],
            'velocities': data['velocities'],
            'accelerations': data['accelerations'],
        }

    def reset_recording(self):
        self.recorded_positions = []
        self.recorded_orientations = []
        self.recorded_joint_angles = []
        self.recorded_timestamps = []

    def set_gains(self, position_gain: float = None, orientation_gain: float = None,
                  nullspace_gain: float = None):
        if position_gain is not None:
            self.gain_position = position_gain
        if orientation_gain is not None:
            self.gain_orientation = orientation_gain
        if nullspace_gain is not None:
            self.nullspace_gain = nullspace_gain


class VirtualDragInterface:
    def __init__(self, robot_kinematics, visualizer):
        self.robot = robot_kinematics
        self.viz = visualizer
        self.drag_teach = DragTeach(robot_kinematics, visualizer)

        self.current_q = np.zeros(robot_kinematics.model.nq)
        self.is_running = False
        self.drag_active = False
        self.target_sphere_name = "drag_target"

    def initialize(self):
        pose = self.robot.forward_kinematics(self.current_q)
        self.viz.display(self.current_q)
        self.viz.draw_sphere(
            self.target_sphere_name,
            pose[:3, 3],
            radius=0.03,
            color=0x00ff00
        )

    def start_drag_mode(self):
        self.drag_teach.start_drag(self.current_q)
        self.drag_active = True
        print("拖拽示教模式已启动")

    def move_target(self, delta: np.ndarray):
        if not self.drag_active:
            return
        delta = np.asarray(delta, dtype=float)
        self.drag_teach.update_target_pose(delta_position=delta)
        target_pose = self.drag_teach.get_drag_target_pose()
        if target_pose is not None:
            self.viz.draw_sphere(
                self.target_sphere_name,
                target_pose[:3, 3],
                radius=0.03,
                color=0xff8800
            )

    def set_target_position(self, position: np.ndarray):
        if not self.drag_active:
            return
        position = np.asarray(position, dtype=float)
        self.drag_teach.update_target_pose(absolute_position=position)
        self.viz.draw_sphere(
            self.target_sphere_name,
            position,
            radius=0.03,
            color=0xff8800
        )

    def update(self, dt: float = 0.01):
        if not self.drag_active:
            return

        self.current_q = self.drag_teach.step(self.current_q, dt)
        self.viz.display(self.current_q)
        self.drag_teach.record_point(self.current_q)

    def stop_drag_mode(self) -> dict:
        if not self.drag_active:
            return {}

        trajectory = self.drag_teach.stop_drag()
        self.drag_active = False
        print(f"拖拽示教完成，记录了 {len(trajectory['positions'])} 个点")

        self.viz.delete(self.target_sphere_name)
        return trajectory

    def run_interactive(self, num_steps: int = 1000):
        self.initialize()
        self.start_drag_mode()
        self.is_running = True

        print("交互式拖拽示教模式")
        print("  w/s - +/- X方向")
        print("  a/d - +/- Y方向")
        print("  q/e - +/- Z方向")
        print("  Space - 记录当前点")
        print("  ESC - 结束示教")

        try:
            for step in range(num_steps):
                target = self.drag_teach.get_drag_target_pose()
                if target is not None and step < 200:
                    t = step / 200
                    radius = 0.2
                    angle = t * 2 * np.pi
                    new_pos = np.array([
                        0.4 + radius * np.cos(angle),
                        0.1 + radius * np.sin(angle),
                        0.3 + 0.1 * np.sin(angle * 2)
                    ])
                    self.set_target_position(new_pos)

                self.update()

                if step % 50 == 0:
                    print(f"步骤 {step}/{num_steps}")

        except KeyboardInterrupt:
            pass
        finally:
            trajectory = self.stop_drag_mode()
            self.is_running = False
            return trajectory


import time
