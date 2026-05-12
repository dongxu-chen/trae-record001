import numpy as np
from mesh import (
    Mesh, 
    generate_rectangular_mesh, 
    generate_cuboid_mesh, 
    mesh_info,
    read_gmsh_file,
    write_gmsh_file
)
from assembly import assemble_global_system, apply_dirichlet_boundary
from solver import solve_linear_system, compute_l2_error, verify_solution
from post import (
    plot_mesh, 
    plot_solution, 
    plot_comparison, 
    plot_contour,
    write_vtk,
    write_vtu,
    export_results
)
from boundary import (
    BoundaryCondition,
    create_boundary_condition,
    apply_multiple_boundary_conditions,
    print_boundary_info
)


def source_function_2d(x: float, y: float) -> float:
    return 2.0 * (np.pi**2) * np.sin(np.pi * x) * np.sin(np.pi * y)


def exact_solution_2d(nodes: np.ndarray) -> np.ndarray:
    x = nodes[:, 0]
    y = nodes[:, 1]
    return np.sin(np.pi * x) * np.sin(np.pi * y)


def source_function_3d(x: float, y: float, z: float) -> float:
    return 3.0 * (np.pi**2) * np.sin(np.pi * x) * np.sin(np.pi * y) * np.sin(np.pi * z)


def exact_solution_3d(nodes: np.ndarray) -> np.ndarray:
    x = nodes[:, 0]
    y = nodes[:, 1]
    z = nodes[:, 2]
    return np.sin(np.pi * x) * np.sin(np.pi * y) * np.sin(np.pi * z)


def run_2d_example():
    print("=" * 60)
    print("二维三角形网格求解泊松方程")
    print("=" * 60)
    
    print("\n1. 生成网格...")
    mesh = generate_rectangular_mesh(
        x_min=0.0,
        x_max=1.0,
        y_min=0.0,
        y_max=1.0,
        nx=11,
        ny=11
    )
    mesh_info(mesh)
    
    print("\n2. 组装全局刚度矩阵和载荷向量...")
    K, F = assemble_global_system(mesh, source_function_2d)
    
    print("\n3. 应用边界条件...")
    bc1 = create_boundary_condition(
        mesh,
        bc_type='dirichlet',
        value=0.0,
        location='all_boundary'
    )
    print_boundary_info(mesh, [bc1])
    
    K, F = apply_multiple_boundary_conditions(K, F, mesh, [bc1])
    
    print("\n4. 求解线性系统...")
    u = solve_linear_system(K, F, method='auto', num_threads=4)
    verify_solution(u)
    
    print("\n5. 计算误差...")
    l2_error = compute_l2_error(u, exact_solution_2d, mesh.nodes)
    print(f"  L2 误差: {l2_error:.6e}")
    
    print("\n6. 导出结果...")
    export_results(mesh, u, "solution_2d", field_name="poisson_solution", formats=['vtk', 'vtu'])
    
    print("\n7. 可视化结果...")
    plot_mesh(mesh, title="矩形区域三角形网格")
    plot_solution(mesh, u, title="泊松方程数值解 (2D)")
    plot_comparison(mesh, u, exact_solution_2d)
    plot_contour(mesh, u, title="数值解等值线图")
    
    print("\n" + "=" * 60)
    print("二维求解完成！")
    print("=" * 60)


def run_3d_example():
    print("\n" + "=" * 60)
    print("三维四面体网格求解泊松方程")
    print("=" * 60)
    
    print("\n1. 生成三维网格...")
    mesh = generate_cuboid_mesh(
        x_min=0.0, x_max=1.0,
        y_min=0.0, y_max=1.0,
        z_min=0.0, z_max=1.0,
        nx=6, ny=6, nz=6
    )
    mesh_info(mesh)
    
    print("\n2. 组装全局刚度矩阵和载荷向量...")
    K, F = assemble_global_system(mesh, source_function_3d)
    
    print("\n3. 应用边界条件...")
    bc1 = create_boundary_condition(
        mesh,
        bc_type='dirichlet',
        value=0.0,
        location='all_boundary'
    )
    print_boundary_info(mesh, [bc1])
    
    K, F = apply_multiple_boundary_conditions(K, F, mesh, [bc1])
    
    print("\n4. 求解线性系统...")
    u = solve_linear_system(K, F, method='cg', num_threads=4, preconditioner='jacobi')
    verify_solution(u)
    
    print("\n5. 计算误差...")
    l2_error = compute_l2_error(u, exact_solution_3d, mesh.nodes)
    print(f"  L2 误差: {l2_error:.6e}")
    
    print("\n6. 导出结果...")
    export_results(mesh, u, "solution_3d", field_name="poisson_solution_3d", formats=['vtk', 'vtu'])
    
    print("\n提示: 三维结果请在 ParaView 中查看 solution_3d.vtu 文件")
    
    print("\n" + "=" * 60)
    print("三维求解完成！")
    print("=" * 60)


def run_gmsh_example():
    print("\n" + "=" * 60)
    print("使用 Gmsh 网格文件示例")
    print("=" * 60)
    
    mesh_2d = generate_rectangular_mesh(0, 1, 0, 1, 8, 8)
    write_gmsh_file(mesh_2d, "example.msh")
    
    print("\n已生成 example.msh 文件")
    print("可以使用 read_gmsh_file('example.msh') 读取")
    
    print("\n" + "=" * 60)
    print("Gmsh 示例完成！")
    print("=" * 60)


def main():
    run_2d_example()
    run_3d_example()
    run_gmsh_example()


if __name__ == "__main__":
    main()
