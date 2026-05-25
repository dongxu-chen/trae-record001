import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Set


@dataclass
class MassPoint:
    position: np.ndarray
    velocity: np.ndarray
    old_position: np.ndarray
    mass: float
    pinned: bool = False
    force: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    cluster_id: int = 0


@dataclass
class Spring:
    p1_idx: int
    p2_idx: int
    rest_length: float
    stiffness: float
    damping: float
    broken: bool = False
    stress: float = 0.0
    spring_type: str = 'structural'


@dataclass
class Triangle:
    p1_idx: int
    p2_idx: int
    p3_idx: int
    active: bool = True


class Cloth:
    def __init__(self, width: int = 10, height: int = 10, 
                 spacing: float = 0.5, mass: float = 0.1,
                 structural_stiffness: float = 1000.0,
                 shear_stiffness: float = 500.0,
                 bend_stiffness: float = 100.0,
                 damping: float = 0.2,
                 tear_threshold: float = 0.3,
                 tear_enabled: bool = False,
                 start_pos: Tuple[float, float, float] = (-2.5, 5.0, 0.0)):
        
        self.width = width
        self.height = height
        self.spacing = spacing
        self.total_mass_points = width * height
        
        self.structural_stiffness = structural_stiffness
        self.shear_stiffness = shear_stiffness
        self.bend_stiffness = bend_stiffness
        self.damping = damping
        self.tear_threshold = tear_threshold
        self.tear_enabled = tear_enabled
        
        self.mass_points: List[MassPoint] = []
        self.springs: List[Spring] = []
        self.triangles: List[Triangle] = []
        
        self._broken_springs_count = 0
        self._cluster_map: np.ndarray = None
        
        self._create_mass_points(mass, start_pos)
        self._create_springs()
        self._create_triangles()
        self._update_clusters()
        
    def _create_mass_points(self, mass: float, start_pos: Tuple[float, float, float]):
        sx, sy, sz = start_pos
        
        for j in range(self.height):
            for i in range(self.width):
                x = sx + i * self.spacing
                y = sy - j * self.spacing
                z = sz
                
                pos = np.array([x, y, z], dtype=np.float64)
                vel = np.zeros(3, dtype=np.float64)
                old_pos = pos.copy()
                
                pinned = (j == 0) and (i % 3 == 0 or i == self.width - 1)
                
                self.mass_points.append(MassPoint(
                    position=pos,
                    velocity=vel,
                    old_position=old_pos,
                    mass=mass,
                    pinned=pinned,
                    force=np.zeros(3, dtype=np.float64),
                    cluster_id=0
                ))
    
    def _create_springs(self):
        for j in range(self.height):
            for i in range(self.width):
                idx = j * self.width + i
                
                if i < self.width - 1:
                    right_idx = j * self.width + (i + 1)
                    self.springs.append(self._create_spring(
                        idx, right_idx, self.structural_stiffness, self.damping, 'structural'
                    ))
                
                if j < self.height - 1:
                    down_idx = (j + 1) * self.width + i
                    self.springs.append(self._create_spring(
                        idx, down_idx, self.structural_stiffness, self.damping, 'structural'
                    ))
                
                if i < self.width - 1 and j < self.height - 1:
                    diag_idx = (j + 1) * self.width + (i + 1)
                    self.springs.append(self._create_spring(
                        idx, diag_idx, self.shear_stiffness, self.damping * 0.5, 'shear'
                    ))
                    
                    diag2_idx = (j + 1) * self.width + i
                    self.springs.append(self._create_spring(
                        idx + 1, diag2_idx, self.shear_stiffness, self.damping * 0.5, 'shear'
                    ))
                
                if i < self.width - 2:
                    right2_idx = j * self.width + (i + 2)
                    self.springs.append(self._create_spring(
                        idx, right2_idx, self.bend_stiffness, self.damping * 0.3, 'bend'
                    ))
                
                if j < self.height - 2:
                    down2_idx = (j + 2) * self.width + i
                    self.springs.append(self._create_spring(
                        idx, down2_idx, self.bend_stiffness, self.damping * 0.3, 'bend'
                    ))
    
    def _create_spring(self, p1_idx: int, p2_idx: int, stiffness: float, 
                       damping: float, spring_type: str) -> Spring:
        p1 = self.mass_points[p1_idx]
        p2 = self.mass_points[p2_idx]
        rest_length = np.linalg.norm(p1.position - p2.position)
        return Spring(p1_idx, p2_idx, rest_length, stiffness, damping, False, 0.0, spring_type)
    
    def _create_triangles(self):
        self.triangles.clear()
        for j in range(self.height - 1):
            for i in range(self.width - 1):
                idx0 = j * self.width + i
                idx1 = j * self.width + (i + 1)
                idx2 = (j + 1) * self.width + i
                idx3 = (j + 1) * self.width + (i + 1)
                
                self.triangles.append(Triangle(idx0, idx2, idx1, True))
                self.triangles.append(Triangle(idx1, idx2, idx3, True))
    
    def check_and_tear(self) -> int:
        if not self.tear_enabled:
            return 0
        
        broken_count = 0
        
        for spring in self.springs:
            if spring.broken or spring.spring_type == 'bend':
                continue
            
            p1 = self.mass_points[spring.p1_idx]
            p2 = self.mass_points[spring.p2_idx]
            
            diff = p1.position - p2.position
            dist = np.linalg.norm(diff)
            
            strain = abs(dist - spring.rest_length) / spring.rest_length
            spring.stress = strain
            
            if strain > self.tear_threshold:
                spring.broken = True
                broken_count += 1
                
                self._deactivate_triangles(spring.p1_idx, spring.p2_idx)
        
        if broken_count > 0:
            self._broken_springs_count += broken_count
            self._update_clusters()
        
        return broken_count
    
    def _deactivate_triangles(self, idx1: int, idx2: int):
        for tri in self.triangles:
            if not tri.active:
                continue
            
            indices = {tri.p1_idx, tri.p2_idx, tri.p3_idx}
            if idx1 in indices and idx2 in indices:
                tri.active = False
    
    def _update_clusters(self):
        n = len(self.mass_points)
        parent = list(range(n))
        
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        
        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx
        
        for spring in self.springs:
            if not spring.broken:
                union(spring.p1_idx, spring.p2_idx)
        
        cluster_ids = {}
        current_id = 0
        for i in range(n):
            root = find(i)
            if root not in cluster_ids:
                cluster_ids[root] = current_id
                current_id += 1
            self.mass_points[i].cluster_id = cluster_ids[root]
        
        self._cluster_map = np.array([mp.cluster_id for mp in self.mass_points], dtype=np.int32)
    
    def get_cluster_map(self) -> np.ndarray:
        if self._cluster_map is None:
            self._update_clusters()
        return self._cluster_map
    
    def reset_forces(self):
        for mp in self.mass_points:
            mp.force.fill(0.0)
    
    def get_position_array(self) -> np.ndarray:
        return np.array([mp.position for mp in self.mass_points], dtype=np.float64)
    
    def get_velocity_array(self) -> np.ndarray:
        return np.array([mp.velocity for mp in self.mass_points], dtype=np.float64)
    
    def set_position_array(self, positions: np.ndarray):
        for i, mp in enumerate(self.mass_points):
            if not mp.pinned:
                mp.position[:] = positions[i]
    
    def set_velocity_array(self, velocities: np.ndarray):
        for i, mp in enumerate(self.mass_points):
            if not mp.pinned:
                mp.velocity[:] = velocities[i]
    
    def get_triangles(self) -> np.ndarray:
        active_triangles = [[tri.p1_idx, tri.p2_idx, tri.p3_idx] 
                           for tri in self.triangles if tri.active]
        if not active_triangles:
            return np.zeros((0, 3), dtype=np.int32)
        return np.array(active_triangles, dtype=np.int32)
    
    def get_wireframe_edges(self) -> np.ndarray:
        edges = []
        for spring in self.springs:
            if not spring.broken and spring.spring_type != 'bend':
                edges.append([spring.p1_idx, spring.p2_idx])
        if not edges:
            return np.zeros((0, 2), dtype=np.int32)
        return np.array(edges, dtype=np.int32)
    
    def get_broken_edges(self) -> np.ndarray:
        edges = []
        for spring in self.springs:
            if spring.broken and spring.spring_type != 'bend':
                edges.append([spring.p1_idx, spring.p2_idx])
        if not edges:
            return np.zeros((0, 2), dtype=np.int32)
        return np.array(edges, dtype=np.int32)
    
    def get_stress_array(self) -> np.ndarray:
        stress = np.zeros(len(self.mass_points), dtype=np.float64)
        count = np.zeros(len(self.mass_points), dtype=np.float64)
        
        for spring in self.springs:
            if not spring.broken:
                stress[spring.p1_idx] += spring.stress
                stress[spring.p2_idx] += spring.stress
                count[spring.p1_idx] += 1
                count[spring.p2_idx] += 1
        
        count[count == 0] = 1
        stress /= count
        return stress
    
    def get_pinned_mask(self) -> np.ndarray:
        return np.array([mp.pinned for mp in self.mass_points], dtype=bool)
    
    def get_mass_array(self) -> np.ndarray:
        return np.array([mp.mass for mp in self.mass_points], dtype=np.float64)
    
    def get_spring_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        active_springs = [s for s in self.springs if not s.broken]
        if not active_springs:
            return (np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32),
                    np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64))
        
        p1_indices = np.array([s.p1_idx for s in active_springs], dtype=np.int32)
        p2_indices = np.array([s.p2_idx for s in active_springs], dtype=np.int32)
        rest_lengths = np.array([s.rest_length for s in active_springs], dtype=np.float64)
        stiffnesses = np.array([s.stiffness for s in active_springs], dtype=np.float64)
        
        return p1_indices, p2_indices, rest_lengths, stiffnesses
    
    def get_broken_count(self) -> int:
        return self._broken_springs_count
    
    def recompute_springs(self):
        self.springs.clear()
        self._broken_springs_count = 0
        self._create_springs()
        self._create_triangles()
        self._update_clusters()
    
    def reset_tearing(self):
        for spring in self.springs:
            spring.broken = False
            spring.stress = 0.0
        for tri in self.triangles:
            tri.active = True
        self._broken_springs_count = 0
        self._update_clusters()
