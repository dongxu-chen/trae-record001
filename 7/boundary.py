import numpy as np
from typing import Callable, Dict, List, Tuple, Optional, Union
from scipy.sparse import csr_matrix
from mesh import Mesh


class BoundaryCondition:
    def __init__(
        self,
        bc_type: str,
        nodes: List[int],
        value: Union[float, Callable] = 0.0
    ):
        self.bc_type = bc_type
        self.nodes = nodes
        self.value = value
    
    def get_values(self, coords: np.ndarray) -> np.ndarray:
        if callable(self.value):
            if coords.shape[1] == 2:
                return np.array([self.value(x, y) for x, y in coords])
            else:
                return np.array([self.value(x, y, z) for x, y, z in coords])
        else:
            return np.ones(len(self.nodes)) * self.value


def find_nodes_by_coordinate(
    mesh: Mesh,
    axis: int,
    target: float,
    tol: float = 1e-10
) -> List[int]:
    nodes = []
    for i, coord in enumerate(mesh.nodes):
        if abs(coord[axis] - target) < tol:
            nodes.append(i)
    return nodes


def find_nodes_by_box(
    mesh: Mesh,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None,
    y_min: Optional[float] = None,
    y_max: Optional[float] = None,
    z_min: Optional[float] = None,
    z_max: Optional[float] = None,
    tol: float = 1e-10
) -> List[int]:
    nodes = []
    for i, coord in enumerate(mesh.nodes):
        x, y = coord[0], coord[1]
        z = coord[2] if mesh.dimension == 3 else 0.0
        
        in_box = True
        if x_min is not None and x < x_min - tol:
            in_box = False
        if x_max is not None and x > x_max + tol:
            in_box = False
        if y_min is not None and y < y_min - tol:
            in_box = False
        if y_max is not None and y > y_max + tol:
            in_box = False
        if z_min is not None and z < z_min - tol:
            in_box = False
        if z_max is not None and z > z_max + tol:
            in_box = False
        
        if in_box:
            nodes.append(i)
    return nodes


def find_nodes_by_function(
    mesh: Mesh,
    selector: Callable[[np.ndarray], bool]
) -> List[int]:
    nodes = []
    for i, coord in enumerate(mesh.nodes):
        if selector(coord):
            nodes.append(i)
    return nodes


def get_boundary_faces(mesh: Mesh) -> Dict[int, List[Tuple[int, ...]]]:
    from collections import defaultdict
    
    if mesh.dimension == 2:
        return _get_boundary_edges_2d(mesh)
    else:
        return _get_boundary_faces_3d(mesh)


def _get_boundary_edges_2d(mesh: Mesh) -> Dict[int, List[Tuple[int, int]]]:
    edge_count = defaultdict(int)
    edge_to_elements = defaultdict(list)
    
    for e, elem in enumerate(mesh.elements):
        edges = [
            tuple(sorted([elem[0], elem[1]])),
            tuple(sorted([elem[1], elem[2]])),
            tuple(sorted([elem[2], elem[0]]))
        ]
        for edge in edges:
            edge_count[edge] += 1
            edge_to_elements[edge].append(e)
    
    boundary_edges = defaultdict(list)
    for edge, count in edge_count.items():
        if count == 1:
            elem_idx = edge_to_elements[edge][0]
            boundary_edges[elem_idx].append(edge)
    
    return dict(boundary_edges)


def _get_boundary_faces_3d(mesh: Mesh) -> Dict[int, List[Tuple[int, int, int]]]:
    from collections import defaultdict
    
    face_count = defaultdict(int)
    face_to_elements = defaultdict(list)
    
    for e, elem in enumerate(mesh.elements):
        faces = [
            tuple(sorted([elem[0], elem[1], elem[2]])),
            tuple(sorted([elem[0], elem[1], elem[3]])),
            tuple(sorted([elem[0], elem[2], elem[3]])),
            tuple(sorted([elem[1], elem[2], elem[3]]))
        ]
        for face in faces:
            face_count[face] += 1
            face_to_elements[face].append(e)
    
    boundary_faces = defaultdict(list)
    for face, count in face_count.items():
        if count == 1:
            elem_idx = face_to_elements[face][0]
            boundary_faces[elem_idx].append(face)
    
    return dict(boundary_faces)


