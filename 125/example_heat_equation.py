#!/usr/bin/env python3
"""
热传导方程求解示例

本示例演示如何使用fenics_solver库求解热传导方程
"""

from dolfin import *
from fenics_solver import HeatEquationSolver, BoundaryCondition
from fenics_solver.visualization import plot_solution, animate_heat_equation
import matplotlib.pyplot as plt


def example1_simple_heat():
    """示例1: 基本热传导方程 - 正弦初始条件"""
    print("=" * 60)
    print("示例1: 基本热传导方程求解")
    print("=" * 60)

    solver = HeatEquationSolver(UnitSquareMesh(32, 32), alpha=0.1)

    u0 = Expression("sin(pi*x[0])*sin(pi*x[1])", degree=2)
    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)

    solver.set_boundary_conditions([bc])
    solver.set_initial_condition(u0)
    solver.set_time_parameters(T=0.5, num_steps=50)

    solutions, times = solver.solve()
    print(f"求解完成! 共 {len(solutions)} 个时间步")

    u_final = solver.get_final_solution()
    print(f"最终时刻解的最大值: {u_final.vector().max():.6f}")

    fig, ax = plot_solution(u_final, title="热传导方程 - 最终时刻 (t=0.5)", cmap="jet")
    plt.savefig("heat_example1_final.png", dpi=150)
    print("最终时刻图像已保存到 heat_example1_final.png")
    plt.close()

    print("\n正在生成动画...")
    animate_heat_equation(solver, title="热传导演化", save_path="heat_animation.gif", fps=10)
    print("动画已保存到 heat_animation.gif")

    return solver


def example2_initial_conditions():
    """示例2: 不同的初始条件 - 高斯脉冲"""
    print("\n" + "=" * 60)
    print("示例2: 高斯脉冲初始条件")
    print("=" * 60)

    solver = HeatEquationSolver(UnitSquareMesh(40, 40), alpha=0.05)

    u0 = Expression("exp(-100*((x[0]-0.5)*(x[0]-0.5) + (x[1]-0.5)*(x[1]-0.5)))", degree=4)
    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)

    solver.set_boundary_conditions([bc])
    solver.set_initial_condition(u0)
    solver.set_time_parameters(T=1.0, num_steps=100)

    solutions, times = solver.solve()
    print(f"求解完成! 共 {len(solutions)} 个时间步")

    u_mid = solver.get_solution_at_time(0.25)
    u_final = solver.get_final_solution()

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    plot_solution(solutions[0], title="初始时刻 (t=0)", ax=axes[0], cmap="jet")
    plot_solution(u_mid, title="中间时刻 (t=0.25)", ax=axes[1], cmap="jet")
    plot_solution(u_final, title="最终时刻 (t=1.0)", ax=axes[2], cmap="jet")

    plt.tight_layout()
    plt.savefig("heat_example2_evolution.png", dpi=150)
    print("演化图像已保存到 heat_example2_evolution.png")
    plt.close()

    return solver


def example3_with_source():
    """示例3: 带源项的热传导方程"""
    print("\n" + "=" * 60)
    print("示例3: 带源项的热传导方程")
    print("=" * 60)

    solver = HeatEquationSolver(UnitSquareMesh(32, 32), alpha=0.1)

    u0 = Constant(0.0)
    f = Constant(1.0)
    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)

    solver.set_boundary_conditions([bc])
    solver.set_initial_condition(u0)
    solver.set_source_term(f)
    solver.set_time_parameters(T=1.0, num_steps=100)

    solutions, times = solver.solve()
    print(f"求解完成! 共 {len(solutions)} 个时间步")

    u_final = solver.get_final_solution()
    print(f"最终时刻解的最大值: {u_final.vector().max():.6f}")

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    time_indices = [0, 5, 10, 20, 50, -1]

    for idx, ti in enumerate(time_indices):
        row = idx // 3
        col = idx % 3
        title = f"t = {times[ti]:.3f}"
        plot_solution(solutions[ti], title=title, ax=axes[row, col], cmap="hot")

    plt.tight_layout()
    plt.savefig("heat_example3_source.png", dpi=150)
    print("图像已保存到 heat_example3_source.png")
    plt.close()

    return solver


def example4_nonuniform_boundary():
    """示例4: 非均匀边界条件"""
    print("\n" + "=" * 60)
    print("示例4: 非均匀边界条件")
    print("=" * 60)

    from fenics_solver.boundary_conditions import create_unit_square_boundary_markers

    mesh = UnitSquareMesh(40, 40)
    solver = HeatEquationSolver(mesh, alpha=0.05)

    markers = create_unit_square_boundary_markers()

    bc_left = BoundaryCondition.create_dirichlet(Constant(1.0), markers["left"])
    bc_right = BoundaryCondition.create_dirichlet(Constant(0.0), markers["right"])
    bc_bottom = BoundaryCondition.create_dirichlet(Constant(0.0), markers["bottom"])
    bc_top = BoundaryCondition.create_dirichlet(Constant(0.0), markers["top"])

    u0 = Constant(0.0)

    solver.set_boundary_conditions([bc_left, bc_right, bc_bottom, bc_top])
    solver.set_initial_condition(u0)
    solver.set_time_parameters(T=2.0, num_steps=100)

    solutions, times = solver.solve()
    print(f"求解完成! 共 {len(solutions)} 个时间步")

    u_final = solver.get_final_solution()
    print(f"最终时刻解的最大值: {u_final.vector().max():.6f}")

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    time_indices = [0, 5, 10, 25, 50, -1]

    for idx, ti in enumerate(time_indices):
        row = idx // 3
        col = idx % 3
        title = f"t = {times[ti]:.3f}"
        plot_solution(solutions[ti], title=title, ax=axes[row, col], cmap="coolwarm")

    plt.tight_layout()
    plt.savefig("heat_example4_boundary.png", dpi=150)
    print("图像已保存到 heat_example4_boundary.png")
    plt.close()

    return solver


def main():
    print("\n热传导方程求解示例程序\n")

    solver1 = example1_simple_heat()
    solver2 = example2_initial_conditions()
    solver3 = example3_with_source()
    solver4 = example4_nonuniform_boundary()

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
    print("\n生成的文件:")
    print("  - heat_example1_final.png")
    print("  - heat_animation.gif")
    print("  - heat_example2_evolution.png")
    print("  - heat_example3_source.png")
    print("  - heat_example4_boundary.png")


if __name__ == "__main__":
    main()
