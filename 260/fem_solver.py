import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from matplotlib.animation import FuncAnimation
from scipy.sparse import csr_matrix, lil_matrix, diags
from scipy.sparse.linalg import cg, spsolve, LinearOperator
import meshpy.triangle as triangle
import time
from itertools import product
import pickle


def generate_mesh(points, facets, holes=None, max_area=0.1, refinement_func=None):
    """
    生成三角形网格，支持自适应加密
    
    参数:
        points: 边界点列表 [(x1,y1), (x2,y2), ...]
        facets: 边界边列表 [(i1,j1), (i2,j2), ...]
        holes: 孔洞点列表 [(x,y), ...]
        max_area: 最大三角形面积
        refinement_func: 自适应加密函数，输入(x,y)返回该点的特征尺寸
    
    返回:
        nodes: 节点坐标数组 (N, 2)
        elements: 单元节点索引数组 (M, 3)
        boundary_markers: 边界标记数组 (N,)
    """
    info = triangle.MeshInfo()
    info.set_points(points)
    info.set_facets(facets)
    if holes is not None:
        info.set_holes(holes)
    
    if refinement_func is None:
        mesh = triangle.build(info, max_volume=max_area, min_angle=20)
    else:
        def triangle_refiner(tri_points, area):
            x = np.mean(tri_points[:, 0])
            y = np.mean(tri_points[:, 1])
            h = refinement_func(x, y)
            return max_area * (h ** 2)
        
        mesh = triangle.build(info, max_volume=max_area, min_angle=20,
                              volume_constraints=True,
                              refinement_func=triangle_refiner)
    
    nodes = np.array(mesh.points)
    elements = np.array(mesh.elements)
    
    boundary_markers = np.zeros(len(nodes), dtype=bool)
    facet_nodes = np.unique(np.array(facets).flatten())
    if len(facet_nodes) > 0 and np.max(facet_nodes) < len(nodes):
        boundary_markers[facet_nodes] = True
    
    return nodes, elements, boundary_markers


def generate_adaptive_mesh(points, facets, holes=None, max_area=0.1, 
                           curvature_regions=None, gradient_regions=None,
                           refinement_level=3):
    """
    生成自适应网格，在曲率大或梯度大的区域局部细化
    
    参数:
        points: 边界点列表
        facets: 边界边列表
        holes: 孔洞列表
        max_area: 最大单元面积（粗网格）
        curvature_regions: 曲率大的区域列表 [(x_center, y_center, radius, refinement_factor)]
        gradient_regions: 梯度大的区域列表 [(x_center, y_center, radius, refinement_factor)]
        refinement_level: 最大加密级别
    
    返回:
        nodes, elements, boundary_markers
    """
    def refinement_func(x, y):
        min_h = 1.0
        
        if curvature_regions is not None:
            for (cx, cy, r, factor) in curvature_regions:
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                if dist < r:
                    h = max(0.1, factor * (dist / r + 0.1))
                    min_h = min(min_h, h)
        
        if gradient_regions is not None:
            for (cx, cy, r, factor) in gradient_regions:
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                if dist < r:
                    h = max(0.1, factor * (dist / r + 0.1))
                    min_h = min(min_h, h)
        
        return min_h
    
    return generate_mesh(points, facets, holes, max_area, refinement_func)


def assemble_global_matrix_vectorized(nodes, elements, rhs_func=None):
    """
    向量化的全局刚度矩阵组装（坐标列表格式）
    
    性能提升: 约10-20倍（取决于问题规模）
    
    参数:
        nodes: 节点坐标 (N, 2)
        elements: 单元节点索引 (M, 3)
        rhs_func: 右端项函数
    
    返回:
        K: 全局刚度矩阵 (CSR稀疏)
        F: 载荷向量
    """
    N = len(nodes)
    M = len(elements)
    
    x = nodes[:, 0]
    y = nodes[:, 1]
    
    e0, e1, e2 = elements[:, 0], elements[:, 1], elements[:, 2]
    
    x0, x1, x2 = x[e0], x[e1], x[e2]
    y0, y1, y2 = y[e0], y[e1], y[e2]
    
    area = 0.5 * np.abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))
    
    b0 = y1 - y2
    b1 = y2 - y0
    b2 = y0 - y1
    
    c0 = x2 - x1
    c1 = x0 - x2
    c2 = x1 - x0
    
    inv_4area = 1.0 / (4.0 * area)
    
    K00 = (b0 * b0 + c0 * c0) * inv_4area
    K01 = (b0 * b1 + c0 * c1) * inv_4area
    K02 = (b0 * b2 + c0 * c2) * inv_4area
    K11 = (b1 * b1 + c1 * c1) * inv_4area
    K12 = (b1 * b2 + c1 * c2) * inv_4area
    K22 = (b2 * b2 + c2 * c2) * inv_4area
    
    rows = np.concatenate([e0, e0, e0, e1, e1, e1, e2, e2, e2])
    cols = np.concatenate([e0, e1, e2, e0, e1, e2, e0, e1, e2])
    data = np.concatenate([K00, K01, K02, K01, K11, K12, K02, K12, K22])
    
    K = csr_matrix((data, (rows, cols)), shape=(N, N))
    
    F = np.zeros(N)
    if rhs_func is not None:
        xc = (x0 + x1 + x2) / 3.0
        yc = (y0 + y1 + y2) / 3.0
        f_vals = rhs_func(xc, yc) * area / 3.0
        
        np.add.at(F, e0, f_vals)
        np.add.at(F, e1, f_vals)
        np.add.at(F, e2, f_vals)
    
    return K, F


