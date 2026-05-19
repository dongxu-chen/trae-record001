from dolfin import *
import numpy as np


class SmoothBoundary(Expression):
    """平滑边界条件类，使用双曲正切函数实现边界平滑过渡"""
    
    def __init__(self, value_left, value_right, transition_width=0.05, center=0.0, **kwargs):
        self.value_left = value_left
        self.value_right = value_right
        self.transition_width = transition_width
        self.center = center
        super().__init__(**kwargs)
    
    def eval(self, value, x):
        dx = x[0] - self.center
        tanh_factor = np.tanh(dx / self.transition_width)
        value[0] = 0.5 * (self.value_left + self.value_right) + \
                   0.5 * (self.value_right - self.value_left) * tanh_factor


class SmoothBoundary2D(Expression):
    """2D平滑边界条件，支持四角不同值的平滑过渡"""
    
    def __init__(self, values, transition_width=0.05, **kwargs):
        self.values = values  # [左下, 右下, 左上, 右上]
        self.transition_width = transition_width
        super().__init__(**kwargs)
    
    def eval(self, value, x):
        def smooth_step(t):
            return 0.5 * (1 + np.tanh(t / self.transition_width))
        
        tx = smooth_step(x[0] - 0.5)
        ty = smooth_step(x[1] - 0.5)
        
        v00, v10, v01, v11 = self.values
        
        val_bottom = (1 - tx) * v00 + tx * v10
        val_top = (1 - tx) * v01 + tx * v11
        value[0] = (1 - ty) * val_bottom + ty * val_top


class BoundaryCondition:
    """边界条件类，用于定义和管理偏微分方程的边界条件"""

    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"
    ROBIN = "robin"

    def __init__(self, bc_type, value, boundary_marker=None, subdomain_id=0, smooth=False, smooth_width=0.05):
        """
        初始化边界条件

        参数:
            bc_type: 边界条件类型 (DIRICHLET, NEUMANN, ROBIN)
            value: 边界值，可以是Expression、Constant或函数
            boundary_marker: 边界标记函数（用于指定边界位置）
            subdomain_id: 子域ID（用于多边界情况）
            smooth: 是否使用平滑过渡
            smooth_width: 平滑过渡宽度
        """
        self.bc_type = bc_type
        self.value = value
        self.boundary_marker = boundary_marker
        self.subdomain_id = subdomain_id
        self.smooth = smooth
        self.smooth_width = smooth_width

    @staticmethod
    def create_dirichlet(value, boundary_marker, subdomain_id=0, smooth=False, smooth_width=0.05):
        """创建Dirichlet边界条件"""
        return BoundaryCondition(
            BoundaryCondition.DIRICHLET, value, boundary_marker, subdomain_id, smooth, smooth_width
        )

    @staticmethod
    def create_dirichlet_smooth(value_left, value_right, boundary_marker, subdomain_id=0, smooth_width=0.05):
        """创建平滑过渡的Dirichlet边界条件"""
        smooth_value = SmoothBoundary(value_left, value_right, smooth_width, degree=2)
        return BoundaryCondition(
            BoundaryCondition.DIRICHLET, smooth_value, boundary_marker, subdomain_id, True, smooth_width
        )

    @staticmethod
    def create_neumann(value, boundary_marker=None, subdomain_id=0):
        """创建Neumann边界条件"""
        return BoundaryCondition(
            BoundaryCondition.NEUMANN, value, boundary_marker, subdomain_id
        )

    @staticmethod
    def create_robin(value, alpha, boundary_marker=None, subdomain_id=0):
        """创建Robin边界条件"""
        return BoundaryCondition(
            BoundaryCondition.ROBIN, (value, alpha), boundary_marker, subdomain_id
        )

    def apply_dirichlet(self, V):
        """应用Dirichlet边界条件"""
        if self.bc_type != BoundaryCondition.DIRICHLET:
            return None

        if self.boundary_marker is None:
            return DirichletBC(V, self.value, "on_boundary")
        else:
            return DirichletBC(V, self.value, self.boundary_marker)


def create_unit_square_boundary_markers():
    """创建单位正方形的边界标记"""

    class LeftBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[0], 0.0)

    class RightBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[0], 1.0)

    class BottomBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[1], 0.0)

    class TopBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[1], 1.0)

    return {
        "left": LeftBoundary(),
        "right": RightBoundary(),
        "bottom": BottomBoundary(),
        "top": TopBoundary(),
    }


def create_unit_cube_boundary_markers():
    """创建单位立方体的边界标记"""

    class LeftBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[0], 0.0)

    class RightBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[0], 1.0)

    class BottomBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[1], 0.0)

    class TopBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[1], 1.0)

    class BackBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[2], 0.0)

    class FrontBoundary(SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and near(x[2], 1.0)

    return {
        "left": LeftBoundary(),
        "right": RightBoundary(),
        "bottom": BottomBoundary(),
        "top": TopBoundary(),
        "back": BackBoundary(),
        "front": FrontBoundary(),
    }
