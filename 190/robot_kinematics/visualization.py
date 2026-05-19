import numpy as np
import pinocchio as pin
import meshcat
import meshcat.geometry as g
import meshcat.transformations as tf


class MeshCatVisualizer:
    def __init__(self, robot_model=None, urdf_path=None, zmq_url=None):
        if zmq_url is not None:
            self.viewer = meshcat.Visualizer(zmq_url=zmq_url)
        else:
            self.viewer = meshcat.Visualizer()
        
        self.robot_model = robot_model
        self.urdf_path = urdf_path
        self.viz = None

        if robot_model is not None or urdf_path is not None:
            self.load_robot(robot_model, urdf_path)

    def load_robot(self, robot_model=None, urdf_path=None):
        if robot_model is not None:
            self.robot_model = robot_model
            self.urdf_path = robot_model.urdf_path
        elif urdf_path is not None:
            self.urdf_path = urdf_path
            from .kinematics import RobotKinematics
            self.robot_model = RobotKinematics(urdf_path)
        
        if self.robot_model is None:
            raise ValueError("Either robot_model or urdf_path must be provided")
        
        self.viz = pin.visualize.MeshcatVisualizer(
            self.robot_model.model,
            self.robot_model.collision_model,
            self.robot_model.visual_model
        )
        self.viz.initViewer(viewer=self.viewer, loadModel=True)

    def open(self):
        if self.viz is None:
            raise RuntimeError("Robot not loaded. Call load_robot first.")
        self.viewer.open()

    def display(self, q: np.ndarray):
        if self.viz is None:
            raise RuntimeError("Robot not loaded. Call load_robot first.")
        q = np.asarray(q, dtype=float)
        self.viz.display(q)

    def display_collisions(self, q: np.ndarray):
        if self.viz is None:
            raise RuntimeError("Robot not loaded. Call load_robot first.")
        q = np.asarray(q, dtype=float)
        self.viz.displayCollisions(True)
        self.viz.display(q)

    def set_camera(self, position: np.ndarray, target: np.ndarray = None):
        position = np.asarray(position, dtype=float)
        if target is None:
            target = np.zeros(3)
        else:
            target = np.asarray(target, dtype=float)
        
        self.viewer["/Cameras/default"].set_transform(
            tf.translation_matrix(position) @ 
            tf.quaternion_matrix(tf.quaternion_from_matrix(
                self._look_at(position, target)
            ))
        )

    def _look_at(self, camera_pos: np.ndarray, target: np.ndarray) -> np.ndarray:
        z_axis = camera_pos - target
        z_axis = z_axis / np.linalg.norm(z_axis)
        y_axis = np.array([0, 0, -1])
        x_axis = np.cross(y_axis, z_axis)
        x_axis = x_axis / np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis, x_axis)
        R = np.column_stack([x_axis, y_axis, z_axis])
        return R

    def draw_frame(self, name: str, transform: np.ndarray, size: float = 0.1):
        transform = np.asarray(transform, dtype=float)
        self.viewer["frames"][name].set_transform(transform)
        self.viewer["frames"][name]["x"].set_object(
            g.Arrow(0.8 * size, 0.2 * size),
            g.MeshBasicMaterial(color=0xff0000)
        )
        self.viewer["frames"][name]["x"].set_transform(
            tf.rotation_matrix(np.pi / 2, [0, 1, 0])
        )
        self.viewer["frames"][name]["y"].set_object(
            g.Arrow(0.8 * size, 0.2 * size),
            g.MeshBasicMaterial(color=0x00ff00)
        )
        self.viewer["frames"][name]["y"].set_transform(
            tf.rotation_matrix(-np.pi / 2, [1, 0, 0])
        )
        self.viewer["frames"][name]["z"].set_object(
            g.Arrow(0.8 * size, 0.2 * size),
            g.MeshBasicMaterial(color=0x0000ff)
        )

    def draw_sphere(self, name: str, position: np.ndarray, radius: float = 0.05,
                    color: int = 0x00ff00):
        position = np.asarray(position, dtype=float)
        self.viewer["objects"][name].set_object(
            g.Sphere(radius),
            g.MeshBasicMaterial(color=color)
        )
        self.viewer["objects"][name].set_transform(tf.translation_matrix(position))

    def draw_box(self, name: str, position: np.ndarray, size: np.ndarray,
                 color: int = 0x0000ff):
        position = np.asarray(position, dtype=float)
        size = np.asarray(size, dtype=float)
        self.viewer["objects"][name].set_object(
            g.Box(size),
            g.MeshBasicMaterial(color=color, transparent=True, opacity=0.5)
        )
        self.viewer["objects"][name].set_transform(tf.translation_matrix(position))

    def draw_line(self, name: str, points: np.ndarray, color: int = 0xff0000):
        points = np.asarray(points, dtype=float)
        self.viewer["objects"][name].set_object(
            g.Line(
                g.PointsGeometry(points.T),
                g.MeshBasicMaterial(color=color)
            )
        )

    def draw_point_cloud(self, name: str, points: np.ndarray, colors: np.ndarray = None,
                         size: float = 0.005):
        points = np.asarray(points, dtype=float)
        if colors is None:
            colors = np.zeros_like(points)
            colors[:, 0] = 1.0
        colors = np.asarray(colors, dtype=float)
        
        self.viewer["objects"][name].set_object(
            g.Points(
                g.PointsGeometry(points.T, color=colors.T),
                g.PointsMaterial(size=size)
            )
        )

    def draw_trajectory(self, name: str, positions: np.ndarray, color: int = 0xff0000,
                        point_size: float = 0.01):
        positions = np.asarray(positions, dtype=float)
        colors = np.tile(
            np.array([[1.0, 0, 0]]), (positions.shape[0], 1)
        )
        self.draw_point_cloud(name, positions, colors, point_size)

    def clear(self):
        self.viewer["frames"].delete()
        self.viewer["objects"].delete()

    def delete(self, name: str):
        self.viewer[name].delete()
