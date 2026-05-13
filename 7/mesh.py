import numpy as np
import struct
from typing import Tuple, List, Dict, Optional


class Mesh:
    def __init__(
        self, 
        nodes: np.ndarray, 
        elements: np.ndarray,
        element_type: str = 'triangle',
        physical_groups: Optional[Dict[int, List[int]]] = None,
        physical_names: Optional[Dict[int, str]] = None
    ):
        self.nodes = np.array(nodes, dtype=np.float64)
        self.elements = np.array(elements, dtype=np.int32)
        self.num_nodes = self.nodes.shape[0]
        self.num_elements = self.elements.shape[0]
        self.element_type = element_type
        
        if element_type == 'triangle':
            self.dimension = 2
            self.nodes_per_element = 3
        elif element_type == 'tetrahedron':
            self.dimension = 3
            self.nodes_per_element = 4
        else:
            raise ValueError(f"未知的单元类型: {element_type}")
        
        self.physical_groups = physical_groups if physical_groups is not None else {}
        self.physical_names = physical_names if physical_names is not None else {}
        
    def get_node_coordinates(self, element_idx: int) -> np.ndarray:
        elem_nodes = self.elements[element_idx]
        return self.nodes[elem_nodes]
    
    def get_boundary_nodes(self, tol: float = 1e-10) -> List[int]:
        if self.dimension == 2:
            return self._get_boundary_nodes_2d(tol)
        else:
            return self._get_boundary_nodes_3d(tol)
    
    def _get_boundary_nodes_2d(self, tol: float) -> List[int]:
        x_min, x_max = self.nodes[:, 0].min(), self.nodes[:, 0].max()
        y_min, y_max = self.nodes[:, 1].min(), self.nodes[:, 1].max()
        
        boundary_nodes = []
        for i, (x, y) in enumerate(self.nodes):
            if (abs(x - x_min) < tol or abs(x - x_max) < tol or
                abs(y - y_min) < tol or abs(y - y_max) < tol):
                boundary_nodes.append(i)
        return boundary_nodes
    
    def _get_boundary_nodes_3d(self, tol: float) -> List[int]:
        x_min, x_max = self.nodes[:, 0].min(), self.nodes[:, 0].max()
        y_min, y_max = self.nodes[:, 1].min(), self.nodes[:, 1].max()
        z_min, z_max = self.nodes[:, 2].min(), self.nodes[:, 2].max()
        
        boundary_nodes = []
        for i, (x, y, z) in enumerate(self.nodes):
            if (abs(x - x_min) < tol or abs(x - x_max) < tol or
                abs(y - y_min) < tol or abs(y - y_max) < tol or
                abs(z - z_min) < tol or abs(z - z_max) < tol):
                boundary_nodes.append(i)
        return boundary_nodes
    
    def get_nodes_by_physical_group(self, tag: int) -> List[int]:
        if tag not in self.physical_groups:
            return []
        return self.physical_groups[tag]


def generate_rectangular_mesh(
    x_min: float, 
    x_max: float, 
    y_min: float, 
    y_max: float,
    nx: int, 
    ny: int
) -> Mesh:
    x = np.linspace(x_min, x_max, nx)
    y = np.linspace(y_min, y_max, ny)
    
    nodes = []
    for j in range(ny):
        for i in range(nx):
            nodes.append([x[i], y[j]])
    nodes = np.array(nodes)
    
    elements = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            node0 = j * nx + i
            node1 = j * nx + i + 1
            node2 = (j + 1) * nx + i
            node3 = (j + 1) * nx + i + 1
            
            elements.append([node0, node1, node2])
            elements.append([node1, node3, node2])
    
    elements = np.array(elements)
    return Mesh(nodes, elements, element_type='triangle')


