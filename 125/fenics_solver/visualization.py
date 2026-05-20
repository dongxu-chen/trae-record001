import matplotlib.pyplot as plt
import matplotlib.tri as tri
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from dolfin import *


def get_mesh_data(mesh, u):
    """从FEniCS网格和解函数中提取绘图数据"""
    coords = mesh.coordinates()
    x = coords[:, 0]
    y = coords[:, 1]

    cells = mesh.cells()

    z = np.array([u(Point(x[i], y[i])) for i in range(len(x))])

    return x, y, z, cells


def plot_solution(u, mesh=None, title="Solution Contour", figsize=(10, 8),
                  cmap="viridis", show_mesh=False, save_path=None, dpi=100):
    """
    绘制解的云图（等高线图）

    参数:
        u: 解函数
        mesh: 网格，如果为None则从u获取
        title: 图标题
        figsize: 图大小
        cmap: 颜色映射
        show_mesh: 是否显示网格
        save_path: 保存路径
        dpi: 图像分辨率
    """
    if mesh is None:
        mesh = u.function_space().mesh()

    x, y, z, cells = get_mesh_data(mesh, u)

    triang = tri.Triangulation(x, y, cells)

    fig, ax = plt.subplots(figsize=figsize)

    contour = ax.tricontourf(triang, z, levels=50, cmap=cmap)
    fig.colorbar(contour, ax=ax, label="u")

    if show_mesh:
        ax.triplot(triang, "k-", lw=0.5, alpha=0.5)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title)
    ax.set_aspect("equal")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches="tight")

    return fig, ax


def plot_solution_3d(u, mesh=None, title="3D Solution Surface", figsize=(12, 8),
                     cmap="viridis", save_path=None, dpi=100):
    """
    绘制解的3D曲面图

    参数:
        u: 解函数
        mesh: 网格，如果为None则从u获取
        title: 图标题
        figsize: 图大小
        cmap: 颜色映射
        save_path: 保存路径
        dpi: 图像分辨率
    """
    if mesh is None:
        mesh = u.function_space().mesh()

    x, y, z, cells = get_mesh_data(mesh, u)

    triang = tri.Triangulation(x, y, cells)

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    surf = ax.plot_trisurf(triang, z, cmap=cmap, linewidth=0.1, alpha=0.9)
    fig.colorbar(surf, ax=ax, label="u", shrink=0.5)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("u")
    ax.set_title(title)
    ax.view_init(elev=30, azim=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches="tight")

    return fig, ax


def plot_gradient(u, mesh=None, title="Gradient Magnitude", figsize=(10, 8),
                  cmap="plasma", save_path=None, dpi=100):
    """
    绘制梯度幅值云图

    参数:
        u: 解函数
        mesh: 网格，如果为None则从u获取
        title: 图标题
        figsize: 图大小
        cmap: 颜色映射
        save_path: 保存路径
        dpi: 图像分辨率
    """
    if mesh is None:
        mesh = u.function_space().mesh()

    V_g = VectorFunctionSpace(mesh, "P", 1)
    grad_u = project(grad(u), V_g)

    coords = mesh.coordinates()
    x = coords[:, 0]
    y = coords[:, 1]
    cells = mesh.cells()

    grad_mag = np.array([
        np.linalg.norm(grad_u(Point(x[i], y[i])))
        for i in range(len(x))
    ])

    triang = tri.Triangulation(x, y, cells)

    fig, ax = plt.subplots(figsize=figsize)
    contour = ax.tricontourf(triang, grad_mag, levels=50, cmap=cmap)
    fig.colorbar(contour, ax=ax, label="|∇u|")

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title)
    ax.set_aspect("equal")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches="tight")

    return fig, ax


def animate_heat_equation(solver, title="Heat Equation Evolution",
                          figsize=(10, 8), cmap="jet", save_path="heat_animation.gif",
                          fps=10, dpi=100):
    """
    创建热传导方程时间演化动画

    参数:
        solver: HeatEquationSolver对象
        title: 图标题
        figsize: 图大小
        cmap: 颜色映射
        save_path: 保存路径 (.gif或.mp4)
        fps: 每秒帧数
        dpi: 图像分辨率
    """
    solutions, times = solver.get_solutions()
    mesh = solver.mesh

    x, y, _, cells = get_mesh_data(mesh, solutions[0])
    triang = tri.Triangulation(x, y, cells)

    vmin = min([u.vector().min() for u in solutions])
    vmax = max([u.vector().max() for u in solutions])

    fig, ax = plt.subplots(figsize=figsize)
    contour = ax.tricontourf(triang, np.zeros_like(x),
                             levels=np.linspace(vmin, vmax, 50), cmap=cmap)
    fig.colorbar(contour, ax=ax, label="Temperature")

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")

    plt.tight_layout()

    def update(frame):
        z = np.array([solutions[frame](Point(x[i], y[i])) for i in range(len(x))])
        ax.clear()
        contour = ax.tricontourf(triang, z, levels=np.linspace(vmin, vmax, 50), cmap=cmap)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(f"{title} - t = {times[frame]:.3f}")
        ax.set_aspect("equal")
        return contour,

    from matplotlib.animation import FuncAnimation
    anim = FuncAnimation(fig, update, frames=len(solutions), interval=1000/fps, blit=False)

    if save_path:
        if save_path.endswith(".gif"):
            anim.save(save_path, writer="pillow", fps=fps, dpi=dpi)
        elif save_path.endswith(".mp4"):
            anim.save(save_path, writer="ffmpeg", fps=fps, dpi=dpi)

    return anim