def apply_dirichlet_bc_optimized(K, F, boundary_markers, bc_values):
    """
    优化的Dirichlet边界条件应用
    
    参数:
        K: 全局刚度矩阵 (CSR)
        F: 载荷向量
        boundary_markers: 边界节点标记 (bool数组)
        bc_values: 边界值数组 (与nodes同长度)
    
    返回:
        K_mod, F_mod
    """
    N = len(F)
    
    if callable(bc_values):
        bc_vals = np.array([bc_values(nodes[i, 0], nodes[i, 1]) for i in range(N)])
    elif isinstance(bc_values, np.ndarray) and len(bc_values) == N:
        bc_vals = bc_values
    else:
        bc_vals = np.full(N, bc_values)
    
    boundary_indices = np.where(boundary_markers)[0]
    
    K_mod = K.tolil()
    F_mod = F.copy()
    
    for idx in boundary_indices:
        val = bc_vals[idx]
        
        row = K_mod.rows[idx]
        for j, col in enumerate(row):
            if col != idx:
                F_mod[col] -= K_mod.data[idx][j] * val
        
        K_mod.rows[idx] = [idx]
        K_mod.data[idx] = [1.0]
        
        for r in range(N):
            if r != idx and idx in K_mod.rows[r]:
                col_idx = K_mod.rows[r].index(idx)
                F_mod[r] -= K_mod.data[r][col_idx] * val
                K_mod.data[r][col_idx] = 0.0
        
        F_mod[idx] = val
    
    return K_mod.tocsr(), F_mod


def jacobi_preconditioner(A):
    """
    构造Jacobi（对角）预处理器
    
    参数:
        A: 系数矩阵 (稀疏)
    
    返回:
        M_inv: 预处理器 (LinearOperator)
    """
    diag = A.diagonal()
    diag_inv = np.where(diag != 0, 1.0 / diag, 0.0)
    
    def matvec(x):
        return diag_inv * x
    
    return LinearOperator(A.shape, matvec=matvec)


def conjugate_gradient_preconditioned(A, b, M=None, x0=None, tol=1e-10, maxiter=10000):
    """
    预条件共轭梯度法求解 Ax = b
    
    参数:
        A: 系数矩阵 (稀疏)
        b: 右端项
        M: 预处理器 (LinearOperator)，None表示不使用预处理器
        x0: 初始猜测
        tol: 收敛容差
        maxiter: 最大迭代次数
    
    返回:
        x: 解向量
        converged: 是否收敛
        iterations: 迭代次数
    """
    N = len(b)
    if x0 is None:
        x = np.zeros(N)
    else:
        x = x0.copy()
    
    r = b - A @ x
    rs_old = np.dot(r, r)
    
    if rs_old < tol:
        return x, True, 0
    
    if M is None:
        z = r
    else:
        z = M @ r
    
    p = z.copy()
    pz_old = np.dot(r, z)
    
    for k in range(maxiter):
        Ap = A @ p
        pap = np.dot(p, Ap)
        
        if pap < 1e-15:
            break
        
        alpha = pz_old / pap
        x = x + alpha * p
        r = r - alpha * Ap
        
        rs_new = np.dot(r, r)
        
        if rs_new < tol:
            return x, True, k + 1
        
        if M is None:
            z = r
        else:
            z = M @ r
        
        pz_new = np.dot(r, z)
        beta = pz_new / pz_old
        p = z + beta * p
        pz_old = pz_new
        rs_old = rs_new
    
    return x, False, maxiter


def compute_electric_field_vectorized(nodes, elements, phi):
    """
    向量化的电场强度计算
    
    参数:
        nodes: 节点坐标 (N, 2)
        elements: 单元节点索引 (M, 3)
        phi: 电势分布 (N,)
    
    返回:
        E_nodes: 节点处的电场强度 (N, 2)
    """
    N = len(nodes)
    M = len(elements)
    
    x = nodes[:, 0]
    y = nodes[:, 1]
    
    e0, e1, e2 = elements[:, 0], elements[:, 1], elements[:, 2]
    
    x0, x1, x2 = x[e0], x[e1], x[e2]
    y0, y1, y2 = y[e0], y[e1], y[e2]
    
    area = 0.5 * np.abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))
    
    b0 = y1 - y2
    b1 = y2 - y0
    b2 = y0 - y1
    
    c0 = x2 - x1
    c1 = x0 - x2
    c2 = x1 - x0
    
    phi0, phi1, phi2 = phi[e0], phi[e1], phi[e2]
    
    grad_phi_x = (b0 * phi0 + b1 * phi1 + b2 * phi2) / (2.0 * area)
    grad_phi_y = (c0 * phi0 + c1 * phi1 + c2 * phi2) / (2.0 * area)
    
    E_x = np.zeros(N)
    E_y = np.zeros(N)
    node_count = np.zeros(N)
    
    E_x_contrib = -grad_phi_x
    E_y_contrib = -grad_phi_y
    
    for e in range(3):
        elem_nodes = elements[:, e]
        np.add.at(E_x, elem_nodes, E_x_contrib)
        np.add.at(E_y, elem_nodes, E_y_contrib)
        np.add.at(node_count, elem_nodes, 1)
    
    E_nodes = np.column_stack([E_x / node_count, E_y / node_count])
    
    return E_nodes


