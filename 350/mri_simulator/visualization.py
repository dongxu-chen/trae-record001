"""
MRI可视化模块
使用matplotlib显示体模、K空间、重建图像等
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.gridspec import GridSpec


class MRIViewer:
    """MRI数据可视化类"""

    def __init__(self, figsize=(12, 10)):
        """
        初始化可视化器
        
        Parameters:
            figsize: 图像大小
        """
        self.figsize = figsize
        self.figures = []

    def _create_figure(self, nrows=1, ncols=1, figsize=None):
        """创建新图形"""
        if figsize is None:
            figsize = self.figsize
        fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
        self.figures.append(fig)
        return fig, axes

    def plot_phantom(self, phantom, show_all=True):
        """
        显示数字体模
        
        Parameters:
            phantom: Phantom对象
            show_all: 是否显示所有参数图
        
        Returns:
            matplotlib图形
        """
        if show_all:
            fig, axes = self._create_figure(1, 3, figsize=(15, 5))

            im0 = axes[0].imshow(phantom.PD, cmap='gray', interpolation='nearest')
            axes[0].set_title('质子密度 (PD)')
            axes[0].set_xlabel('x (像素)')
            axes[0].set_ylabel('y (像素)')
            plt.colorbar(im0, ax=axes[0])

            im1 = axes[1].imshow(phantom.T1, cmap='viridis', interpolation='nearest')
            axes[1].set_title('T1 弛豫时间 (s)')
            axes[1].set_xlabel('x (像素)')
            plt.colorbar(im1, ax=axes[1])

            im2 = axes[2].imshow(phantom.T2, cmap='plasma', interpolation='nearest')
            axes[2].set_title('T2 弛豫时间 (s)')
            axes[2].set_xlabel('x (像素)')
            plt.colorbar(im2, ax=axes[2])

            plt.tight_layout()
        else:
            fig, ax = self._create_figure(1, 1, figsize=(8, 8))
            im = ax.imshow(phantom.PD, cmap='gray', interpolation='nearest')
            ax.set_title('质子密度 (PD)')
            ax.set_xlabel('x (像素)')
            ax.set_ylabel('y (像素)')
            plt.colorbar(im, ax=ax)

        return fig

    def plot_kspace(self, kspace_data, show_log=True):
        """
        显示K空间数据
        
        Parameters:
            kspace_data: K空间数据(复数值)
            show_log: 是否以对数刻度显示
        
        Returns:
            matplotlib图形
        """
        mag = np.abs(kspace_data)
        phase = np.angle(kspace_data)

        if show_log:
            mag_display = np.log1p(mag)
        else:
            mag_display = mag

        fig, axes = self._create_figure(1, 2, figsize=(14, 6))

        im0 = axes[0].imshow(mag_display, cmap='gray', interpolation='nearest')
        title = 'K空间幅度 (对数刻度)' if show_log else 'K空间幅度'
        axes[0].set_title(title)
        axes[0].set_xlabel('kx')
        axes[0].set_ylabel('ky')
        plt.colorbar(im0, ax=axes[0])

        im1 = axes[1].imshow(phase, cmap='hsv', interpolation='nearest',
                            vmin=-np.pi, vmax=np.pi)
        axes[1].set_title('K空间相位')
        axes[1].set_xlabel('kx')
        cbar = plt.colorbar(im1, ax=axes[1])
        cbar.set_ticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
        cbar.set_ticklabels(['-π', '-π/2', '0', 'π/2', 'π'])

        plt.tight_layout()
        return fig

    def plot_reconstructed_image(self, recon_result, show_all=True):
        """
        显示重建结果
        
        Parameters:
            recon_result: Reconstructor返回的结果字典
            show_all: 是否显示所有分量
        
        Returns:
            matplotlib图形
        """
        if show_all:
            fig, axes = self._create_figure(1, 3, figsize=(15, 5))

            im0 = axes[0].imshow(recon_result['magnitude'], cmap='gray',
                                 interpolation='nearest')
            axes[0].set_title('幅度图像')
            axes[0].set_xlabel('x (像素)')
            axes[0].set_ylabel('y (像素)')
            plt.colorbar(im0, ax=axes[0])

            im1 = axes[1].imshow(recon_result['phase'], cmap='hsv',
                                 interpolation='nearest',
                                 vmin=-np.pi, vmax=np.pi)
            axes[1].set_title('相位图像')
            axes[1].set_xlabel('x (像素)')
            cbar = plt.colorbar(im1, ax=axes[1])
            cbar.set_ticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
            cbar.set_ticklabels(['-π', '-π/2', '0', 'π/2', 'π'])

            real = np.real(recon_result['complex'])
            im2 = axes[2].imshow(real, cmap='gray', interpolation='nearest')
            axes[2].set_title('实部图像')
            axes[2].set_xlabel('x (像素)')
            plt.colorbar(im2, ax=axes[2])

            plt.tight_layout()
        else:
            fig, ax = self._create_figure(1, 1, figsize=(8, 8))
            im = ax.imshow(recon_result['magnitude'], cmap='gray',
                          interpolation='nearest')
            ax.set_title('重建图像 (幅度)')
            ax.set_xlabel('x (像素)')
            ax.set_ylabel('y (像素)')
            plt.colorbar(im, ax=ax)

        return fig

    def plot_signal(self, time_points, signal_real, signal_imag=None, title='MR信号'):
        """
        显示MR信号随时间的变化
        
        Parameters:
            time_points: 时间点数组
            signal_real: 信号实部
            signal_imag: 信号虚部 (可选)
            title: 图表标题
        
        Returns:
            matplotlib图形
        """
        fig, ax = self._create_figure(1, 1, figsize=(10, 6))

        ax.plot(time_points, signal_real, 'b-', label='实部', linewidth=1.5)

        if signal_imag is not None:
            ax.plot(time_points, signal_imag, 'r--', label='虚部', linewidth=1.5)

        magnitude = np.abs(signal_real + 1j * (signal_imag if signal_imag is not None else 0))
        ax.plot(time_points, magnitude, 'k-', label='幅度', linewidth=2, alpha=0.7)

        ax.set_title(title)
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('信号强度')
        ax.grid(True, alpha=0.3)
        ax.legend()

        return fig

    def plot_kspace_trajectory(self, kx, ky, title='K空间轨迹'):
        """
        绘制K空间轨迹
        
        Parameters:
            kx, ky: K空间坐标
            title: 图表标题
        
        Returns:
            matplotlib图形
        """
        fig, ax = self._create_figure(1, 1, figsize=(8, 8))

        if kx.ndim == 2:
            for i in range(kx.shape[0]):
                ax.plot(kx[i, :], ky[i, :], 'b-', linewidth=0.8, alpha=0.7)
        else:
            ax.plot(kx.flatten(), ky.flatten(), 'b-', linewidth=0.8, alpha=0.7)

        ax.set_title(title)
        ax.set_xlabel('kx (1/m)')
        ax.set_ylabel('ky (1/m)')
        ax.axhline(0, color='k', linewidth=0.5, alpha=0.5)
        ax.axvline(0, color='k', linewidth=0.5, alpha=0.5)
        ax.grid(True, alpha=0.3)
        ax.axis('equal')

        return fig

    def plot_sequence_comparison(self, recon_results, sequence_names):
        """
        比较不同序列的重建结果
        
        Parameters:
            recon_results: 重建结果列表
            sequence_names: 序列名称列表
        
        Returns:
            matplotlib图形
        """
        n = len(recon_results)
        fig, axes = self._create_figure(1, n, figsize=(5 * n, 5))

        if n == 1:
            axes = [axes]

        for i, (result, name) in enumerate(zip(recon_results, sequence_names)):
            im = axes[i].imshow(result['magnitude'], cmap='gray',
                               interpolation='nearest')
            axes[i].set_title(name)
            axes[i].set_xlabel('x (像素)')
            plt.colorbar(im, ax=axes[i])

        plt.tight_layout()
        return fig

    def plot_bloch_evolution(self, time_points, Mx, My, Mz, title='磁化强度演化'):
        """
        绘制Bloch方程磁化强度演化曲线
        
        Parameters:
            time_points: 时间点
            Mx, My, Mz: 磁化强度分量
            title: 图表标题
        
        Returns:
            matplotlib图形
        """
        fig, axes = self._create_figure(2, 2, figsize=(12, 10))

        axes[0, 0].plot(time_points, Mx, 'b-', label='Mx', linewidth=1.5)
        axes[0, 0].set_title('Mx 磁化强度')
        axes[0, 0].set_xlabel('时间 (s)')
        axes[0, 0].set_ylabel('Mx/M0')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].legend()

        axes[0, 1].plot(time_points, My, 'r-', label='My', linewidth=1.5)
        axes[0, 1].set_title('My 磁化强度')
        axes[0, 1].set_xlabel('时间 (s)')
        axes[0, 1].set_ylabel('My/M0')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].legend()

        axes[1, 0].plot(time_points, Mz, 'g-', label='Mz', linewidth=1.5)
        axes[1, 0].set_title('Mz 磁化强度')
        axes[1, 0].set_xlabel('时间 (s)')
        axes[1, 0].set_ylabel('Mz/M0')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].legend()

        Mxy = np.sqrt(Mx ** 2 + My ** 2)
        axes[1, 1].plot(time_points, Mxy, 'k-', label='|Mxy|', linewidth=1.5)
        axes[1, 1].set_title('横向磁化强度幅度')
        axes[1, 1].set_xlabel('时间 (s)')
        axes[1, 1].set_ylabel('|Mxy|/M0')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].legend()

        plt.suptitle(title, fontsize=14)
        plt.tight_layout()
        return fig

    def plot_3d_magnetization(self, Mx, My, Mz, title='磁化强度矢量轨迹'):
        """
        绘制3D磁化强度矢量轨迹
        
        Parameters:
            Mx, My, Mz: 磁化强度分量
            title: 图表标题
        
        Returns:
            matplotlib图形
        """
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='3d')
        self.figures.append(fig)

        ax.plot(Mx, My, Mz, 'b-', linewidth=1.5, alpha=0.8, label='轨迹')

        ax.scatter(Mx[0], My[0], Mz[0], 'go', s=100, label='起点', zorder=5)
        ax.scatter(Mx[-1], My[-1], Mz[-1], 'ro', s=100, label='终点', zorder=5)

        u, v = np.mgrid[0:2 * np.pi:20j, 0:np.pi:10j]
        x_sphere = np.cos(u) * np.sin(v)
        y_sphere = np.sin(u) * np.sin(v)
        z_sphere = np.cos(v)
        ax.plot_wireframe(x_sphere, y_sphere, z_sphere,
                         color='gray', alpha=0.1, linewidth=0.5)

        ax.set_xlabel('Mx')
        ax.set_ylabel('My')
        ax.set_zlabel('Mz')
        ax.set_title(title)
        ax.legend()
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_zlim(-1.1, 1.1)

        return fig

    def plot_sampling_mask(self, mask, title='采样掩码'):
        """
        绘制采样掩码
        
        Parameters:
            mask: 采样掩码
            title: 图表标题
        
        Returns:
            matplotlib图形
        """
        fig, ax = self._create_figure(1, 1, figsize=(8, 8))

        ax.imshow(mask, cmap='gray', interpolation='nearest')
        ax.set_title(title)
        ax.set_xlabel('kx')
        ax.set_ylabel('ky')

        return fig

    def plot_compare_recon_methods(self, results, method_names):
        """
        比较不同重建方法的结果
        
        Parameters:
            results: 重建结果字典列表
            method_names: 方法名称列表
        
        Returns:
            matplotlib图形
        """
        n = len(results)
        fig, axes = self._create_figure(2, n, figsize=(5 * n, 10))

        for i, (result, name) in enumerate(zip(results, method_names)):
            im0 = axes[0, i].imshow(result['magnitude'], cmap='gray',
                                   interpolation='nearest')
            axes[0, i].set_title(f'{name} - 幅度')
            axes[0, i].set_xlabel('x (像素)')
            plt.colorbar(im0, ax=axes[0, i])

            im1 = axes[1, i].imshow(result['phase'], cmap='hsv',
                                   interpolation='nearest',
                                   vmin=-np.pi, vmax=np.pi)
            axes[1, i].set_title(f'{name} - 相位')
            axes[1, i].set_xlabel('x (像素)')
            cbar = plt.colorbar(im1, ax=axes[1, i])
            cbar.set_ticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
            cbar.set_ticklabels(['-π', '-π/2', '0', 'π/2', 'π'])

        plt.tight_layout()
        return fig

    def plot_noise_analysis(self, clean_image, noisy_images, snr_levels):
        """
        分析不同噪声水平的重建结果
        
        Parameters:
            clean_image: 无噪声图像
            noisy_images: 含噪声图像列表
            snr_levels: SNR水平列表 (dB)
        
        Returns:
            matplotlib图形
        """
        n = len(noisy_images) + 1
        fig, axes = self._create_figure(1, n, figsize=(5 * n, 5))

        axes[0].imshow(np.abs(clean_image), cmap='gray', interpolation='nearest')
        axes[0].set_title('原始 (无噪声)')
        axes[0].set_xlabel('x (像素)')

        for i, (noisy, snr) in enumerate(zip(noisy_images, snr_levels)):
            axes[i + 1].imshow(np.abs(noisy), cmap='gray', interpolation='nearest')
            axes[i + 1].set_title(f'SNR = {snr} dB')
            axes[i + 1].set_xlabel('x (像素)')

        plt.tight_layout()
        return fig

    def plot_profile(self, image, line_index=None, axis=0, title='图像剖面'):
        """
        绘制图像的一维剖面
        
        Parameters:
            image: 输入图像
            line_index: 剖面线索引 (默认中心)
            axis: 0=行剖面, 1=列剖面
            title: 图表标题
        
        Returns:
            matplotlib图形
        """
        fig, axes = self._create_figure(1, 2, figsize=(14, 6))

        if np.iscomplexobj(image):
            image = np.abs(image)

        Ny, Nx = image.shape

        if line_index is None:
            line_index = Ny // 2 if axis == 0 else Nx // 2

        axes[0].imshow(image, cmap='gray', interpolation='nearest')
        axes[0].set_title('图像')
        axes[0].set_xlabel('x (像素)')
        axes[0].set_ylabel('y (像素)')

        if axis == 0:
            axes[0].axhline(line_index, color='r', linewidth=2)
            profile = image[line_index, :]
            x_axis = np.arange(Nx)
            x_label = 'x (像素)'
        else:
            axes[0].axvline(line_index, color='r', linewidth=2)
            profile = image[:, line_index]
            x_axis = np.arange(Ny)
            x_label = 'y (像素)'

        axes[1].plot(x_axis, profile, 'b-', linewidth=1.5)
        axes[1].set_title(title)
        axes[1].set_xlabel(x_label)
        axes[1].set_ylabel('信号强度')
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def show_all(self):
        """显示所有创建的图形"""
        plt.show()

    def save_all(self, prefix='mri_', dpi=150):
        """
        保存所有图形
        
        Parameters:
            prefix: 文件名前缀
            dpi: 输出分辨率
        """
        for i, fig in enumerate(self.figures):
            fig.savefig(f'{prefix}{i:03d}.png', dpi=dpi, bbox_inches='tight')

    def close_all(self):
        """关闭所有图形"""
        for fig in self.figures:
            plt.close(fig)
        self.figures = []
