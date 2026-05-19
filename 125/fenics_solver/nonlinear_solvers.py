from dolfin import *
import numpy as np
import sys


class ConvergenceHistory:
    """收敛历史记录器"""
    
    def __init__(self):
        self.iterations = []
        self.residuals = []
        self.increments = []
        self.timesteps = []
    
    def add_iteration(self, iter_num, residual, increment=None):
        """添加一次迭代记录"""
        self.iterations.append(iter_num)
        self.residuals.append(residual)
        if increment is not None:
            self.increments.append(increment)
    
    def add_timestep(self, time, num_iters):
        """添加时间步记录"""
        self.timesteps.append((time, num_iters))
    
    def clear(self):
        """清空历史"""
        self.iterations = []
        self.residuals = []
        self.increments = []
        self.timesteps = []
    
    def get_data(self):
        """获取数据"""
        return {
            'iterations': self.iterations,
            'residuals': self.residuals,
            'increments': self.increments,
            'timesteps': self.timesteps
        }


class NewtonRaphsonSolver:
    """Newton-Raphson迭代求解器
    
    求解非线性方程组 R(u) = 0
    使用切线刚度矩阵进行迭代
    """
    
    def __init__(self, V, bcs=None):
        """
        初始化Newton-Raphson求解器
        
        参数:
            V: 有限元函数空间
            bcs: 边界条件列表
        """
        self.V = V
        self.bcs = bcs if bcs is not None else []
        self.history = ConvergenceHistory()
        
        self.max_iterations = 50
        self.rel_tolerance = 1e-6
        self.abs_tolerance = 1e-8
        self.divergence_tol = 1e10
        self.line_search = True
        self.line_search_max_iter = 10
        self.relaxation = 1.0
        
        self.linear_solver = "lu"
        self.preconditioner = "default"
    
    def set_parameters(self, max_iterations=None, rel_tolerance=None,
                       abs_tolerance=None, line_search=None, relaxation=None):
        """设置求解器参数"""
        if max_iterations is not None:
            self.max_iterations = max_iterations
        if rel_tolerance is not None:
            self.rel_tolerance = rel_tolerance
        if abs_tolerance is not None:
            self.abs_tolerance = abs_tolerance
        if line_search is not None:
            self.line_search = line_search
        if relaxation is not None:
            self.relaxation = relaxation
    
    def solve(self, u, residual_form, jacobian_form, bcs=None,
              load_factor=1.0, load_incremental_form=None):
        """
        执行Newton-Raphson迭代求解
        
        参数:
            u: 解函数（初始猜测）
            residual_form: 残差形式 R(u)
            jacobian_form: 雅可比形式 dR/du
            bcs: 边界条件（如为None则使用初始化时的边界条件）
            load_factor: 荷载因子
            load_incremental_form: 增量荷载形式
        
        返回:
            success: 是否收敛
            num_iters: 迭代次数
        """
        if bcs is None:
            bcs = self.bcs
        
        self.history.clear()
        
        du = Function(self.V)
        
        bc_apply = True
        if bcs:
            for bc in bcs:
                bc.apply(u.vector())
        
        R = assemble(residual_form)
        for bc in bcs:
            bc.apply(R)
        residual_0 = R.norm("l2")
        residual = residual_0
        
        print(f"Newton-Raphson: 初始残差 = {residual_0:.2e}")
        
        if residual_0 < self.abs_tolerance:
            print("Newton-Raphson: 初始解已满足收敛准则")
            return True, 0
        
        self.history.add_iteration(0, residual)
        
        for k in range(self.max_iterations):
            J = assemble(jacobian_form)
            for bc in bcs:
                bc.apply(J, R)
            
            try:
                solve(J, du.vector(), R, self.linear_solver)
            except RuntimeError as e:
                print(f"Newton-Raphson: 线性求解失败: {e}")
                return False, k
            
            delta_norm = du.vector().norm("l2")
            
            if self.line_search:
                alpha = self._line_search(u, du, residual_form, R, bcs)
            else:
                alpha = self.relaxation
            
            u.vector().axpy(-alpha, du.vector())
            
            R = assemble(residual_form)
            for bc in bcs:
                bc.apply(R)
            residual = R.norm("l2")
            
            rel_residual = residual / residual_0 if residual_0 > 0 else residual
            
            self.history.add_iteration(k+1, residual, delta_norm)
            
            print(f"Newton-Raphson: 迭代 {k+1}, 残差 = {residual:.2e}, "
                  f"相对残差 = {rel_residual:.2e}, 更新范数 = {delta_norm:.2e}, "
                  f"线搜索 α = {alpha:.3f}")
            
            if residual < self.abs_tolerance or rel_residual < self.rel_tolerance:
                print(f"Newton-Raphson: 收敛! 迭代次数 = {k+1}")
                return True, k+1
            
            if residual > self.divergence_tol:
                print(f"Newton-Raphson: 发散! 残差 = {residual:.2e}")
                return False, k+1
        
        print(f"Newton-Raphson: 达到最大迭代次数仍未收敛")
        return False, self.max_iterations
    
    def _line_search(self, u, du, residual_form, R, bcs):
        """Armijo线搜索"""
        alpha = 1.0
        beta = 0.5
        c = 1e-4
        
        u_old = u.copy(deepcopy=True)
        
        for i in range(self.line_search_max_iter):
            u.vector()[:] = u_old.vector() - alpha * du.vector()
            
            R_new = assemble(residual_form)
            for bc in bcs:
                bc.apply(R_new)
            residual_new = R_new.norm("l2")
            residual_old = R.norm("l2")
            
            if residual_new <= (1 - c * alpha) * residual_old:
                u.vector()[:] = u_old.vector()
                return alpha
            
            alpha *= beta
        
        u.vector()[:] = u_old.vector()
        return alpha


