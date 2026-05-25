import numpy as np
from typing import List, Tuple
from cloth import Cloth
from bvh import BVH
from collision import Collider


class SelfCollision(Collider):
    def __init__(self, cloth: Cloth,
                 threshold: float = 0.05,
                 stiffness: float = 0.8,
                 friction: float = 0.3,
                 restitution: float = 0.1,
                 use_bvh: bool = True,
                 max_leaf_size: int = 4):
        
        self.cloth = cloth
        self.threshold = threshold
        self.stiffness = stiffness
        self.friction = friction
        self.restitution = restitution
        self.use_bvh = use_bvh
        self.max_leaf_size = max_leaf_size
        self.enabled = True
        
        self._bvh = None
        self._collision_count = 0
        self._init_bvh()
    
    def _init_bvh(self):
        positions = self.cloth.get_position_array()
        if self.use_bvh:
            margin = self.threshold * 0.5
            self._bvh = BVH(positions, margin=margin, max_leaf_size=self.max_leaf_size)
    
    def _find_collisions_brute_force(self, positions: np.ndarray) -> List[Tuple[int, int]]:
        collisions = []
        n = len(positions)
        
        for i in range(n):
            for j in range(i + 1, n):
                if abs(i - j) <= 2:
                    continue
                
                dist = np.linalg.norm(positions[i] - positions[j])
                if dist < self.threshold:
                    collisions.append((i, j))
        
        return collisions
    
    def _find_collisions_bvh(self, positions: np.ndarray) -> List[Tuple[int, int]]:
        if self._bvh is None:
            self._init_bvh()
        
        self._bvh.refit(positions)
        return self._bvh.query_self_collisions(self.threshold)
    
    def _find_collisions(self, positions: np.ndarray) -> List[Tuple[int, int]]:
        if self.use_bvh:
            return self._find_collisions_bvh(positions)
        else:
            return self._find_collisions_brute_force(positions)
    
    def _resolve_collision(self, i: int, j: int,
                           positions: np.ndarray,
                           velocities: np.ndarray,
                           masses: np.ndarray) -> Tuple[int, int]:
        
        p1 = self.cloth.mass_points[i]
        p2 = self.cloth.mass_points[j]
        
        if p1.pinned and p2.pinned:
            return 0, 0
        
        diff = positions[i] - positions[j]
        dist = np.linalg.norm(diff)
        
        if dist < 1e-8:
            direction = np.array([0.0, 1.0, 0.0])
        else:
            direction = diff / dist
        
        penetration = self.threshold - dist
        if penetration <= 0:
            return 0, 0
        
        m1 = p1.mass
        m2 = p2.mass
        
        if p1.pinned:
            total_mass = m2
            ratio1 = 0.0
            ratio2 = 1.0
        elif p2.pinned:
            total_mass = m1
            ratio1 = 1.0
            ratio2 = 0.0
        else:
            total_mass = m1 + m2
            ratio1 = m2 / total_mass
            ratio2 = m1 / total_mass
        
        correction = direction * penetration * self.stiffness
        
        if not p1.pinned:
            positions[i] += correction * ratio1
        if not p2.pinned:
            positions[j] -= correction * ratio2
        
        vel_diff = velocities[i] - velocities[j]
        vel_normal = np.dot(vel_diff, direction)
        
        if vel_normal < 0:
            impulse_magnitude = -(1.0 + self.restitution) * vel_normal / (1.0 / m1 + 1.0 / m2)
            impulse = impulse_magnitude * direction
            
            if not p1.pinned:
                velocities[i] += impulse / m1
            if not p2.pinned:
                velocities[j] -= impulse / m2
            
            vel_tangent = vel_diff - vel_normal * direction
            tangent_magnitude = np.linalg.norm(vel_tangent)
            
            if tangent_magnitude > 1e-6:
                tangent_dir = vel_tangent / tangent_magnitude
                friction_impulse = -min(self.friction * impulse_magnitude, tangent_magnitude * total_mass) * tangent_dir
                
                if not p1.pinned:
                    velocities[i] += friction_impulse / m1
                if not p2.pinned:
                    velocities[j] -= friction_impulse / m2
        
        return 1, penetration
    
    def __call__(self, positions: np.ndarray, velocities: np.ndarray, masses: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.enabled or self.threshold <= 0:
            return positions, velocities
        
        new_positions = positions.copy()
        new_velocities = velocities.copy()
        
        total_resolved = 0
        total_penetration = 0.0
        
        iterations = 3
        for iter_idx in range(iterations):
            collisions = self._find_collisions(new_positions)
            
            if not collisions:
                break
            
            for i, j in collisions:
                resolved, penetration = self._resolve_collision(
                    i, j, new_positions, new_velocities, masses
                )
                total_resolved += resolved
                total_penetration += penetration
        
        self._collision_count = total_resolved
        
        return new_positions, new_velocities
    
    def get_collision_count(self) -> int:
        return self._collision_count
    
    def rebuild_bvh(self, cloth: Cloth = None):
        if cloth is not None:
            self.cloth = cloth
        positions = self.cloth.get_position_array()
        margin = self.threshold * 0.5
        self._bvh = BVH(positions, margin=margin, max_leaf_size=self.max_leaf_size)
