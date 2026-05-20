from dolfin import *
import numpy as np


class MaterialProperty(Expression):
    """材料属性基类，支持空间变化的物性参数"""
    
    def __init__(self, base_value, **kwargs):
        self.base_value = base_value
        super().__init__(**kwargs)


class LayeredMaterial(MaterialProperty):
    """分层材料，在不同区域有不同属性值，平滑过渡"""
    
    def __init__(self, layers, transition_width=0.02, **kwargs):
        """
        初始化分层材料
        
        参数:
            layers: 图层列表，每个元素为 (z_position, value) 元组
            transition_width: 层间过渡宽度
        """
        self.layers = sorted(layers, key=lambda x: x[0])
        self.transition_width = transition_width
        super().__init__(layers[0][1], **kwargs)
    
    def eval(self, value, x):
        z = x[0]  # 默认x方向为层方向
        values = np.array([v for (z0, v) in self.layers])
        positions = np.array([z0 for (z0, v) in self.layers])
        
        if z <= positions[0]:
            value[0] = values[0]
        elif z >= positions[-1]:
            value[0] = values[-1]
        else:
            idx = np.searchsorted(positions, z) - 1
            z0, v0 = self.layers[idx]
            z1, v1 = self.layers[idx + 1]
            
            dz = z1 - z0
            t = (z - z0) / dz
            
            t_smooth = 0.5 * (1 + np.tanh((t - 0.5) * dz / self.transition_width))
            value[0] = v0 + (v1 - v0) * t_smooth


class GaussianInclusionMaterial(MaterialProperty):
    """高斯分布夹杂材料"""
    
    def __init__(self, base_value, inclusions, **kwargs):
        """
        初始化高斯夹杂材料
        
        参数:
            base_value: 基体材料属性
            inclusions: 夹杂列表，每个元素为 (center, radius, value) 元组
        """
        self.inclusions = inclusions
        super().__init__(base_value, **kwargs)
    
    def eval(self, value, x):
        val = self.base_value
        for center, radius, inc_value in self.inclusions:
            dist2 = sum((xi - ci)**2 for xi, ci in zip(x, center))
            factor = np.exp(-dist2 / (2 * radius**2))
            val = val + (inc_value - self.base_value) * factor
        value[0] = val


class FunctionGradientMaterial(MaterialProperty):
    """功能梯度材料，使用解析函数定义属性变化"""
    
    def __init__(self, gradient_func, **kwargs):
        """
        初始化功能梯度材料
        
        参数:
            gradient_func: 返回属性值的函数 f(x)
        """
        self.gradient_func = gradient_func
        super().__init__(0.0, **kwargs)
    
    def eval(self, value, x):
        value[0] = self.gradient_func(x)


def create_homogeneous_material(value):
    """创建均质材料"""
    return Constant(value)


def create_layered_conductivity(layers, transition_width=0.02):
    """创建分层热传导系数"""
    return LayeredMaterial(layers, transition_width, degree=2)


def create_functionally_graded_conductivity(func):
    """创建功能梯度热传导系数"""
    return FunctionGradientMaterial(func, degree=2)


def create_inclusion_material(base_value, inclusions):
    """创建带夹杂的材料属性"""
    return GaussianInclusionMaterial(base_value, inclusions, degree=2)


def interpolate_material_to_function(material_expr, V):
    """将材料属性表达式插值到有限元函数空间，确保单元积分正确"""
    material_func = Function(V)
    material_func.interpolate(material_expr)
    return material_func


class ThermalMaterial:
    """热传导材料属性集合"""
    
    def __init__(self, conductivity, specific_heat=1.0, density=1.0):
        """
        初始化热材料属性
        
        参数:
            conductivity: 热传导系数 k(x)
            specific_heat: 比热容 c(x)
            density: 密度 ρ(x)
        """
        self.conductivity = conductivity
        self.specific_heat = specific_heat
        self.density = density
    
    def get_diffusivity(self):
        """计算热扩散系数 α = k/(ρc)"""
        if isinstance(self.conductivity, (float, int)) and \
           isinstance(self.specific_heat, (float, int)) and \
           isinstance(self.density, (float, int)):
            return self.conductivity / (self.density * self.specific_heat)
        else:
            return self.conductivity / (self.density * self.specific_heat)
    
    def interpolate_to_space(self, V):
        """将材料属性插值到函数空间"""
        if hasattr(self.conductivity, 'eval'):
            self.k_func = interpolate_material_to_function(self.conductivity, V)
        else:
            self.k_func = self.conductivity
        
        if hasattr(self.specific_heat, 'eval'):
            self.c_func = interpolate_material_to_function(self.specific_heat, V)
        else:
            self.c_func = self.specific_heat
        
        if hasattr(self.density, 'eval'):
            self.rho_func = interpolate_material_to_function(self.density, V)
        else:
            self.rho_func = self.density
        
        return self
