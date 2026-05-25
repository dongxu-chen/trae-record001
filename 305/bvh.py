import numpy as np
from typing import List, Tuple
from dataclasses import dataclass, field


@dataclass
class AABB:
    min: np.ndarray
    max: np.ndarray
    
    @classmethod
    def from_points(cls, points: np.ndarray) -> 'AABB':
        return cls(
            min=np.min(points, axis=0),
            max=np.max(points, axis=0)
        )
    
    def expand(self, margin: float):
        self.min -= margin
        self.max += margin
    
    def intersects(self, other: 'AABB') -> bool:
        return (
            self.min[0] <= other.max[0] and self.max[0] >= other.min[0] and
            self.min[1] <= other.max[1] and self.max[1] >= other.min[1] and
            self.min[2] <= other.max[2] and self.max[2] >= other.min[2]
        )
    
    def center(self) -> np.ndarray:
        return (self.min + self.max) * 0.5
    
    def surface_area(self) -> float:
        d = self.max - self.min
        return 2.0 * (d[0] * d[1] + d[1] * d[2] + d[2] * d[0])


@dataclass
class BVHNode:
    aabb: AABB
    left: 'BVHNode' = None
    right: 'BVHNode' = None
    point_indices: List[int] = None
    is_leaf: bool = False


class BVH:
    def __init__(self, positions: np.ndarray, margin: float = 0.01, max_leaf_size: int = 4):
        self.positions = positions
        self.margin = margin
        self.max_leaf_size = max_leaf_size
        self.root = None
        self._build()
    
    def _build(self):
        n = len(self.positions)
        indices = list(range(n))
        self.root = self._build_recursive(indices)
    
    def _build_recursive(self, indices: List[int]) -> BVHNode:
        if len(indices) <= self.max_leaf_size:
            aabb = AABB.from_points(self.positions[indices])
            aabb.expand(self.margin)
            return BVHNode(aabb=aabb, point_indices=indices, is_leaf=True)
        
        points = self.positions[indices]
        aabb = AABB.from_points(points)
        aabb.expand(self.margin)
        
        center = aabb.center()
        extents = aabb.max - aabb.min
        axis = np.argmax(extents)
        
        mid = np.median(points[:, axis])
        left_indices = []
        right_indices = []
        
        for i, idx in enumerate(indices):
            if points[i, axis] < mid:
                left_indices.append(idx)
            else:
                right_indices.append(idx)
        
        if len(left_indices) == 0 or len(right_indices) == 0:
            left_indices = indices[:len(indices) // 2]
            right_indices = indices[len(indices) // 2:]
        
        left_node = self._build_recursive(left_indices)
        right_node = self._build_recursive(right_indices)
        
        return BVHNode(aabb=aabb, left=left_node, right=right_node, is_leaf=False)
    
    def refit(self, positions: np.ndarray = None):
        if positions is not None:
            self.positions = positions
        self._refit_recursive(self.root)
    
    def _refit_recursive(self, node: BVHNode):
        if node.is_leaf:
            aabb = AABB.from_points(self.positions[node.point_indices])
            aabb.expand(self.margin)
            node.aabb = aabb
        else:
            self._refit_recursive(node.left)
            self._refit_recursive(node.right)
            
            node.aabb.min = np.minimum(node.left.aabb.min, node.right.aabb.min)
            node.aabb.max = np.maximum(node.left.aabb.max, node.right.aabb.max)
    
    def query_self_collisions(self, threshold: float) -> List[Tuple[int, int]]:
        collisions = []
        self._query_self_collisions_recursive(self.root, self.root, threshold, collisions)
        return collisions
    
    def _query_self_collisions_recursive(self, a: BVHNode, b: BVHNode, 
                                          threshold: float, 
                                          collisions: List[Tuple[int, int]]):
        if a is None or b is None:
            return
        
        if not a.aabb.intersects(b.aabb):
            return
        
        if a.is_leaf and b.is_leaf:
            if a is b:
                for i, idx1 in enumerate(a.point_indices):
                    for j in range(i + 1, len(a.point_indices)):
                        idx2 = a.point_indices[j]
                        if abs(idx1 - idx2) > 2:
                            dist = np.linalg.norm(self.positions[idx1] - self.positions[idx2])
                            if dist < threshold:
                                collisions.append((idx1, idx2))
            else:
                for idx1 in a.point_indices:
                    for idx2 in b.point_indices:
                        if abs(idx1 - idx2) > 2:
                            dist = np.linalg.norm(self.positions[idx1] - self.positions[idx2])
                            if dist < threshold:
                                collisions.append((idx1, idx2))
            return
        
        if a.is_leaf:
            self._query_self_collisions_recursive(a, b.left, threshold, collisions)
            self._query_self_collisions_recursive(a, b.right, threshold, collisions)
        elif b.is_leaf:
            self._query_self_collisions_recursive(a.left, b, threshold, collisions)
            self._query_self_collisions_recursive(a.right, b, threshold, collisions)
        else:
            self._query_self_collisions_recursive(a.left, b.left, threshold, collisions)
            self._query_self_collisions_recursive(a.left, b.right, threshold, collisions)
            self._query_self_collisions_recursive(a.right, b.left, threshold, collisions)
            self._query_self_collisions_recursive(a.right, b.right, threshold, collisions)
    
    def query_point(self, point_idx: int, threshold: float) -> List[int]:
        result = []
        query_aabb = AABB(
            min=self.positions[point_idx] - threshold,
            max=self.positions[point_idx] + threshold
        )
        self._query_point_recursive(self.root, point_idx, query_aabb, threshold, result)
        return result
    
    def _query_point_recursive(self, node: BVHNode, point_idx: int, 
                               query_aabb: AABB, threshold: float, 
                               result: List[int]):
        if node is None or not node.aabb.intersects(query_aabb):
            return
        
        if node.is_leaf:
            for idx in node.point_indices:
                if idx != point_idx and abs(idx - point_idx) > 2:
                    dist = np.linalg.norm(self.positions[point_idx] - self.positions[idx])
                    if dist < threshold:
                        result.append(idx)
        else:
            self._query_point_recursive(node.left, point_idx, query_aabb, threshold, result)
            self._query_point_recursive(node.right, point_idx, query_aabb, threshold, result)
