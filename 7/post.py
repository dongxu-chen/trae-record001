import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from typing import Optional, Callable
from mesh import Mesh


def _ensure_ccw_ordering_2d(coords: np.ndarray) -> np.ndarray:
    x0, y0 = coords[0]
    x1, y1 = coords[1]
    x2, y2 = coords[2]
    
    area = x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1)
    
    if area < 0:
        return np.array([0, 2, 1])
    return np.array([0, 1, 2])


def _ensure_positive_orientation_3d(coords: np.ndarray) -> np.ndarray:
    A_mat = np.array([
        [1, coords[0,0], coords[0,1], coords[0,2]],
        [1, coords[1,0], coords[1,1], coords[1,2]],
        [1, coords[2,0], coords[2,1], coords[2,2]],
        [1, coords[3,0], coords[3,1], coords[3,2]]
    ])
    
    det_val = np.linalg.det(A_mat)
    
    if det_val < 0:
        return np.array([1, 0, 2, 3])
    return np.array([0, 1, 2, 3])


def write_vtk(
    mesh: Mesh,
    u: np.ndarray,
    filename: str,
    field_name: str = "solution"
) -> None:
    num_nodes = mesh.num_nodes
    num_elements = mesh.num_elements
    
    with open(filename, 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("Finite Element Solution\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n")
        
        f.write(f"POINTS {num_nodes} double\n")
        if mesh.dimension == 2:
            for i in range(num_nodes):
                x, y = mesh.nodes[i]
                f.write(f"{x:.12e} {y:.12e} 0.0\n")
        else:
            for i in range(num_nodes):
                x, y, z = mesh.nodes[i]
                f.write(f"{x:.12e} {y:.12e} {z:.12e}\n")
        
        if mesh.element_type == 'triangle':
            nodes_per_elem = 3
            cell_type = 5
        else:
            nodes_per_elem = 4
            cell_type = 10
        
        total_size = num_elements * (nodes_per_elem + 1)
        f.write(f"CELLS {num_elements} {total_size}\n")
        
        for e in range(num_elements):
            elem_nodes = mesh.elements[e]
            coords = mesh.get_node_coordinates(e)
            
            if mesh.element_type == 'triangle':
                reorder = _ensure_ccw_ordering_2d(coords)
            else:
                reorder = _ensure_positive_orientation_3d(coords)
            
            ordered_nodes = [str(elem_nodes[r]) for r in reorder]
            node_str = ' '.join(ordered_nodes)
            f.write(f"{nodes_per_elem} {node_str}\n")
        
        f.write(f"CELL_TYPES {num_elements}\n")
        for _ in range(num_elements):
            f.write(f"{cell_type}\n")
        
        f.write(f"POINT_DATA {num_nodes}\n")
        f.write(f"SCALARS {field_name} double\n")
        f.write("LOOKUP_TABLE default\n")
        for val in u:
            f.write(f"{val:.12e}\n")
    
    print(f"VTK 文件已写入: {filename}")


def write_vtu(
    mesh: Mesh,
    u: np.ndarray,
    filename: str,
    field_name: str = "solution"
) -> None:
    num_nodes = mesh.num_nodes
    num_elements = mesh.num_elements
    
    if mesh.element_type == 'triangle':
        cell_type = 5
        nodes_per_elem = 3
    else:
        cell_type = 10
        nodes_per_elem = 4
    
    with open(filename, 'w') as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">\n')
        f.write('  <UnstructuredGrid>\n')
        f.write(f'    <Piece NumberOfPoints="{num_nodes}" NumberOfCells="{num_elements}">\n')
        
        f.write('      <Points>\n')
        f.write('        <DataArray type="Float64" NumberOfComponents="3" format="ascii">\n')
        
        if mesh.dimension == 2:
            for i in range(num_nodes):
                x, y = mesh.nodes[i]
                f.write(f"          {x:.12e} {y:.12e} 0.0\n")
        else:
            for i in range(num_nodes):
                x, y, z = mesh.nodes[i]
                f.write(f"          {x:.12e} {y:.12e} {z:.12e}\n")
        
        f.write('        </DataArray>\n')
        f.write('      </Points>\n')
        
        f.write('      <Cells>\n')
        f.write('        <DataArray type="Int64" Name="connectivity" format="ascii">\n')
        
        for e in range(num_elements):
            elem_nodes = mesh.elements[e]
            coords = mesh.get_node_coordinates(e)
            
            if mesh.element_type == 'triangle':
                reorder = _ensure_ccw_ordering_2d(coords)
            else:
                reorder = _ensure_positive_orientation_3d(coords)
            
            ordered_nodes = ' '.join([str(elem_nodes[r]) for r in reorder])
            f.write(f"          {ordered_nodes}\n")
        
        f.write('        </DataArray>\n')
        
        f.write('        <DataArray type="Int64" Name="offsets" format="ascii">\n')
        offset = 0
        for _ in range(num_elements):
            offset += nodes_per_elem
            f.write(f"          {offset}\n")
        f.write('        </DataArray>\n')
        
        f.write('        <DataArray type="UInt8" Name="types" format="ascii">\n')
        for _ in range(num_elements):
            f.write(f"          {cell_type}\n")
        f.write('        </DataArray>\n')
        f.write('      </Cells>\n')
        
        f.write('      <PointData>\n')
        f.write(f'        <DataArray type="Float64" Name="{field_name}" NumberOfComponents="1" format="ascii">\n')
        for val in u:
            f.write(f"          {val:.12e}\n")
        f.write('        </DataArray>\n')
        f.write('      </PointData>\n')
        
        f.write('    </Piece>\n')
        f.write('  </UnstructuredGrid>\n')
        f.write('</VTKFile>\n')
    
    print(f"VTU 文件已写入: {filename}")


def plot_mesh(mesh: Mesh, title: str = "网格结构") -> None:
    if mesh.dimension == 3:
        print("3D 网格需要在 ParaView 中查看，已跳过 matplotlib 绘图")
        return
    
    fig, ax = plt.subplots(figsize=(8, 8))
    
    x = mesh.nodes[:, 0]
    y = mesh.nodes[:, 1]
    triangles = mesh.elements
    
    tri = Triangulation(x, y, triangles)
    
    ax.triplot(tri, 'bo-', lw=1, markersize=4)
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title(title)
    ax.set_aspect('equal')
    
    boundary_nodes = mesh.get_boundary_nodes()
    if boundary_nodes:
        ax.plot(x[boundary_nodes], y[boundary_nodes], 'ro', markersize=6, label='边界节点')
        ax.legend()
    
    plt.tight_layout()
    plt.show()


def plot_solution(
    mesh: Mesh,
    u: np.ndarray,
    title: str = "数值解",
    save_path: Optional[str] = None
) -> None:
    if mesh.dimension == 3:
        print("3D 解需要在 ParaView 中查看，已跳过 matplotlib 绘图")
        print(f"提示: 使用 write_vtk() 或 write_vtu() 导出为 ParaView 格式")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    x = mesh.nodes[:, 0]
    y = mesh.nodes[:, 1]
    triangles = mesh.elements
    
    tri = Triangulation(x, y, triangles)
    
    tpc = ax.tripcolor(tri, u, shading='gouraud', cmap='viridis')
    
    fig.colorbar(tpc, ax=ax, label='u(x, y)')
    
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title(title)
    ax.set_aspect('equal')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图形已保存至: {save_path}")
    
    plt.show()


def plot_comparison(
    mesh: Mesh,
    u: np.ndarray,
    exact_solution: Callable[[np.ndarray], np.ndarray],
    save_path: Optional[str] = None
) -> None:
    if mesh.dimension == 3:
        print("3D 对比图需要在 ParaView 中查看，已跳过 matplotlib 绘图")
        return
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    x = mesh.nodes[:, 0]
    y = mesh.nodes[:, 1]
    triangles = mesh.elements
    
    tri = Triangulation(x, y, triangles)
    u_exact = exact_solution(mesh.nodes)
    
    tpc1 = axes[0].tripcolor(tri, u, shading='gouraud', cmap='viridis')
    fig.colorbar(tpc1, ax=axes[0], label='u')
    axes[0].set_xlabel('x')
    axes[0].set_ylabel('y')
    axes[0].set_title('数值解')
    axes[0].set_aspect('equal')
    
    tpc2 = axes[1].tripcolor(tri, u_exact, shading='gouraud', cmap='viridis')
    fig.colorbar(tpc2, ax=axes[1], label='u_exact')
    axes[1].set_xlabel('x')
    axes[1].set_ylabel('y')
    axes[1].set_title('精确解')
    axes[1].set_aspect('equal')
    
    error = np.abs(u - u_exact)
    tpc3 = axes[2].tripcolor(tri, error, shading='gouraud', cmap='hot')
    fig.colorbar(tpc3, ax=axes[2], label='|error|')
    axes[2].set_xlabel('x')
    axes[2].set_ylabel('y')
    axes[2].set_title('绝对误差')
    axes[2].set_aspect('equal')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图形已保存至: {save_path}")
    
    plt.show()


def plot_contour(
    mesh: Mesh,
    u: np.ndarray,
    levels: int = 15,
    title: str = "等值线图",
    save_path: Optional[str] = None
) -> None:
    if mesh.dimension == 3:
        print("3D 等值线需要在 ParaView 中查看，已跳过 matplotlib 绘图")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    x = mesh.nodes[:, 0]
    y = mesh.nodes[:, 1]
    triangles = mesh.elements
    
    tri = Triangulation(x, y, triangles)
    
    contour = ax.tricontour(tri, u, levels=levels, linewidths=1.5, cmap='viridis')
    ax.clabel(contour, inline=True, fontsize=10, fmt='%.3f')
    
    ax.triplot(tri, 'k-', lw=0.5, alpha=0.3)
    
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title(title)
    ax.set_aspect('equal')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图形已保存至: {save_path}")
    
    plt.show()


def export_results(
    mesh: Mesh,
    u: np.ndarray,
    basename: str,
    field_name: str = "solution",
    formats: list = ['vtk', 'vtu']
) -> None:
    if 'vtk' in formats:
        write_vtk(mesh, u, f"{basename}.vtk", field_name)
    if 'vtu' in formats:
        write_vtu(mesh, u, f"{basename}.vtu", field_name)
