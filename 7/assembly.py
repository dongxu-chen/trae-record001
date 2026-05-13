import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from typing import Callable
from mesh import Mesh


def compute_element_stiffness_matrix_2d(coords: np.ndarray) -> np.ndarray:
    x0, y0 = coords[0]
    x1, y1 = coords[1]
    x2, y2 = coords[2]
    
    A = 0.5 * abs(
        x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1)
    )
    
    b = np.array([y1 - y2, y2 - y0, y0 - y1])
    c = np.array([x2 - x1, x0 - x2, x1 - x0])
    
    Ke = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            Ke[i, j] = (b[i] * b[j] + c[i] * c[j]) / (4 * A)
    
    return Ke


def compute_element_stiffness_matrix_3d(coords: np.ndarray) -> np.ndarray:
    x0, y0, z0 = coords[0]
    x1, y1, z1 = coords[1]
    x2, y2, z2 = coords[2]
    x3, y3, z3 = coords[3]
    
    A_mat = np.array([
        [1, x0, y0, z0],
        [1, x1, y1, z1],
        [1, x2, y2, z2],
        [1, x3, y3, z3]
    ])
    
    V = abs(np.linalg.det(A_mat)) / 6.0
    
    if V < 1e-15:
        return np.zeros((4, 4))
    
    b = np.array([
        -(y2*z3 - y3*z2 - y1*z3 + y3*z1 + y1*z2 - y2*z1),
        y2*z3 - y3*z2 - y0*z3 + y3*z0 + y0*z2 - y2*z0,
        -(y1*z3 - y3*z1 - y0*z3 + y3*z0 + y0*z1 - y1*z0),
        y1*z2 - y2*z1 - y0*z2 + y2*z0 + y0*z1 - y1*z0
    ]) / (6.0 * V)
    
    c = np.array([
        x2*z3 - x3*z2 - x1*z3 + x3*z1 + x1*z2 - x2*z1,
        -(x2*z3 - x3*z2 - x0*z3 + x3*z0 + x0*z2 - x2*z0),
        x1*z3 - x3*z1 - x0*z3 + x3*z0 + x0*z1 - x1*z0,
        -(x1*z2 - x2*z1 - x0*z2 + x2*z0 + x0*z1 - x1*z0)
    ]) / (6.0 * V)
    
    d = np.array([
        -(x2*y3 - x3*y2 - x1*y3 + x3*y1 + x1*y2 - x2*y1),
        x2*y3 - x3*y2 - x0*y3 + x3*y0 + x0*y2 - x2*y0,
        -(x1*y3 - x3*y1 - x0*y3 + x3*y0 + x0*y1 - x1*y0),
        x1*y2 - x2*y1 - x0*y2 + x2*y0 + x0*y1 - x1*y0
    ]) / (6.0 * V)
    
    Ke = np.zeros((4, 4))
    for i in range(4):
        for j in range(4):
            Ke[i, j] = (b[i]*b[j] + c[i]*c[j] + d[i]*d[j]) * V
    
    return Ke


def compute_element_stiffness_matrix(coords: np.ndarray, dimension: int) -> np.ndarray:
    if dimension == 2:
        return compute_element_stiffness_matrix_2d(coords)
    else:
        return compute_element_stiffness_matrix_3d(coords)


def compute_element_load_vector_2d(
    coords: np.ndarray, 
    source: Callable[[float, float], float]
) -> np.ndarray:
    x0, y0 = coords[0]
    x1, y1 = coords[1]
    x2, y2 = coords[2]
    
    A = 0.5 * abs(
        x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1)
    )
    
    quad_points = np.array([
        [1/3, 1/3, 1/3]
    ])
    quad_weights = np.array([1.0])
    
    Fe = np.zeros(3)
    for q, (xi, eta, zeta) in enumerate(quad_points):
        N = np.array([xi, eta, zeta])
        x = np.dot(N, coords[:, 0])
        y = np.dot(N, coords[:, 1])
        f_val = source(x, y)
        Fe += f_val * N * A * quad_weights[q]
    
    return Fe


def compute_element_load_vector_3d(
    coords: np.ndarray, 
    source: Callable[[float, float, float], float]
) -> np.ndarray:
    quad_points = np.array([
        [1/4, 1/4, 1/4, 1/4]
    ])
    quad_weights = np.array([1.0])
    
    A_mat = np.array([
        [1, coords[0,0], coords[0,1], coords[0,2]],
        [1, coords[1,0], coords[1,1], coords[1,2]],
        [1, coords[2,0], coords[2,1], coords[2,2]],
        [1, coords[3,0], coords[3,1], coords[3,2]]
    ])
    V = abs(np.linalg.det(A_mat)) / 6.0
    
    Fe = np.zeros(4)
    for q, N in enumerate(quad_points):
        x = np.dot(N, coords[:, 0])
        y = np.dot(N, coords[:, 1])
        z = np.dot(N, coords[:, 2])
        f_val = source(x, y, z)
        Fe += f_val * N * V * quad_weights[q]
    
    return Fe


def compute_element_load_vector(
    coords: np.ndarray, 
    source: Callable,
    dimension: int
) -> np.ndarray:
    if dimension == 2:
        return compute_element_load_vector_2d(coords, source)
    else:
        return compute_element_load_vector_3d(coords, source)


def assemble_global_system(
    mesh: Mesh, 
    source: Callable
) -> tuple[csr_matrix, np.ndarray]:
    num_nodes = mesh.num_nodes
    dimension = mesh.dimension
    
    rows = []
    cols = []
    data = []
    F = np.zeros(num_nodes)
    
    num_nodes_per_elem = mesh.nodes_per_element
    
    for e in range(mesh.num_elements):
        coords = mesh.get_node_coordinates(e)
        nodes = mesh.elements[e]
        
        Ke = compute_element_stiffness_matrix(coords, dimension)
        Fe = compute_element_load_vector(coords, source, dimension)
        
        for i in range(num_nodes_per_elem):
            global_i = nodes[i]
            F[global_i] += Fe[i]
            for j in range(num_nodes_per_elem):
                global_j = nodes[j]
                rows.append(global_i)
                cols.append(global_j)
                data.append(Ke[i, j])
    
    K_sparse = csr_matrix(
        (np.array(data), (np.array(rows), np.array(cols))),
        shape=(num_nodes, num_nodes)
    )
    
    return K_sparse, F


def apply_dirichlet_boundary(
    K: csr_matrix, 
    F: np.ndarray, 
    boundary_nodes: list[int], 
    value: float = 0.0
) -> tuple[csr_matrix, np.ndarray]:
    K = K.tolil()
    F = F.copy()
    
    for node in boundary_nodes:
        F[node] = value
        
        K[node, :] = 0.0
        K[:, node] = 0.0
        K[node, node] = 1.0
    
    return K.tocsr(), F