def solve_poisson(points, facets, holes=None, max_area=0.1, 
                  rhs_func=None, bc_func=None, bc_values=0.0,
                  use_adaptive=False, curvature_regions=None, 
                  gradient_regions=None, use_preconditioner=True,
                  verbose=True):
    """
    求解二维泊松方程（优化版本）
    
    参数:
        points: 边界点列表
        facets: 边界边列表
        holes: 孔洞列表
        max_area: 最大单元面积
        rhs_func: 右端项函数 (rho/epsilon0)
        bc_func: 边界条件函数
        bc_values: 默认边界值
        use_adaptive: 是否使用自适应网格
        curvature_regions: 曲率区域列表
        gradient_regions: 梯度区域列表
        use_preconditioner: 是否使用对角预处理器
        verbose: 是否打印详细信息
    
    返回:
        nodes, elements, phi, E
    """
    if verbose:
        print("生成网格...")
    t0 = time.time()
    
    if use_adaptive:
        nodes, elements, boundary_markers = generate_adaptive_mesh(
            points, facets, holes, max_area, curvature_regions, gradient_regions
        )
    else:
        nodes, elements, boundary_markers = generate_mesh(
            points, facets, holes, max_area
        )
    
    t_mesh = time.time() - t0
    if verbose:
        print(f"网格生成完成: {len(nodes)} 节点, {len(elements)} 单元, 耗时 {t_mesh:.3f}s")
    
    if verbose:
        print("组装刚度矩阵...")
    t1 = time.time()
    
    K, F = assemble_global_matrix_vectorized(nodes, elements, rhs_func)
    
    t_assemble = time.time() - t1
    if verbose:
        print(f"刚度矩阵组装完成, 耗时 {t_assemble:.3f}s")
    
    if verbose:
        print("应用边界条件...")
    
    if bc_func is not None:
        boundary_markers, bc_values = bc_func(nodes)
    
    K, F = apply_dirichlet_bc_optimized(K, F, boundary_markers, bc_values)
    
    if verbose:
        print("求解线性系统...")
    t2 = time.time()
    
    if use_preconditioner:
        M = jacobi_preconditioner(K)
        phi, converged, iters = conjugate_gradient_preconditioned(K, F, M=M)
        method_str = "预条件共轭梯度法"
    else:
        phi, converged, iters = conjugate_gradient_preconditioned(K, F, M=None)
        method_str = "共轭梯度法"
    
    t_solve = time.time() - t2
    if verbose:
        if converged:
            print(f"{method_str}收敛，迭代次数: {iters}, 耗时 {t_solve:.3f}s")
        else:
            print(f"{method_str}未收敛，达到最大迭代次数 {iters}")
            print("使用直接求解器作为后备...")
            phi = spsolve(K, F)
    
    if verbose:
        print("计算电场强度...")
    E = compute_electric_field_vectorized(nodes, elements, phi)
    
    if verbose:
        print(f"总耗时: {time.time() - t0:.3f}s")
    
    return nodes, elements, phi, E