def plot_mesh(mesh, title="FEniCS Mesh", figsize=(8, 8), save_path=None, dpi=100):
    """
    绘制计算网格

    参数:
        mesh: FEniCS网格对象
        title: 图标题
        figsize: 图大小
        save_path: 保存路径
        dpi: 图像分辨率
    """
    coords = mesh.coordinates()
    x = coords[:, 0]
    y = coords[:, 1]
    cells = mesh.cells()

    triang = tri.Triangulation(x, y, cells)

    fig, ax = plt.subplots(figsize=figsize)
    ax.triplot(triang, "b-", lw=1)
    ax.plot(x, y, "ro", markersize=3)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(f"{title} (nodes: {mesh.num_vertices()}, elements: {mesh.num_cells()})")
    ax.set_aspect("equal")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches="tight")

    return fig, ax


def plot_comparison(u1, u2, mesh=None, titles=["Solution 1", "Solution 2"],
                    figsize=(14, 6), cmap="viridis", save_path=None, dpi=100):
    """
    并排比较两个解

    参数:
        u1: 第一个解
        u2: 第二个解
        mesh: 网格，如果为None则从u1获取
        titles: 标题列表
        figsize: 图大小
        cmap: 颜色映射
        save_path: 保存路径
        dpi: 图像分辨率
    """
    if mesh is None:
        mesh = u1.function_space().mesh()

    x, y, z1, cells = get_mesh_data(mesh, u1)
    z2 = np.array([u2(Point(x[i], y[i])) for i in range(len(x))])

    triang = tri.Triangulation(x, y, cells)

    vmin = min(z1.min(), z2.min())
    vmax = max(z1.max(), z2.max())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    contour1 = ax1.tricontourf(triang, z1, levels=50, cmap=cmap, vmin=vmin, vmax=vmax)
    ax1.set_xlabel("x")
    ax1.set_ylabel("y")
    ax1.set_title(titles[0])
    ax1.set_aspect("equal")

    contour2 = ax2.tricontourf(triang, z2, levels=50, cmap=cmap, vmin=vmin, vmax=vmax)
    ax2.set_xlabel("x")
    ax2.set_ylabel("y")
    ax2.set_title(titles[1])
    ax2.set_aspect("equal")

    fig.colorbar(contour2, ax=[ax1, ax2], label="u", shrink=0.8)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches="tight")

    return fig, (ax1, ax2)


