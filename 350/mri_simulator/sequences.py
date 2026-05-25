"""
MRI脉冲序列模块
实现多种MRI脉冲序列：自旋回波(SE)、梯度回波(GRE)、反转恢复(IR)

正确的K空间梯度轨迹公式：
k(t) = γ ∫₀ᵗ G(τ) dτ

对于笛卡尔采样：
- k空间步长: Δk = 1/FOV
- 梯度面积: Area = k/γ = (n * Δk)/γ = n / (γ * FOV)
- 梯度幅度与持续时间乘积: G * T = n / (γ * FOV)
"""

import numpy as np

GAMMA_RAD = 42.576e6 * 2 * np.pi


class PulseSequence:
    """脉冲序列基类"""

    def __init__(self, tr=1.0, te=0.05, matrix_size=(128, 128), fov=(0.256, 0.256)):
        """
        初始化脉冲序列
        
        Parameters:
            tr: 重复时间 (秒)
            te: 回波时间 (秒)
            matrix_size: K空间矩阵大小 (Ny, Nx)
            fov: 视场大小 (米, FOV_y, FOV_x)
        """
        self.tr = tr
        self.te = te
        self.matrix_size = matrix_size
        self.fov = fov

        Ny, Nx = matrix_size
        FOVy, FOVx = fov

        self.delta_kx = 1.0 / FOVx
        self.delta_ky = 1.0 / FOVy

        self.kx_max = (Nx / 2.0) * self.delta_kx
        self.ky_max = (Ny / 2.0) * self.delta_ky

        self.kx = np.linspace(-self.kx_max, self.kx_max, Nx)
        self.ky = np.linspace(-self.ky_max, self.ky_max, Ny)

        self.acq_time = 0.01

        self.gx_readout = Nx / (GAMMA_RAD * FOVx * self.acq_time)

        self.adc_samples = Nx
        self.dwell_time = self.acq_time / Nx

        self.kspace = np.zeros(matrix_size, dtype=np.complex128)

    def calculate_phase_encoding_area(self, ky_idx):
        """
        计算相位编码梯度面积
        
        Parameters:
            ky_idx: ky线索引
            
        Returns:
            梯度面积 (G * T) = ky / γ
        """
        Ny = self.matrix_size[0]
        ky_value = (ky_idx - Ny / 2.0) * self.delta_ky
        return ky_value / GAMMA_RAD

    def calculate_phase_encoding_amplitude(self, ky_idx, duration):
        """
        计算指定持续时间的相位编码梯度幅度
        
        Parameters:
            ky_idx: ky线索引
            duration: 梯度持续时间 (秒)
            
        Returns:
            梯度幅度 (T/m)
        """
        area = self.calculate_phase_encoding_area(ky_idx)
        return area / duration if duration > 0 else 0.0

    def get_kspace_trajectory(self):
        """获取K空间轨迹"""
        return self.kx, self.ky

    def calculate_readout_gradient(self):
        """
        计算读出梯度幅度
        
        Returns:
            读出梯度幅度 (T/m)
        """
        return self.gx_readout


class SpinEcho(PulseSequence):
    """
    自旋回波(Spin Echo, SE)序列
    90°激发脉冲 -> TE/2 演化 + 相位编码 -> 180°重聚脉冲 -> TE/2 演化 -> 读出梯度 + 采集
    """

    def __init__(self, tr=1.0, te=0.05, matrix_size=(128, 128), fov=(0.256, 0.256)):
        super().__init__(tr, te, matrix_size, fov)
        self.alpha_exc = np.pi / 2
        self.alpha_refoc = np.pi
        self.phase_encode_duration = te / 4.0

    def simulate(self, solver, phantom, use_gpu=False):
        """
        模拟自旋回波序列
        
        Parameters:
            solver: Bloch求解器 (BlochSolver 或 BlochSolverGPU)
            phantom: Phantom对象
            use_gpu: 是否使用GPU加速
        
        Returns:
            填充后的K空间数据
        """
        pd, t1, t2 = phantom.get_voxel_params()
        x, y = phantom.get_positions()

        if use_gpu:
            solver.set_params(pd, t1, t2)
            solver.set_positions(x, y)
        else:
            solver.set_params(pd, t1, t2)

        Ny, Nx = self.matrix_size
        tau = self.te / 2.0

        for ky_idx in range(Ny):
            solver.reset_magnetization()

            gy_phase = self.calculate_phase_encoding_amplitude(ky_idx, self.phase_encode_duration)

            if not use_gpu:
                solver.apply_excitation(self.alpha_exc, 0.0)
                solver.evolve(self.phase_encode_duration, 0.0, gy_phase, x, y)
                solver.evolve(tau - self.phase_encode_duration, 0.0, 0.0, x, y)
                solver.apply_excitation(self.alpha_refoc, np.pi / 2.0)
                solver.evolve(tau, 0.0, 0.0, x, y)

                for kx_idx in range(Nx):
                    if kx_idx > 0:
                        solver.evolve(self.dwell_time, self.gx_readout, 0.0, x, y)
                    signal = solver.get_signal()
                    self.kspace[ky_idx, kx_idx] = signal
            else:
                solver.apply_excitation(self.alpha_exc, 0.0)
                solver.evolve(self.phase_encode_duration, 0.0, gy_phase)
                solver.evolve(tau - self.phase_encode_duration, 0.0, 0.0)
                solver.apply_excitation(self.alpha_refoc, np.pi / 2.0)
                solver.evolve(tau, 0.0, 0.0)

                kspace_line = solver.acquire_kspace_line(Nx, self.dwell_time, self.gx_readout)
                self.kspace[ky_idx, :] = kspace_line

            tr_remaining = self.tr - self.te - self.acq_time
            if tr_remaining > 0:
                if use_gpu:
                    solver.evolve(tr_remaining, 0.0, 0.0)
                else:
                    solver.evolve(tr_remaining, 0.0, 0.0, x, y)

        return self.kspace

    def get_sequence_name(self):
        return "Spin Echo"