def plot_results(nodes, elements, phi, E, title="泊松方程求解结果"):
    """
    可视化求解结果
    """
    tri = Triangulation(nodes[:, 0], nodes[:, 1], elements)
    
    E_mag = np.sqrt(E[:, 0]**2 + E[:, 1]**2)
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    im1 = axes[0].tripcolor(tri, phi, shading='gouraud', cmap='viridis')
    axes[0].set_title('电势分布 φ(x,y)')
    axes[0].set_xlabel('x')
    axes[0].set_ylabel('y')
    axes[0].set_aspect('equal')
    plt.colorbar(im1, ax=axes[0])
    
    im2 = axes[1].tripcolor(tri, E_mag, shading='gouraud', cmap='hot')
    axes[1].set_title('电场强度 |E|')
    axes[1].set_xlabel('x')
    axes[1].set_ylabel('y')
    axes[1].set_aspect('equal')
    plt.colorbar(im2, ax=axes[1])
    
    axes[2].triplot(tri, 'k-', lw=0.5, alpha=0.5)
    step = max(1, len(nodes) // 50)
    axes[2].quiver(nodes[::step, 0], nodes[::step, 1], 
                   E[::step, 0], E[::step, 1], 
                   E_mag[::step], cmap='hot', scale=20)
    axes[2].set_title('电场矢量 E')
    axes[2].set_xlabel('x')
    axes[2].set_ylabel('y')
    axes[2].set_aspect('equal')
    
    plt.suptitle(title, fontsize=14)
    plt.tight_layout()
    plt.show()


def plot_mesh_comparison(nodes_coarse, elements_coarse, 
                         nodes_fine, elements_fine, title="网格对比"):
    """
    对比显示粗网格和自适应细化网格
    """
    tri_coarse = Triangulation(nodes_coarse[:, 0], nodes_coarse[:, 1], elements_coarse)
    tri_fine = Triangulation(nodes_fine[:, 0], nodes_fine[:, 1], elements_fine)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    axes[0].triplot(tri_coarse, 'k-', lw=0.5)
    axes[0].set_title(f'均匀网格 ({len(nodes_coarse)} 节点, {len(elements_coarse)} 单元)')
    axes[0].set_xlabel('x')
    axes[0].set_ylabel('y')
    axes[0].set_aspect('equal')
    
    axes[1].triplot(tri_fine, 'k-', lw=0.5)
    axes[1].set_title(f'自适应网格 ({len(nodes_fine)} 节点, {len(elements_fine)} 单元)')
    axes[1].set_xlabel('x')
    axes[1].set_ylabel('y')
    axes[1].set_aspect('equal')
    
    plt.suptitle(title, fontsize=14)
    plt.tight_layout()
    plt.show()


def example_parallel_plate():
    """
    示例1: 平行板电容器
    """
    print("\n" + "="*60)
    print("示例1: 平行板电容器")
    print("="*60)
    
    points = [
        (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)
    ]
    facets = [(0, 1), (1, 2), (2, 3), (3, 0)]
    
    def bc_func(nodes):
        markers = np.zeros(len(nodes), dtype=bool)
        values = np.zeros(len(nodes))
        
        for i, (x, y) in enumerate(nodes):
            if abs(y - 0.0) < 1e-6:
                markers[i] = True
                values[i] = 0.0
            elif abs(y - 1.0) < 1e-6:
                markers[i] = True
                values[i] = 1.0
        
        return markers, values
    
    print("\n--- 普通网格 + 无预处理器 ---")
    nodes1, elements1, phi1, E1 = solve_poisson(
        points, facets, max_area=0.01, bc_func=bc_func, 
        use_preconditioner=False
    )
    
    print("\n--- 普通网格 + 预处理器 ---")
    nodes2, elements2, phi2, E2 = solve_poisson(
        points, facets, max_area=0.01, bc_func=bc_func, 
        use_preconditioner=True
    )
    
    plot_results(nodes2, elements2, phi2, E2, title="平行板电容器 - 泊松方程求解")
    
    return nodes2, elements2, phi2, E2


def example_point_charge():
    """
    示例2: 点电荷电场（自适应网格）
    """
    print("\n" + "="*60)
    print("示例2: 点电荷电场（自适应网格）")
    print("="*60)
    
    R = 2.0
    n_points = 40
    points = []
    for i in range(n_points):
        theta = 2 * np.pi * i / n_points
        points.append((R * np.cos(theta), R * np.sin(theta)))
    
    facets = [(i, (i + 1) % n_points) for i in range(n_points)]
    
    def rhs_func(x, y):
        r2 = x**2 + y**2
        sigma = 0.1
        return np.exp(-r2 / (2 * sigma**2)) / (2 * np.pi * sigma**2)
    
    def bc_func(nodes):
        markers = np.zeros(len(nodes), dtype=bool)
        values = np.zeros(len(nodes))
        
        for i, (x, y) in enumerate(nodes):
            r = np.sqrt(x**2 + y**2)
            if abs(r - R) < 1e-3:
                markers[i] = True
                values[i] = 0.0
        
        return markers, values
    
    curvature_regions = [(0.0, 0.0, 0.5, 0.1)]
    
    print("\n--- 均匀网格 ---")
    nodes_coarse, elements_coarse, phi_coarse, E_coarse = solve_poisson(
        points, facets, max_area=0.05, rhs_func=rhs_func, bc_func=bc_func
    )
    
    print("\n--- 自适应网格 ---")
    nodes_fine, elements_fine, phi_fine, E_fine = solve_poisson(
        points, facets, max_area=0.05, rhs_func=rhs_func, bc_func=bc_func,
        use_adaptive=True, curvature_regions=curvature_regions
    )
    
    plot_mesh_comparison(nodes_coarse, elements_coarse, 
                         nodes_fine, elements_fine,
                         title="点电荷电场 - 网格对比")
    
    plot_results(nodes_fine, elements_fine, phi_fine, E_fine, 
                 title="点电荷电场 - 自适应网格求解")
    
    return nodes_fine, elements_fine, phi_fine, E_fine


def example_coaxial_cable():
    """
    示例3: 同轴电缆（自适应网格 + 预处理器）
    """
    print("\n" + "="*60)
    print("示例3: 同轴电缆（自适应网格 + 预处理器）")
    print("="*60)
    
    R1, R2 = 0.5, 2.0
    n_points = 60
    
    points = []
    for i in range(n_points):
        theta = 2 * np.pi * i / n_points
        points.append((R2 * np.cos(theta), R2 * np.sin(theta)))
    for i in range(n_points):
        theta = 2 * np.pi * i / n_points
        points.append((R1 * np.cos(theta), R1 * np.sin(theta)))
    
    facets = []
    for i in range(n_points):
        facets.append((i, (i + 1) % n_points))
    for i in range(n_points):
        facets.append((n_points + i, n_points + (i + 1) % n_points))
    
    holes = [(0.0, 0.0)]
    
    def bc_func(nodes):
        markers = np.zeros(len(nodes), dtype=bool)
        values = np.zeros(len(nodes))
        
        for i, (x, y) in enumerate(nodes):
            r = np.sqrt(x**2 + y**2)
            if abs(r - R2) < 1e-3:
                markers[i] = True
                values[i] = 0.0
            elif abs(r - R1) < 1e-3:
                markers[i] = True
                values[i] = 1.0
        
        return markers, values
    
    gradient_regions = [(0.0, 0.0, R1 + 0.3, 0.15)]
    
    print("\n--- 均匀网格 + 无预处理器 ---")
    t0 = time.time()
    nodes1, elements1, phi1, E1 = solve_poisson(
        points, facets, holes=holes, max_area=0.05, bc_func=bc_func,
        use_preconditioner=False, verbose=False
    )
    t1 = time.time()
    print(f"均匀网格: {len(nodes1)} 节点, 总耗时 {t1-t0:.3f}s")
    
    print("\n--- 自适应网格 + 预处理器 ---")
    t0 = time.time()
    nodes2, elements2, phi2, E2 = solve_poisson(
        points, facets, holes=holes, max_area=0.05, bc_func=bc_func,
        use_adaptive=True, gradient_regions=gradient_regions,
        use_preconditioner=True, verbose=False
    )
    t1 = time.time()
    print(f"自适应网格: {len(nodes2)} 节点, 总耗时 {t1-t0:.3f}s")
    
    plot_mesh_comparison(nodes1, elements1, nodes2, elements2,
                         title="同轴电缆 - 网格对比")
    
    plot_results(nodes2, elements2, phi2, E2, 
                 title="同轴电缆 - 自适应网格求解")
    
    return nodes2, elements2, phi2, E2


def performance_comparison():
    """
    性能对比测试
    """
    print("\n" + "="*60)
    print("性能对比测试")
    print("="*60)
    
    R = 2.0
    n_points = 40
    points = []
    for i in range(n_points):
        theta = 2 * np.pi * i / n_points
        points.append((R * np.cos(theta), R * np.sin(theta)))
    
    facets = [(i, (i + 1) % n_points) for i in range(n_points)]
    
    def rhs_func(x, y):
        r2 = x**2 + y**2
        sigma = 0.2
        return np.exp(-r2 / (2 * sigma**2)) / (2 * np.pi * sigma**2)
    
    def bc_func(nodes):
        markers = np.zeros(len(nodes), dtype=bool)
        values = np.zeros(len(nodes))
        for i, (x, y) in enumerate(nodes):
            r = np.sqrt(x**2 + y**2)
            if abs(r - R) < 1e-3:
                markers[i] = True
        return markers, values
    
    nodes, elements, _ = generate_mesh(points, facets, max_area=0.02)
    
    print(f"\n测试问题: {len(nodes)} 节点, {len(elements)} 单元")
    
    t0 = time.time()
    K1, F1 = assemble_global_matrix_vectorized(nodes, elements, rhs_func)
    t_vec = time.time() - t0
    print(f"向量化组装: {t_vec:.4f}s")
    
    boundary_markers, bc_vals = bc_func(nodes)
    
    t0 = time.time()
    K_bc, F_bc = apply_dirichlet_bc_optimized(K1, F1, boundary_markers, bc_vals)
    phi_noprec, conv_noprec, iter_noprec = conjugate_gradient_preconditioned(
        K_bc, F_bc, M=None, tol=1e-8
    )
    t_noprec = time.time() - t0
    print(f"无预处理器CG: {t_noprec:.4f}s, 迭代 {iter_noprec} 次, 收敛={conv_noprec}")
    
    t0 = time.time()
    K_bc, F_bc = apply_dirichlet_bc_optimized(K1, F1, boundary_markers, bc_vals)
    M = jacobi_preconditioner(K_bc)
    phi_prec, conv_prec, iter_prec = conjugate_gradient_preconditioned(
        K_bc, F_bc, M=M, tol=1e-8
    )
    t_prec = time.time() - t0
    print(f"预条件CG: {t_prec:.4f}s, 迭代 {iter_prec} 次, 收敛={conv_prec}")
    
    if t_noprec > 0 and t_prec > 0:
        speedup = t_noprec / t_prec
        iter_reduction = (1 - iter_prec / iter_noprec) * 100
        print(f"\n预处理器加速比: {speedup:.2f}x")
        print(f"迭代次数减少: {iter_reduction:.1f}%")


def assemble_mass_matrix(nodes, elements):
    """
    组装质量矩阵（用于时域求解）
    
    参数:
        nodes: 节点坐标 (N, 2)
        elements: 单元节点索引 (M, 3)
    
    返回:
        M: 质量矩阵 (稀疏对角)
    """
    N = len(nodes)
    M = len(elements)
    
    x = nodes[:, 0]
    y = nodes[:, 1]
    
    e0, e1, e2 = elements[:, 0], elements[:, 1], elements[:, 2]
    
    x0, x1, x2 = x[e0], x[e1], x[e2]
    y0, y1, y2 = y[e0], y[e1], y[e2]
    
    area = 0.5 * np.abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))
    
    mass_diag = np.zeros(N)
    mass_contrib = area / 12.0
    
    np.add.at(mass_diag, e0, mass_contrib * 2)
    np.add.at(mass_diag, e1, mass_contrib * 2)
    np.add.at(mass_diag, e2, mass_contrib * 2)
    
    M_mat = diags(mass_diag)
    
    return M_mat, mass_diag