def plot_convergence_history(history, title="Newton-Raphson收敛历史",
                             figsize=(14, 5), save_path=None, dpi=150,
                             show_increments=True):
    """
    绘制Newton-Raphson迭代收敛历史
    
    参数:
        history: ConvergenceHistory对象
        title: 图标题
        figsize: 图大小
        save_path: 保存路径
        dpi: 图像分辨率
        show_increments: 是否显示增量范数
    
    返回:
        fig, axes: 图和坐标轴对象
    """
    data = history.get_data()
    
    if show_increments and len(data['increments']) > 0:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        axes = (ax1, ax2)
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(figsize[0]//2, figsize[1]))
        axes = (ax1,)
    
    iters = data['iterations']
    residuals = data['residuals']
    
    ax1.semilogy(iters, residuals, 'bo-', linewidth=2, markersize=6)
    ax1.set_xlabel('迭代次数')
    ax1.set_ylabel('残差范数')
    ax1.set_title('残差收敛曲线')
    ax1.grid(True, which='both', alpha=0.3)
    ax1.grid(True, which='minor', alpha=0.15)
    
    if len(residuals) > 1:
        for i in range(1, min(4, len(residuals))):
            conv_rate = np.log(residuals[i]/residuals[i-1]) / np.log(10)
            if abs(conv_rate) > 0.01:
                ax1.annotate(f'{conv_rate:.2f}',
                           xy=((iters[i]+iters[i-1])/2, np.sqrt(residuals[i]*residuals[i-1])),
                           ha='center', fontsize=8)
    
    if show_increments and len(data['increments']) > 0:
        increments = data['increments']
        ax2.semilogy(iters[1:], increments, 'rs-', linewidth=2, markersize=6)
        ax2.set_xlabel('迭代次数')
        ax2.set_ylabel('解增量范数')
        ax2.set_title('解增量收敛曲线')
        ax2.grid(True, which='both', alpha=0.3)
        ax2.grid(True, which='minor', alpha=0.15)
    
    fig.suptitle(title, fontsize=14, y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
    
    return fig, axes


def plot_timestep_history(time_history, title="时间步收敛历史",
                          figsize=(12, 5), save_path=None, dpi=150):
    """
    绘制时间步长的迭代收敛历史
    
    参数:
        time_history: ConvergenceHistory对象
        title: 图标题
        figsize: 图大小
        save_path: 保存路径
        dpi: 图像分辨率
    
    返回:
        fig, (ax1, ax2): 图和坐标轴对象
    """
    data = time_history.get_data()
    timesteps = data['timesteps']
    
    if len(timesteps) == 0:
        print("没有时间步数据")
        return None, None
    
    times = [t for t, n in timesteps]
    num_iters = [n for t, n in timesteps]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    ax1.bar(range(len(times)), num_iters, color='skyblue', edgecolor='navy', alpha=0.7)
    ax1.set_xlabel('时间步序号')
    ax1.set_ylabel('Newton迭代次数')
    ax1.set_title('各时间步迭代次数')
    ax1.grid(True, axis='y', alpha=0.3)
    
    avg_iters = np.mean(num_iters)
    ax1.axhline(y=avg_iters, color='r', linestyle='--', 
                label=f'平均 = {avg_iters:.1f}')
    ax1.legend()
    
    cumulative_iters = np.cumsum(num_iters)
    ax2.plot(times, cumulative_iters, 'b-', linewidth=2)
    ax2.fill_between(times, cumulative_iters, alpha=0.3)
    ax2.set_xlabel('时间')
    ax2.set_ylabel('累计迭代次数')
    ax2.set_title('累计迭代次数 - 时间')
    ax2.grid(True, alpha=0.3)
    
    fig.suptitle(title, fontsize=14, y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
    
    return fig, (ax1, ax2)


def plot_nonlinear_comparison(histories, labels, title="求解器性能比较",
                              figsize=(12, 6), save_path=None, dpi=150):
    """
    比较多个求解器的收敛历史
    
    参数:
        histories: ConvergenceHistory对象列表
        labels: 对应标签列表
        title: 图标题
        figsize: 图大小
        save_path: 保存路径
        dpi: 图像分辨率
    
    返回:
        fig, ax: 图和坐标轴对象
    """
    markers = ['o', 's', '^', 'D', 'v', 'p']
    colors = ['b', 'r', 'g', 'm', 'c', 'orange']
    
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    for i, (history, label) in enumerate(zip(histories, labels)):
        data = history.get_data()
        iters = data['iterations']
        residuals = data['residuals']
        
        marker = markers[i % len(markers)]
        color = colors[i % len(colors)]
        
        ax.semilogy(iters, residuals, f'{color}{marker}-', 
                    linewidth=2, markersize=6, label=label)
    
    ax.set_xlabel('迭代次数')
    ax.set_ylabel('残差范数')
    ax.set_title(title)
    ax.grid(True, which='both', alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
    
    return fig, ax


def plot_material_property(material, T_range, mesh=None, n_points=100,
                           title="材料属性", figsize=(12, 5),
                           save_path=None, dpi=150):
    """
    绘制材料属性随温度变化曲线
    
    参数:
        material: 材料对象（需要有conductivity和rho_c方法）
        T_range: 温度范围 (T_min, T_max)
        mesh: 网格（用于空间变化的材料）
        n_points: 采样点数
        title: 图标题
        figsize: 图大小
        save_path: 保存路径
        dpi: 图像分辨率
    
    返回:
        fig, axes: 图和坐标轴对象
    """
    T_values = np.linspace(T_range[0], T_range[1], n_points)
    
    k_values = []
    rho_c_values = []
    
    for T in T_values:
        if hasattr(material, 'conductivity'):
            k_val = material.conductivity(Constant(T))
            if hasattr(k_val, 'values'):
                k_val = float(k_val.values()[0])
            else:
                k_val = float(k_val)
        else:
            k_val = 1.0
        k_values.append(k_val)
        
        if hasattr(material, 'rho_c'):
            rc_val = material.rho_c(Constant(T))
            if hasattr(rc_val, 'values'):
                rc_val = float(rc_val.values()[0])
            else:
                rc_val = float(rc_val)
        else:
            rc_val = 1.0
        rho_c_values.append(rc_val)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    ax1.plot(T_values, k_values, 'b-', linewidth=2)
    ax1.set_xlabel('温度 T')
    ax1.set_ylabel('热传导系数 k(T)')
    ax1.set_title('热传导系数')
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(T_values, rho_c_values, 'r-', linewidth=2)
    ax2.set_xlabel('温度 T')
    ax2.set_ylabel('体积热容 ρc(T)')
    ax2.set_title('体积热容')
    ax2.grid(True, alpha=0.3)
    
    fig.suptitle(title, fontsize=14, y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
    
    return fig, (ax1, ax2)

