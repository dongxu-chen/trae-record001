import importlib.util
import time

if importlib.util.find_spec("cupy") is not None:
    import cupy as np
    GPU_AVAILABLE = True
else:
    import numpy as np
    GPU_AVAILABLE = False

from potentials import (
    get_potential_config, compute_potential_energy, compute_force_vector,
    lennard_jones_potential, lennard_jones_force_vector, tail_correction
)
from integrators import VerletIntegrator, BerendsenThermostat
from neighbor_list import NeighborList
from utils import (
    initialize_fcc, initialize_velocities, pbc_wrap, pbc_distance,
    pbc_wrap_to_positive, calculate_kinetic_energy, calculate_temperature,
    get_box_length, to_cpu
)
from trajectory import XYZWriter, ExtendedXYZWriter


class MolecularDynamics:
    """
    分子动力学模拟主类
    
    功能:
        - 多种势函数: Lennard-Jones, Morse, Coulomb
        - 周期性边界条件 (最近镜像法)
        - Verlet积分 (先速度后位置)
        - 邻居列表优化
        - Berendsen恒温热浴
        - XYZ格式轨迹输出
        - GPU加速 (CuPy可选)
    """
    
    def __init__(self, n_particles=100, temperature=1.0, density=0.8, 
                 dt=0.001, n_steps=10000, r_cut=2.5, r_skin=0.3,
                 dim=3, use_gpu=False, seed=None,
                 potential_type='lj', potential_config=None,
                 thermostat_enabled=False, thermostat_type='berendsen',
                 thermostat_tau=0.1, target_temperature=None):
        """
        初始化MD模拟
        
        参数:
            n_particles: 粒子数
            temperature: 初始温度 (约化单位)
            density: 数密度
            dt: 时间步长
            n_steps: 总模拟步数
            r_cut: 截断半径
            r_skin: 邻居列表皮肤层厚度
            dim: 维度 (2或3)
            use_gpu: 是否使用GPU加速
            seed: 随机种子
            potential_type: 势函数类型 ('lj', 'morse', 'coulomb')
            potential_config: 势函数配置字典
            thermostat_enabled: 是否启用恒温器
            thermostat_type: 恒温器类型 ('berendsen')
            thermostat_tau: Berendsen耦合时间
            target_temperature: 恒温器目标温度
        """
        self.n_particles = n_particles
        self.initial_temperature = temperature
        self.target_temperature = target_temperature if target_temperature else temperature
        self.density = density
        self.dt = dt
        self.n_steps = n_steps
        self.r_cut = r_cut
        self.r_skin = r_skin
        self.dim = dim
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.seed = seed
        
        self.potential_type = potential_type
        self.potential_config = potential_config or get_potential_config(
            potential_type, r_cut=r_cut
        )
        
        self.thermostat_enabled = thermostat_enabled
        self.thermostat_type = thermostat_type
        self.thermostat_tau = thermostat_tau
        self.thermostat = None
        
        self.box_length = get_box_length(n_particles, density, dim)
        
        self.positions = None
        self.velocities = None
        self.forces = None
        
        self.integrator = None
        self.neighbor_list = None
        
        self.kinetic_energy = 0.0
        self.potential_energy = 0.0
        self.temperature = 0.0
        
        self.current_step = 0
        self.n_neighbor_updates = 0
        
        self.trajectory = []
        self.energy_history = []
        
        self.xyz_writer = None
        
        self._initialize_system()
        
    def _initialize_system(self):
        """初始化系统 - 位置、速度、力、积分器、邻居列表、恒温器"""
        self.positions = initialize_fcc(self.n_particles, self.box_length, self.dim)
        self.velocities = initialize_velocities(
            self.n_particles, self.initial_temperature, 
            self.dim, self.seed, self.use_gpu
        )
        
        if self.use_gpu:
            self.positions = np.array(self.positions)
            self.velocities = np.array(self.velocities)
        
        self.integrator = VerletIntegrator(self.dt, self.use_gpu)
        
        self.neighbor_list = NeighborList(
            self.r_cut, self.r_skin, self.box_length, self.use_gpu
        )
        self.neighbor_list.build(self.positions)
        self.n_neighbor_updates += 1
        
        if self.thermostat_enabled:
            if self.thermostat_type == 'berendsen':
                self.thermostat = BerendsenThermostat(
                    self.target_temperature, self.thermostat_tau, self.use_gpu
                )
        
        self.forces = self._compute_forces()
        self._update_thermodynamic()
        
    def _compute_forces(self):
        """
        计算所有粒子受到的力
        
        返回:
            forces: 力矩阵 (N, dim)
        """
        n_particles = self.positions.shape[0]
        forces = np.zeros_like(self.positions)
        potential_energy = 0.0
        
        for i in range(n_particles):
            neighbors = self.neighbor_list[i]
            
            if len(neighbors) == 0:
                continue
            
            dr = self.positions[neighbors] - self.positions[i]
            dr = pbc_distance(dr, self.box_length)
            r2 = np.sum(dr ** 2, axis=1)
            
            mask = r2 < self.r_cut ** 2
            if not np.any(mask):
                continue
            
            r2_masked = r2[mask]
            dr_masked = dr[mask]
            neighbors_masked = neighbors[mask]
            
            f_vec = compute_force_vector(dr_masked, r2_masked, self.potential_config)
            
            for j, fj in enumerate(f_vec):
                forces[i] += fj
                forces[neighbors_masked[j]] -= fj
            
            pe = compute_potential_energy(r2_masked, self.potential_config)
            potential_energy += np.sum(pe)
        
        self.potential_energy = potential_energy / 2.0
        
        return forces
    
    def _compute_forces_vectorized(self):
        """
        向量化版本的力计算 (GPU优化)
        
        返回:
            forces: 力矩阵 (N, dim)
        """
        n_particles = self.positions.shape[0]
        forces = np.zeros_like(self.positions)
        potential_energy = 0.0
        
        pairs_i = []
        pairs_j = []
        
        for i in range(n_particles):
            neighbors = self.neighbor_list[i]
            for j in neighbors:
                if j > i:
                    pairs_i.append(i)
                    pairs_j.append(j)
        
        if len(pairs_i) == 0:
            self.potential_energy = 0.0
            return forces
        
        pairs_i = np.array(pairs_i, dtype=np.int64)
        pairs_j = np.array(pairs_j, dtype=np.int64)
        
        dr = self.positions[pairs_j] - self.positions[pairs_i]
        dr = pbc_distance(dr, self.box_length)
        r2 = np.sum(dr ** 2, axis=1)
        
        mask = r2 < self.r_cut ** 2
        
        if np.any(mask):
            r2_masked = r2[mask]
            dr_masked = dr[mask]
            i_masked = pairs_i[mask]
            j_masked = pairs_j[mask]
            
            f_vec = compute_force_vector(dr_masked, r2_masked, self.potential_config)
            
            for k in range(len(i_masked)):
                forces[i_masked[k]] += f_vec[k]
                forces[j_masked[k]] -= f_vec[k]
            
            pe = compute_potential_energy(r2_masked, self.potential_config)
            potential_energy = np.sum(pe)
        
        self.potential_energy = potential_energy
        
        return forces
    
    def _update_thermodynamic(self):
        """更新热力学量"""
        self.kinetic_energy = calculate_kinetic_energy(self.velocities)
        self.temperature = calculate_temperature(self.velocities)
        if self.potential_type == 'lj':
            self.potential_energy += tail_correction(self.r_cut, self.density) * self.n_particles
    
    def step(self):
        """
        执行单步MD模拟 (修正后的正确流程)
        
        步骤:
        1. 检查邻居列表是否需要更新
        2. Verlet积分: 先更新半步速度，再更新位置
        3. 应用PBC边界条件 (最近镜像法)
        4. 计算新位置处的力
        5. 完成速度更新
        6. 应用恒温器 (如果启用)
        """
        if self.neighbor_list.need_update(self.positions):
            self.neighbor_list.build(self.positions)
            self.n_neighbor_updates += 1
        
        new_positions, half_velocities = self.integrator.step(
            self.positions, self.velocities, self.forces
        )
        
        new_positions = pbc_wrap_to_positive(new_positions, self.box_length)
        self.positions = new_positions
        
        new_forces = self._compute_forces_vectorized() if self.use_gpu else self._compute_forces()
        
        self.velocities = self.integrator.finalize_velocity(
            half_velocities, new_forces
        )
        
        if self.thermostat_enabled and self.thermostat is not None:
            self.velocities = self.thermostat.apply(
                self.velocities, self.dt, self.temperature
            )
        
        self.forces = new_forces
        self._update_thermodynamic()
        self.current_step += 1
    
    def run(self, output_interval=100, save_trajectory=False, 
            trajectory_file='trajectory.xyz', include_velocities=True,
            include_forces=False, element='Ar', verbose=True):
        """
        运行完整的模拟
        
        参数:
            output_interval: 输出间隔步数
            save_trajectory: 是否保存轨迹
            trajectory_file: 轨迹文件名
            include_velocities: 轨迹中是否包含速度
            include_forces: 轨迹中是否包含力
            element: 元素符号
            verbose: 是否打印输出
        
        返回:
            energy_history: 能量历史数据
        """
        if save_trajectory:
            self.xyz_writer = ExtendedXYZWriter(
                trajectory_file, element=element,
                include_velocities=include_velocities,
                include_forces=include_forces
            )
            self.xyz_writer.open()
            self.xyz_writer.write_frame(
                self.positions, self.velocities, self.forces,
                step=0, box_length=self.box_length,
                properties={'Temperature': f'{self.temperature:.4f}'}
            )
        
        if verbose:
            self._print_header()
            self._print_state(0)
        
        start_time = time.time()
        
        for step in range(1, self.n_steps + 1):
            self.step()
            
            if step % output_interval == 0:
                if save_trajectory and self.xyz_writer:
                    self.xyz_writer.write_frame(
                        self.positions, self.velocities, self.forces,
                        step=step, box_length=self.box_length,
                        properties={'Temperature': f'{self.temperature:.4f}'}
                    )
                
                self.energy_history.append({
                    'step': step,
                    'kinetic_energy': to_cpu(self.kinetic_energy),
                    'potential_energy': to_cpu(self.potential_energy),
                    'total_energy': to_cpu(self.kinetic_energy + self.potential_energy),
                    'temperature': to_cpu(self.temperature)
                })
                
                if verbose:
                    self._print_state(step)
        
        end_time = time.time()
        
        if self.xyz_writer:
            self.xyz_writer.close()
        
        if verbose:
            print(f"\n模拟完成! 总时间: {end_time - start_time:.2f}秒")
            print(f"邻居列表更新次数: {self.n_neighbor_updates}")
            print(f"平均每步耗时: {(end_time - start_time) / self.n_steps:.4f}毫秒")
            if save_trajectory:
                print(f"轨迹已保存到: {trajectory_file}")
        
        return self.energy_history
    
    def _print_header(self):
        """打印表头"""
        ptype_names = {'lj': 'Lennard-Jones', 'morse': 'Morse', 'coulomb': 'Coulomb'}
        pname = ptype_names.get(self.potential_type, self.potential_type)
        
        print("=" * 80)
        print(f"分子动力学模拟 - {pname}势系统")
        print(f"粒子数: {self.n_particles}, 温度: {self.target_temperature}, 密度: {self.density}")
        print(f"步长: {self.dt}, 总步数: {self.n_steps}, 截断半径: {self.r_cut}")
        print(f"使用GPU: {self.use_gpu}, 维度: {self.dim}D")
        if self.thermostat_enabled:
            print(f"恒温器: Berendsen, tau={self.thermostat_tau}, T_target={self.target_temperature}")
        print("=" * 80)
        print(f"{'步':>8} | {'动能':>12} | {'势能':>12} | {'总能':>12} | {'温度':>10}")
        print("-" * 80)
    
    def _print_state(self, step):
        """打印当前状态"""
        ke = to_cpu(self.kinetic_energy)
        pe = to_cpu(self.potential_energy)
        te = ke + pe
        temp = to_cpu(self.temperature)
        print(f"{step:>8d} | {ke:>12.4f} | {pe:>12.4f} | {te:>12.4f} | {temp:>10.4f}")
    
    def get_state(self):
        """获取当前系统状态"""
        return {
            'step': self.current_step,
            'positions': to_cpu(self.positions),
            'velocities': to_cpu(self.velocities),
            'forces': to_cpu(self.forces),
            'kinetic_energy': to_cpu(self.kinetic_energy),
            'potential_energy': to_cpu(self.potential_energy),
            'total_energy': to_cpu(self.kinetic_energy + self.potential_energy),
            'temperature': to_cpu(self.temperature),
            'box_length': self.box_length
        }
    
    def reset(self):
        """重置模拟"""
        self.current_step = 0
        self.trajectory = []
        self.energy_history = []
        self._initialize_system()
    
    def get_trajectory(self):
        """获取轨迹数据"""
        return self.trajectory
    
    def get_energy_history(self):
        """获取能量历史"""
        return self.energy_history
