#!/usr/bin/env python3
"""
非线性求解器综合示例

本示例演示:
1. 非线性泊松方程求解
2. 非线性热传导方程求解（温度相关材料属性）
3. 相变材料模拟
4. Newton-Raphson迭代收敛历史可视化
5. MPI并行求解
"""

import sys
from dolfin import *
import matplotlib.pyplot as plt
import numpy as np

from fenics_solver import (
    NonlinearPoissonSolver, NonlinearHeatSolver,
    BoundaryCondition, NewtonRaphsonSolver,
    NonlinearThermalMaterial, TemperatureDependentConductivity,
    PhaseChangeMaterial, create_parallel_mesh,
    plot_solution, plot_convergence_history,
    plot_timestep_history, plot_material_property,
    ParallelUtils
)

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def example1_nonlinear_poisson():
    """示例1: 非线性泊松方程 - 传导系数依赖于解"""
    print("=" * 70)
    print("示例1: 非线性泊松方程")
    print("=" * 70)
    
    mesh = UnitSquareMesh(40, 40)
    
    solver = NonlinearPoissonSolver(mesh)
    
    bc_left = DirichletBC(solver.V, Constant(0.0), "near(x[0], 0.0)")
    bc_right = DirichletBC(solver.V, Constant(1.0), "near(x[0], 1.0)")
    solver.bcs = [bc_left, bc_right]
    
    solver.set_source(Constant(10.0))
    
    def nonlinear_k(u):
        return 1.0 + 10.0 * u ** 2
    
    solver.set_conductivity(nonlinear_k)
    
    solver.solver.set_parameters(max_iterations=20, rel_tolerance=1e-6)
    
    print("求解非线性泊松方程...")
    success, num_iters, u = solver.solve()
    
    if success:
        print(f"求解成功! 迭代次数: {num_iters}")
        print(f"解最大值: {u.vector().max():.4f}")
        print(f"解最小值: {u.vector().min():.4f}")
    else:
        print(f"求解失败!")
    
    fig, ax = plt.subplots(figsize=(10, 8))
    plot_solution(u, mesh, title="非线性泊松方程解 - k(u) = 1 + 10u²", ax=ax)
    plt.savefig("nonlinear_poisson_solution.png", dpi=150, bbox_inches="tight")
    print("解图已保存到 nonlinear_poisson_solution.png")
    plt.close()
    
    plot_convergence_history(solver.history, 
                           title="Newton-Raphson收敛历史 - 非线性泊松方程",
                           save_path="nonlinear_poisson_convergence.png")
    print("收敛历史图已保存到 nonlinear_poisson_convergence.png")
    plt.close('all')
    
    return solver


def example2_temperature_dependent_heat():
    """示例2: 温度相关热传导方程"""
    print("\n" + "=" * 70)
    print("示例2: 温度相关热传导方程")
    print("=" * 70)
    
    mesh = UnitSquareMesh(30, 30)
    
    k_func = TemperatureDependentConductivity(k0=1.0, alpha_k=0.01)
    material = NonlinearThermalMaterial(k_func=k_func)
    
    solver = NonlinearHeatSolver(mesh, material=material)
    
    bc_left = DirichletBC(solver.V, Constant(100.0), "near(x[0], 0.0)")
    bc_right = DirichletBC(solver.V, Constant(0.0), "near(x[0], 1.0)")
    solver.bcs = [bc_left, bc_right]
    
    u0 = Expression("100.0 * exp(-50.0 * (x[0] * x[0] + x[1] * x[1]))", degree=2)
    solver.set_initial_condition(u0)
    solver.set_source(Constant(0.0))
    solver.set_time_step(0.01)
    solver.set_time_scheme(0.5)
    
    solver.solver.set_parameters(max_iterations=15, rel_tolerance=1e-5)
    
    print("求解温度相关热传导方程...")
    print("材料属性: k(T) = 1.0 * (1 + 0.01 * T)")
    
    T_final = 0.1
    num_steps = int(T_final / 0.01)
    solutions = []
    times = []
    
    for step in range(num_steps):
        success, niters, u = solver.solve_timestep()
        if not success:
            print(f"时间步 {step+1} 求解失败!")
            break
        
        if step % 5 == 0 or step == num_steps - 1:
            solutions.append(u.copy(deepcopy=True))
            times.append(solver.time)
            print(f"时间步 {step+1}/{num_steps}: t = {solver.time:.4f}, "
                  f"迭代次数 = {niters}, T_max = {u.vector().max():.2f}")
    
    print(f"\n求解完成!")
    print(f"最终时间: {solver.time:.4f}")
    print(f"最终最大温度: {solver.u.vector().max():.2f}")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    for i, (u, t) in enumerate(zip(solutions, times)):
        row = i // 2
        col = i % 2
        plot_solution(u, mesh, title=f"温度分布 t = {t:.3f}", ax=axes[row, col])
    plt.tight_layout()
    plt.savefig("temperature_dependent_heat.png", dpi=150, bbox_inches="tight")
    print("温度演化图已保存到 temperature_dependent_heat.png")
    plt.close()
    
    plot_timestep_history(solver.time_history,
                         title="时间步收敛历史",
                         save_path="heat_timestep_history.png")
    print("时间步历史图已保存到 heat_timestep_history.png")
    plt.close('all')
    
    return solver


