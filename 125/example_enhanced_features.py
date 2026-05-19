#!/usr/bin/env python3
"""
增强功能综合示例

本示例演示:
1. 平滑边界条件 - 避免强间断
2. 非均匀材料属性 - 物性函数插值
3. 自适应时间步长 - 基于CFL条件
4. 网格自适应细化 - 误差估计与单元标记
"""

import sys
from dolfin import *
import matplotlib.pyplot as plt
import numpy as np

from fenics_solver import (
    PoissonSolver, HeatEquationSolver, BoundaryCondition,
    ThermalMaterial, plot_solution, plot_mesh,
    create_unit_square_boundary_markers,
    ErrorEstimator, MeshAdapter
)

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def example1_smooth_boundary():
    """示例1: 平滑边界条件，避免边界处的强间断"""
    print("=" * 70)
    print("示例1: 平滑边界条件")
    print("=" * 70)
    
    mesh = UnitSquareMesh(40, 40)
    solver = PoissonSolver(mesh)
    
    markers = create_unit_square_boundary_markers()
    
    bc_left = BoundaryCondition.create_dirichlet(Constant(1.0), markers["left"])
    bc_right = BoundaryCondition.create_dirichlet(Constant(0.0), markers["right"])
    bc_bottom = BoundaryCondition.create_dirichlet(Constant(0.5), markers["bottom"])
    bc_top = BoundaryCondition.create_dirichlet(Constant(0.5), markers["top"])
    
    solver.set_boundary_conditions([bc_left, bc_right, bc_bottom, bc_top])
    solver.set_source_term(Constant(0.0))
    
    u = solver.solve()
    
    print("求解完成")
    print(f"解最大值: {u.vector().max():.4f}")
    print(f"解最小值: {u.vector().min():.4f}")
    
    fig, ax = plt.subplots(figsize=(10, 8))
    plot_solution(u, mesh, title="泊松方程解 - 不同边界条件", ax=ax)
    plt.savefig("poisson_smooth_boundary.png", dpi=150, bbox_inches="tight")
    print("结果已保存到 poisson_smooth_boundary.png")
    plt.close()
    
    return solver


def example2_heterogeneous_material():
    """示例2: 非均匀材料属性 - 分层材料和夹杂材料"""
    print("\n" + "=" * 70)
    print("示例2: 非均匀材料属性")
    print("=" * 70)
    
    mesh = UnitSquareMesh(50, 50)
    
    print("创建分层材料属性...")
    layers = [
        (0.0, 1.0),
        (0.3, 5.0),
        (0.5, 0.5),
        (0.7, 3.0),
        (1.0, 1.0)
    ]
    
    class LayeredK(Expression):
        def __init__(self, layers, **kwargs):
            self.layers = layers
            super().__init__(**kwargs)
        
        def eval(self, value, x):
            z = x[0]
            if z <= self.layers[0][0]:
                value[0] = self.layers[0][1]
            elif z >= self.layers[-1][0]:
                value[0] = self.layers[-1][1]
            else:
                for i in range(len(self.layers)-1):
                    z0, v0 = self.layers[i]
                    z1, v1 = self.layers[i+1]
                    if z0 <= z <= z1:
                        alpha = (z - z0) / (z1 - z0)
                        value[0] = v0 + alpha * (v1 - v0)
                        break
    
    k_layered = LayeredK(layers, degree=2)
    
    material = ThermalMaterial(conductivity=k_layered)
    
    solver = PoissonSolver(mesh, material=material)
    
    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)
    solver.set_boundary_conditions([bc])
    solver.set_source_term(Constant(1.0))
    
    u = solver.solve()
    
    print("求解完成")
    print(f"解最大值: {u.vector().max():.4f}")
    print(f"解最小值: {u.vector().min():.4f}")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    plot_solution(u, mesh, title="分层材料泊松方程解", ax=axes[0])
    
    V_k = FunctionSpace(mesh, "P", 1)
    k_func = Function(V_k)
    k_func.interpolate(k_layered)
    plot_solution(k_func, mesh, title="热传导系数分布", ax=axes[1])
    
    plt.tight_layout()
    plt.savefig("heterogeneous_material.png", dpi=150, bbox_inches="tight")
    print("结果已保存到 heterogeneous_material.png")
    plt.close()
    
    return solver