class GradientEcho(PulseSequence):
    """
    梯度回波(Gradient Echo, GRE/FLASH)序列
    alpha°激发脉冲 -> 相位编码 -> 读出梯度反转形成回波 -> 采集
    """

    def __init__(self, tr=0.05, te=0.01, flip_angle=np.pi / 6, matrix_size=(128, 128), fov=(0.256, 0.256)):
        super().__init__(tr, te, matrix_size, fov)
        self.alpha = flip_angle
        self.phase_encode_duration = te / 2.0

    def simulate(self, solver, phantom, use_gpu=False):
        """
        模拟梯度回波序列
        
        Parameters:
            solver: Bloch求解器
            phantom: Phantom对象
            use_gpu: 是否使用GPU加速
        
        Returns:
            填充后的K空间数据
        """
        pd, t1, t2 = phantom.get_voxel_params()
        x, y = phantom.get_positions()

        if use_gpu:
            solver.set_params(pd, t1, t2)
            solver.set_positions(x, y)
        else:
            solver.set_params(pd, t1, t2)

        Ny, Nx = self.matrix_size

        for ky_idx in range(Ny):
            if ky_idx > 0:
                if use_gpu:
                    solver.evolve(self.tr, 0.0, 0.0)
                else:
                    solver.evolve(self.tr, 0.0, 0.0, x, y)

            gy_phase = self.calculate_phase_encoding_amplitude(ky_idx, self.phase_encode_duration)

            if not use_gpu:
                solver.apply_excitation(self.alpha, 0.0)
                solver.evolve(self.phase_encode_duration, 0.0, gy_phase, x, y)
                solver.evolve(self.te - self.phase_encode_duration, 0.0, 0.0, x, y)

                for kx_idx in range(Nx):
                    if kx_idx > 0:
                        solver.evolve(self.dwell_time, self.gx_readout, 0.0, x, y)
                    signal = solver.get_signal()
                    self.kspace[ky_idx, kx_idx] = signal
            else:
                solver.apply_excitation(self.alpha, 0.0)
                solver.evolve(self.phase_encode_duration, 0.0, gy_phase)
                solver.evolve(self.te - self.phase_encode_duration, 0.0, 0.0)

                kspace_line = solver.acquire_kspace_line(Nx, self.dwell_time, self.gx_readout)
                self.kspace[ky_idx, :] = kspace_line

        return self.kspace

    def get_sequence_name(self):
        return "Gradient Echo"


