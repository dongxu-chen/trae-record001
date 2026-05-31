import numpy as np


class Camera:
    def __init__(self, position=(0.0, 50.0, 100.0), target=(0.0, 0.0, 0.0)):
        self.position = np.array(position, dtype=np.float32)
        self.target = np.array(target, dtype=np.float32)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        self.fov = 45.0
        self.near = 0.1
        self.far = 1000.0

        self._yaw = -90.0
        self._pitch = -30.0
        self._distance = 120.0

        self.is_underwater = False
        self._water_surface_y = 0.0

        self._update_position_from_angles()

    def _update_position_from_angles(self):
        yaw_rad = np.radians(self._yaw)
        pitch_rad = np.radians(self._pitch)

        x = self._distance * np.cos(pitch_rad) * np.sin(yaw_rad)
        y = self._distance * np.sin(pitch_rad)
        z = self._distance * np.cos(pitch_rad) * np.cos(yaw_rad)

        self.position = self.target + np.array([x, y, z])

    def update_underwater_state(self, water_y=0.0):
        self._water_surface_y = water_y
        self.is_underwater = self.position[1] < water_y

    def get_view_matrix(self):
        f = self.target - self.position
        f = f / np.linalg.norm(f)

        s = np.cross(f, self.up)
        s_norm = np.linalg.norm(s)
        if s_norm < 1e-6:
            s = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        else:
            s = s / s_norm

        u = np.cross(s, f)

        view = np.eye(4, dtype=np.float32)
        view[0, 0] = s[0]
        view[0, 1] = s[1]
        view[0, 2] = s[2]
        view[1, 0] = u[0]
        view[1, 1] = u[1]
        view[1, 2] = u[2]
        view[2, 0] = -f[0]
        view[2, 1] = -f[1]
        view[2, 2] = -f[2]

        view[0, 3] = -np.dot(s, self.position)
        view[1, 3] = -np.dot(u, self.position)
        view[2, 3] = np.dot(f, self.position)

        return view

    def get_projection_matrix(self, width, height):
        aspect = width / height
        f = 1.0 / np.tan(np.radians(self.fov) / 2.0)

        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = f / aspect
        proj[1, 1] = f
        proj[2, 2] = (self.far + self.near) / (self.near - self.far)
        proj[2, 3] = (2.0 * self.far * self.near) / (self.near - self.far)
        proj[3, 2] = -1.0

        return proj

    def rotate(self, delta_yaw, delta_pitch):
        self._yaw += delta_yaw
        self._pitch += delta_pitch

        self._pitch = np.clip(self._pitch, -89.0, 89.0)

        self._update_position_from_angles()

    def zoom(self, delta):
        self._distance += delta
        self._distance = np.clip(self._distance, 10.0, 500.0)
        self._update_position_from_angles()

    def pan(self, delta_x, delta_y):
        f = self.target - self.position
        f = f / np.linalg.norm(f)

        right = np.cross(f, self.up)
        right_norm = np.linalg.norm(right)
        if right_norm < 1e-6:
            right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        else:
            right = right / right_norm

        up = np.cross(right, f)

        pan_speed = 0.1 * self._distance
        self.target += right * delta_x * pan_speed
        self.target += up * delta_y * pan_speed

        self._update_position_from_angles()

    def move_vertical(self, delta):
        self.target[1] += delta * 2.0
        self._update_position_from_angles()