def example3_adaptive_time_stepping():
    """示例3: 基于CFL条件的自适应时间步长"""
    print("\n" + "=" * 70)
    print("示例3: 自适应时间步长热传导")
    print("=" * 70)
    
    mesh = UnitSquareMesh(40, 40)
    
    print("固定时间步长求解...")
    solver_fixed = HeatEquationSolver(mesh, alpha=0.1)
    
    u0 = Expression("exp(-100*((x[0]-0.5)*(x[0]-0.5) + (x[1]-0.5)*(x[1]-0.5)))", degree=4)
    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)
    
    solver_fixed.set_boundary_conditions([bc])
    solver_fixed.set_initial_condition(u0)
    solver_fixed.set_time_parameters(T=0.1, num_steps=100)
    solutions_fixed, times_fixed = solver_fixed.solve()
    
    print(f"\n固定时间步长:")
    print(f"  时间步数: {len(times_fixed)}")
    print(f"  时间步长: dt = {0.1/100:.6f}")
    
    print("\n自适应时间步长求解...")
    solver_adaptive = HeatEquationSolver(mesh, alpha=0.1)
    solver_adaptive.enable_adaptive_time_stepping(cfl_number=0.5)
    
    solver_adaptive.set_boundary_conditions([bc])
    solver_adaptive.set_initial_condition(u0)
    solver_adaptive.set_time_adaptive(T=0.1)
    solutions_adaptive, times_adaptive = solver_adaptive.solve()
    
    dt_history = solver_adaptive.time_step_history
    print(f"\n自适应时间步长:")
    print(f"  时间步数: {len(times_adaptive)}")
    print(f"  平均步长: {np.mean(dt_history):.6f}")
    print(f"  最大步长: {np.max(dt_history):.6f}")
    print(f"  最小步长: {np.min(dt_history):.6f}")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    plot_solution(solutions_fixed[-1], mesh, title="固定步长 - 最终时刻", ax=axes[0, 0])
    plot_solution(solutions_adaptive[-1], mesh, title="自适应步长 - 最终时刻", ax=axes[0, 1])
    
    axes[1, 0].plot(times_fixed[:-1], [0.1/100] * len(times_fixed[:-1]), 'b-', label='固定步长')
    axes[1, 0].plot(times_adaptive[:-1], dt_history, 'r-o', markersize=3, label='自适应步长')
    axes[1, 0].set_xlabel('时间')
    axes[1, 0].set_ylabel('时间步长 dt')
    axes[1, 0].set_title('时间步长对比')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].plot(times_fixed, [u.vector().max() for u in solutions_fixed], 'b-', label='固定步长')
    axes[1, 1].plot(times_adaptive, [u.vector().max() for u in solutions_adaptive], 'r--', label='自适应步长')
    axes[1, 1].set_xlabel('时间')
    axes[1, 1].set_ylabel('最大温度')
    axes[1, 1].set_title('温度演化对比')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("adaptive_time_stepping.png", dpi=150, bbox_inches="tight")
    print("结果已保存到 adaptive_time_stepping.png")
    plt.close()
    
    return solver_fixed, solver_adaptive


def example4_mesh_adaptation():
    """示例4: 误差估计与网格自适应细化"""
    print("\n" + "=" * 70)
    print("示例4: 网格自适应细化")
    print("=" * 70)
    
    initial_mesh = UnitSquareMesh(16, 16)
    
    print(f"初始网格: {initial_mesh.num_cells()} 单元, {initial_mesh.num_vertices()} 节点")
    
    markers = create_unit_square_boundary_markers()
    bc_left = BoundaryCondition.create_dirichlet(Constant(1.0), markers["left"])
    bc_right = BoundaryCondition.create_dirichlet(Constant(0.0), markers["right"])
    bc_bottom = BoundaryCondition.create_dirichlet(Constant(0.0), markers["bottom"])
    bc_top = BoundaryCondition.create_dirichlet(Constant(0.0), markers["top"])
    bcs = [bc_left, bc_right, bc_bottom, bc_top]
    
    f = Expression("100*exp(-100*((x[0]-0.7)*(x[0]-0.7) + (x[1]-0.3)*(x[1]-0.3)))", degree=4)
    
    adapter = MeshAdapter(initial_mesh, refine_fraction=0.3)
    current_mesh = initial_mesh
    
    errors = []
    num_cells_list = []
    solutions = []
    
    for iteration in range(4):
        print(f"\n自适应迭代 {iteration + 1}")
        print(f"  当前网格: {current_mesh.num_cells()} 单元")
        
        solver = PoissonSolver(current_mesh)
        solver.set_boundary_conditions(bcs)
        solver.set_source_term(f)
        u = solver.solve()
        
        eta = ErrorEstimator.residual_based_error(u, f, current_mesh)
        total_error = np.sum(eta.vector().get_local())
        errors.append(total_error)
        num_cells_list.append(current_mesh.num_cells())
        solutions.append(u.copy(deepcopy=True))
        
        print(f"  估计误差: {total_error:.6e}")
        
        if iteration < 3:
            cell_markers = adapter.mark_cells_for_refinement(eta, method="fixed_fraction")
            current_mesh = adapter.adapt_mesh(cell_markers)
    
    print(f"\n网格自适应完成")
    print(f"最终网格: {current_mesh.num_cells()} 单元")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    for i, (u, n_cells) in enumerate(zip(solutions, num_cells_list)):
        row = i // 2
        col = i % 2
        mesh = solutions[i].function_space().mesh()
        plot_solution(u, mesh, title=f"迭代 {i+1} - {n_cells} 单元", ax=axes[row, col])
    
    plt.tight_layout()
    plt.savefig("mesh_adaptation.png", dpi=150, bbox_inches="tight")
    print("结果已保存到 mesh_adaptation.png")
    plt.close()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.loglog(num_cells_list, errors, 'bo-', markersize=8)
    ax.set_xlabel('单元数')
    ax.set_ylabel('估计误差')
    ax.set_title('网格收敛')
    ax.grid(True, alpha=0.3)
    plt.savefig("mesh_convergence.png", dpi=150, bbox_inches="tight")
    print("收敛图已保存到 mesh_convergence.png")
    plt.close()
    
    return adapter, solutions


