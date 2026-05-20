from dolfin import *
import numpy as np


class ErrorEstimator:
    """后验误差估计器"""
    
    @staticmethod
    def residual_based_error(u, f, mesh=None):
        """
        基于残差的后验误差估计
        
        参数:
            u: 有限元解
            f: 源项
            mesh: 网格（可选）
            
        返回:
            cell_markers: 单元误差标记
            eta_h: 每个单元的误差指示子
        """
        if mesh is None:
            mesh = u.function_space().mesh()
        
        V = u.function_space()
        degree = V.ufl_element().degree()
        
        DG = FunctionSpace(mesh, "DG", degree)
        eta_h = Function(DG)
        
        v = TestFunction(DG)
        h = CellDiameter(mesh)
        
        residual = inner(f + div(grad(u)), v) * dx
        assemble(residual, tensor=eta_h.vector())
        
        cell_volumes = np.array([cell.volume() for cell in cells(mesh)])
        eta_values = eta_h.vector().get_local()
        eta_values = np.abs(eta_values) * cell_volumes
        eta_h.vector()[:] = eta_values
        
        return eta_h
    
    @staticmethod
    def gradient_jump_error(u, mesh=None):
        """
        基于梯度跳跃的误差估计（适用于边值问题）
        
        参数:
            u: 有限元解
            mesh: 网格（可选）
            
        返回:
            eta_h: 每个单元的误差指示子
        """
        if mesh is None:
            mesh = u.function_space().mesh()
        
        V = FunctionSpace(mesh, "DG", 0)
        eta_h = Function(V)
        
        n = FacetNormal(mesh)
        h = CellDiameter(mesh)
        
        eta_form = h('+') * inner(jump(grad(u), n), jump(grad(u), n)) * dS
        eta = assemble(eta_form)
        
        eta_array = np.zeros(mesh.num_cells())
        for i, cell in enumerate(cells(mesh)):
            for facet in facets(cell):
                if facet.exterior():
                    continue
                eta_array[i] += eta
        eta_h.vector()[:] = eta_array
        
        return eta_h
    
    @staticmethod
    def zienkiewicz_zhu_error(u, mesh=None):
        """
        Zienkiewicz-Zhu误差估计器（超收敛分片恢复）
        
        参数:
            u: 有限元解
            mesh: 网格（可选）
            
        返回:
            eta_h: 每个单元的误差指示子
        """
        if mesh is None:
            mesh = u.function_space().mesh()
        
        V = u.function_space()
        degree = V.ufl_element().degree()
        
        grad_u = project(grad(u), VectorFunctionSpace(mesh, "CG", degree))
        
        V_ZZ = VectorFunctionSpace(mesh, "CG", degree + 1)
        grad_u_smooth = project(grad_u, V_ZZ)
        
        DG0 = FunctionSpace(mesh, "DG", 0)
        eta_h = Function(DG0)
        
        error = grad_u_smooth - grad(u)
        eta_form = inner(error, error) * dx
        eta = assemble(eta_form)
        
        return eta_h


