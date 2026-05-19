#!/usr/bin/env python3
"""
泊松方程求解示例

本示例演示如何使用fenics_solver库求解泊松方程
"""

from dolfin import *
from fenics_solver import PoissonSolver, BoundaryCondition, plot_solution
from fenics_solver.boundary_conditions import create_unit_square_boundary_markers
import matplotlib.pyplot as plt


def example1_simple_poisson():
    """示例1: 简单的泊松方程 - 均布源项，齐次边界"""
    print("=" * 60)
    print("示例1: 简单的泊松方程求解")
    print("=" * 60)

    solver = PoissonSolver(UnitSquareMesh(32, 32))

    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)
    solver.set_boundary_conditions([bc])
    solver.set_source_term(Constant(1.0))

    u = solver.solve()
    print(f"求解完成!")
    print(f"解的最大值: {u.vector().max():.6f}")
    print(f"解的最小值: {u.vector().min():.6f}")

    fig, ax = plot_solution(u, title="泊松方程解 - 简单示例", show_mesh=True)
    plt.savefig("poisson_example1.png", dpi=150)
    print("图像已保存到 poisson_example1.png")
    plt.close()

    return solver


def example2_manufactured_solution():
    """示例2: 使用精确解验证 - 制造解方法"""
    print("\n" + "=" * 60)
    print("示例2: 制造解方法验证")
    print("=" * 60)

    u_exact = Expression("sin(pi*x[0])*sin(pi*x[1])", degree=4)
    f = Expression("2*pi*pi*sin(pi*x[0])*sin(pi*x[1])", degree=4)

    solver = PoissonSolver(UnitSquareMesh(64, 64))

    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)
    solver.set_boundary_conditions([bc])
    solver.set_source_term(f)

    u = solver.solve()

    l2_error = solver.get_error(u_exact, norm_type="L2")
    h1_error = solver.get_error(u_exact, norm_type="H1")

    print(f"L2误差: {l2_error:.6e}")
    print(f"H1误差: {h1_error:.6e}")

    fig, ax = plot_solution(u, title="泊松方程解 - 制造解验证")
    plt.savefig("poisson_example2.png", dpi=150)
    print("图像已保存到 poisson_example2.png")
    plt.close()

    return solver


def example3_complex_boundary_conditions():
    """示例3: 复杂的边界条件 - 不同边界不同值"""
    print("\n" + "=" * 60)
    print("示例3: 复杂边界条件")
    print("=" * 60)

    mesh = UnitSquareMesh(40, 40)
    solver = PoissonSolver(mesh)

    markers = create_unit_square_boundary_markers()

    bc_left = BoundaryCondition.create_dirichlet(Constant(0.0), markers["left"])
    bc_right = BoundaryCondition.create_dirichlet(Constant(1.0), markers["right"])
    bc_bottom = BoundaryCondition.create_dirichlet(Constant(0.0), markers["bottom"])
    bc_top = BoundaryCondition.create_dirichlet(Constant(0.0), markers["top"])

    solver.set_boundary_conditions([bc_left, bc_right, bc_bottom, bc_top])
    solver.set_source_term(Constant(0.0))

    u = solver.solve()

    print(f"求解完成!")
    print(f"解的最大值: {u.vector().max():.6f}")

    fig, ax = plot_solution(u, title="泊松方程解 - 复杂边界条件", cmap="coolwarm")
    plt.savefig("poisson_example3.png", dpi=150)
    print("图像已保存到 poisson_example3.png")
    plt.close()

    return solver


def example4_variable_source_term():
    """示例4: 变化的源项"""
    print("\n" + "=" * 60)
    print("示例4: 变化的源项")
    print("=" * 60)

    mesh = UnitSquareMesh(50, 50)
    solver = PoissonSolver(mesh)

    f = Expression("100*exp(-100*((x[0]-0.5)*(x[0]-0.5) + (x[1]-0.5)*(x[1]-0.5)))", degree=4)

    bc = BoundaryCondition.create_dirichlet(Constant(0.0), None)
    solver.set_boundary_conditions([bc])
    solver.set_source_term(f)

    u = solver.solve()

    print(f"求解完成!")
    print(f"解的最大值: {u.vector().max():.6f}")

    fig, ax = plot_solution(u, title="泊松方程解 - 高斯源项", cmap="inferno")
    plt.savefig("poisson_example4.png", dpi=150)
    print("图像已保存到 poisson_example4.png")
    plt.close()

    return solver


def main():
    print("\n泊松方程求解示例程序\n")

    solver1 = example1_simple_poisson()
    solver2 = example2_manufactured_solution()
    solver3 = example3_complex_boundary_conditions()
    solver4 = example4_variable_source_term()

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
    print("\n生成的文件:")
    print("  - poisson_example1.png")
    print("  - poisson_example2.png")
    print("  - poisson_example3.png")
    print("  - poisson_example4.png")


if __name__ == "__main__":
    main()
