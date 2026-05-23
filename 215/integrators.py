import importlib.util

if importlib.util.find_spec("cupy") is not None:
    import cupy as np
    GPU_AVAILABLE = True
else:
    import numpy as np
    GPU_AVAILABLE = False


class VerletIntegrator:
    """
    Velocity Verlet积分器 (先速度后位置顺序)
    
    算法 (正确的时间可逆顺序):
        1. v(t+dt/2) = v(t) + 0.5 * a(t) * dt      (更新半步速度)
        2. r(t+dt) = r(t) + v(t+dt/2) * dt         (更新位置)
        3. 计算新力 F(t+dt), 得到 a(t+dt)
        4. v(t+dt) = v(t+dt/2) + 0.5 * a(t+dt) * dt (完成速度更新)
    """
    
    def __init__(self, dt, use_gpu=False):
        """
        初始化Verlet积分器
        
        参数:
            dt: 时间步长
            use_gpu: 是否使用GPU加速
        """
        self.dt = dt
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
    def step(self, positions, velocities, forces, mass=1.0):
        """
        执行前半步积分: 先更新半步速度，再更新位置
        
        参数:
            positions: 位置 r(t) (N, dim)
            velocities: 速度 v(t) (N, dim)
            forces: 力 F(t) (N, dim)
            mass: 粒子质量
        
        返回:
            new_positions: 新位置 r(t+dt) (N, dim)
            half_velocities: 半步速度 v(t+dt/2) (N, dim)
        """
        dt = self.dt
        half_velocities = velocities + 0.5 * forces / mass * dt
        new_positions = positions + half_velocities * dt
        return new_positions, half_velocities
    
    def finalize_velocity(self, half_velocities, new_forces, mass=1.0):
        """
        使用新位置处的力完成速度更新
        
        参数:
            half_velocities: 半步速度 v(t+dt/2) (N, dim)
            new_forces: 新位置处的力 F(t+dt) (N, dim)
            mass: 粒子质量
        
        返回:
            new_velocities: 完整速度 v(t+dt) (N, dim)
        """
        new_velocities = half_velocities + 0.5 * new_forces / mass * self.dt
        return new_velocities


class LangevinIntegrator:
    """
    Langevin动力学积分器 (NVT系综)
    用于温度控制
    """
    
    def __init__(self, dt, temperature, gamma=1.0, use_gpu=False):
        """
        初始化Langevin积分器
        
        参数:
            dt: 时间步长
            temperature: 目标温度
            gamma: 摩擦系数
            use_gpu: 是否使用GPU加速
        """
        self.dt = dt
        self.temperature = temperature
        self.gamma = gamma
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
    def step(self, positions, velocities, forces, mass=1.0):
        """
        执行Langevin积分步
        
        参数:
            positions: 位置 (N, dim)
            velocities: 速度 (N, dim)
            forces: 力 (N, dim)
            mass: 粒子质量
        
        返回:
            new_positions: 新位置
            new_velocities: 新速度
        """
        dt = self.dt
        gamma = self.gamma
        T = self.temperature
        
        n_particles, dim = positions.shape
        
        # 随机力 (高斯白噪声)
        if self.use_gpu:
            xi = np.random.randn(n_particles, dim)
        else:
            xi = np.random.randn(n_particles, dim)
        
        sigma = np.sqrt(2.0 * gamma * T * dt / mass)
        
        # 简化的BAOAB格式
        v_half = velocities + 0.5 * dt * (forces / mass - gamma * velocities)
        new_positions = positions + v_half * dt
        v_half += sigma * xi
        new_velocities = (v_half + 0.5 * dt * forces / mass) / (1.0 + 0.5 * dt * gamma)
        
        return new_positions, new_velocities


class BerendsenThermostat:
    """
    Berendsen恒温热浴
    
    通过速度缩放将系统温度耦合到外部热浴:
    v_i(t+dt) = v_i(t) * lambda
    lambda = sqrt(1 + dt/tau * (T_target/T_current - 1))
    
    参数:
        temperature: 目标温度
        tau: 耦合时间常数 (越大越温和)
    """
    
    def __init__(self, temperature, tau=0.1, use_gpu=False):
        """
        初始化Berendsen恒温器
        
        参数:
            temperature: 目标温度
            tau: 耦合时间常数 (约化时间单位)
            use_gpu: 是否使用GPU
        """
        self.target_temperature = temperature
        self.tau = tau
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.current_lambda = 1.0
        
    def apply(self, velocities, dt, current_temperature):
        """
        应用Berendsen热浴，缩放速度以调节温度
        
        参数:
            velocities: 当前速度 (N, dim)
            dt: 时间步长
            current_temperature: 当前温度
        
        返回:
            scaled_velocities: 缩放后的速度
        """
        if current_temperature > 0:
            self.current_lambda = np.sqrt(
                1.0 + (dt / self.tau) * (self.target_temperature / current_temperature - 1.0)
            )
        else:
            self.current_lambda = 1.0
        
        return velocities * self.current_lambda
    
    def get_lambda(self):
        """获取上次使用的缩放因子"""
        return self.current_lambda


def velocity_verlet_step(positions, velocities, forces, dt, mass=1.0):
    """
    函数式Velocity Verlet积分 (单步)
    
    参数:
        positions: 位置 (N, dim)
        velocities: 速度 (N, dim)
        forces: 力 (N, dim)
        dt: 时间步长
        mass: 粒子质量
    
    返回:
        new_positions: 新位置
        half_velocities: 半步速度
    """
    new_positions = positions + velocities * dt + 0.5 * forces / mass * dt ** 2
    half_velocities = velocities + 0.5 * forces / mass * dt
    return new_positions, half_velocities


def velocity_verlet_finalize(half_velocities, new_forces, dt, mass=1.0):
    """
    函数式Velocity Verlet速度更新
    
    参数:
        half_velocities: 半步速度 (N, dim)
        new_forces: 新位置处的力 (N, dim)
        dt: 时间步长
        mass: 粒子质量
    
    返回:
        new_velocities: 新速度
    """
    return half_velocities + 0.5 * new_forces / mass * dt
