"""
MRI图像重建模块
实现从K空间到图像空间的重建, 包括FFT、网格化重建、以及一些高级重建技术

高级功能: 
- 并行成像: SENSE (SENSitivity Encoding)、GRAPPA (GeneRalized Autocalibrating Partially Parallel Acquisitions)
- 场不均匀校正: B0/B1场不均匀性模拟和校正
- 磁化率加权成像(SWI): 相位数据处理和最小密度投影
"""

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter
from scipy.fft import fft2, ifft2, fftshift, ifftshift
from scipy.signal import convolve2d


class Reconstructor:
    """MRI图像重建器类"""

    def __init__(self, matrix_size=(128, 128), fov=(0.256, 0.256)):
        """
        初始化重建器
        
        Parameters:
            matrix_size: 图像矩阵大小 (Ny, Nx)
            fov: 视场大小 (米)
        """
        self.matrix_size = matrix_size
        self.fov = fov
        self.pixel_size = (fov[0] / matrix_size[0], fov[1] / matrix_size[1])

    def inverse_fft(self, kspace_data):
        """
        2D逆FFT重建(笛卡尔采样)
        
        Parameters:
            kspace_data: K空间数据 (复数值)
        
        Returns:
            重建的复图像
        """
        data = ifftshift(kspace_data)
        image = ifft2(data)
        image = fftshift(image)

        return image

    def inverse_fft_2d(self, kspace_data):
        """
        2D逆FFT重建(笛卡尔采样)- 与inverse_fft相同, 提供别名
        
        Parameters:
            kspace_data: K空间数据 (复数值)
        
        Returns:
            重建的复图像
        """
        return self.inverse_fft(kspace_data)

    def magnitude_image(self, complex_image):
        """
        获取复图像的幅度图像
        
        Parameters:
            complex_image: 复图像
        
        Returns:
            幅度图像
        """
        return np.abs(complex_image)

    def phase_image(self, complex_image):
        """
        获取复图像的相位图像
        
        Parameters:
            complex_image: 复图像
        
        Returns:
            相位图像 (弧度)
        """
        return np.angle(complex_image)

    def real_image(self, complex_image):
        """获取实部图像"""
        return np.real(complex_image)

    def imag_image(self, complex_image):
        """获取虚部图像"""
        return np.imag(complex_image)

    def zero_pad(self, kspace_data, target_size=(256, 256)):
        """
        零填充K空间以提高图像分辨率(插值效果)
        
        Parameters:
            kspace_data: 原始K空间数据
            target_size: 目标大小 (Ny, Nx)
        
        Returns:
            零填充后的K空间
        """
        Ny, Nx = kspace_data.shape
        Ty, Tx = target_size

        pad_y = Ty - Ny
        pad_x = Tx - Nx

        pad_y_top = pad_y // 2
        pad_y_bottom = pad_y - pad_y_top
        pad_x_left = pad_x // 2
        pad_x_right = pad_x - pad_x_left

        kspace_shifted = fftshift(kspace_data)
        padded = np.pad(kspace_shifted,
                       ((pad_y_top, pad_y_bottom), (pad_x_left, pad_x_right)),
                       mode='constant')
        padded = ifftshift(padded)

        return padded

    def apodize(self, kspace_data, filter_type='hamming', window_size=None):
        """
        对K空间应用窗函数(降低Gibbs伪影)
        
        Parameters:
            kspace_data: K空间数据
            filter_type: 滤波器类型 ('hamming', 'hanning', 'gaussian', 'none')
            window_size: 高斯窗口的标准差
        
        Returns:
            滤波后的K空间数据
        """
        Ny, Nx = kspace_data.shape

        if filter_type == 'hamming':
            win_y = np.hamming(Ny)
            win_x = np.hamming(Nx)
        elif filter_type == 'hanning':
            win_y = np.hanning(Ny)
            win_x = np.hanning(Nx)
        elif filter_type == 'gaussian':
            if window_size is None:
                window_size = Ny / 4.0
            win_y = np.exp(-(np.arange(Ny) - Ny / 2.0) ** 2 / (2 * window_size ** 2))
            win_x = np.exp(-(np.arange(Nx) - Nx / 2.0) ** 2 / (2 * window_size ** 2))
        elif filter_type == 'none':
            return kspace_data
        else:
            raise ValueError(f"未知的滤波器类型: {filter_type}")

        window = np.outer(win_y, win_x)
        window = fftshift(window)

        return kspace_data * window

    def grid(self, kx, ky, kspace_data, overgrid_factor=2, kernel_width=3):
        """
        网格化重建(用于非笛卡尔采样, 如放射状、螺旋)
        
        Parameters:
            kx, ky: K空间坐标 (1/m)
            kspace_data: K空间数据点
            overgrid_factor: 过网格因子
            kernel_width: 卷积核宽度
        
        Returns:
            重建的复图像
        """
        Ny, Nx = self.matrix_size
        dkx = 1.0 / self.fov[1]
        dky = 1.0 / self.fov[0]

        Ny_og = Ny * overgrid_factor
        Nx_og = Nx * overgrid_factor
        dkx_og = dkx / overgrid_factor
        dky_og = dky / overgrid_factor

        kx_og = np.arange(Nx_og) * dkx_og - Nx_og * dkx_og / 2.0
        ky_og = np.arange(Ny_og) * dky_og - Ny_og * dky_og / 2.0

        grid_data = np.zeros((Ny_og, Nx_og), dtype=np.complex128)
        density = np.zeros((Ny_og, Nx_og), dtype=np.float64)

        kx_flat = kx.flatten()
        ky_flat = ky.flatten()
        data_flat = kspace_data.flatten()

        for i in range(len(kx_flat)):
            kx_i = kx_flat[i]
            ky_i = ky_flat[i]
            data_i = data_flat[i]

            kx_idx = int((kx_i + Nx_og * dkx_og / 2.0) / dkx_og)
            ky_idx = int((ky_i + Ny_og * dky_og / 2.0) / dky_og)

            for dx in range(-kernel_width, kernel_width + 1):
                for dy in range(-kernel_width, kernel_width + 1):
                    x_idx = kx_idx + dx
                    y_idx = ky_idx + dy

                    if 0 <= x_idx < Nx_og and 0 <= y_idx < Ny_og:
                        dist = np.sqrt(dx ** 2 + dy ** 2)
                        if dist <= kernel_width:
                            kernel = np.exp(-dist ** 2 / (2 * (kernel_width / 2.0) ** 2))
                            grid_data[y_idx, x_idx] += data_i * kernel
                            density[y_idx, x_idx] += kernel

        density[density > 0] = 1.0 / density[density > 0]
        grid_data = grid_data * density

        image = self.inverse_fft(grid_data)

        crop_y = (Ny_og - Ny) // 2
        crop_x = (Nx_og - Nx) // 2
        image = image[crop_y:crop_y + Ny, crop_x:crop_x + Nx]

        return image

    def compress_sensing_recon(self, kspace_data, mask, lamda=0.01, num_iter=50):
        """
        简单的压缩传感重建(基于ISTA算法)
        
        Parameters:
            kspace_data: 欠采样的K空间数据
            mask: 采样掩码
            lamda: 正则化参数
            num_iter: 迭代次数
        
        Returns:
            重建的复图像
        """
        image = self.inverse_fft(kspace_data)

        for i in range(num_iter):
            kspace_current = fftshift(fft2(ifftshift(image)))
            kspace_current = mask * kspace_data + (1 - mask) * kspace_current

            image = self.inverse_fft(kspace_current)

            real_part = np.real(image)
            imag_part = np.imag(image)

            real_part = self._soft_threshold(real_part, lamda)
            imag_part = self._soft_threshold(imag_part, lamda)

            image = real_part + 1j * imag_part

        return image

    def _soft_threshold(self, x, lamda):
        """软阈值函数(用于压缩传感)"""
        return np.sign(x) * np.maximum(np.abs(x) - lamda, 0)

    def sensitivity_encoding(self, kspace_data, coil_sensitivity, mask):
        """
        SENSE重建(并行成像)
        
        Parameters:
            kspace_data: 多通道K空间数据 (num_coils, Ny, Nx)
            coil_sensitivity: 线圈敏感度图 (num_coils, Ny, Nx)
            mask: 采样掩码
        
        Returns:
            合并后的复图像
        """
        num_coils = kspace_data.shape[0]
        Ny, Nx = self.matrix_size

        coil_images = np.zeros((num_coils, Ny, Nx), dtype=np.complex128)
        for c in range(num_coils):
            coil_images[c] = self.inverse_fft(kspace_data[c])

        csm_conj = np.conj(coil_sensitivity)
        csm_sq = np.sum(np.abs(coil_sensitivity) ** 2, axis=0)

        image = np.sum(csm_conj * coil_images, axis=0)
        image[csm_sq > 0] = image[csm_sq > 0] / csm_sq[csm_sq > 0]

        return image

    def denoise_image(self, image, method='gaussian', sigma=1.0):
        """
        对重建图像进行去噪
        
        Parameters:
            image: 输入图像(幅度或复数)
            method: 去噪方法 ('gaussian', 'median', 'bilateral')
            sigma: 高斯滤波器标准差
        
        Returns:
            去噪后的图像
        """
        if np.iscomplexobj(image):
            mag = np.abs(image)
            phase = np.angle(image)

            if method == 'gaussian':
                mag_denoised = gaussian_filter(mag, sigma=sigma)
            elif method == 'median':
                mag_denoised = median_filter(mag, size=int(sigma * 2 + 1))
            else:
                raise ValueError(f"未知的去噪方法: {method}")

            return mag_denoised * np.exp(1j * phase)
        else:
            if method == 'gaussian':
                return gaussian_filter(image, sigma=sigma)
            elif method == 'median':
                return median_filter(image, size=int(sigma * 2 + 1))
            else:
                raise ValueError(f"未知的去噪方法: {method}")

    def calculate_psnr(self, image1, image2):
        """
        计算两幅图像之间的峰值信噪比(PSNR)
        
        Parameters:
            image1: 参考图像
            image2: 测试图像
        
        Returns:
            PSNR值 (dB)
        """
        if np.iscomplexobj(image1):
            image1 = np.abs(image1)
            image2 = np.abs(image2)

        max_val = np.max(image1)
        mse = np.mean((image1 - image2) ** 2)

        if mse == 0:
            return float('inf')

        psnr = 10 * np.log10(max_val ** 2 / mse)
        return psnr

    def normalize(self, image):
        """
        归一化图像到[0, 1]范围
        
        Parameters:
            image: 输入图像
        
        Returns:
            归一化后的图像
        """
        if np.iscomplexobj(image):
            image = np.abs(image)

        image_min = np.min(image)
        image_max = np.max(image)

        if image_max - image_min == 0:
            return np.zeros_like(image)

        return (image - image_min) / (image_max - image_min)

    def remove_phase_overshoot(self, phase_image):
        """
        去除相位卷绕(相位解卷绕)
        
        Parameters:
            phase_image: 相位图像 (弧度)
        
        Returns:
            解卷绕后的相位图像
        """
        unwrapped = np.unwrap(phase_image)
        return unwrapped

    def reconstruct_cartesian(self, kspace_data, apodize_filter='hamming'):
        """
        完整的笛卡尔重建流程
        
        Parameters:
            kspace_data: K空间数据
            apodize_filter: 窗函数类型
        
        Returns:
            字典, 包含复图像、幅度图像、相位图像
        """
        kspace_filtered = self.apodize(kspace_data, filter_type=apodize_filter)

        complex_image = self.inverse_fft(kspace_filtered)
        mag_image = self.magnitude_image(complex_image)
        phase_image = self.phase_image(complex_image)

        return {
            'complex': complex_image,
            'magnitude': mag_image,
            'phase': phase_image,
            'kspace_filtered': kspace_filtered
        }

    def reconstruct_gridded(self, kx, ky, kspace_data, overgrid_factor=2):
        """
        完整的网格化重建流程
        
        Parameters:
            kx, ky: K空间坐标
            kspace_data: K空间数据
            overgrid_factor: 过网格因子
        
        Returns:
            字典, 包含复图像、幅度图像、相位图像
        """
        complex_image = self.grid(kx, ky, kspace_data, overgrid_factor=overgrid_factor)
        mag_image = self.magnitude_image(complex_image)
        phase_image = self.phase_image(complex_image)

        return {
            'complex': complex_image,
            'magnitude': mag_image,
            'phase': phase_image
        }

    # ==================== 并行成像: SENSE / GRAPPA ====================

    def generate_coil_sensitivity(self, num_coils=4, coil_width=None):
        """
        生成模拟的多通道线圈敏感度图
        
        Parameters:
            num_coils: 线圈数量
            coil_width: 线圈宽度(像素), 默认为矩阵大小的一半
        
        Returns:
            线圈敏感度图 (num_coils, Ny, Nx), 复数值
        """
        Ny, Nx = self.matrix_size
        if coil_width is None:
            coil_width = min(Ny, Nx) / 2.0

        y = np.arange(Ny) - Ny / 2.0
        x = np.arange(Nx) - Nx / 2.0
        xx, yy = np.meshgrid(x, y)

        coil_sensitivity = np.zeros((num_coils, Ny, Nx), dtype=np.complex128)

        angles = np.linspace(0, 2 * np.pi, num_coils, endpoint=False)
        radius = min(Ny, Nx) / 3.0

        for c in range(num_coils):
            cx = radius * np.cos(angles[c])
            cy = radius * np.sin(angles[c])

            dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            amplitude = np.exp(-dist ** 2 / (2 * coil_width ** 2))

            phase = np.arctan2(yy - cy, xx - cx)

            coil_sensitivity[c] = amplitude * np.exp(1j * phase)

        return coil_sensitivity

    def simulate_multicoil_kspace(self, kspace_single, coil_sensitivity):
        """
        从单通道K空间模拟多通道K空间数据
        
        Parameters:
            kspace_single: 单通道K空间数据 (Ny, Nx)
            coil_sensitivity: 线圈敏感度图 (num_coils, Ny, Nx)
        
        Returns:
            多通道K空间数据 (num_coils, Ny, Nx)
        """
        num_coils = coil_sensitivity.shape[0]
        Ny, Nx = kspace_single.shape

        image_single = self.inverse_fft(kspace_single)

        kspace_multi = np.zeros((num_coils, Ny, Nx), dtype=np.complex128)
        for c in range(num_coils):
            coil_image = image_single * coil_sensitivity[c]
            kspace_multi[c] = fftshift(fft2(ifftshift(coil_image)))

        return kspace_multi

    def apply_undersampling(self, kspace_multi, acceleration=2, center_lines=24):
        """
        对多通道K空间应用欠采样掩码(用于并行成像)
        
        Parameters:
            kspace_multi: 多通道K空间数据 (num_coils, Ny, Nx)
            acceleration: 加速因子 R
            center_lines: 中心自动校准信号(ACS)行数
        
        Returns:
            (欠采样K空间, 采样掩码)
        """
        num_coils, Ny, Nx = kspace_multi.shape

        mask = np.zeros((Ny, Nx), dtype=np.bool_)

        center_start = (Ny - center_lines) // 2
        center_end = center_start + center_lines
        mask[center_start:center_end, :] = True

        for ky in range(0, Ny, acceleration):
            if ky < center_start or ky >= center_end:
                mask[ky, :] = True

        kspace_undersampled = kspace_multi * mask[np.newaxis, :, :]

        return kspace_undersampled, mask

    def sensitivity_encoding_full(self, kspace_undersampled, coil_sensitivity, mask, regularization=1e-6):
        """
        完整的SENSE重建(图像域最小二乘解)
        
        SENSE算法原理: 
        对于每个欠采样的相位编码线, 在图像域求解: 
        min || E x - y ||^2 + λ || x ||^2
        
        其中 E 是编码矩阵, 包含线圈敏感度和傅里叶变换
        
        Parameters:
            kspace_undersampled: 欠采样多通道K空间 (num_coils, Ny, Nx)
            coil_sensitivity: 线圈敏感度图 (num_coils, Ny, Nx)
            mask: 采样掩码 (Ny, Nx)
            regularization: 正则化参数
        
        Returns:
            SENSE重建的复图像 (Ny, Nx)
        """
        num_coils, Ny, Nx = kspace_undersampled.shape

        coil_images = np.zeros((num_coils, Ny, Nx), dtype=np.complex128)
        for c in range(num_coils):
            mask_2d = np.where(mask, 1, 0)
            kspace_zero_filled = kspace_undersampled[c] * mask_2d
            coil_images[c] = self.inverse_fft(kspace_zero_filled)

        csm_conj = np.conj(coil_sensitivity)
        csm_sq = np.sum(np.abs(coil_sensitivity) ** 2, axis=0) + regularization

        image = np.sum(csm_conj * coil_images, axis=0) / csm_sq

        return image

    def _extract_grappa_kernel(self, kspace_acs, kernel_size=(5, 5), acceleration=2):
        """
        从ACS区域提取GRAPPA卷积核
        
        Parameters:
            kspace_acs: 自动校准区域K空间 (num_coils, Ny_acs, Nx)
            kernel_size: 卷积核大小 (ky, kx)
            acceleration: 加速因子
        
        Returns:
            GRAPPA卷积核 (num_coils, num_coils, kernel_size[0], kernel_size[1])
        """
        num_coils, Ny_acs, Nx = kspace_acs.shape
        kx, ky = kernel_size

        num_sources = num_coils * ky * kx
        num_targets = num_coils * acceleration

        sources = []
        targets = []

        y_start = ky // 2
        y_end = Ny_acs - ky // 2 - acceleration + 1
        x_start = kx // 2
        x_end = Nx - kx // 2

        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                src_block = kspace_acs[:, y - ky // 2:y + ky // 2 + 1,
                                        x - kx // 2:x + kx // 2 + 1]
                sources.append(src_block.flatten())

                tgt_block = kspace_acs[:, y + 1:y + acceleration + 1, x]
                targets.append(tgt_block.flatten())

        sources = np.array(sources)
        targets = np.array(targets)

        sources = np.hstack([sources, np.ones((sources.shape[0], 1))])

        try:
            kernels, _, _, _ = np.linalg.lstsq(sources, targets, rcond=None)
        except np.linalg.LinAlgError:
            sources += 1e-10 * np.eye(sources.shape[1])
            kernels, _, _, _ = np.linalg.lstsq(sources, targets, rcond=None)

        kernels = kernels[:-1, :].T
        kernels = kernels.reshape(num_targets, num_coils, ky, kx)
        kernels = kernels.reshape(acceleration, num_coils, num_coils, ky, kx)

        return kernels

    def grappa_reconstruct(self, kspace_undersampled, mask, kernel_size=(5, 5), acceleration=2, center_lines=24):
        """
        GRAPPA重建(K空间插值)
        
        GRAPPA算法原理: 
        1. 从中心ACS区域学习卷积核
        2. 用卷积核插值缺失的K空间线
        
        Parameters:
            kspace_undersampled: 欠采样多通道K空间 (num_coils, Ny, Nx)
            mask: 采样掩码 (Ny, Nx)
            kernel_size: 卷积核大小
            acceleration: 加速因子
            center_lines: ACS区域行数
        
        Returns:
            GRAPPA重建的复图像 (Ny, Nx)
        """
        num_coils, Ny, Nx = kspace_undersampled.shape

        center_start = (Ny - center_lines) // 2
        center_end = center_start + center_lines
        kspace_acs = kspace_undersampled[:, center_start:center_end, :]

        kernels = self._extract_grappa_kernel(kspace_acs, kernel_size, acceleration)

        kspace_recon = kspace_undersampled.copy()

        ky_k, kx_k = kernel_size
        pad_y = ky_k // 2
        pad_x = kx_k // 2

        kspace_padded = np.pad(kspace_undersampled,
                              ((0, 0), (pad_y, pad_y), (pad_x, pad_x)),
                              mode='constant')

        for y in range(pad_y, Ny + pad_y - acceleration):
            if np.all(mask[y - pad_y, :]):
                continue

            for x in range(pad_x, Nx + pad_x):
                src_block = kspace_padded[:, y - pad_y:y + pad_y + 1,
                                        x - pad_x:x + pad_x + 1]

                for r in range(acceleration):
                    if y + r + 1 - pad_y >= Ny:
                        continue
                    if np.any(mask[y + r + 1 - pad_y, :]):
                        continue

                    kernel_r = kernels[r]
                    for c_tgt in range(num_coils):
                        kspace_recon[c_tgt, y + r + 1 - pad_y, x - pad_x] = \
                            np.sum(kernel_r[c_tgt] * src_block)

        coil_images = np.zeros((num_coils, Ny, Nx), dtype=np.complex128)
        for c in range(num_coils):
            coil_images[c] = self.inverse_fft(kspace_recon[c])

        sos_image = np.sqrt(np.sum(np.abs(coil_images) ** 2, axis=0))

        phase_ref = np.angle(coil_images[0])
        final_image = sos_image * np.exp(1j * phase_ref)

        return final_image

    # ==================== B0/B1场不均匀性模拟和校正 ====================

    def simulate_b0_inhomogeneity(self, strength=50, smooth_sigma=10):
        """
        模拟B0场不均匀性(主磁场不均匀)
        
        Parameters:
            strength: 不均匀强度 (Hz)
            smooth_sigma: 平滑程度 (像素)
        
        Returns:
            B0场不均匀性图 (Ny, Nx), 单位: Hz
        """
        Ny, Nx = self.matrix_size

        delta_b0 = np.random.randn(Ny, Nx) * strength
        delta_b0 = gaussian_filter(delta_b0, sigma=smooth_sigma)

        return delta_b0

    def simulate_b1_inhomogeneity(self, pattern='quadratic', strength=0.3):
        """
        模拟B1场不均匀性(射频场不均匀)
        
        Parameters:
            pattern: 不均匀模式 ('quadratic', 'cosine', 'gaussian', 'gradient')
            strength: 不均匀强度 (0-1)
        
        Returns:
            B1场不均匀性图 (Ny, Nx), 相对值 (0.5-1.5)
        """
        Ny, Nx = self.matrix_size
        y = np.linspace(-1, 1, Ny)
        x = np.linspace(-1, 1, Nx)
        xx, yy = np.meshgrid(x, y)

        if pattern == 'quadratic':
            b1 = 1.0 - strength * (xx ** 2 + yy ** 2)
        elif pattern == 'cosine':
            b1 = 1.0 - strength * np.cos(np.pi * xx) * np.cos(np.pi * yy)
        elif pattern == 'gaussian':
            b1 = 1.0 - strength * np.exp(-(xx ** 2 + yy ** 2) / 0.5)
        elif pattern == 'gradient':
            b1 = 1.0 + strength * xx
        else:
            raise ValueError(f"未知的B1模式: {pattern}")

        b1 = np.clip(b1, 0.5, 1.5)

        return b1

    def apply_b0_inhomogeneity(self, image, delta_b0, te):
        """
        在复图像上添加B0场不均匀性效应
        
        相位偏移: Δφ = 2π * ΔB0 * TE
        
        Parameters:
            image: 复图像 (Ny, Nx)
            delta_b0: B0不均匀性图 (Ny, Nx), 单位: Hz
            te: 回波时间 (秒)
        
        Returns:
            含B0不均匀的复图像
        """
        phase_shift = 2 * np.pi * delta_b0 * te
        return image * np.exp(1j * phase_shift)

    def apply_b1_inhomogeneity(self, image, b1_map):
        """
        在复图像上添加B1场不均匀性效应
        
        幅度调制: Mxy ∝ B1
        
        Parameters:
            image: 复图像 (Ny, Nx)
            b1_map: B1不均匀性图 (Ny, Nx), 相对值
        
        Returns:
            含B1不均匀的复图像
        """
        return image * b1_map

    def correct_b0_phase(self, image, delta_b0=None, te=None, phase_unwrap=True):
        """
        校正B0场引起的相位偏移
        
        Parameters:
            image: 含B0不均匀的复图像
            delta_b0: B0不均匀性图 (可选, 如果未提供则从图像估计)
            te: 回波时间 (秒, 可选)
            phase_unwrap: 是否进行相位解卷绕
        
        Returns:
            校正后的复图像
        """
        if delta_b0 is not None and te is not None:
            phase_shift = 2 * np.pi * delta_b0 * te
            corrected = image * np.exp(-1j * phase_shift)
        else:
            mag = np.abs(image)
            phase = np.angle(image)

            if phase_unwrap:
                phase = self.remove_phase_overshoot(phase)

            phase_filtered = gaussian_filter(phase, sigma=5)
            corrected = mag * np.exp(1j * (phase - phase_filtered))

        return corrected

    def correct_b1_magnitude(self, image, b1_map):
        """
        校正B1场引起的幅度不均匀
        
        Parameters:
            image: 含B1不均匀的复图像
            b1_map: B1不均匀性图
        
        Returns:
            校正后的复图像
        """
        b1_safe = np.where(np.abs(b1_map) > 1e-6, b1_map, 1e-6)
        return image / b1_safe

    def simulate_artifact(self, image, artifact_type='ghosting', **kwargs):
        """
        模拟MRI扫描伪影
        
        Parameters:
            image: 原始复图像
            artifact_type: 伪影类型
                - 'ghosting': 奈奎斯特鬼影
                - 'motion': 运动伪影
                - 'truncation': 截断伪影(Gibbs)
                - 'susceptibility': 磁化率伪影
        
        Returns:
            含伪影的复图像
        """
        mag = np.abs(image)
        phase = np.angle(image)

        if artifact_type == 'ghosting':
            strength = kwargs.get('strength', 0.1)
            direction = kwargs.get('direction', 'y')

            kspace = fftshift(fft2(ifftshift(image)))
            if direction == 'y':
                ghost = np.zeros_like(kspace)
                shift = kspace.shape[0] // 4
                ghost[shift:, :] = kspace[:-shift, :] * strength
            else:
                ghost = np.zeros_like(kspace)
                shift = kspace.shape[1] // 4
                ghost[:, shift:] = kspace[:, :-shift] * strength

            kspace_with_ghost = kspace + ghost
            artifact_image = self.inverse_fft(kspace_with_ghost)

        elif artifact_type == 'motion':
            strength = kwargs.get('strength', 2.0)
            num_lines = mag.shape[0]

            kspace = fftshift(fft2(ifftshift(image)))
            for y in range(num_lines):
                shift_x = np.random.normal(0, strength)
                phase_shift = 2 * np.pi * shift_x * np.arange(kspace.shape[1]) / kspace.shape[1]
                kspace[y, :] *= np.exp(1j * phase_shift)

            artifact_image = self.inverse_fft(kspace)

        elif artifact_type == 'truncation':
            keep_fraction = kwargs.get('keep_fraction', 0.3)

            kspace = fftshift(fft2(ifftshift(image)))
            Ny, Nx = kspace.shape
            mask = np.zeros_like(kspace, dtype=np.bool_)
            cy, cx = Ny // 2, Nx // 2
            ry = int(Ny * keep_fraction / 2)
            rx = int(Nx * keep_fraction / 2)
            mask[cy - ry:cy + ry, cx - rx:cx + rx] = True

            kspace_truncated = kspace * mask
            artifact_image = self.inverse_fft(kspace_truncated)

        elif artifact_type == 'susceptibility':
            strength = kwargs.get('strength', 3.0)
            te = kwargs.get('te', 0.02)

            y = np.linspace(-1, 1, mag.shape[0])
            x = np.linspace(-1, 1, mag.shape[1])
            xx, yy = np.meshgrid(x, y)

            chi = np.zeros_like(mag)
            chi[(xx ** 2 + yy ** 2) < 0.3] = strength

            phase_shift = 2 * np.pi * 42.58e6 * chi * te * 1e-6
            artifact_image = mag * np.exp(1j * (phase + phase_shift))

        else:
            raise ValueError(f"未知的伪影类型: {artifact_type}")

        return artifact_image

    # ==================== 磁化率加权成像(SWI) ====================

    def swi_phase_processing(self, phase_image, mag_image=None, sigma=2, power=4, num_echoes=1):
        """
        SWI相位处理 - 生成相位掩码
        
        SWI原理: 
        1. 高通滤波相位图去除背景相位
        2. 生成相位掩码: mask = (phase < 0)
        3. 掩码增强: mask^power
        
        Parameters:
            phase_image: 输入相位图像 (弧度)
            mag_image: 幅度图像(可选, 用于加权)
            sigma: 高通滤波标准差
            power: 相位掩码增强指数
            num_echoes: 回波数(用于多回波SWI)
        
        Returns:
            处理后的相位掩码
        """
        phase_unwrapped = self.remove_phase_overshoot(phase_image)

        phase_lowpass = gaussian_filter(phase_unwrapped, sigma=sigma)
        phase_highpass = phase_unwrapped - phase_lowpass

        phase_mask = np.ones_like(phase_highpass)
        negative_mask = phase_highpass < 0
        phase_mask[negative_mask] = (phase_highpass[negative_mask] / np.pi + 1)

        phase_mask = np.clip(phase_mask, 0, 1)

        phase_mask = phase_mask ** power

        if mag_image is not None:
            mag_weight = mag_image / (np.max(mag_image) + 1e-10)
            phase_mask = phase_mask * (0.5 + 0.5 * mag_weight)

        return phase_mask

    def swi_reconstruct(self, kspace_data, te=0.02, sigma=2, power=4, num_slices=1, mip_slices=5):
        """
        完整的SWI重建流程
        
        Parameters:
            kspace_data: K空间数据 (Ny, Nx) 或 (num_slices, Ny, Nx)
            te: 回波时间 (秒)
            sigma: 相位高通滤波标准差
            power: 相位掩码增强指数
            num_slices: 层数(用于3D mIP)
            mip_slices: 最小强度投影层数
        
        Returns:
            字典包含: SWI图像、幅度图像、相位图像、相位掩码
        """
        if kspace_data.ndim == 2:
            kspace_data = kspace_data[np.newaxis, :, :]

        num_slices_data = kspace_data.shape[0]

        swi_volumes = []
        mag_volumes = []
        phase_volumes = []
        mask_volumes = []

        for s in range(num_slices_data):
            recon = self.reconstruct_cartesian(kspace_data[s], apodize_filter='none')

            mag = recon['magnitude']
            phase = recon['phase']

            phase_mask = self.swi_phase_processing(phase, mag, sigma, power)

            swi_image = mag * phase_mask

            swi_volumes.append(swi_image)
            mag_volumes.append(mag)
            phase_volumes.append(phase)
            mask_volumes.append(phase_mask)

        swi_volumes = np.array(swi_volumes)
        mag_volumes = np.array(mag_volumes)
        phase_volumes = np.array(phase_volumes)
        mask_volumes = np.array(mask_volumes)

        if num_slices_data > 1:
            swi_mip = np.zeros_like(swi_volumes)
            for s in range(num_slices_data):
                start = max(0, s - mip_slices // 2)
                end = min(num_slices_data, s + mip_slices // 2 + 1)
                swi_mip[s] = np.min(swi_volumes[start:end], axis=0)
        else:
            swi_mip = swi_volumes[0]
            swi_volumes = swi_volumes[0]
            mag_volumes = mag_volumes[0]
            phase_volumes = phase_volumes[0]
            mask_volumes = mask_volumes[0]

        return {
            'swi': swi_mip,
            'magnitude': mag_volumes,
            'phase': phase_volumes,
            'phase_mask': mask_volumes,
            'swi_original': swi_volumes
        }

    def swi_phase_mapping(self, kspace_multi_echo, tes):
        """
        多回波SWI相位映射 - 定量磁化率成像(QSM)基础
        
        Parameters:
            kspace_multi_echo: 多回波K空间 (num_echoes, Ny, Nx)
            tes: 回波时间列表 (秒)
        
        Returns:
            定量磁化率图 (ppm)
        """
        num_echoes = len(tes)
        Ny, Nx = kspace_multi_echo.shape[1:]

        phases = np.zeros((num_echoes, Ny, Nx))
        magnitudes = np.zeros((num_echoes, Ny, Nx))

        for e in range(num_echoes):
            recon = self.reconstruct_cartesian(kspace_multi_echo[e], apodize_filter='none')
            phases[e] = recon['phase']
            magnitudes[e] = recon['magnitude']

        phase_diff = phases - phases[0:1]

        for e in range(num_echoes):
            phase_diff[e] = self.remove_phase_overshoot(phase_diff[e])

        te_array = np.array(tes).reshape(-1, 1, 1)
        slope = np.sum(phase_diff * te_array, axis=0) / (np.sum(te_array ** 2, axis=0) + 1e-10)

        chi = slope / (2 * np.pi * 42.58e6) * 1e6

        return chi

    # ==================== 辅助函数 ====================

    def combine_coil_images(self, coil_images, method='sos'):
        """
        合并多通道线圈图像
        
        Parameters:
            coil_images: 多通道图像 (num_coils, Ny, Nx)
            method: 合并方法
                - 'sos': 平方和开根号 (Sum Of Squares)
                - 'sum': 直接求和
                - 'weighted': 幅度加权求和
        
        Returns:
            合并后的图像
        """
        if method == 'sos':
            return np.sqrt(np.sum(np.abs(coil_images) ** 2, axis=0))
        elif method == 'sum':
            return np.sum(coil_images, axis=0)
        elif method == 'weighted':
            mag = np.abs(coil_images)
            weights = mag / (np.sum(mag, axis=0, keepdims=True) + 1e-10)
            return np.sum(weights * coil_images, axis=0)
        else:
            raise ValueError(f"未知的合并方法: {method}")