def example5_combined_heat_with_material():
    """示例5: 非均匀材料热传导 + 自适应时间步长"""
    print("\n" + "=" * 70)
    print("示例5: 非均匀材料热传导 + 自适应时间步长")
    print("=" * 70)
    
    mesh = UnitSquareMesh(40, 40)
    
    class CircularInclusion(Expression):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
        
        def eval(self, value, x):
            r2 = (x[0] - 0.5)**2 + (x[1] - 0.5)**2
            if r2 < 0.1**2:
                value[0] = 10.0
            else:
                value[0] = 1.0
    
    k_inclusion = CircularInclusion(degree=2)
    material = ThermalMaterial(conductivity=k_inclusion, specific_heat=1.0, density=1.0)
    
    solver = HeatEquationSolver(mesh, material=material)
    solver.enable_adaptive_time_stepping(cfl_number=0.3)
    
    u0 = Expression("exp(-50*((x[0]-0.5)*(x[0]-0.5) + (x[1]-0.5)*(x[1]-0.5)))", degree=4)
    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)
    
    solver.set_boundary_conditions([bc])
    solver.set_initial_condition(u0)
    solver.set_time_adaptive(T=0.05)
    solutions, times = solver.solve()
    
    dt_history = solver.time_step_history
    print(f"\n求解统计:")
    print(f"  时间步数: {len(times)}")
    print(f"  平均步长: {np.mean(dt_history):.6f}")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    time_indices = [0, len(times)//4, len(times)//2, 3*len(times)//4, -1]
    
    for idx, ti in enumerate(time_indices):
        row = idx // 3
        col = idx % 3
        plot_solution(solutions[ti], mesh, title=f"t = {times[ti]:.4f}", ax=axes[row, col])
    
    V_k = FunctionSpace(mesh, "P", 1)
    k_func = Function(V_k)
    k_func.interpolate(k_inclusion)
    plot_solution(k_func, mesh, title="热传导系数分布", ax=axes[1, 2])
    
    plt.tight_layout()
    plt.savefig("combined_heat_material.png", dpi=150, bbox_inches="tight")
    print("结果已保存到 combined_heat_material.png")
    plt.close()
    
    return solver


def main():
    print("\n偏微分方程有限元求解器 - 增强功能示例\n")
    
    print("运行示例1: 平滑边界条件")
    solver1 = example1_smooth_boundary()
    
    print("\n运行示例2: 非均匀材料属性")
    solver2 = example2_heterogeneous_material()
    
    print("\n运行示例3: 自适应时间步长")
    solver3_fixed, solver3_adaptive = example3_adaptive_time_stepping()
    
    print("\n运行示例4: 网格自适应细化")
    adapter, solutions4 = example4_mesh_adaptation()
    
    print("\n运行示例5: 综合示例 - 非均匀材料热传导")
    solver5 = example5_combined_heat_with_material()
    
    print("\n" + "=" * 70)
    print("所有示例运行完成!")
    print("=" * 70)
    print("\n生成的文件:")
    print("  - poisson_smooth_boundary.png")
    print("  - heterogeneous_material.png")
    print("  - adaptive_time_stepping.png")
    print("  - mesh_adaptation.png")
    print("  - mesh_convergence.png")
    print("  - combined_heat_material.png")


if __name__ == "__main__":
    main()