def example3_phase_change_material():
    """示例3: 相变材料模拟"""
    print("\n" + "=" * 70)
    print("示例3: 相变材料热传导模拟")
    print("=" * 70)
    
    mesh = UnitSquareMesh(30, 30)
    
    pc_material = PhaseChangeMaterial(
        k_solid=1.0,
        k_liquid=5.0,
        rho_c_solid=1.0,
        rho_c_liquid=1.0,
        T_m=50.0,
        L=100.0,
        delta_T=5.0
    )
    
    plot_material_property(pc_material, T_range=(0, 100),
                          title="相变材料属性",
                          save_path="phase_change_material_properties.png")
    print("材料属性图已保存到 phase_change_material_properties.png")
    plt.close()
    
    solver = NonlinearHeatSolver(mesh, material=pc_material)
    
    bc_left = DirichletBC(solver.V, Constant(100.0), "near(x[0], 0.0)")
    bc_right = DirichletBC(solver.V, Constant(0.0), "near(x[0], 1.0)")
    solver.bcs = [bc_left, bc_right]
    
    u0 = Constant(0.0)
    solver.set_initial_condition(u0)
    solver.set_source(Constant(0.0))
    solver.set_time_step(0.005)
    solver.set_time_scheme(1.0)
    
    solver.solver.set_parameters(max_iterations=30, rel_tolerance=1e-5)
    
    print("求解相变热传导方程...")
    print(f"相变温度: T_m = 50.0")
    print(f"潜热: L = 100.0")
    print(f"固相传导系数: k_s = 1.0")
    print(f"液相传导系数: k_l = 5.0")
    
    T_final = 0.1
    num_steps = int(T_final / 0.005)
    solutions = []
    times = []
    
    for step in range(num_steps):
        success, niters, u = solver.solve_timestep()
        if not success:
            print(f"时间步 {step+1} 求解失败!")
            break
        
        if step % 10 == 0 or step == num_steps - 1:
            solutions.append(u.copy(deepcopy=True))
            times.append(solver.time)
            print(f"时间步 {step+1}/{num_steps}: t = {solver.time:.4f}, "
                  f"迭代次数 = {niters}, T_max = {u.vector().max():.2f}")
    
    print(f"\n求解完成!")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    for i, (u, t) in enumerate(zip(solutions, times)):
        row = i // 3
        col = i % 3
        plot_solution(u, mesh, title=f"相变温度分布 t = {t:.3f}", ax=axes[row, col])
    plt.tight_layout()
    plt.savefig("phase_change_solution.png", dpi=150, bbox_inches="tight")
    print("相变温度分布图已保存到 phase_change_solution.png")
    plt.close()
    
    return solver


