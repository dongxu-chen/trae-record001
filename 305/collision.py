import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple


class Collider(ABC):
    @abstractmethod
    def __call__(self, positions: np.ndarray, velocities: np.ndarray, masses: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        pass


class SphereCollider(Collider):
    def __init__(self, center: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 radius: float = 1.0,
                 restitution: float = 0.5,
                 friction: float = 0.3):
        self.center = np.array(center, dtype=np.float64)
        self.radius = radius
        self.restitution = restitution
        self.friction = friction
        self.enabled = True
    
    def __call__(self, positions: np.ndarray, velocities: np.ndarray, masses: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.enabled:
            return positions, velocities
        
        new_positions = positions.copy()
        new_velocities = velocities.copy()
        
        for i in range(len(positions)):
            to_center = new_positions[i] - self.center
            dist = np.linalg.norm(to_center)
            
            if dist < self.radius:
                if dist < 1e-6:
                    normal = np.array([0.0, 1.0, 0.0])
                else:
                    normal = to_center / dist
                
                penetration = self.radius - dist
                new_positions[i] = self.center + normal * (self.radius + 1e-4)
                
                vel_normal = np.dot(new_velocities[i], normal)
                
                if vel_normal < 0:
                    vel_normal_component = vel_normal * normal
                    vel_tangent_component = new_velocities[i] - vel_normal_component
                    
                    new_velocities[i] = (
                        -self.restitution * vel_normal_component + \
                        (1.0 - self.friction) * vel_tangent_component
                    )
        
        return new_positions, new_velocities


class PlaneCollider(Collider):
    def __init__(self, normal: Tuple[float, float, float] = (0.0, 1.0, 0.0),
                 point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 restitution: float = 0.3,
                 friction: float = 0.5):
        self.normal = np.array(normal, dtype=np.float64)
        self.normal = self.normal / np.linalg.norm(self.normal)
        self.point = np.array(point, dtype=np.float64)
        self.restitution = restitution
        self.friction = friction
        self.enabled = True
    
    def __call__(self, positions: np.ndarray, velocities: np.ndarray, masses: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.enabled:
            return positions, velocities
        
        new_positions = positions.copy()
        new_velocities = velocities.copy()
        
        plane_d = -np.dot(self.normal, self.point)
        
        for i in range(len(positions)):
            distance = np.dot(self.normal, new_positions[i]) + plane_d
            
            if distance < 0:
                new_positions[i] = new_positions[i] - self.normal * (distance - 1e-4)
                
                vel_normal = np.dot(new_velocities[i], self.normal)
                
                if vel_normal < 0:
                    vel_normal_component = vel_normal * self.normal
                    vel_tangent_component = new_velocities[i] - vel_normal_component
                    
                    new_velocities[i] = (
                        -self.restitution * vel_normal_component + \
                        (1.0 - self.friction) * vel_tangent_component
                    )
        
        return new_positions, new_velocities