class NonlinearPoissonSolver:
    """非线性泊松方程求解器
    
    求解: -∇·(k(u)∇u) = f
    """
    
    def __init__(self, mesh, degree=1):
        self.mesh = mesh
        self.V = FunctionSpace(mesh, "CG", degree)
        self.u = Function(self.V)
        self.bcs = []
        self.f = None
        self.k = None
        self.solver = NewtonRaphsonSolver(self.V)
        self.history = self.solver.history
    
    def set_boundary_conditions(self, bcs):
        """设置边界条件"""
        self.bcs = []
        for bc in bcs:
            if hasattr(bc, 'apply'):
                self.bcs.append(bc)
            elif hasattr(bc, 'apply_dirichlet'):
                self.bcs.append(bc.apply_dirichlet(self.V))
    
    def set_source(self, f):
        """设置源项"""
        self.f = f
    
    def set_conductivity(self, k):
        """设置非线性传导系数 k(u)"""
        self.k = k
    
    def solve(self, u_guess=None):
        """求解非线性泊松方程"""
        if u_guess is not None:
            self.u.assign(u_guess)
        
        if self.k is None:
            self.k = lambda u: Constant(1.0)
        if self.f is None:
            self.f = Constant(0.0)
        
        v = TestFunction(self.V)
        u_trial = TrialFunction(self.V)
        
        F = self.k(self.u) * inner(grad(self.u), grad(v)) * dx - self.f * v * dx
        
        J = derivative(F, self.u, u_trial)
        
        success, num_iters = self.solver.solve(self.u, F, J, self.bcs)
        
        return success, num_iters, self.u


