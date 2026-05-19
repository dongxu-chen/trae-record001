from dolfin import *
import numpy as np
from .boundary_conditions import BoundaryCondition
from .material_properties import ThermalMaterial


class HeatEquationSolver:
    """热传导方程有限元求解器 - 增强版

    求解方程: ρc ∂u/∂t - ∇·(k∇u) = f(x, t) 在区域Ω内
    边界条件: u = g_D (Dirichlet) 或 k∂u/∂n = g_N (Neumann)
    初始条件: u(x, 0) = u0(x)

    增强功能:
    - 非均匀材料属性支持
    - 基于CFL条件的自适应时间步长
    - 多种时间离散格式
    """

    def __init__(self, mesh=None, degree=1, alpha=1.0, material=None):
        """
        初始化热传导方程求解器

        参数:
            mesh: 计算网格，如果为None则创建默认单位正方形网格
            degree: 有限元函数空间的阶数
            alpha: 热扩散系数（均质材料时使用）
            material: ThermalMaterial对象，用于非均匀材料
        """
        self.mesh = mesh if mesh is not None else UnitSquareMesh(32, 32)
        self.degree = degree
        self.V = FunctionSpace(self.mesh, "P", degree)
        self.u_n = Function(self.V)
        self.u = Function(self.V)
        self.bcs = []
        self.f = None
        self.dt = None
        self.T = None
        self.time = 0.0
        self.solutions = []
        self.times = []
        self.time_step_history = []
        self.residual_history = []
        
        if material is not None:
            self.material = material
            self.material.interpolate_to_space(self.V)
            self.use_material = True
        else:
            self.alpha = Constant(alpha)
            self.k = Constant(alpha)
            self.rho_c = Constant(1.0)
            self.use_material = False
        
        self.adaptive_time = False
        self.cfl_number = 0.5
        self.max_dt = None
        self.min_dt = None

    def set_mesh(self, mesh):
        """设置计算网格"""
        self.mesh = mesh
        self.V = FunctionSpace(self.mesh, "P", self.degree)
        self.u_n = Function(self.V)
        self.u = Function(self.V)
        self.bcs = []
        
        if self.use_material:
            self.material.interpolate_to_space(self.V)

    def set_material(self, material):
        """设置热材料属性"""
        self.material = material
        self.material.interpolate_to_space(self.V)
        self.use_material = True

    def set_diffusion_coefficient(self, alpha):
        """设置热扩散系数（均质材料）"""
        self.alpha = Constant(alpha)
        self.k = Constant(alpha)
        self.rho_c = Constant(1.0)
        self.use_material = False

    def enable_adaptive_time_stepping(self, cfl_number=0.5, max_dt=None, min_dt=None):
        """
        启用自适应时间步长

        参数:
            cfl_number: CFL数（通常0.2-0.8）
            max_dt: 最大时间步长
            min_dt: 最小时间步长
        """
        self.adaptive_time = True
        self.cfl_number = cfl_number
        self.max_dt = max_dt
        self.min_dt = min_dt

    def _compute_max_diffusivity(self):
        """计算最大扩散系数，用于CFL估计"""
        if self.use_material:
            k_values = self.material.k_func.vector().get_local()
            rho_c_values = self.material.rho_func.vector().get_local() * \
                           self.material.c_func.vector().get_local()
            diffusivity = k_values / np.maximum(rho_c_values, 1e-10)
            return np.max(diffusivity)
        else:
            return float(self.alpha)

    def _compute_cfl_dt(self):
        """基于CFL条件计算时间步长"""
        h_min = self.mesh.hmin()
        alpha_max = self._compute_max_diffusivity()
        
        dt_cfl = self.cfl_number * h_min**2 / (2 * alpha_max)
        
        if self.max_dt is not None:
            dt_cfl = min(dt_cfl, self.max_dt)
        if self.min_dt is not None:
            dt_cfl = max(dt_cfl, self.min_dt)
        
        return dt_cfl

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

    def set_initial_condition(self, u0):
        """
        设置初始条件

        参数:
            u0: 初始温度分布
        """
        self.u_n.interpolate(u0)
        self.solutions = [self.u_n.copy(deepcopy=True)]
        self.times = [0.0]
        self.time_step_history = []
        self.residual_history = []

    def set_source_term(self, f):
        """
        设置源项f(x, t)

        参数:
            f: 源项，可以是Expression、Constant或Function
        """
        self.f = f

    def set_time_parameters(self, T, num_steps):
        """
        设置时间参数（固定时间步长）

        参数:
            T: 总时间
            num_steps: 时间步数
        """
        self.T = T
        self.dt = Constant(T / num_steps)
        self.adaptive_time = False

    def set_time_adaptive(self, T, initial_dt=None):
        """
        设置自适应时间步长参数

        参数:
            T: 总时间
            initial_dt: 初始时间步长（如果为None，由CFL计算）
        """
        self.T = T
        if initial_dt is None:
            self.dt = Constant(self._compute_cfl_dt())
        else:
            self.dt = Constant(initial_dt)
        self.adaptive_time = True

    def _assemble_residual(self, u):
        """计算残差用于自适应时间步长调整"""
        v = TestFunction(self.V)
        dt = float(self.dt)
        
        if self.use_material:
            k = self.material.k_func
            rho_c = self.material.rho_func * self.material.c_func
        else:
            k = self.k
            rho_c = self.rho_c
        
        if self.f is None:
            f = Constant(0.0)
        else:
            f = self.f
        
        residual = rho_c * (u - self.u_n) / dt * v * dx + k * inner(grad(u), grad(v)) * dx - f * v * dx
        return assemble(residual)

    def solve(self, solver_type="lu", time_scheme="theta", theta=0.5):
        """
        求解热传导方程

        参数:
            solver_type: 求解器类型 ('lu', 'gmres', 'cg')
            time_scheme: 时间离散格式 ('theta', 'euler', 'crank_nicolson')
            theta: theta方法的theta值（0=向前欧拉，0.5=Crank-Nicolson，1=向后欧拉）

        返回:
            时间步的解列表和时间列表
        """
        if self.f is None:
            self.f = Constant(0.0)
        if self.dt is None:
            self.set_time_parameters(1.0, 10)

        u = TrialFunction(self.V)
        v = TestFunction(self.V)

        if time_scheme == "euler":
            theta = 1.0
        elif time_scheme == "crank_nicolson":
            theta = 0.5

        if self.use_material:
            k = self.material.k_func
            rho_c = self.material.rho_func * self.material.c_func
        else:
            k = self.k
            rho_c = self.rho_c

        self.time = 0.0
        step = 0
        
        while self.time < self.T - 1e-10:
            if self.adaptive_time:
                new_dt = self._compute_cfl_dt()
                self.dt = Constant(new_dt)
            else:
                new_dt = float(self.dt)
            
            if self.time + new_dt > self.T:
                new_dt = self.T - self.time
                self.dt = Constant(new_dt)
            
            F = rho_c * u * v * dx + self.dt * k * theta * inner(grad(u), grad(v)) * dx - \
                (rho_c * self.u_n * v * dx - self.dt * k * (1 - theta) * inner(grad(self.u_n), grad(v)) * dx + \
                 self.dt * self.f * v * dx)
            
            a, L = lhs(F), rhs(F)

            solve(a == L, self.u, self.bcs, solver_parameters={"linear_solver": solver_type})
            
            residual = self._assemble_residual(self.u)
            residual_norm = np.linalg.norm(residual.get_local())
            self.residual_history.append(residual_norm)
            
            self.u_n.assign(self.u)
            self.time = self.time + new_dt
            step += 1
            
            self.solutions.append(self.u.copy(deepcopy=True))
            self.times.append(self.time)
            self.time_step_history.append(new_dt)
            
            if step % 10 == 0:
                print(f"时间步 {step}, t = {self.time:.4f}, dt = {new_dt:.6f}, 残差 = {residual_norm:.2e}")

        print(f"求解完成，共 {step} 个时间步")
        return self.solutions, self.times

    def get_solutions(self):
        """获取所有时间步的解"""
        return self.solutions, self.times

    def get_final_solution(self):
        """获取最终时刻的解"""
        if self.solutions:
            return self.solutions[-1]
        return None

    def get_solution_at_time(self, t):
        """获取指定时间的解（线性插值）"""
        if not self.times or t < self.times[0] or t > self.times[-1]:
            return None

        for i in range(len(self.times) - 1):
            if self.times[i] <= t <= self.times[i + 1]:
                alpha = (t - self.times[i]) / (self.times[i + 1] - self.times[i])
                u_interp = Function(self.V)
                u_interp.vector()[:] = (1 - alpha) * self.solutions[i].vector()[:] + alpha * self.solutions[i + 1].vector()[:]
                return u_interp

        return self.solutions[-1]

    def get_time_step_history(self):
        """获取时间步长历史"""
        return self.time_step_history, self.times

    def save_solutions(self, filename):
        """
        保存所有时间步的解到PVD文件

        参数:
            filename: 文件名
        """
        if not self.solutions:
            raise ValueError("请先求解方程")

        file = File(f"{filename}.pvd")
        for u, t in zip(self.solutions, self.times):
            file << (u, t)