def example4_newton_raphson_comparison():
    """示例4: Newton-Raphson参数比较"""
    print("\n" + "=" * 70)
    print("示例4: Newton-Raphson求解器参数比较")
    print("=" * 70)
    
    mesh = UnitSquareMesh(30, 30)
    
    solvers = []
    labels = []
    
    solver1 = NonlinearPoissonSolver(mesh)
    solver1.bcs = [DirichletBC(solver1.V, Constant(0.0), "on_boundary")]
    solver1.set_source(Constant(20.0))
    solver1.set_conductivity(lambda u: 1.0 + 20.0 * u ** 2)
    solver1.solver.set_parameters(max_iterations=30, line_search=False, relaxation=1.0)
    solvers.append(solver1)
    labels.append("无松弛, 无搜索")
    
    solver2 = NonlinearPoissonSolver(mesh)
    solver2.bcs = [DirichletBC(solver2.V, Constant(0.0), "on_boundary")]
    solver2.set_source(Constant(20.0))
    solver2.set_conductivity(lambda u: 1.0 + 20.0 * u ** 2)
    solver2.solver.set_parameters(max_iterations=30, line_search=False, relaxation=0.5)
    solvers.append(solver2)
    labels.append("松弛 α=0.5")
    
    solver3 = NonlinearPoissonSolver(mesh)
    solver3.bcs = [DirichletBC(solver3.V, Constant(0.0), "on_boundary")]
    solver3.set_source(Constant(20.0))
    solver3.set_conductivity(lambda u: 1.0 + 20.0 * u ** 2)
    solver3.solver.set_parameters(max_iterations=30, line_search=True)
    solvers.append(solver3)
    labels.append("Armijo线搜索")
    
    histories = []
    for i, solver in enumerate(solvers):
        print(f"\n求解 {labels[i]}...")
        success, num_iters, u = solver.solve()
        if success:
            print(f"  成功! 迭代次数: {num_iters}")
            histories.append(solver.history)
        else:
            print(f"  失败!")
            histories.append(solver.history)
    
    from fenics_solver.visualization import plot_nonlinear_comparison
    plot_nonlinear_comparison(histories, labels,
                             title="Newton-Raphson参数比较",
                             save_path="newton_comparison.png")
    print("比较图已保存到 newton_comparison.png")
    plt.close('all')
    
    return solvers


def example5_parallel_solver():
    """示例5: MPI并行求解"""
    print("\n" + "=" * 70)
    print("示例5: MPI并行求解")
    print("=" * 70)
    
    rank = ParallelUtils.get_rank()
    size = ParallelUtils.get_size()
    
    if size == 1:
        print("当前为串行模式")
        print("提示: 使用 'mpirun -np 4 python example_nonlinear_solver.py' 运行并行模式")
    else:
        print(f"并行模式: 进程 {rank} / {size}")
    
    if rank == 0:
        print(f"\n创建网格...")
    
    nx, ny = 100, 100
    mesh = create_parallel_mesh(nx, ny)
    
    if rank == 0:
        print(f"本地单元数: {mesh.num_cells()}")
        print(f"本地顶点数: {mesh.num_vertices()}")
    
    solver = NonlinearPoissonSolver(mesh)
    
    if rank == 0:
        print(f"\n有限元空间维度: {solver.V.dim()}")
    
    bc = DirichletBC(solver.V, Constant(0.0), "on_boundary")
    solver.bcs = [bc]
    solver.set_source(Constant(10.0))
    solver.set_conductivity(lambda u: 1.0 + 5.0 * u ** 2)
    
    if rank == 0:
        print("求解非线性泊松方程...")
    
    ParallelUtils.barrier()
    
    success, num_iters, u = solver.solve()
    
    if rank == 0:
        if success:
            print(f"求解成功! 迭代次数: {num_iters}")
            print(f"解最大值: {u.vector().max():.4f}")
        else:
            print(f"求解失败!")
        
        plot_convergence_history(solver.history,
                               title="并行求解收敛历史",
                               save_path="parallel_convergence.png")
        print("收敛历史图已保存到 parallel_convergence.png")
        
        fig, ax = plt.subplots(figsize=(10, 8))
        plot_solution(u, mesh, title="并行非线性泊松解", ax=ax)
        plt.savefig("parallel_solution.png", dpi=150, bbox_inches="tight")
        print("解图已保存到 parallel_solution.png")
        plt.close('all')
    
    return solver


def main():
    print("\n非线性有限元求解器 - 综合示例\n")
    
    solver1 = example1_nonlinear_poisson()
    solver2 = example2_temperature_dependent_heat()
    solver3 = example3_phase_change_material()
    solver4 = example4_newton_raphson_comparison()
    
    if ParallelUtils.get_rank() == 0:
        solver5 = example5_parallel_solver()
    
    if ParallelUtils.get_rank() == 0:
        print("\n" + "=" * 70)
        print("所有示例运行完成!")
        print("=" * 70)
        print("\n生成的文件:")
        print("  - nonlinear_poisson_solution.png")
        print("  - nonlinear_poisson_convergence.png")
        print("  - temperature_dependent_heat.png")
        print("  - heat_timestep_history.png")
        print("  - phase_change_material_properties.png")
        print("  - phase_change_solution.png")
        print("  - newton_comparison.png")
        print("  - parallel_convergence.png")
        print("  - parallel_solution.png")


if __name__ == "__main__":
    main()