class NonlinearHeatSolver:
    """非线性热传导方程求解器
    
    求解: ρc(u) ∂u/∂t - ∇·(k(u)∇u) = f
    """
    
    def __init__(self, mesh, degree=1, material=None):
        self.mesh = mesh
        self.V = FunctionSpace(mesh, "CG", degree)
        self.u = Function(self.V)
        self.u_n = Function(self.V)
        self.bcs = []
        self.f = None
        self.material = material
        self.solver = NewtonRaphsonSolver(self.V)
        self.history = self.solver.history
        self.time_history = ConvergenceHistory()
        
        self.theta = 0.5
        self.dt = None
        self.time = 0.0
    
    def set_boundary_conditions(self, bcs):
        """设置边界条件"""
        self.bcs = []
        for bc in bcs:
            if hasattr(bc, 'apply'):
                self.bcs.append(bc)
            elif hasattr(bc, 'apply_dirichlet'):
                self.bcs.append(bc.apply_dirichlet(self.V))
    
    def set_initial_condition(self, u0):
        """设置初始条件"""
        self.u_n.interpolate(u0)
        self.u.assign(self.u_n)
    
    def set_source(self, f):
        """设置源项"""
        self.f = f
    
    def set_time_step(self, dt):
        """设置时间步长"""
        self.dt = dt
    
    def set_time_scheme(self, theta):
        """设置时间离散格式（θ方法）"""
        self.theta = theta
    
    def solve_timestep(self):
        """求解一个时间步"""
        if self.dt is None:
            raise ValueError("时间步长未设置")
        
        if self.material is None:
            k = lambda T: Constant(1.0)
            rho_c = lambda T: Constant(1.0)
        else:
            k = lambda T: self.material.conductivity(T)
            rho_c = lambda T: self.material.rho_c(T)
        
        if self.f is None:
            self.f = Constant(0.0)
        
        v = TestFunction(self.V)
        u_trial = TrialFunction(self.V)
        
        u_mid = (1 - self.theta) * self.u_n + self.theta * self.u
        
        F = (rho_c(self.u) * (self.u - self.u_n) / Constant(self.dt) * v * dx
             + k(u_mid) * inner(grad(u_mid), grad(v)) * dx
             - self.f * v * dx)
        
        J = derivative(F, self.u, u_trial)
        
        success, num_iters = self.solver.solve(self.u, F, J, self.bcs)
        
        self.time_history.add_timestep(self.time, num_iters)
        
        if success:
            self.u_n.assign(self.u)
            self.time += self.dt
        
        return success, num_iters, self.u


class ParallelUtils:
    """MPI并行工具类"""
    
    @staticmethod
    def is_mpi_enabled():
        """检查MPI是否启用"""
        try:
            return MPI.size(MPI.comm_world) > 1
        except:
            return False
    
    @staticmethod
    def get_rank():
        """获取当前进程编号"""
        try:
            return MPI.rank(MPI.comm_world)
        except:
            return 0
    
    @staticmethod
    def get_size():
        """获取总进程数"""
        try:
            return MPI.size(MPI.comm_world)
        except:
            return 1
    
    @staticmethod
    def is_root():
        """是否为主进程（rank 0）"""
        return ParallelUtils.get_rank() == 0
    
    @staticmethod
    def barrier():
        """进程同步"""
        try:
            MPI.barrier(MPI.comm_world)
        except:
            pass
    
    @staticmethod
    def print(*args, **kwargs):
        """仅主进程打印"""
        if ParallelUtils.is_root():
            print(*args, **kwargs)
    
    @staticmethod
    def sum(value):
        """全局求和"""
        try:
            return MPI.sum(MPI.comm_world, value)
        except:
            return value
    
    @staticmethod
    def min(value):
        """全局最小值"""
        try:
            return MPI.min(MPI.comm_world, value)
        except:
            return value
    
    @staticmethod
    def max(value):
        """全局最大值"""
        try:
            return MPI.max(MPI.comm_world, value)
        except:
            return value


def create_parallel_mesh(nx, ny, nz=None):
    """创建并行网格
    
    参数:
        nx, ny, nz: 各方向单元数
    
    返回:
        mesh: 分布式网格
    """
    if nz is None:
        mesh = UnitSquareMesh(nx, ny)
    else:
        mesh = UnitCubeMesh(nx, ny, nz)
    
    rank = ParallelUtils.get_rank()
    size = ParallelUtils.get_size()
    
    if size > 1 and ParallelUtils.is_root():
        print(f"并行模式: {size} 个进程")
        print(f"  进程 {rank}: 本地单元数 = {mesh.num_cells()}, "
              f"本地顶点数 = {mesh.num_vertices()}")
    
    return mesh


def assemble_parallel(form, mesh=None):
    """并行组装
    
    这是FEniCS内置的并行组装的包装器
    """
    return assemble(form)


def solve_parallel(A, x, b, solver_type="mumps"):
    """并行线性求解
    
    支持的求解器:
    - mumps: MUMPS直接求解器（推荐用于并行）
    - superlu_dist: SuperLU_DIST
    - hypre_amg: HYPRE代数多重网格
    - petsc: PETSc求解器
    """
    if ParallelUtils.get_size() > 1:
        solver = PETScLUSolver(solver_type)
        solver.solve(A, x, b)
    else:
        solve(A, x, b, solver_type)