class MeshAdapter:
    """网格自适应细化器"""
    
    def __init__(self, base_mesh, refine_fraction=0.3, coarsen_fraction=0.0,
                 max_refinement_level=5, min_cell_size=1e-4):
        """
        初始化网格适配器
        
        参数:
            base_mesh: 初始网格
            refine_fraction: 需要细化的单元比例
            coarsen_fraction: 需要粗化的单元比例
            max_refinement_level: 最大细化层数
            min_cell_size: 最小单元尺寸
        """
        self.base_mesh = base_mesh
        self.refine_fraction = refine_fraction
        self.coarsen_fraction = coarsen_fraction
        self.max_refinement_level = max_refinement_level
        self.min_cell_size = min_cell_size
        self.refinement_levels = MeshFunction("size_t", base_mesh, base_mesh.topology().dim(), 0)
        self.current_mesh = base_mesh
    
    def mark_cells_for_refinement(self, eta_h, method="gradient"):
        """
        标记需要细化的单元
        
        参数:
            eta_h: 误差指示子函数
            method: 标记方法 ('gradient', 'fixed_fraction', 'threshold')
        
        返回:
            cell_markers: 单元标记函数（1表示需要细化）
        """
        mesh = self.current_mesh
        dim = mesh.topology().dim()
        cell_markers = MeshFunction("bool", mesh, dim, False)
        
        eta_values = eta_h.vector().get_local()
        
        if method == "fixed_fraction":
            num_cells = len(eta_values)
            num_refine = int(num_cells * self.refine_fraction)
            
            sorted_indices = np.argsort(eta_values)[::-1]
            refine_indices = sorted_indices[:num_refine]
            
            for idx in refine_indices:
                cell_markers[idx] = True
        
        elif method == "gradient":
            eta_mean = np.mean(eta_values)
            eta_std = np.std(eta_values)
            threshold = eta_mean + 0.5 * eta_std
            
            for i, eta in enumerate(eta_values):
                if eta > threshold:
                    cell_markers[i] = True
        
        elif method == "threshold":
            threshold = np.percentile(eta_values, 100 * (1 - self.refine_fraction))
            
            for i, eta in enumerate(eta_values):
                if eta > threshold:
                    cell_markers[i] = True
        
        else:
            raise ValueError(f"未知的标记方法: {method}")
        
        for i in range(len(eta_values)):
            cell = Cell(mesh, i)
            if cell.h() < self.min_cell_size or self.refinement_levels[i] >= self.max_refinement_level:
                cell_markers[i] = False
        
        return cell_markers
    
    def adapt_mesh(self, cell_markers):
        """
        根据标记细化网格
        
        参数:
            cell_markers: 单元标记函数
            
        返回:
            refined_mesh: 细化后的网格
        """
        refined_mesh = refine(self.current_mesh, cell_markers)
        
        old_num_cells = self.current_mesh.num_cells()
        new_num_cells = refined_mesh.num_cells()
        print(f"网格细化: {old_num_cells} -> {new_num_cells} 单元")
        
        new_refinement_levels = MeshFunction("size_t", refined_mesh, refined_mesh.topology().dim(), 0)
        
        parent_cells = refined_mesh.data().array('parent_cell', refined_mesh.topology().dim())
        
        for i in range(new_num_cells):
            parent_idx = parent_cells[i]
            if parent_idx < old_num_cells:
                new_refinement_levels[i] = self.refinement_levels[parent_idx] + 1 if cell_markers[parent_idx] else self.refinement_levels[parent_idx]
        
        self.current_mesh = refined_mesh
        self.refinement_levels = new_refinement_levels
        
        return refined_mesh
    
    def get_current_mesh(self):
        """获取当前网格"""
        return self.current_mesh


def adaptive_solve(problem_class, initial_mesh, max_iterations=5, 
                   tolerance=1e-3, **problem_kwargs):
    """
    自适应求解循环
    
    参数:
        problem_class: 问题类（必须有 solve 和 get_solution 方法）
        initial_mesh: 初始网格
        max_iterations: 最大自适应迭代次数
        tolerance: 误差容限
        **problem_kwargs: 传递给问题类的参数
    
    返回:
        solution: 最终解
        mesh_adapter: 网格适配器对象
        error_history: 误差历史
    """
    mesh_adapter = MeshAdapter(initial_mesh)
    error_history = []
    
    current_mesh = initial_mesh
    
    for iteration in range(max_iterations):
        print(f"\n自适应迭代 {iteration + 1}/{max_iterations}")
        print(f"当前网格: {current_mesh.num_cells()} 单元")
        
        problem = problem_class(current_mesh, **problem_kwargs)
        u = problem.solve()
        
        eta_h = ErrorEstimator.residual_based_error(u, problem.f, current_mesh)
        total_error = np.sum(eta_h.vector().get_local())
        error_history.append(total_error)
        
        print(f"估计误差: {total_error:.6e}")
        
        if total_error < tolerance or iteration == max_iterations - 1:
            print("达到收敛容限或最大迭代次数")
            break
        
        cell_markers = mesh_adapter.mark_cells_for_refinement(eta_h, method="fixed_fraction")
        current_mesh = mesh_adapter.adapt_mesh(cell_markers)
    
    return problem.get_solution(), mesh_adapter, error_history


class PoissonProblem:
    """用于自适应求解的泊松问题包装类"""
    
    def __init__(self, mesh, f=None, bcs=None):
        self.mesh = mesh
        self.V = FunctionSpace(mesh, "CG", 1)
        self.u = Function(self.V)
        self.f = f if f is not None else Constant(1.0)
        self.bcs = bcs if bcs is not None else []
        
        self.ubcs = []
        for bc in self.bcs:
            if hasattr(bc, 'apply_dirichlet'):
                dirichlet_bc = bc.apply_dirichlet(self.V)
                if dirichlet_bc is not None:
                    self.ubcs.append(dirichlet_bc)
    
    def solve(self):
        u = TrialFunction(self.V)
        v = TestFunction(self.V)
        
        a = inner(grad(u), grad(v)) * dx
        L = self.f * v * dx
        
        solve(a == L, self.u, self.ubcs)
        return self.u
    
    def get_solution(self):
        return self.u
