from dolfin import *
import numpy as np


class NonlinearMaterial:
    """非线性材料基类"""
    
    def __init__(self):
        self.history = {}
    
    def sigma(self, epsilon):
        """计算应力"""
        raise NotImplementedError
    
    def tangent(self, epsilon):
        """计算切线刚度"""
        raise NotImplementedError


class ElasticMaterial(NonlinearMaterial):
    """线弹性材料"""
    
    def __init__(self, E, nu):
        super().__init__()
        self.E = E
        self.nu = nu
        self.mu = E / (2 * (1 + nu))
        self.lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))
    
    def sigma(self, epsilon):
        """胡克定律"""
        dim = epsilon.ufl_shape[0] if hasattr(epsilon, 'ufl_shape') else 2
        trace_eps = tr(epsilon)
        I = Identity(dim)
        return 2 * self.mu * epsilon + self.lmbda * trace_eps * I
    
    def tangent(self, epsilon):
        """弹性切线刚度（常数）"""
        return lambda eps: self.sigma(eps)


class PerfectPlasticMaterial(NonlinearMaterial):
    """理想弹塑性材料（Von Mises屈服准则）"""
    
    def __init__(self, E, nu, sigma_y):
        super().__init__()
        self.E = E
        self.nu = nu
        self.sigma_y = sigma_y
        self.mu = E / (2 * (1 + nu))
        self.lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))
    
    def sigma(self, epsilon):
        """理想弹塑性本构"""
        dim = epsilon.ufl_shape[0] if hasattr(epsilon, 'ufl_shape') else 2
        I = Identity(dim)
        
        sigma_el = 2 * self.mu * epsilon + self.lmbda * tr(epsilon) * I
        
        dev_sigma = sigma_el - (1/dim) * tr(sigma_el) * I
        sigma_von_mises = sqrt(3/2 * inner(dev_sigma, dev_sigma))
        
        return conditional(
            lt(sigma_von_mises, self.sigma_y),
            sigma_el,
            self.sigma_y * dev_sigma / conditional(eq(sigma_von_mises, 0), 1e-10, sigma_von_mises)
        )
    
    def tangent(self, epsilon):
        """弹塑性切线刚度"""
        dim = epsilon.ufl_shape[0] if hasattr(epsilon, 'ufl_shape') else 2
        I = Identity(dim)
        
        sigma_el = 2 * self.mu * epsilon + self.lmbda * tr(epsilon) * I
        dev_sigma = sigma_el - (1/dim) * tr(sigma_el) * I
        sigma_von_mises = sqrt(3/2 * inner(dev_sigma, dev_sigma))
        
        def tangent_func(eps):
            sigma = self.sigma(eps)
            dev_sigma = sigma - (1/dim) * tr(sigma) * I
            sigma_eq = sqrt(3/2 * inner(dev_sigma, dev_sigma))
            
            elastic_tangent = 2 * self.mu * I + self.lmbda * outer(I, I)
            
            plastic_factor = conditional(
                lt(sigma_eq, self.sigma_y),
                0.0,
                3 * self.mu / (3 * self.mu + 1e-10)
            )
            
            return elastic_tangent
        
        return tangent_func


class HardeningPlasticMaterial(NonlinearMaterial):
    """硬化弹塑性材料（各向同性硬化）"""
    
    def __init__(self, E, nu, sigma_y0, H):
        super().__init__()
        self.E = E
        self.nu = nu
        self.sigma_y0 = sigma_y0
        self.H = H
        self.mu = E / (2 * (1 + nu))
        self.lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))
        self.epsilon_p = None
    
    def sigma(self, epsilon):
        """带硬化的弹塑性本构"""
        dim = epsilon.ufl_shape[0] if hasattr(epsilon, 'ufl_shape') else 2
        I = Identity(dim)
        
        if self.epsilon_p is None:
            self.epsilon_p = Function(FunctionSpace(epsilon.function_space().mesh(), "DG", 0))
        
        sigma_el = 2 * self.mu * (epsilon - self.epsilon_p) + self.lmbda * tr(epsilon - self.epsilon_p) * I
        
        dev_sigma = sigma_el - (1/dim) * tr(sigma_el) * I
        sigma_von_mises = sqrt(3/2 * inner(dev_sigma, dev_sigma))
        
        sigma_y = self.sigma_y0 + self.H * sqrt(2/3 * inner(self.epsilon_p, self.epsilon_p))
        
        return conditional(
            lt(sigma_von_mises, sigma_y),
            sigma_el,
            sigma_y * dev_sigma / conditional(eq(sigma_von_mises, 0), 1e-10, sigma_von_mises)
        )