class InversionRecovery(PulseSequence):
    """
    反转恢复(Inversion Recovery, IR)序列
    180°反转脉冲 -> TI -> 90°激发脉冲 -> 相位编码 -> 180°重聚 -> 采集
    """

    def __init__(self, tr=2.5, ti=0.5, te=0.05, matrix_size=(128, 128), fov=(0.256, 0.256)):
        super().__init__(tr, te, matrix_size, fov)
        self.ti = ti
        self.alpha_inv = np.pi
        self.alpha_exc = np.pi / 2
        self.alpha_refoc = np.pi
        self.phase_encode_duration = te / 4.0

    def simulate(self, solver, phantom, use_gpu=False):
        """
        模拟反转恢复序列
        
        Parameters:
            solver: Bloch求解器
            phantom: Phantom对象
            use_gpu: 是否使用GPU加速
        
        Returns:
            填充后的K空间数据
        """
        pd, t1, t2 = phantom.get_voxel_params()
        x, y = phantom.get_positions()

        if use_gpu:
            solver.set_params(pd, t1, t2)
            solver.set_positions(x, y)
        else:
            solver.set_params(pd, t1, t2)

        Ny, Nx = self.matrix_size
        tau = self.te / 2.0

        if not use_gpu:
            solver.apply_excitation(self.alpha_inv, 0.0)
            solver.evolve(self.ti, 0.0, 0.0, x, y)
        else:
            solver.apply_excitation(self.alpha_inv, 0.0)
            solver.evolve(self.ti, 0.0, 0.0)

        for ky_idx in range(Ny):
            gy_phase = self.calculate_phase_encoding_amplitude(ky_idx, self.phase_encode_duration)

            if not use_gpu:
                solver.apply_excitation(self.alpha_exc, 0.0)
                solver.evolve(self.phase_encode_duration, 0.0, gy_phase, x, y)
                solver.evolve(tau - self.phase_encode_duration, 0.0, 0.0, x, y)
                solver.apply_excitation(self.alpha_refoc, np.pi / 2)
                solver.evolve(tau, 0.0, 0.0, x, y)

                for kx_idx in range(Nx):
                    if kx_idx > 0:
                        solver.evolve(self.dwell_time, self.gx_readout, 0.0, x, y)
                    signal = solver.get_signal()
                    self.kspace[ky_idx, kx_idx] = signal

                tr_remaining = self.tr - self.te - self.acq_time
                if tr_remaining > 0:
                    solver.evolve(tr_remaining, 0.0, 0.0, x, y)
            else:
                solver.apply_excitation(self.alpha_exc, 0.0)
                solver.evolve(self.phase_encode_duration, 0.0, gy_phase)
                solver.evolve(tau - self.phase_encode_duration, 0.0, 0.0)
                solver.apply_excitation(self.alpha_refoc, np.pi / 2)
                solver.evolve(tau, 0.0, 0.0)

                kspace_line = solver.acquire_kspace_line(Nx, self.dwell_time, self.gx_readout)
                self.kspace[ky_idx, :] = kspace_line

                tr_remaining = self.tr - self.te - self.acq_time
                if tr_remaining > 0:
                    solver.evolve(tr_remaining, 0.0, 0.0)

        return self.kspace

    def get_sequence_name(self):
        return "Inversion Recovery"


class EchoPlanar(PulseSequence):
    """
    回波平面成像(Echo Planar Imaging, EPI)序列
    单次激发快速成像序列，连续采集多行K空间
    """

    def __init__(self, tr=3.0, te=0.04, matrix_size=(128, 128), fov=(0.256, 0.256)):
        super().__init__(tr, te, matrix_size, fov)
        self.alpha = np.pi / 2
        self.blip_duration = self.dwell_time * 2

    def simulate(self, solver, phantom, use_gpu=False):
        """
        模拟EPI序列
        
        Parameters:
            solver: Bloch求解器
            phantom: Phantom对象
            use_gpu: 是否使用GPU加速
        
        Returns:
            填充后的K空间数据
        """
        pd, t1, t2 = phantom.get_voxel_params()
        x, y = phantom.get_positions()

        if use_gpu:
            solver.set_params(pd, t1, t2)
            solver.set_positions(x, y)
        else:
            solver.set_params(pd, t1, t2)

        Ny, Nx = self.matrix_size

        if not use_gpu:
            solver.apply_excitation(self.alpha, 0.0)
            solver.evolve(self.te, 0.0, 0.0, x, y)
        else:
            solver.apply_excitation(self.alpha, 0.0)
            solver.evolve(self.te, 0.0, 0.0)

        direction = 1
        for ky_idx in range(Ny):
            if ky_idx > 0:
                gy_blip = self.calculate_phase_encoding_amplitude(1, self.blip_duration)
                if not use_gpu:
                    solver.evolve(self.blip_duration, 0.0, gy_blip, x, y)
                else:
                    solver.evolve(self.blip_duration, 0.0, gy_blip)

            gx_current = self.gx_readout * direction

            if not use_gpu:
                for kx_idx in range(Nx):
                    if kx_idx > 0:
                        solver.evolve(self.dwell_time, gx_current, 0.0, x, y)
                    signal = solver.get_signal()
                    self.kspace[ky_idx, kx_idx] = signal
            else:
                kspace_line = solver.acquire_kspace_line(Nx, self.dwell_time, gx_current)
                if direction == -1:
                    self.kspace[ky_idx, :] = kspace_line[::-1]
                else:
                    self.kspace[ky_idx, :] = kspace_line

            direction *= -1

        return self.kspace

    def get_sequence_name(self):
        return "Echo Planar Imaging"