def generate_cuboid_mesh(
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    z_min: float, z_max: float,
    nx: int, ny: int, nz: int
) -> Mesh:
    x = np.linspace(x_min, x_max, nx)
    y = np.linspace(y_min, y_max, ny)
    z = np.linspace(z_min, z_max, nz)
    
    nodes = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                nodes.append([x[i], y[j], z[k]])
    nodes = np.array(nodes)
    
    elements = []
    for k in range(nz - 1):
        for j in range(ny - 1):
            for i in range(nx - 1):
                n0 = k * ny * nx + j * nx + i
                n1 = k * ny * nx + j * nx + i + 1
                n2 = k * ny * nx + (j + 1) * nx + i
                n3 = k * ny * nx + (j + 1) * nx + i + 1
                n4 = (k + 1) * ny * nx + j * nx + i
                n5 = (k + 1) * ny * nx + j * nx + i + 1
                n6 = (k + 1) * ny * nx + (j + 1) * nx + i
                n7 = (k + 1) * ny * nx + (j + 1) * nx + i + 1
                
                elements.append([n0, n1, n2, n4])
                elements.append([n1, n3, n2, n5])
                elements.append([n2, n3, n7, n5])
                elements.append([n2, n7, n6, n4])
                elements.append([n2, n5, n4, n6])
                elements.append([n1, n5, n3, n7])
    
    elements = np.array(elements)
    return Mesh(nodes, elements, element_type='tetrahedron')


def read_gmsh_file(filename: str) -> Mesh:
    with open(filename, 'r') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    
    if not lines:
        raise ValueError("空的 Gmsh 文件")
    
    if lines[0] == '$MeshFormat':
        return _read_gmsh_v2(filename, content)
    elif lines[0] == '$MeshFormat' and '4.1' in content:
        return _read_gmsh_v4(filename, content)
    else:
        raise ValueError(f"不支持的 Gmsh 格式")


def _read_gmsh_v2(filename: str, content: str) -> Mesh:
    lines = content.split('\n')
    
    nodes = []
    elements = []
    physical_groups = {}
    physical_names = {}
    element_type = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line == '$Nodes':
            i += 1
            num_nodes = int(lines[i].strip())
            i += 1
            for _ in range(num_nodes):
                parts = lines[i].strip().split()
                x = float(parts[1])
                y = float(parts[2])
                z = float(parts[3])
                nodes.append([x, y, z])
                i += 1
        elif line == '$Elements':
            i += 1
            num_elements = int(lines[i].strip())
            i += 1
            for _ in range(num_elements):
                parts = lines[i].strip().split()
                elem_type = int(parts[1])
                
                if elem_type == 2:
                    element_type = 'triangle'
                    num_tags = int(parts[2])
                    n0 = int(parts[3 + num_tags]) - 1
                    n1 = int(parts[4 + num_tags]) - 1
                    n2 = int(parts[5 + num_tags]) - 1
                    elements.append([n0, n1, n2])
                    
                    if num_tags >= 1:
                        tag = int(parts[3])
                        if tag not in physical_groups:
                            physical_groups[tag] = []
                        physical_groups[tag].extend([n0, n1, n2])
                        
                elif elem_type == 4:
                    element_type = 'tetrahedron'
                    num_tags = int(parts[2])
                    n0 = int(parts[3 + num_tags]) - 1
                    n1 = int(parts[4 + num_tags]) - 1
                    n2 = int(parts[5 + num_tags]) - 1
                    n3 = int(parts[6 + num_tags]) - 1
                    elements.append([n0, n1, n2, n3])
                    
                    if num_tags >= 1:
                        tag = int(parts[3])
                        if tag not in physical_groups:
                            physical_groups[tag] = []
                        physical_groups[tag].extend([n0, n1, n2, n3])
                i += 1
        elif line == '$PhysicalNames':
            i += 1
            num_names = int(lines[i].strip())
            i += 1
            for _ in range(num_names):
                parts = lines[i].strip().split(' ', 2)
                tag = int(parts[1])
                name = parts[2].strip('"')
                physical_names[tag] = name
                i += 1
        else:
            i += 1
    
    if element_type is None:
        raise ValueError("未找到有效的单元类型（三角形或四面体）")
    
    nodes = np.array(nodes)
    if element_type == 'triangle':
        nodes = nodes[:, :2]
    
    for tag in physical_groups:
        physical_groups[tag] = list(set(physical_groups[tag]))
    
    return Mesh(nodes, elements, element_type, physical_groups, physical_names)


