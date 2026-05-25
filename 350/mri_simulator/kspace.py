"""
K空间模块
处理K空间数据的填充、采样、和操作
"""

import numpy as np
from scipy.ndimage import gaussian_filter


class KSpace:
    """K空间数据处理类"""

    def __init__(self, matrix_size=(128, 128)):
        """
        初始化K空间
        
        Parameters:
            matrix_size: K空间矩阵大小 (Ny, Nx)
        """
        self.matrix_size = matrix_size
        self.data = np.zeros(matrix_size, dtype=np.complex128)
        self.mask = np.ones(matrix_size, dtype=np.bool_)

    def fill(self, ky_idx, kx_data):
        """
        填充K空间的一行
        
        Parameters:
            ky_idx: ky线索引
            kx_data: kx方向的数据
        """
        if ky_idx < 0 or ky_idx >= self.matrix_size[0]:
            raise ValueError(f"ky索引超出范围: {ky_idx}")
        self.data[ky_idx, :] = kx_data

    def fill_cartesian(self, kspace_data):
        """
        填充完整的笛卡尔K空间数据
        
        Parameters:
            kspace_data: K空间数据
        """
        if kspace_data.shape != self.matrix_size:
            raise ValueError(f"数据形状不匹配: {kspace_data.shape} != {self.matrix_size}")
        self.data = kspace_data.copy()

    def apply_mask(self, mask):
        """
        应用K空间采样掩码
        
        Parameters:
            mask: 采样掩码 (与K空间同大小的布尔数组)
        """
        if mask.shape != self.matrix_size:
            raise ValueError(f"掩码形状不匹配")
        self.mask = mask
        self.data = self.data * mask

    def generate_cartesian_mask(self, acceleration=1, center_fraction=0.1):
        """
        生成笛卡尔欠采样掩码(并行成像用)
        
        Parameters:
            acceleration: 加速因子 R
            center_fraction: 中心区域采样比例
        
        Returns:
            采样掩码
        """
        Ny, Nx = self.matrix_size
        mask = np.zeros((Ny, Nx), dtype=np.bool_)

        center_lines = int(Ny * center_fraction)
        center_start = (Ny - center_lines) // 2
        center_end = center_start + center_lines

        mask[center_start:center_end, :] = True

        for ky in range(0, Ny, acceleration):
            if ky < center_start or ky >= center_end:
                mask[ky, :] = True

        self.mask = mask
        return mask

    def generate_random_mask(self, acceleration=1, center_fraction=0.08):
        """
        生成随机欠采样掩码(压缩传感用)
        
        Parameters:
            acceleration: 加速因子 R
            center_fraction: 中心区域采样比例
        
        Returns:
            采样掩码
        """
        Ny, Nx = self.matrix_size
        mask = np.zeros((Ny, Nx), dtype=np.bool_)

        center_lines = int(Ny * center_fraction)
        center_start = (Ny - center_lines) // 2
        center_end = center_start + center_lines

        mask[center_start:center_end, :] = True

        num_samples = int(Ny / acceleration) - center_lines
        num_samples = max(0, num_samples)

        outer_ky = np.concatenate([np.arange(0, center_start), np.arange(center_end, Ny)])
        if len(outer_ky) > 0 and num_samples > 0:
            weights = np.exp(-np.abs(outer_ky - Ny / 2) ** 2 / (2 * (Ny / 6) ** 2))
            weights = weights / np.sum(weights)
            selected = np.random.choice(outer_ky, size=num_samples, replace=False, p=weights)
            mask[selected, :] = True

        self.mask = mask
        return mask

    def add_noise(self, snr=30.0):
        """
        添加高斯白噪声
        
        Parameters:
            snr: 信噪比 (dB)
        
        噪声按照以下公式计算: 
        noise_level = max_signal / (10^(SNR/20))
        """
        signal_power = np.mean(np.abs(self.data) ** 2)
        noise_power = signal_power / (10 ** (snr / 10.0))
        noise_std = np.sqrt(noise_power / 2.0)

        noise = noise_std * (np.random.randn(*self.matrix_size) +
                         1j * np.random.randn(*self.matrix_size))

        self.data = self.data + noise

        return noise

    def zero_fill(self):
        """
        零填充K空间以增加图像矩阵大小
        
        Returns:
            零填充后的K空间
        """
        return self.data

    def get_phase(self):
        """获取K空间相位"""
        return np.angle(self.data)

    def get_magnitude(self):
        """获取K空间幅度"""
        return np.abs(self.data)

    def fftshift(self):
        """对K空间进行fftshift"""
        self.data = np.fft.fftshift(self.data)
        return self.data

    def ifftshift(self):
        """对K空间进行ifftshift"""
        self.data = np.fft.ifftshift(self.data)
        return self.data

    def get_data(self):
        """获取K空间数据"""
        return self.data.copy()

    def get_sampling_pattern(self):
        """获取采样模式"""
        return self.mask.copy()

    def calculate_sampling_efficiency(self):
        """计算采样效率(已采样点/总点数)"""
        return np.sum(self.mask) / np.prod(self.matrix_size)

    def save(self, filename):
        """
        保存K空间数据到文件
        
        Parameters:
            filename: 文件名
        """
        np.save(filename, self.data)

    def load(self, filename):
        """
        从文件加载K空间数据
        
        Parameters:
            filename: 文件名
        """
        self.data = np.load(filename)
        self.matrix_size = self.data.shape

    def plot_sampling_pattern(self):
        """绘制采样模式"""
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(self.mask, cmap='gray', interpolation='nearest')
        ax.set_title('K空间采样模式')
        ax.set_xlabel('kx')
        ax.set_ylabel('ky')
        return fig