def apply_dirichlet(
    K: csr_matrix,
    F: np.ndarray,
    mesh: Mesh,
    bc: BoundaryCondition
) -> Tuple[csr_matrix, np.ndarray]:
    K = K.tolil()
    F = F.copy()
    
    nodes = bc.nodes
    coords = mesh.nodes[nodes]
    values = bc.get_values(coords)
    
    for idx, node in enumerate(nodes):
        value = values[idx]
        F[node] = value
        
        K[node, :] = 0.0
        K[:, node] = 0.0
        K[node, node] = 1.0
    
    return K.tocsr(), F


def apply_neumann(
    K: csr_matrix,
    F: np.ndarray,
    mesh: Mesh,
    bc: BoundaryCondition
) -> Tuple[csr_matrix, np.ndarray]:
    F = F.copy()
    
    nodes = bc.nodes
    coords = mesh.nodes[nodes]
    values = bc.get_values(coords)
    
    for idx, node in enumerate(nodes):
        value = values[idx]
        F[node] += value
    
    return K, F


def apply_multiple_boundary_conditions(
    K: csr_matrix,
    F: np.ndarray,
    mesh: Mesh,
    boundary_conditions: List[BoundaryCondition]
) -> Tuple[csr_matrix, np.ndarray]:
    neumann_bcs = [bc for bc in boundary_conditions if bc.bc_type == 'neumann']
    dirichlet_bcs = [bc for bc in boundary_conditions if bc.bc_type == 'dirichlet']
    
    for bc in neumann_bcs:
        K, F = apply_neumann(K, F, mesh, bc)
    
    for bc in dirichlet_bcs:
        K, F = apply_dirichlet(K, F, mesh, bc)
    
    return K, F


def apply_periodic_boundary(
    K: csr_matrix,
    F: np.ndarray,
    mesh: Mesh,
    master_nodes: List[int],
    slave_nodes: List[int]
) -> Tuple[csr_matrix, np.ndarray]:
    if len(master_nodes) != len(slave_nodes):
        raise ValueError("主节点和从节点数量必须相同")
    
    K = K.tolil()
    F = F.copy()
    
    for master, slave in zip(master_nodes, slave_nodes):
        for col in range(K.shape[1]):
            if K[slave, col] != 0:
                K[master, col] += K[slave, col]
                K[slave, col] = 0
        
        for row in range(K.shape[0]):
            if K[row, slave] != 0:
                K[row, master] += K[row, slave]
                K[row, slave] = 0
        
        F[master] += F[slave]
        F[slave] = 0
        
        K[slave, slave] = 1.0
        K[slave, master] = -1.0
    
    return K.tocsr(), F


def create_boundary_condition(
    mesh: Mesh,
    bc_type: str,
    value: Union[float, Callable] = 0.0,
    location: str = 'all_boundary',
    **kwargs
) -> BoundaryCondition:
    if location == 'all_boundary':
        nodes = mesh.get_boundary_nodes()
    elif location == 'by_coordinate':
        nodes = find_nodes_by_coordinate(mesh, **kwargs)
    elif location == 'by_box':
        nodes = find_nodes_by_box(mesh, **kwargs)
    elif location == 'by_function':
        nodes = find_nodes_by_function(mesh, **kwargs)
    elif location == 'by_physical_group':
        tag = kwargs.get('tag', 1)
        nodes = mesh.get_nodes_by_physical_group(tag)
    elif location == 'by_nodes':
        nodes = kwargs.get('nodes', [])
    else:
        raise ValueError(f"未知的边界位置类型: {location}")
    
    return BoundaryCondition(bc_type, nodes, value)


def print_boundary_info(
    mesh: Mesh,
    boundary_conditions: List[BoundaryCondition]
) -> None:
    print(f"\n边界条件信息:")
    print(f"  总边界节点数: {len(mesh.get_boundary_nodes())}")
    for i, bc in enumerate(boundary_conditions):
        value_str = '函数' if callable(bc.value) else f'{bc.value}'
        print(f"  [{i+1}] {bc.bc_type.upper()}: {len(bc.nodes)} 个节点, 值={value_str}")