class RambergOsgoodMaterial(NonlinearMaterial):
    """Ramberg-Osgood非线性弹性材料"""
    
    def __init__(self, E, nu, alpha, n):
        super().__init__()
        self.E = E
        self.nu = nu
        self.alpha = alpha
        self.n = n
        self.mu = E / (2 * (1 + nu))
        self.lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))
    
    def sigma(self, epsilon):
        """Ramberg-Osgood本构"""
        dim = epsilon.ufl_shape[0] if hasattr(epsilon, 'ufl_shape') else 2
        I = Identity(dim)
        
        sigma_el = 2 * self.mu * epsilon + self.lmbda * tr(epsilon) * I
        
        dev_sigma = sigma_el - (1/dim) * tr(sigma_el) * I
        sigma_von_mises = sqrt(3/2 * inner(dev_sigma, dev_sigma))
        
        epsilon_eq = sigma_von_mises / self.E + self.alpha * (sigma_von_mises / self.E) ** self.n
        
        factor = conditional(eq(epsilon_eq, 0), 1.0, sigma_von_mises / epsilon_eq / self.E)
        
        return factor * sigma_el


class ViscoPlasticMaterial(NonlinearMaterial):
    """粘塑性材料（Perzyna模型）"""
    
    def __init__(self, E, nu, sigma_y, eta, n):
        super().__init__()
        self.E = E
        self.nu = nu
        self.sigma_y = sigma_y
        self.eta = eta
        self.n = n
        self.mu = E / (2 * (1 + nu))
        self.lmbda = E * nu / ((1 + nu) * (1 - 2 * nu))
    
    def sigma(self, epsilon, epsilon_dot, dt):
        """Perzyna粘塑性本构"""
        dim = epsilon.ufl_shape[0] if hasattr(epsilon, 'ufl_shape') else 2
        I = Identity(dim)
        
        sigma_el = 2 * self.mu * epsilon + self.lmbda * tr(epsilon) * I
        
        dev_sigma = sigma_el - (1/dim) * tr(sigma_el) * I
        sigma_von_mises = sqrt(3/2 * inner(dev_sigma, dev_sigma))
        
        phi = conditional(
            lt(sigma_von_mises, self.sigma_y),
            0.0,
            ((sigma_von_mises - self.sigma_y) / self.eta) ** self.n
        )
        
        epsilon_p_dot = (3/2) * phi * dev_sigma / conditional(eq(sigma_von_mises, 0), 1e-10, sigma_von_mises)
        
        return sigma_el - dt * (self.mu * epsilon_p_dot + 0.5 * self.lmbda * tr(epsilon_p_dot) * I)


class NonlinearThermalMaterial:
    """非线性热材料属性"""
    
    def __init__(self, k_func=None, rho_c_func=None):
        """
        初始化非线性热材料
        
        参数:
            k_func: 热传导系数函数 k(T)
            rho_c_func: 体积热容函数 ρc(T)
        """
        self.k_func = k_func
        self.rho_c_func = rho_c_func
    
    def conductivity(self, T):
        """获取温度相关的热传导系数"""
        if self.k_func is None:
            return Constant(1.0)
        return self.k_func(T)
    
    def rho_c(self, T):
        """获取温度相关的体积热容"""
        if self.rho_c_func is None:
            return Constant(1.0)
        return self.rho_c_func(T)


class TemperatureDependentConductivity:
    """温度相关的热传导系数"""
    
    def __init__(self, k0, alpha_k=0.0):
        self.k0 = k0
        self.alpha_k = alpha_k
    
    def __call__(self, T):
        return self.k0 * (1 + self.alpha_k * T)


class PhaseChangeMaterial:
    """相变材料（焓法）"""
    
    def __init__(self, k_solid, k_liquid, rho_c_solid, rho_c_liquid,
                 T_m, L, delta_T=1.0):
        self.k_solid = k_solid
        self.k_liquid = k_liquid
        self.rho_c_solid = rho_c_solid
        self.rho_c_liquid = rho_c_liquid
        self.T_m = T_m
        self.L = L
        self.delta_T = delta_T
    
    def conductivity(self, T):
        """相变区间平滑过渡的热传导系数"""
        def smooth_transition(x):
            return 0.5 * (1 + tanh(x / self.delta_T))
        
        alpha = smooth_transition(T - self.T_m)
        return self.k_solid * (1 - alpha) + self.k_liquid * alpha
    
    def rho_c(self, T):
        """体积热容（含潜热贡献）"""
        def gaussian(x):
            return exp(-x**2 / (2 * self.delta_T**2)) / sqrt(2 * pi * self.delta_T**2)
        
        base = self.rho_c_solid + (self.rho_c_liquid - self.rho_c_solid) * \
               0.5 * (1 + tanh((T - self.T_m) / self.delta_T))
        
        latent_heat = self.L * gaussian(T - self.T_m)
        
        return base + latent_heat