def solve_transient(points, facets, holes=None, max_area=0.1,
                    initial_func=None, rhs_func_time=None, bc_func_time=None,
                    t_start=0.0, t_end=1.0, dt=0.01, sigma=0.0,
                    use_preconditioner=True, save_interval=1, verbose=True):
    """
    求解瞬态热传导/扩散方程（简化时域电磁场模型）
    
    方程: dφ/dt = ∇²φ + f(x,y,t)
    
    参数:
        points, facets, holes: 几何定义
        max_area: 最大单元面积
        initial_func: 初始条件函数 φ(x,y,0)
        rhs_func_time: 时变右端项函数 f(x,y,t)
        bc_func_time: 时变边界条件函数，返回(markers, values)
        t_start, t_end: 时间区间
        dt: 时间步长
        sigma: 阻尼/扩散系数
        use_preconditioner: 是否使用预处理器
        save_interval: 保存间隔（步）
        verbose: 是否打印信息
    
    返回:
        results: 字典，包含 time_points, phi_history, E_history
    """
    if verbose:
        print("生成网格...")
    nodes, elements, boundary_markers = generate_mesh(points, facets, holes, max_area)
    N = len(nodes)
    
    if verbose:
        print(f"网格: {N} 节点, {len(elements)} 单元")
        print("组装刚度矩阵和质量矩阵...")
    
    K, _ = assemble_global_matrix_vectorized(nodes, elements)
    M_mat, M_diag = assemble_mass_matrix(nodes, elements)
    
    if verbose:
        print("时间步进求解...")
    
    if initial_func is not None:
        phi = np.array([initial_func(x, y) for x, y in nodes])
    else:
        phi = np.zeros(N)
    
    n_steps = int((t_end - t_start) / dt) + 1
    
    results = {
        'time_points': [],
        'phi_history': [],
        'E_history': [],
        'nodes': nodes,
        'elements': elements
    }
    
    A = M_mat + dt * sigma * K
    
    for step in range(n_steps):
        t = t_start + step * dt
        
        if bc_func_time is not None:
            boundary_markers, bc_values = bc_func_time(nodes, t)
        
        F = phi.copy()
        if rhs_func_time is not None:
            def rhs_current(x, y):
                return rhs_func_time(x, y, t)
            _, F_rhs = assemble_global_matrix_vectorized(nodes, elements, rhs_current)
            F = F + dt * F_rhs
        
        A_bc, F_bc = apply_dirichlet_bc_optimized(A, F, boundary_markers, bc_values)
        
        if use_preconditioner:
            M_prec = jacobi_preconditioner(A_bc)
            phi_new, converged, iters = conjugate_gradient_preconditioned(
                A_bc, F_bc, M=M_prec, x0=phi, tol=1e-8, maxiter=500
            )
        else:
            phi_new, converged, iters = conjugate_gradient_preconditioned(
                A_bc, F_bc, M=None, x0=phi, tol=1e-8, maxiter=500
            )
        
        phi = phi_new
        
        if step % save_interval == 0:
            E = compute_electric_field_vectorized(nodes, elements, phi)
            results['time_points'].append(t)
            results['phi_history'].append(phi.copy())
            results['E_history'].append(E.copy())
            
            if verbose and step % 10 == 0:
                print(f"  t={t:.3f}, 迭代={iters}, |φ|={np.linalg.norm(phi):.4f}")
    
    if verbose:
        print(f"时域求解完成，共 {n_steps} 时间步")
    
    return results