def solve_heat_simple(nx=32, ny=32, alpha=1.0, T=1.0, num_steps=50, u0=None, bc_value=Constant(0.0)):
    """
    简化的热传导方程求解函数

    参数:
        nx, ny: x和y方向的网格数
        alpha: 热扩散系数
        T: 总时间
        num_steps: 时间步数
        u0: 初始条件
        bc_value: 边界值

    返回:
        HeatEquationSolver对象
    """
    solver = HeatEquationSolver(UnitSquareMesh(nx, ny), alpha=alpha)

    if u0 is None:
        u0 = Expression("sin(pi*x[0])*sin(pi*x[1])", degree=2)

    bc = BoundaryCondition.create_dirichlet(bc_value, None)
    solver.set_boundary_conditions([bc])
    solver.set_initial_condition(u0)
    solver.set_time_parameters(T, num_steps)
    solver.solve()

    return solver


def solve_heat_adaptive(nx=32, ny=32, alpha=1.0, T=1.0, cfl_number=0.5, u0=None, bc_value=Constant(0.0)):
    """
    自适应时间步长的热传导方程求解函数

    参数:
        nx, ny: x和y方向的网格数
        alpha: 热扩散系数
        T: 总时间
        cfl_number: CFL数
        u0: 初始条件
        bc_value: 边界值

    返回:
        HeatEquationSolver对象
    """
    solver = HeatEquationSolver(UnitSquareMesh(nx, ny), alpha=alpha)
    solver.enable_adaptive_time_stepping(cfl_number=cfl_number)

    if u0 is None:
        u0 = Expression("sin(pi*x[0])*sin(pi*x[1])", degree=2)

    bc = BoundaryCondition.create_dirichlet(bc_value, None)
    solver.set_boundary_conditions([bc])
    solver.set_initial_condition(u0)
    solver.set_time_adaptive(T)
    solver.solve()

    return solver
