from dolfin import *
import numpy as np
from .boundary_conditions import BoundaryCondition
from .material_properties import ThermalMaterial


class PoissonSolver:
    """泊松方程有限元求解器 - 增强版

    求解方程: -∇·(k∇u) = f(x) 在区域Ω内
    边界条件: u = g_D (Dirichlet) 或 k∂u/∂n = g_N (Neumann)

    增强功能:
    - 非均匀材料属性支持
    - 更好的边界条件处理
    """

    def __init__(self, mesh=None, degree=1, k=1.0, material=None):
        """
        初始化泊松方程求解器

        参数:
            mesh: 计算网格，如果为None则创建默认单位正方形网格
            degree: 有限元函数空间的阶数
            k: 扩散系数（均质材料）
            material: ThermalMaterial对象，用于非均匀材料
        """
        self.mesh = mesh if mesh is not None else UnitSquareMesh(32, 32)
        self.degree = degree
        self.V = FunctionSpace(self.mesh, "P", degree)
        self.u = Function(self.V)
        self.bcs = []
        self.f = None
        self.solution = None
        
        if material is not None:
            self.material = material
            self.material.interpolate_to_space(self.V)
            self.use_material = True
        else:
            self.k = Constant(k)
            self.use_material = False

    def set_mesh(self, mesh):
        """设置计算网格"""
        self.mesh = mesh
        self.V = FunctionSpace(self.mesh, "P", self.degree)
        self.u = Function(self.V)
        self.bcs = []
        
        if self.use_material:
            self.material.interpolate_to_space(self.V)

    def set_material(self, material):
        """设置材料属性"""
        self.material = material
        self.material.interpolate_to_space(self.V)
        self.use_material = True

    def set_diffusion_coefficient(self, k):
        """设置扩散系数（均质材料）"""
        self.k = Constant(k)
        self.use_material = False

    def set_boundary_conditions(self, boundary_conditions):
        """
        设置边界条件

        参数:
            boundary_conditions: BoundaryCondition对象列表
        """
        self.bcs = []
        for bc in boundary_conditions:
            if bc.bc_type == BoundaryCondition.DIRICHLET:
                dirichlet_bc = bc.apply_dirichlet(self.V)
                if dirichlet_bc is not None:
                    self.bcs.append(dirichlet_bc)

    def set_source_term(self, f):
        """
        设置源项f(x)

        参数:
            f: 源项，可以是Expression、Constant或Function
        """
        self.f = f

    def solve(self, solver_type="lu"):
        """
        求解泊松方程

        参数:
            solver_type: 求解器类型 ('lu', 'gmres', 'cg')

        返回:
            解函数u
        """
        if self.f is None:
            self.f = Constant(0.0)

        u = TrialFunction(self.V)
        v = TestFunction(self.V)

        if self.use_material:
            k = self.material.k_func
        else:
            k = self.k

        a = k * inner(grad(u), grad(v)) * dx
        L = self.f * v * dx

        solve(a == L, self.u, self.bcs, solver_parameters={"linear_solver": solver_type})
        self.solution = self.u
        return self.u

    def get_solution(self):
        """获取解"""
        return self.solution

    def get_error(self, u_exact, norm_type="L2"):
        """
        计算与精确解的误差

        参数:
            u_exact: 精确解
            norm_type: 误差范数类型 ('L2', 'H1')

        返回:
            误差值
        """
        if self.solution is None:
            raise ValueError("请先求解方程")

        error = (self.solution - u_exact) ** 2 * dx
        if norm_type == "L2":
            return sqrt(abs(assemble(error)))
        elif norm_type == "H1":
            error_H1 = error + inner(grad(self.solution - u_exact), grad(self.solution - u_exact)) * dx
            return sqrt(abs(assemble(error_H1)))
        else:
            raise ValueError(f"不支持的范数类型: {norm_type}")

    def save_solution(self, filename, file_format="pvd"):
        """
        保存解到文件

        参数:
            filename: 文件名
            file_format: 文件格式 ('vtk', 'pvd', 'hdf5')
        """
        if self.solution is None:
            raise ValueError("请先求解方程")

        if file_format in ["vtk", "pvd"]:
            file = File(f"{filename}.pvd")
            file << self.solution
        elif file_format == "hdf5":
            file = HDF5File(self.mesh.mpi_comm(), f"{filename}.h5", "w")
            file.write(self.solution, "u")
            file.close()
        else:
            raise ValueError(f"不支持的文件格式: {file_format}")


def solve_poisson_simple(nx=32, ny=32, f=Constant(1.0), bc_value=Constant(0.0), k=1.0):
    """
    简化的泊松方程求解函数

    参数:
        nx, ny: x和y方向的网格数
        f: 源项
        bc_value: 边界值
        k: 扩散系数

    返回:
        PoissonSolver对象
    """
    solver = PoissonSolver(UnitSquareMesh(nx, ny), k=k)

    bc = BoundaryCondition.create_dirichlet(bc_value, None)
    solver.set_boundary_conditions([bc])
    solver.set_source_term(f)
    solver.solve()

    return solver