def plot_field_advanced(nodes, elements, phi, E, 
                        plot_types=['contour', 'quiver', 'mesh'],
                        title="场量可视化", n_levels=20,
                        save_path=None):
    """
    增强的场量可视化
    
    参数:
        nodes, elements: 网格信息
        phi: 电势分布
        E: 电场强度
        plot_types: 绘图类型列表，可选 'contour', 'contourf', 'quiver', 'mesh', 'streamplot'
        title: 图标题
        n_levels: 等值线层数
        save_path: 保存路径
    """
    tri = Triangulation(nodes[:, 0], nodes[:, 1], elements)
    E_mag = np.sqrt(E[:, 0]**2 + E[:, 1]**2)
    
    n_plots = len(plot_types)
    fig, axes = plt.subplots(1, n_plots, figsize=(6 * n_plots, 5))
    if n_plots == 1:
        axes = [axes]
    
    for ax, ptype in zip(axes, plot_types):
        if ptype == 'contour':
            cs = ax.tricontour(tri, phi, levels=n_levels, cmap='viridis', linewidths=1)
            ax.clabel(cs, inline=1, fontsize=8, fmt='%.2f')
            ax.set_title('等势线')
        
        elif ptype == 'contourf':
            cs = ax.tricontourf(tri, phi, levels=n_levels, cmap='viridis')
            plt.colorbar(cs, ax=ax)
            ax.set_title('电势云图')
        
        elif ptype == 'quiver':
            step = max(1, len(nodes) // 80)
            ax.quiver(nodes[::step, 0], nodes[::step, 1],
                      E[::step, 0], E[::step, 1],
                      E_mag[::step], cmap='hot', scale=30, width=0.002)
            ax.set_title('电场矢量')
        
        elif ptype == 'mesh':
            ax.triplot(tri, 'k-', lw=0.3, alpha=0.6)
            ax.tricontourf(tri, E_mag, levels=n_levels, cmap='hot', alpha=0.7)
            ax.set_title('网格与电场强度')
        
        elif ptype == 'streamplot':
            xi, yi = np.meshgrid(np.linspace(nodes[:, 0].min(), nodes[:, 0].max(), 50),
                                 np.linspace(nodes[:, 1].min(), nodes[:, 1].max(), 50))
            from scipy.interpolate import griddata
            Exi = griddata(nodes, E[:, 0], (xi, yi), method='linear')
            Eyi = griddata(nodes, E[:, 1], (xi, yi), method='linear')
            Emagi = np.sqrt(Exi**2 + Eyi**2)
            ax.streamplot(xi, yi, Exi, Eyi, color=Emagi, cmap='hot', 
                         density=1.5, linewidth=1)
            ax.set_title('电场流线')
        
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_aspect('equal')
    
    plt.suptitle(title, fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    plt.show()


def animate_transient(results, field='phi', interval=100, save_path=None):
    """
    时域结果动画
    
    参数:
        results: solve_transient 返回的结果字典
        field: 'phi' 或 'E'
        interval: 帧间隔(ms)
        save_path: 保存为mp4的路径
    """
    nodes = results['nodes']
    elements = results['elements']
    tri = Triangulation(nodes[:, 0], nodes[:, 1], elements)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    if field == 'phi':
        data_history = results['phi_history']
        vmin = np.min([np.min(d) for d in data_history])
        vmax = np.max([np.max(d) for d in data_history])
        im = ax.tripcolor(tri, data_history[0], shading='gouraud', 
                         cmap='viridis', vmin=vmin, vmax=vmax)
        plt.colorbar(im, ax=ax, label='φ')
        ax.set_title('电势分布随时间演化')
    else:
        E_history = results['E_history']
        E_mag_history = [np.sqrt(E[:, 0]**2 + E[:, 1]**2) for E in E_history]
        vmin = np.min([np.min(d) for d in E_mag_history])
        vmax = np.max([np.max(d) for d in E_mag_history])
        im = ax.tripcolor(tri, E_mag_history[0], shading='gouraud',
                         cmap='hot', vmin=vmin, vmax=vmax)
        plt.colorbar(im, ax=ax, label='|E|')
        ax.set_title('电场强度随时间演化')
    
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_aspect('equal')
    time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)
    
    def update(frame):
        if field == 'phi':
            im.set_array(data_history[frame])
        else:
            im.set_array(E_mag_history[frame])
        time_text.set_text(f't = {results["time_points"][frame]:.3f}')
        return im, time_text
    
    anim = FuncAnimation(fig, update, frames=len(results['time_points']),
                        interval=interval, blit=True)
    
    if save_path:
        anim.save(save_path, writer='ffmpeg', fps=10)
    
    plt.show()
    
    return anim


class ParameterSweep:
    """
    参数化扫描类
    
    支持扫描几何参数、材料属性等
    """
    
    def __init__(self, base_setup_func):
        """
        参数:
            base_setup_func: 基础设置函数，输入参数字典，返回求解所需的完整参数
        """
        self.base_setup_func = base_setup_func
        self.parameters = {}
        self.results = []
    
    def add_parameter(self, name, values):
        """
        添加扫描参数
        
        参数:
            name: 参数名
            values: 参数值列表
        """
        self.parameters[name] = values
    
    def run(self, verbose=True):
        """
        执行参数扫描
        
        返回:
            results: 结果列表，每个元素包含参数组合和求解结果
        """
        param_names = list(self.parameters.keys())
        param_values = list(self.parameters.values())
        combinations = list(product(*param_values))
        
        n_cases = len(combinations)
        if verbose:
            print(f"参数化扫描: {n_cases} 个参数组合")
        
        for idx, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            
            if verbose:
                print(f"\n案例 {idx+1}/{n_cases}: {params}")
            
            try:
                t0 = time.time()
                setup = self.base_setup_func(params)
                nodes, elements, phi, E = solve_poisson(**setup, verbose=False)
                elapsed = time.time() - t0
                
                result = {
                    'parameters': params,
                    'nodes': nodes,
                    'elements': elements,
                    'phi': phi,
                    'E': E,
                    'E_max': np.max(np.sqrt(E[:, 0]**2 + E[:, 1]**2)),
                    'phi_mean': np.mean(phi),
                    'solve_time': elapsed,
                    'n_nodes': len(nodes),
                    'n_elements': len(elements)
                }
                self.results.append(result)
                
                if verbose:
                    print(f"  完成: E_max={result['E_max']:.4f}, 耗时={elapsed:.3f}s")
            
            except Exception as e:
                if verbose:
                    print(f"  失败: {str(e)}")
                self.results.append({
                    'parameters': params,
                    'error': str(e)
                })
        
        return self.results
    
    def plot_sweep_1d(self, param_name, quantity='E_max', ax=None):
        """
        绘制单参数扫描结果
        
        参数:
            param_name: 要绘制的参数名
            quantity: 要绘制的量 ('E_max', 'phi_mean', 'solve_time'等)
        """
        valid_results = [r for r in self.results if 'error' not in r]
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        other_params = [k for k in self.parameters.keys() if k != param_name]
        
        for combo in product(*[self.parameters[k] for k in other_params]):
            filter_dict = dict(zip(other_params, combo))
            filtered = [r for r in valid_results if 
                       all(r['parameters'][k] == v for k, v in filter_dict.items())]
            
            if filtered:
                x_vals = [r['parameters'][param_name] for r in filtered]
                y_vals = [r[quantity] for r in filtered]
                
                label = ', '.join([f'{k}={v}' for k, v in filter_dict.items()])
                ax.plot(x_vals, y_vals, 'o-', label=label if label else param_name)
        
        ax.set_xlabel(param_name)
        ax.set_ylabel(quantity)
        ax.set_title(f'参数化扫描: {quantity} vs {param_name}')
        ax.grid(True, alpha=0.3)
        if other_params:
            ax.legend()
        
        return ax
    
    def plot_sweep_2d(self, param_x, param_y, quantity='E_max'):
        """
        绘制双参数扫描热图
        """
        valid_results = [r for r in self.results if 'error' not in r]
        
        x_vals = sorted(self.parameters[param_x])
        y_vals = sorted(self.parameters[param_y])
        
        z_data = np.zeros((len(y_vals), len(x_vals)))
        
        for r in valid_results:
            xi = x_vals.index(r['parameters'][param_x])
            yi = y_vals.index(r['parameters'][param_y])
            z_data[yi, xi] = r[quantity]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.pcolormesh(x_vals, y_vals, z_data, cmap='viridis', shading='auto')
        plt.colorbar(im, ax=ax, label=quantity)
        
        ax.set_xlabel(param_x)
        ax.set_ylabel(param_y)
        ax.set_title(f'参数化扫描: {quantity}')
        
        for i, y in enumerate(y_vals):
            for j, x in enumerate(x_vals):
                ax.text(x, y, f'{z_data[i, j]:.3f}', 
                       ha='center', va='center', color='white', fontsize=9)
        
        return ax
    
    def save(self, filepath):
        """保存扫描结果"""
        with open(filepath, 'wb') as f:
            pickle.dump({'parameters': self.parameters, 'results': self.results}, f)
    
    def load(self, filepath):
        """加载扫描结果"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.parameters = data['parameters']
            self.results = data['results']


def example_transient_heating():
    """
    示例: 时域热传导（高斯热源）
    """
    print("\n" + "="*60)
    print("示例: 时域热传导（高斯热源）")
    print("="*60)
    
    L = 2.0
    points = [(-L, -L), (L, -L), (L, L), (-L, L)]
    facets = [(0, 1), (1, 2), (2, 3), (3, 0)]
    
    def initial_func(x, y):
        return 0.0
    
    def rhs_func(x, y, t):
        sigma = 0.3
        t_peak = 0.5
        amp = np.exp(-((t - t_peak)**2) / (2 * 0.2**2))
        return 5.0 * amp * np.exp(-(x**2 + y**2) / (2 * sigma**2))
    
    def bc_func(nodes, t):
        markers = np.ones(len(nodes), dtype=bool)
        values = np.zeros(len(nodes))
        return markers, values
    
    results = solve_transient(
        points, facets, max_area=0.05,
        initial_func=initial_func,
        rhs_func_time=rhs_func,
        bc_func_time=bc_func,
        t_start=0.0, t_end=2.0, dt=0.02,
        sigma=1.0, save_interval=5, verbose=True
    )
    
    idx_mid = len(results['time_points']) // 2
    t_mid = results['time_points'][idx_mid]
    phi_mid = results['phi_history'][idx_mid]
    E_mid = results['E_history'][idx_mid]
    
    plot_field_advanced(
        results['nodes'], results['elements'], phi_mid, E_mid,
        plot_types=['contourf', 'quiver', 'streamplot'],
        title=f'时域结果 t={t_mid:.2f}s'
    )
    
    print("生成动画...")
    animate_transient(results, field='phi', interval=100)
    
    return results


def example_parameter_sweep():
    """
    示例: 同轴电缆参数化扫描
    """
    print("\n" + "="*60)
    print("示例: 同轴电缆参数化扫描")
    print("="*60)
    
    def setup_coaxial(params):
        R1 = params.get('R1', 0.5)
        R2 = params.get('R2', 2.0)
        max_area = params.get('max_area', 0.05)
        V_inner = params.get('V_inner', 1.0)
        
        n_points = 40
        points = []
        for i in range(n_points):
            theta = 2 * np.pi * i / n_points
            points.append((R2 * np.cos(theta), R2 * np.sin(theta)))
        for i in range(n_points):
            theta = 2 * np.pi * i / n_points
            points.append((R1 * np.cos(theta), R1 * np.sin(theta)))
        
        facets = []
        for i in range(n_points):
            facets.append((i, (i + 1) % n_points))
        for i in range(n_points):
            facets.append((n_points + i, n_points + (i + 1) % n_points))
        
        holes = [(0.0, 0.0)]
        
        def bc_func(nodes):
            markers = np.zeros(len(nodes), dtype=bool)
            values = np.zeros(len(nodes))
            for i, (x, y) in enumerate(nodes):
                r = np.sqrt(x**2 + y**2)
                if abs(r - R2) < 1e-3:
                    markers[i] = True
                    values[i] = 0.0
                elif abs(r - R1) < 1e-3:
                    markers[i] = True
                    values[i] = V_inner
            return markers, values
        
        return {
            'points': points,
            'facets': facets,
            'holes': holes,
            'max_area': max_area,
            'bc_func': bc_func,
            'use_preconditioner': True
        }
    
    sweep = ParameterSweep(setup_coaxial)
    sweep.add_parameter('R1', [0.3, 0.5, 0.7, 0.9])
    sweep.add_parameter('V_inner', [0.5, 1.0, 1.5])
    
    results = sweep.run(verbose=True)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sweep.plot_sweep_1d('R1', 'E_max', ax=axes[0])
    sweep.plot_sweep_1d('R1', 'solve_time', ax=axes[1])
    plt.tight_layout()
    plt.show()
    
    if len(sweep.parameters) >= 2:
        sweep.plot_sweep_2d('R1', 'V_inner', 'E_max')
        plt.show()
    
    return sweep


def example_advanced_visualization():
    """
    示例: 高级可视化功能
    """
    print("\n" + "="*60)
    print("示例: 高级场量可视化")
    print("="*60)
    
    R = 2.0
    n_points = 40
    points = []
    for i in range(n_points):
        theta = 2 * np.pi * i / n_points
        points.append((R * np.cos(theta), R * np.sin(theta)))
    facets = [(i, (i + 1) % n_points) for i in range(n_points)]
    
    def rhs_func(x, y):
        r2 = x**2 + y**2
        sigma = 0.2
        return np.exp(-r2 / (2 * sigma**2)) / (2 * np.pi * sigma**2)
    
    def bc_func(nodes):
        markers = np.zeros(len(nodes), dtype=bool)
        values = np.zeros(len(nodes))
        for i, (x, y) in enumerate(nodes):
            r = np.sqrt(x**2 + y**2)
            if abs(r - R) < 1e-3:
                markers[i] = True
        return markers, values
    
    nodes, elements, phi, E = solve_poisson(
        points, facets, max_area=0.03, rhs_func=rhs_func, bc_func=bc_func
    )
    
    plot_field_advanced(
        nodes, elements, phi, E,
        plot_types=['contourf', 'contour', 'quiver', 'streamplot'],
        title='点电荷电场 - 高级可视化'
    )
    
    return nodes, elements, phi, E


if __name__ == "__main__":
    example_parallel_plate()
    example_point_charge()
    example_coaxial_cable()
    performance_comparison()
    
    example_advanced_visualization()
    example_transient_heating()
    example_parameter_sweep()
