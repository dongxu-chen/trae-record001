import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple
from abc import ABC, abstractmethod


@dataclass
class RigidBodyState:
    position: np.ndarray
    velocity: np.ndarray
    orientation: np.ndarray
    angular_velocity: np.ndarray
    mass: float
    inertia_tensor: np.ndarray
    force: np.ndarray = field(default_factory=lambda: np.zeros(3))
    torque: np.ndarray = field(default_factory=lambda: np.zeros(3))


class RigidBody(ABC):
    def __init__(self, position: Tuple[float, float, float], 
                 mass: float = 1.0,
                 restitution: float = 0.5,
                 friction: float = 0.3,
                 is_dynamic: bool = True):
        
        self.state = RigidBodyState(
            position=np.array(position, dtype=np.float64),
            velocity=np.zeros(3, dtype=np.float64),
            orientation=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
            angular_velocity=np.zeros(3, dtype=np.float64),
            mass=mass,
            inertia_tensor=np.eye(3, dtype=np.float64) * mass
        )
        
        self.restitution = restitution
        self.friction = friction
        self.is_dynamic = is_dynamic
        self.enabled = True
        self.couple_with_cloth = True
        
        self._attachment_points: List[Tuple[int, np.ndarray]] = []
    
    @abstractmethod
    def get_velocity_at_point(self, world_point: np.ndarray) -> np.ndarray:
        pass
    
    @abstractmethod
    def apply_force_at_point(self, force: np.ndarray, world_point: np.ndarray):
        pass
    
    @abstractmethod
    def closest_point(self, point: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        pass
    
    def reset_forces(self):
        self.state.force.fill(0.0)
        self.state.torque.fill(0.0)
    
    def integrate(self, dt: float):
        if not self.is_dynamic or not self.enabled:
            return
        
        acceleration = self.state.force / self.state.mass
        self.state.velocity += acceleration * dt
        self.state.position += self.state.velocity * dt
        
        inv_inertia = np.linalg.inv(self.state.inertia_tensor)
        angular_acceleration = inv_inertia @ self.state.torque
        self.state.angular_velocity += angular_acceleration * dt
        
        q = self.state.orientation
        omega = self.state.angular_velocity
        
        q_dot = 0.5 * np.array([
            -q[1] * omega[0] - q[2] * omega[1] - q[3] * omega[2],
             q[0] * omega[0] + q[2] * omega[2] - q[3] * omega[1],
             q[0] * omega[1] - q[1] * omega[2] + q[3] * omega[0],
             q[0] * omega[2] + q[1] * omega[1] - q[2] * omega[0]
        ])
        
        self.state.orientation += q_dot * dt
        self.state.orientation /= np.linalg.norm(self.state.orientation)
    
    def add_attachment_point(self, cloth_point_idx: int, local_offset: Tuple[float, float, float]):
        self._attachment_points.append((cloth_point_idx, np.array(local_offset, dtype=np.float64)))
    
    def get_attachment_points(self) -> List[Tuple[int, np.ndarray]]:
        return self._attachment_points
    
    def clear_attachment_points(self):
        self._attachment_points.clear()


class RigidSphere(RigidBody):
    def __init__(self, position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 radius: float = 1.0,
                 mass: float = 1.0,
                 restitution: float = 0.5,
                 friction: float = 0.3,
                 is_dynamic: bool = True):
        
        super().__init__(position, mass, restitution, friction, is_dynamic)
        self.radius = radius
        
        self.state.inertia_tensor = np.eye(3) * (2.0 / 5.0) * mass * radius * radius
    
    def get_velocity_at_point(self, world_point: np.ndarray) -> np.ndarray:
        r = world_point - self.state.position
        return self.state.velocity + np.cross(self.state.angular_velocity, r)
    
    def apply_force_at_point(self, force: np.ndarray, world_point: np.ndarray):
        if not self.is_dynamic:
            return
        self.state.force += force
        r = world_point - self.state.position
        self.state.torque += np.cross(r, force)
    
    def closest_point(self, point: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        to_point = point - self.state.position
        dist = np.linalg.norm(to_point)
        
        if dist < 1e-6:
            normal = np.array([0.0, 1.0, 0.0])
        else:
            normal = to_point / dist
        
        closest = self.state.position + normal * self.radius
        penetration = self.radius - dist
        
        return closest, normal, penetration


class RigidBox(RigidBody):
    def __init__(self, position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
                 mass: float = 1.0,
                 restitution: float = 0.5,
                 friction: float = 0.3,
                 is_dynamic: bool = True):
        
        super().__init__(position, mass, restitution, friction, is_dynamic)
        self.size = np.array(size, dtype=np.float64)
        
        w, h, d = size
        self.state.inertia_tensor = np.diag([
            (1.0 / 12.0) * mass * (h * h + d * d),
            (1.0 / 12.0) * mass * (w * w + d * d),
            (1.0 / 12.0) * mass * (w * w + h * h)
        ])
    
    def _rotate_vector(self, vec: np.ndarray) -> np.ndarray:
        q = self.state.orientation
        w, x, y, z = q
        
        rot_mat = np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ])
        
        return rot_mat @ vec
    
    def _inverse_rotate_vector(self, vec: np.ndarray) -> np.ndarray:
        q = self.state.orientation
        w, x, y, z = q
        
        rot_mat = np.array([
            [1 - 2*(y*y + z*z), 2*(x*y + w*z), 2*(x*z - w*y)],
            [2*(x*y - w*z), 1 - 2*(x*x + z*z), 2*(y*z + w*x)],
            [2*(x*z + w*y), 2*(y*z - w*x), 1 - 2*(x*x + y*y)]
        ])
        
        return rot_mat @ vec
    
    def get_velocity_at_point(self, world_point: np.ndarray) -> np.ndarray:
        r = world_point - self.state.position
        return self.state.velocity + np.cross(self.state.angular_velocity, r)
    
    def apply_force_at_point(self, force: np.ndarray, world_point: np.ndarray):
        if not self.is_dynamic:
            return
        self.state.force += force
        r = world_point - self.state.position
        self.state.torque += np.cross(r, force)
    
    def closest_point(self, point: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        local_point = self._inverse_rotate_vector(point - self.state.position)
        half_size = self.size * 0.5
        
        clamped = np.clip(local_point, -half_size, half_size)
        
        if np.allclose(local_point, clamped):
            diff = local_point
            abs_diff = np.abs(diff)
            axis = np.argmax(abs_diff)
            
            if diff[axis] > 0:
                normal_local = np.zeros(3)
                normal_local[axis] = 1.0
            else:
                normal_local = np.zeros(3)
                normal_local[axis] = -1.0
            
            closest_local = clamped
            penetration = half_size[axis] - abs_diff[axis]
        else:
            closest_local = clamped
            normal_local = local_point - clamped
            norm = np.linalg.norm(normal_local)
            if norm > 1e-6:
                normal_local /= norm
            else:
                normal_local = np.array([0.0, 1.0, 0.0])
            penetration = -norm
        
        closest_world = self._rotate_vector(closest_local) + self.state.position
        normal_world = self._rotate_vector(normal_local)
        
        return closest_world, normal_world, penetration


class ClothRigidCoupling:
    def __init__(self, cloth, rigid_bodies: List[RigidBody] = None):
        self.cloth = cloth
        self.rigid_bodies = rigid_bodies if rigid_bodies else []
        self.coupling_stiffness = 0.9
        self.attachment_stiffness = 1.0
    
    def add_rigid_body(self, body: RigidBody):
        self.rigid_bodies.append(body)
    
    def compute_coupling_forces(self, dt: float):
        for body in self.rigid_bodies:
            if not body.enabled or not body.couple_with_cloth:
                continue
            
            body.reset_forces()
            
            for mp in self.cloth.mass_points:
                if mp.pinned:
                    continue
                
                closest, normal, penetration = body.closest_point(mp.position)
                
                if penetration > 0:
                    correction = normal * penetration * self.coupling_stiffness
                    mp.position += correction
                    
                    cloth_vel = mp.velocity
                    body_vel = body.get_velocity_at_point(mp.position)
                    
                    rel_vel = cloth_vel - body_vel
                    vel_normal = np.dot(rel_vel, normal)
                    
                    if vel_normal < 0:
                        impulse_magnitude = -(1.0 + body.restitution) * vel_normal / (1.0 / mp.mass + 1.0 / body.state.mass)
                        impulse = impulse_magnitude * normal
                        
                        mp.velocity += impulse / mp.mass
                        body.apply_force_at_point(-impulse / dt, mp.position)
                        
                        vel_tangent = rel_vel - vel_normal * normal
                        tangent_magnitude = np.linalg.norm(vel_tangent)
                        
                        if tangent_magnitude > 1e-6:
                            tangent_dir = vel_tangent / tangent_magnitude
                            friction_impulse = -min(body.friction * impulse_magnitude, tangent_magnitude * mp.mass) * tangent_dir
                            
                            mp.velocity += friction_impulse / mp.mass
                            body.apply_force_at_point(-friction_impulse / dt, mp.position)
    
    def update_attachments(self):
        for body in self.rigid_bodies:
            if not body.enabled or not body.couple_with_cloth:
                continue
            
            for point_idx, local_offset in body.get_attachment_points():
                world_pos = body.state.position + body._rotate_vector(local_offset) if hasattr(body, '_rotate_vector') else body.state.position + local_offset
                
                mp = self.cloth.mass_points[point_idx]
                
                if mp.pinned:
                    continue
                
                correction = world_pos - mp.position
                mp.position += correction * self.attachment_stiffness
                
                body_vel = body.get_velocity_at_point(world_pos)
                mp.velocity = body_vel
    
    def integrate_rigid_bodies(self, dt: float):
        for body in self.rigid_bodies:
            if body.enabled and body.is_dynamic:
                body.integrate(dt)