def generate_kspace_trajectory_cartesian(matrix_size=(128, 128), fov=(0.256, 0.256)):
    """
    生成笛卡尔K空间轨迹坐标
    
    Parameters:
        matrix_size: 矩阵大小 (Ny, Nx)
        fov: 视场大小 (米)
    
    Returns:
        (kx, ky) 坐标数组
    """
    Ny, Nx = matrix_size
    dkx = 1.0 / fov[1]
    dky = 1.0 / fov[0]

    kx = np.arange(Nx) * dkx - Nx * dkx / 2.0
    ky = np.arange(Ny) * dky - Ny * dky / 2.0

    kx_grid, ky_grid = np.meshgrid(kx, ky)

    return kx_grid, ky_grid


def generate_kspace_trajectory_radial(num_spokes=64, num_points=256, fov=(0.256, 0.256)):
    """
    生成放射状K空间轨迹
    
    Parameters:
        num_spokes: 射线数量
        num_points: 每条射线上的点数
        fov: 视场大小 (米)
    
    Returns:
        (kx, ky) 坐标数组, 形状为 (num_spokes, num_points)
    """
    k_max = 1.0 / (2.0 * min(fov) / 2.0)

    angles = np.linspace(0, np.pi, num_spokes, endpoint=False)
    radii = np.linspace(0, k_max, num_points)

    kx = np.zeros((num_spokes, num_points))
    ky = np.zeros((num_spokes, num_points))

    for i, angle in enumerate(angles):
        kx[i, :] = radii * np.cos(angle)
        ky[i, :] = radii * np.sin(angle)

    return kx, ky


def generate_kspace_trajectory_spiral(num_arms=8, num_points=512, fov=(0.256, 0.256)):
    """
    生成螺旋K空间轨迹
    
    Parameters:
        num_arms: 螺旋臂数量
        num_points: 每臂的点数
        fov: 视场大小 (米)
    
    Returns:
        (kx, ky) 坐标数组, 形状为 (num_arms, num_points)
    """
    k_max = 1.0 / (2.0 * min(fov) / 2.0)

    kx = np.zeros((num_arms, num_points))
    ky = np.zeros((num_arms, num_points))

    for arm in range(num_arms):
        theta0 = 2 * np.pi * arm / num_arms
        theta = np.linspace(0, 6 * np.pi, num_points) + theta0
        r = np.linspace(0, k_max, num_points)

        kx[arm, :] = r * np.cos(theta)
        ky[arm, :] = r * np.sin(theta)

    return kx, ky