def _read_gmsh_v4(filename: str, content: str) -> Mesh:
    lines = content.split('\n')
    
    nodes = []
    elements = []
    physical_groups = {}
    physical_names = {}
    element_type = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line == '$Nodes':
            i += 1
            while i < len(lines) and lines[i].strip() != '$EndNodes':
                if lines[i].strip().startswith('#') or not lines[i].strip():
                    i += 1
                    continue
                parts = lines[i].strip().split()
                num_nodes = int(parts[3]) if len(parts) >= 4 else 0
                i += 1
                
                for _ in range(num_nodes):
                    tag_line = lines[i].strip()
                    i += 1
                
                for _ in range(num_nodes):
                    coords = lines[i].strip().split()
                    x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                    nodes.append([x, y, z])
                    i += 1
        elif line == '$Elements':
            i += 1
            while i < len(lines) and lines[i].strip() != '$EndElements':
                if lines[i].strip().startswith('#') or not lines[i].strip():
                    i += 1
                    continue
                parts = lines[i].strip().split()
                if len(parts) < 4:
                    i += 1
                    continue
                entity_type = int(parts[0])
                num_elements = int(parts[3])
                i += 1
                
                for _ in range(num_elements):
                    elem_parts = lines[i].strip().split()
                    elem_tag = int(elem_parts[0])
                    
                    if entity_type == 2:
                        element_type = 'triangle'
                        n0 = int(elem_parts[1]) - 1
                        n1 = int(elem_parts[2]) - 1
                        n2 = int(elem_parts[3]) - 1
                        elements.append([n0, n1, n2])
                    elif entity_type == 4:
                        element_type = 'tetrahedron'
                        n0 = int(elem_parts[1]) - 1
                        n1 = int(elem_parts[2]) - 1
                        n2 = int(elem_parts[3]) - 1
                        n3 = int(elem_parts[4]) - 1
                        elements.append([n0, n1, n2, n3])
                    i += 1
        else:
            i += 1
    
    if element_type is None:
        raise ValueError("未找到有效的单元类型")
    
    nodes = np.array(nodes)
    if element_type == 'triangle':
        nodes = nodes[:, :2]
    
    return Mesh(nodes, elements, element_type, physical_groups, physical_names)


def write_gmsh_file(mesh: Mesh, filename: str) -> None:
    with open(filename, 'w') as f:
        f.write("$MeshFormat\n")
        f.write("2.2 0 8\n")
        f.write("$EndMeshFormat\n")
        
        f.write("$Nodes\n")
        f.write(f"{mesh.num_nodes}\n")
        
        if mesh.dimension == 2:
            for i, (x, y) in enumerate(mesh.nodes):
                f.write(f"{i + 1} {x:.12e} {y:.12e} 0.0\n")
        else:
            for i, (x, y, z) in enumerate(mesh.nodes):
                f.write(f"{i + 1} {x:.12e} {y:.12e} {z:.12e}\n")
        
        f.write("$EndNodes\n")
        
        f.write("$Elements\n")
        f.write(f"{mesh.num_elements}\n")
        
        elem_type_num = 2 if mesh.element_type == 'triangle' else 4
        
        for i, elem in enumerate(mesh.elements):
            node_str = ' '.join([str(n + 1) for n in elem])
            f.write(f"{i + 1} {elem_type_num} 2 1 1 {node_str}\n")
        
        f.write("$EndElements\n")
    
    print(f"Gmsh 文件已写入: {filename}")


def mesh_info(mesh: Mesh) -> None:
    print(f"网格信息:")
    print(f"  维度: {mesh.dimension}D")
    print(f"  单元类型: {mesh.element_type}")
    print(f"  节点数: {mesh.num_nodes}")
    print(f"  单元数: {mesh.num_elements}")
    print(f"  节点范围: x∈[{mesh.nodes[:,0].min():.4f}, {mesh.nodes[:,0].max():.4f}]")
    print(f"            y∈[{mesh.nodes[:,1].min():.4f}, {mesh.nodes[:,1].max():.4f}]")
    if mesh.dimension == 3:
        print(f"            z∈[{mesh.nodes[:,2].min():.4f}, {mesh.nodes[:,2].max():.4f}]")
    
    if mesh.physical_names:
        print(f"  物理组:")
        for tag, name in mesh.physical_names.items():
            count = len(mesh.physical_groups.get(tag, []))
            print(f"    {tag}: {name} ({count} 个节点)")
