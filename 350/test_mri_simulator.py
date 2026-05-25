"""
MRI模拟器单元测试
验证各个模块的基本功能
"""

import unittest
import numpy as np

from mri_simulator.phantom import Phantom, generate_shepp_logan, generate_brain_phantom
from mri_simulator.bloch import BlochSolver, GAMMA_RAD
from mri_simulator.sequences import SpinEcho, GradientEcho, InversionRecovery
from mri_simulator.kspace import KSpace
from mri_simulator.reconstruction import Reconstructor


class TestPhantom(unittest.TestCase):
    """测试数字体模模块"""

    def test_phantom_creation(self):
        """测试体模创建"""
        phantom = Phantom(size=(32, 32), fov=(0.256, 0.256))
        self.assertEqual(phantom.size, (32, 32))
        self.assertEqual(phantom.fov, (0.256, 0.256))
        self.assertEqual(phantom.PD.shape, (32, 32))
        self.assertEqual(phantom.T1.shape, (32, 32))
        self.assertEqual(phantom.T2.shape, (32, 32))

    def test_add_ellipse(self):
        """测试添加椭圆"""
        phantom = Phantom(size=(32, 32), fov=(0.256, 0.256))
        phantom.add_ellipse((0, 0), (0.05, 0.05), 0, 1.0, 1.0, 0.1)
        self.assertTrue(np.any(phantom.PD > 0))
        self.assertTrue(np.any(phantom.T1 > 0))
        self.assertTrue(np.any(phantom.T2 > 0))

    def test_add_rectangle(self):
        """测试添加矩形"""
        phantom = Phantom(size=(32, 32), fov=(0.256, 0.256))
        phantom.add_rectangle((0, 0), (0.05, 0.05), 0, 0.8, 0.9, 0.08)
        self.assertTrue(np.any(phantom.PD > 0))

    def test_shepp_logan(self):
        """测试Shepp-Logan体模生成"""
        phantom = generate_shepp_logan(size=(32, 32))
        self.assertEqual(phantom.PD.shape, (32, 32))
        self.assertTrue(np.max(phantom.PD) > 0)

    def test_brain_phantom(self):
        """测试脑体模生成"""
        phantom = generate_brain_phantom(size=(32, 32))
        self.assertEqual(phantom.PD.shape, (32, 32))

    def test_get_voxel_params(self):
        """测试获取体素参数"""
        phantom = generate_shepp_logan(size=(16, 16))
        pd, t1, t2 = phantom.get_voxel_params()
        self.assertEqual(len(pd), 256)
        self.assertEqual(len(t1), 256)
        self.assertEqual(len(t2), 256)

    def test_get_positions(self):
        """测试获取体素坐标"""
        phantom = generate_shepp_logan(size=(16, 16))
        x, y = phantom.get_positions()
        self.assertEqual(len(x), 256)
        self.assertEqual(len(y), 256)


class TestBlochSolver(unittest.TestCase):
    """测试Bloch方程求解器"""

    def test_initialization(self):
        """测试初始化"""
        solver = BlochSolver(n_voxels=100)
        self.assertEqual(solver.n_voxels, 100)
        self.assertEqual(len(solver.Mx), 100)
        self.assertEqual(len(solver.My), 100)
        self.assertEqual(len(solver.Mz), 100)

    def test_set_params(self):
        """测试设置参数"""
        solver = BlochSolver(n_voxels=10)
        pd = np.ones(10) * 0.8
        t1 = np.ones(10) * 1.0
        t2 = np.ones(10) * 0.1
        solver.set_params(pd, t1, t2)
        np.testing.assert_array_equal(solver.M0, pd)
        np.testing.assert_array_equal(solver.T1, t1)
        np.testing.assert_array_equal(solver.T2, t2)

    def test_reset_magnetization(self):
        """测试重置磁化强度"""
        solver = BlochSolver(n_voxels=10)
        pd = np.ones(10)
        solver.set_params(pd, np.ones(10), np.ones(10))
        solver.Mx = np.ones(10) * 0.5
        solver.My = np.ones(10) * 0.3
        solver.Mz = np.ones(10) * 0.2
        solver.reset_magnetization()
        np.testing.assert_array_equal(solver.Mx, np.zeros(10))
        np.testing.assert_array_equal(solver.My, np.zeros(10))
        np.testing.assert_array_equal(solver.Mz, pd)

    def test_apply_excitation_90(self):
        """测试90度激发脉冲(沿x轴的90度脉冲将Mz转到-Mx方向)"""
        solver = BlochSolver(n_voxels=1)
        solver.set_params(np.array([1.0]), np.array([1.0]), np.array([0.1]))
        solver.apply_excitation(np.pi / 2, 0.0)
        self.assertAlmostEqual(solver.Mx[0], -1.0, places=6)
        self.assertAlmostEqual(solver.My[0], 0.0, places=6)
        self.assertAlmostEqual(solver.Mz[0], 0.0, places=6)

    def test_apply_excitation_180(self):
        """测试180度反转脉冲"""
        solver = BlochSolver(n_voxels=1)
        solver.set_params(np.array([1.0]), np.array([1.0]), np.array([0.1]))
        solver.apply_excitation(np.pi, 0.0)
        self.assertAlmostEqual(solver.Mx[0], 0.0, places=6)
        self.assertAlmostEqual(solver.My[0], 0.0, places=6)
        self.assertAlmostEqual(solver.Mz[0], -1.0, places=6)

    def test_relax(self):
        """测试弛豫过程"""
        solver = BlochSolver(n_voxels=1)
        solver.set_params(np.array([1.0]), np.array([1.0]), np.array([0.1]))
        solver.apply_excitation(np.pi / 2, 0.0)
        initial_Mxy = np.sqrt(solver.Mx[0] ** 2 + solver.My[0] ** 2)
        initial_Mz = solver.Mz[0]

        solver.relax(0.1)

        e2 = np.exp(-0.1 / 0.1)
        e1 = np.exp(-0.1 / 1.0)
        expected_Mxy = initial_Mxy * e2
        expected_Mz = initial_Mz * e1 + 1.0 * (1 - e1)

        actual_Mxy = np.sqrt(solver.Mx[0] ** 2 + solver.My[0] ** 2)
        self.assertAlmostEqual(actual_Mxy, expected_Mxy, places=6)
        self.assertAlmostEqual(solver.Mz[0], expected_Mz, places=6)

    def test_precess(self):
        """测试自由进动"""
        solver = BlochSolver(n_voxels=1)
        solver.set_params(np.array([1.0]), np.array([1.0]), np.array([0.1]))
        solver.apply_excitation(np.pi / 2, 0.0)

        x = np.array([0.01])
        y = np.array([0.0])
        duration = 0.001
        gx = 0.001
        gy = 0.0

        initial_Mx = solver.Mx[0]
        initial_My = solver.My[0]

        solver.precess(duration, gx, gy, x, y)

        delta_omega = GAMMA_RAD * (gx * x[0] + gy * y[0])
        phi = delta_omega * duration

        expected_Mx = initial_Mx * np.cos(phi) - initial_My * np.sin(phi)
        expected_My = initial_Mx * np.sin(phi) + initial_My * np.cos(phi)

        self.assertAlmostEqual(solver.Mx[0], expected_Mx, places=6)
        self.assertAlmostEqual(solver.My[0], expected_My, places=6)

    def test_get_signal(self):
        """测试获取信号"""
        solver = BlochSolver(n_voxels=10)
        solver.set_params(np.ones(10), np.ones(10), np.ones(10))
        solver.apply_excitation(np.pi / 2, 0.0)
        signal = solver.get_signal()
        self.assertIsInstance(signal, complex)
        self.assertNotEqual(signal, 0)

    def test_magnetization_conservation(self):
        """测试磁化强度守恒(无弛豫时)"""
        solver = BlochSolver(n_voxels=1)
        solver.set_params(np.array([1.0]), np.array([1e10]), np.array([1e10]))
        initial_M = np.sqrt(solver.Mx[0] ** 2 + solver.My[0] ** 2 + solver.Mz[0] ** 2)

        solver.apply_excitation(np.pi / 3, 0.0)
        after_pulse = np.sqrt(solver.Mx[0] ** 2 + solver.My[0] ** 2 + solver.Mz[0] ** 2)

        self.assertAlmostEqual(initial_M, after_pulse, places=6)


class TestPulseSequences(unittest.TestCase):
    """测试脉冲序列模块"""

    def setUp(self):
        """设置测试环境"""
        self.matrix_size = (16, 16)
        self.fov = (0.256, 0.256)
        self.phantom = generate_shepp_logan(size=self.matrix_size, fov=self.fov)
        self.n_voxels = self.matrix_size[0] * self.matrix_size[1]
        self.solver = BlochSolver(self.n_voxels)

    def test_spin_echo(self):
        """测试自旋回波序列"""
        se = SpinEcho(tr=1.0, te=0.05, matrix_size=self.matrix_size, fov=self.fov)
        kspace = se.simulate(self.solver, self.phantom, use_gpu=False)
        self.assertEqual(kspace.shape, self.matrix_size)
        self.assertTrue(np.any(np.abs(kspace) > 0))
        self.assertEqual(se.get_sequence_name(), "Spin Echo")

    def test_gradient_echo(self):
        """测试梯度回波序列"""
        gre = GradientEcho(
            tr=0.05, te=0.01, flip_angle=np.pi / 6,
            matrix_size=self.matrix_size, fov=self.fov
        )
        kspace = gre.simulate(self.solver, self.phantom, use_gpu=False)
        self.assertEqual(kspace.shape, self.matrix_size)
        self.assertTrue(np.any(np.abs(kspace) > 0))
        self.assertEqual(gre.get_sequence_name(), "Gradient Echo")

    def test_inversion_recovery(self):
        """测试反转恢复序列"""
        ir = InversionRecovery(
            tr=2.5, ti=0.5, te=0.05,
            matrix_size=self.matrix_size, fov=self.fov
        )
        kspace = ir.simulate(self.solver, self.phantom, use_gpu=False)
        self.assertEqual(kspace.shape, self.matrix_size)
        self.assertTrue(np.any(np.abs(kspace) > 0))
        self.assertEqual(ir.get_sequence_name(), "Inversion Recovery")

    def test_sequence_timing(self):
        """测试序列时间参数"""
        se = SpinEcho(tr=2.0, te=0.1, matrix_size=(8, 8), fov=(0.256, 0.256))
        self.assertEqual(se.tr, 2.0)
        self.assertEqual(se.te, 0.1)
        self.assertEqual(se.matrix_size, (8, 8))


class TestKSpace(unittest.TestCase):
    """测试K空间模块"""

    def test_initialization(self):
        """测试初始化"""
        kspace = KSpace(matrix_size=(32, 32))
        self.assertEqual(kspace.matrix_size, (32, 32))
        self.assertEqual(kspace.data.shape, (32, 32))
        self.assertEqual(kspace.mask.shape, (32, 32))

    def test_fill_and_fill_cartesian(self):
        """测试填充K空间"""
        kspace = KSpace(matrix_size=(16, 16))
        data = np.random.randn(16, 16) + 1j * np.random.randn(16, 16)
        kspace.fill_cartesian(data)
        np.testing.assert_array_equal(kspace.data, data)

    def test_fill_line(self):
        """测试填充单行"""
        kspace = KSpace(matrix_size=(16, 16))
        line_data = np.random.randn(16) + 1j * np.random.randn(16)
        kspace.fill(5, line_data)
        np.testing.assert_array_equal(kspace.data[5, :], line_data)

    def test_generate_cartesian_mask(self):
        """测试生成笛卡尔欠采样掩码"""
        kspace = KSpace(matrix_size=(64, 64))
        mask = kspace.generate_cartesian_mask(acceleration=4, center_fraction=0.1)
        self.assertEqual(mask.shape, (64, 64))
        self.assertTrue(np.any(mask))
        self.assertTrue(np.any(~mask))
        center_lines = int(64 * 0.1)
        for i in range(64 // 2 - center_lines // 2, 64 // 2 + center_lines // 2):
            self.assertTrue(np.all(mask[i, :]))

    def test_generate_random_mask(self):
        """测试生成随机欠采样掩码"""
        kspace = KSpace(matrix_size=(64, 64))
        np.random.seed(42)
        mask = kspace.generate_random_mask(acceleration=4, center_fraction=0.1)
        self.assertEqual(mask.shape, (64, 64))
        sampling_rate = np.sum(mask) / (64 * 64)
        self.assertLess(sampling_rate, 0.5)

    def test_add_noise(self):
        """测试添加噪声"""
        kspace = KSpace(matrix_size=(32, 32))
        kspace.data = np.ones((32, 32), dtype=np.complex128)
        np.random.seed(42)
        noise = kspace.add_noise(snr=20.0)
        self.assertEqual(noise.shape, (32, 32))
        self.assertTrue(np.any(np.abs(kspace.data - 1.0) > 0))

    def test_fftshift(self):
        """测试fftshift"""
        kspace = KSpace(matrix_size=(8, 8))
        original = np.ones((8, 8), dtype=np.complex128)
        original[0, 0] = 10.0
        kspace.fill_cartesian(original)
        shifted = kspace.fftshift()
        self.assertEqual(shifted[4, 4], 10.0)

    def test_magnitude_phase(self):
        """测试获取幅度和相位"""
        kspace = KSpace(matrix_size=(8, 8))
        data = np.exp(1j * np.linspace(0, 2 * np.pi, 64).reshape(8, 8))
        kspace.fill_cartesian(data)
        mag = kspace.get_magnitude()
        phase = kspace.get_phase()
        np.testing.assert_array_almost_equal(mag, np.ones((8, 8)))
        np.testing.assert_array_almost_equal(phase, np.angle(data))


class TestReconstructor(unittest.TestCase):
    """测试图像重建模块"""

    def setUp(self):
        """设置测试环境"""
        self.matrix_size = (32, 32)
        self.fov = (0.256, 0.256)
        self.reconstructor = Reconstructor(matrix_size=self.matrix_size, fov=self.fov)

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.reconstructor.matrix_size, (32, 32))
        self.assertEqual(self.reconstructor.fov, (0.256, 0.256))

    def test_inverse_fft(self):
        """测试逆FFT重建"""
        phantom = generate_shepp_logan(size=self.matrix_size, fov=self.fov)
        kspace = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(phantom.PD)))
        image = self.reconstructor.inverse_fft(kspace)
        np.testing.assert_array_almost_equal(np.abs(image), phantom.PD, decimal=5)

    def test_magnitude_phase_image(self):
        """测试幅度和相位图像"""
        complex_image = np.random.randn(32, 32) + 1j * np.random.randn(32, 32)
        mag = self.reconstructor.magnitude_image(complex_image)
        phase = self.reconstructor.phase_image(complex_image)
        np.testing.assert_array_almost_equal(mag, np.abs(complex_image))
        np.testing.assert_array_almost_equal(phase, np.angle(complex_image))

    def test_apodize(self):
        """测试窗函数"""
        kspace = np.ones((32, 32), dtype=np.complex128)
        filtered_hamming = self.reconstructor.apodize(kspace, filter_type='hamming')
        filtered_hanning = self.reconstructor.apodize(kspace, filter_type='hanning')
        filtered_none = self.reconstructor.apodize(kspace, filter_type='none')

        self.assertEqual(filtered_hamming.shape, (32, 32))
        self.assertEqual(filtered_hanning.shape, (32, 32))
        np.testing.assert_array_equal(filtered_none, kspace)

    def test_zero_pad(self):
        """测试零填充"""
        kspace = np.ones((16, 16), dtype=np.complex128)
        recon = Reconstructor(matrix_size=(16, 16), fov=(0.256, 0.256))
        padded = recon.zero_pad(kspace, target_size=(32, 32))
        self.assertEqual(padded.shape, (32, 32))

    def test_denoise_image(self):
        """测试图像去噪"""
        image = np.random.randn(32, 32)
        denoised = self.reconstructor.denoise_image(image, method='gaussian', sigma=1.0)
        self.assertEqual(denoised.shape, (32, 32))

        denoised_median = self.reconstructor.denoise_image(image, method='median', sigma=1.0)
        self.assertEqual(denoised_median.shape, (32, 32))

    def test_normalize(self):
        """测试归一化"""
        image = np.random.randn(32, 32) * 100 + 50
        normalized = self.reconstructor.normalize(image)
        self.assertAlmostEqual(np.min(normalized), 0.0, places=6)
        self.assertAlmostEqual(np.max(normalized), 1.0, places=6)

    def test_calculate_psnr(self):
        """测试PSNR计算"""
        image1 = np.ones((32, 32))
        image2 = image1 + 0.01 * np.random.randn(32, 32)
        psnr = self.reconstructor.calculate_psnr(image1, image2)
        self.assertGreater(psnr, 30)

        psnr_same = self.reconstructor.calculate_psnr(image1, image1)
        self.assertEqual(psnr_same, float('inf'))

    def test_reconstruct_cartesian(self):
        """测试完整的笛卡尔重建流程"""
        phantom = generate_shepp_logan(size=self.matrix_size, fov=self.fov)
        kspace = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(phantom.PD)))

        result = self.reconstructor.reconstruct_cartesian(kspace)
        self.assertIn('complex', result)
        self.assertIn('magnitude', result)
        self.assertIn('phase', result)
        self.assertEqual(result['complex'].shape, self.matrix_size)
        self.assertEqual(result['magnitude'].shape, self.matrix_size)
        self.assertEqual(result['phase'].shape, self.matrix_size)

    def test_soft_threshold(self):
        """测试软阈值函数"""
        x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        thresholded = self.reconstructor._soft_threshold(x, 0.5)
        expected = np.array([-1.5, -0.5, 0.0, 0.5, 1.5])
        np.testing.assert_array_almost_equal(thresholded, expected)


class TestFullPipeline(unittest.TestCase):
    """测试完整的MRI模拟流程"""

    def test_full_pipeline(self):
        """测试从体模到重建图像的完整流程"""
        matrix_size = (16, 16)
        fov = (0.256, 0.256)

        phantom = generate_shepp_logan(size=matrix_size, fov=fov)

        n_voxels = matrix_size[0] * matrix_size[1]
        solver = BlochSolver(n_voxels)

        se = SpinEcho(tr=1.0, te=0.05, matrix_size=matrix_size, fov=fov)
        kspace_data = se.simulate(solver, phantom, use_gpu=False)

        reconstructor = Reconstructor(matrix_size=matrix_size, fov=fov)
        recon_result = reconstructor.reconstruct_cartesian(kspace_data)

        self.assertEqual(recon_result['magnitude'].shape, matrix_size)
        self.assertTrue(np.any(recon_result['magnitude'] > 0))

    def test_kspace_undersampled_recon(self):
        """测试欠采样K空间重建"""
        matrix_size = (16, 16)
        fov = (0.256, 0.256)

        phantom = generate_shepp_logan(size=matrix_size, fov=fov)
        n_voxels = matrix_size[0] * matrix_size[1]
        solver = BlochSolver(n_voxels)

        se = SpinEcho(tr=1.0, te=0.05, matrix_size=matrix_size, fov=fov)
        kspace_full = se.simulate(solver, phantom, use_gpu=False)

        kspace_obj = KSpace(matrix_size=matrix_size)
        kspace_obj.fill_cartesian(kspace_full)
        mask = kspace_obj.generate_cartesian_mask(acceleration=2, center_fraction=0.25)
        kspace_obj.apply_mask(mask)

        reconstructor = Reconstructor(matrix_size=matrix_size, fov=fov)
        recon = reconstructor.reconstruct_cartesian(kspace_obj.get_data())

        self.assertEqual(recon['magnitude'].shape, matrix_size)


class TestParallelImaging(unittest.TestCase):
    """测试并行成像SENSE/GRAPPA"""

    def setUp(self):
        self.matrix_size = (32, 32)
        self.recon = Reconstructor(matrix_size=self.matrix_size)

    def test_coil_sensitivity_generation(self):
        """测试线圈敏感度图生成"""
        num_coils = 4
        csm = self.recon.generate_coil_sensitivity(num_coils=num_coils)
        self.assertEqual(csm.shape, (num_coils, *self.matrix_size))
        self.assertTrue(np.iscomplexobj(csm))
        self.assertTrue(np.max(np.abs(csm)) <= 1.0)
        self.assertTrue(np.max(np.abs(csm)) > 0.5)

    def test_multicoil_kspace_simulation(self):
        """测试多通道K空间模拟"""
        num_coils = 4
        kspace_single = np.random.randn(*self.matrix_size) + 1j * np.random.randn(*self.matrix_size)
        csm = self.recon.generate_coil_sensitivity(num_coils=num_coils)
        kspace_multi = self.recon.simulate_multicoil_kspace(kspace_single, csm)
        self.assertEqual(kspace_multi.shape, (num_coils, *self.matrix_size))
        self.assertTrue(np.iscomplexobj(kspace_multi))

    def test_undersampling(self):
        """测试欠采样掩码生成"""
        num_coils = 4
        acceleration = 2
        kspace_multi = np.random.randn(num_coils, *self.matrix_size) + 1j * np.random.randn(num_coils, *self.matrix_size)
        center_lines = 8
        kspace_under, mask = self.recon.apply_undersampling(kspace_multi, acceleration=acceleration, center_lines=center_lines)
        self.assertEqual(kspace_under.shape, kspace_multi.shape)
        self.assertEqual(mask.shape, self.matrix_size)
        sampling_ratio = np.sum(mask) / mask.size
        expected_lines = center_lines + (self.matrix_size[0] - center_lines) // acceleration
        expected_ratio = expected_lines / self.matrix_size[0]
        self.assertAlmostEqual(sampling_ratio, expected_ratio, places=1)

    def test_sense_reconstruction(self):
        """测试SENSE重建"""
        num_coils = 4
        recon = Reconstructor(matrix_size=self.matrix_size)

        test_image = np.zeros(self.matrix_size, dtype=np.complex128)
        test_image[10:22, 10:22] = 1.0 + 0j
        kspace_single = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(test_image)))

        csm = recon.generate_coil_sensitivity(num_coils=num_coils)
        kspace_multi = recon.simulate_multicoil_kspace(kspace_single, csm)
        kspace_under, mask = recon.apply_undersampling(kspace_multi, acceleration=2, center_lines=8)

        recon_image = recon.sensitivity_encoding_full(kspace_under, csm, mask)
        self.assertEqual(recon_image.shape, self.matrix_size)
        self.assertTrue(np.iscomplexobj(recon_image))
        self.assertTrue(np.max(np.abs(recon_image)) > 0)


class TestFieldInhomogeneity(unittest.TestCase):
    """测试B0/B1场不均匀性模拟和校正"""

    def setUp(self):
        self.matrix_size = (32, 32)
        self.recon = Reconstructor(matrix_size=self.matrix_size)

    def test_b0_inhomogeneity_simulation(self):
        """测试B0场不均匀性模拟"""
        delta_b0 = self.recon.simulate_b0_inhomogeneity(strength=50, smooth_sigma=3)
        self.assertEqual(delta_b0.shape, self.matrix_size)
        self.assertTrue(np.max(np.abs(delta_b0)) > 0)
        self.assertTrue(np.max(np.abs(delta_b0)) < 200)

    def test_b1_inhomogeneity_simulation(self):
        """测试B1场不均匀性模拟"""
        for pattern in ['quadratic', 'cosine', 'gaussian', 'gradient']:
            b1 = self.recon.simulate_b1_inhomogeneity(pattern=pattern, strength=0.3)
            self.assertEqual(b1.shape, self.matrix_size)
            self.assertTrue(np.min(b1) >= 0.5)
            self.assertTrue(np.max(b1) <= 1.5)

    def test_apply_b0_inhomogeneity(self):
        """测试应用B0场不均匀性"""
        delta_b0 = self.recon.simulate_b0_inhomogeneity(strength=20, smooth_sigma=2)
        test_image = np.ones(self.matrix_size, dtype=np.complex128)
        te = 0.02

        distorted = self.recon.apply_b0_inhomogeneity(test_image, delta_b0, te)
        self.assertEqual(distorted.shape, test_image.shape)
        self.assertTrue(np.any(np.angle(distorted) != 0))

    def test_apply_b1_inhomogeneity(self):
        """测试应用B1场不均匀性"""
        b1 = self.recon.simulate_b1_inhomogeneity(pattern='quadratic', strength=0.3)
        test_image = np.ones(self.matrix_size, dtype=np.complex128)

        distorted = self.recon.apply_b1_inhomogeneity(test_image, b1)
        self.assertEqual(distorted.shape, test_image.shape)
        self.assertTrue(np.any(np.abs(distorted) != 1.0))

    def test_b0_correction(self):
        """测试B0场校正"""
        delta_b0 = self.recon.simulate_b0_inhomogeneity(strength=30, smooth_sigma=2)
        test_image = np.ones(self.matrix_size, dtype=np.complex128)
        te = 0.02

        distorted = self.recon.apply_b0_inhomogeneity(test_image, delta_b0, te)
        corrected = self.recon.correct_b0_phase(distorted, delta_b0, te)

        phase_error = np.mean(np.abs(np.angle(corrected) - np.angle(test_image)))
        self.assertAlmostEqual(phase_error, 0.0, places=6)

    def test_b1_correction(self):
        """测试B1场校正"""
        b1 = self.recon.simulate_b1_inhomogeneity(pattern='gradient', strength=0.3)
        test_image = np.ones(self.matrix_size, dtype=np.complex128)

        distorted = self.recon.apply_b1_inhomogeneity(test_image, b1)
        corrected = self.recon.correct_b1_magnitude(distorted, b1)

        mag_error = np.mean(np.abs(np.abs(corrected) - np.abs(test_image)))
        self.assertAlmostEqual(mag_error, 0.0, places=6)

    def test_artifact_simulation(self):
        """测试MRI伪影模拟"""
        test_image = np.zeros(self.matrix_size, dtype=np.complex128)
        test_image[10:22, 10:22] = 1.0 + 0j

        for artifact in ['ghosting', 'motion', 'truncation', 'susceptibility']:
            distorted = self.recon.simulate_artifact(test_image, artifact_type=artifact)
            self.assertEqual(distorted.shape, test_image.shape)

    def test_bloch_b0_b1_support(self):
        """测试Bloch求解器的B0/B1支持"""
        n_voxels = 100
        solver = BlochSolver(n_voxels)

        pd = np.ones(n_voxels)
        t1 = np.ones(n_voxels) * 1.0
        t2 = np.ones(n_voxels) * 0.1

        solver.set_params(pd, t1, t2)

        delta_b0 = np.linspace(-100, 100, n_voxels)
        b1_correction = np.linspace(0.7, 1.3, n_voxels)
        solver.set_field_inhomogeneity(delta_B0=delta_b0, B1_correction=b1_correction)

        dt = solver.get_adaptive_dt()
        self.assertTrue(dt > 0)
        self.assertTrue(dt < 0.01)

        solver.apply_excitation(np.pi / 2)
        self.assertTrue(np.std(np.abs(solver.Mz)) > 0)


class TestSWIReconstruction(unittest.TestCase):
    """测试磁化率加权成像(SWI)重建"""

    def setUp(self):
        self.matrix_size = (32, 32)
        self.recon = Reconstructor(matrix_size=self.matrix_size)

    def test_phase_processing(self):
        """测试SWI相位处理"""
        phase_image = np.random.uniform(-np.pi, np.pi, self.matrix_size)
        mag_image = np.random.rand(*self.matrix_size)

        phase_mask = self.recon.swi_phase_processing(phase_image, mag_image, sigma=2, power=4)
        self.assertEqual(phase_mask.shape, self.matrix_size)
        self.assertTrue(np.min(phase_mask) >= 0)
        self.assertTrue(np.max(phase_mask) <= 1)

        phase_mask2 = self.recon.swi_phase_processing(phase_image, sigma=2, power=4)
        self.assertEqual(phase_mask2.shape, self.matrix_size)

    def test_swi_reconstruction(self):
        """测试SWI重建"""
        kspace = np.random.randn(*self.matrix_size) + 1j * np.random.randn(*self.matrix_size)

        result = self.recon.swi_reconstruct(kspace, te=0.02, sigma=2, power=4)
        self.assertIn('swi', result)
        self.assertIn('magnitude', result)
        self.assertIn('phase', result)
        self.assertIn('phase_mask', result)
        self.assertEqual(result['swi'].shape, self.matrix_size)
        self.assertEqual(result['magnitude'].shape, self.matrix_size)
        self.assertEqual(result['phase'].shape, self.matrix_size)

    def test_swi_multi_slice(self):
        """测试多切片SWI重建"""
        num_slices = 5
        kspace = np.random.randn(num_slices, *self.matrix_size) + 1j * np.random.randn(num_slices, *self.matrix_size)

        result = self.recon.swi_reconstruct(kspace, te=0.02, sigma=2, power=4, mip_slices=3)
        self.assertIn('swi', result)
        self.assertIn('swi_original', result)
        self.assertEqual(result['swi'].shape, (num_slices, *self.matrix_size))
        self.assertEqual(result['swi_original'].shape, (num_slices, *self.matrix_size))

    def test_phase_mapping(self):
        """测试多回波相位映射(QSM基础)"""
        num_echoes = 3
        tes = [0.01, 0.02, 0.03]

        kspace_multi = np.zeros((num_echoes, *self.matrix_size), dtype=np.complex128)
        for e in range(num_echoes):
            kspace_multi[e] = np.random.randn(*self.matrix_size) + 1j * np.random.randn(*self.matrix_size)

        chi = self.recon.swi_phase_mapping(kspace_multi, tes)
        self.assertEqual(chi.shape, self.matrix_size)
        self.assertTrue(not np.iscomplexobj(chi))

    def test_combine_coil_images(self):
        """测试线圈图像合并"""
        num_coils = 4
        coil_images = np.random.randn(num_coils, *self.matrix_size) + 1j * np.random.randn(num_coils, *self.matrix_size)

        for method in ['sos', 'sum', 'weighted']:
            combined = self.recon.combine_coil_images(coil_images, method=method)
            self.assertEqual(combined.shape, self.matrix_size)


def run_tests():
    """运行所有测试"""
    print("运行MRI模拟器单元测试...")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestPhantom))
    suite.addTests(loader.loadTestsFromTestCase(TestBlochSolver))
    suite.addTests(loader.loadTestsFromTestCase(TestPulseSequences))
    suite.addTests(loader.loadTestsFromTestCase(TestKSpace))
    suite.addTests(loader.loadTestsFromTestCase(TestReconstructor))
    suite.addTests(loader.loadTestsFromTestCase(TestFullPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestParallelImaging))
    suite.addTests(loader.loadTestsFromTestCase(TestFieldInhomogeneity))
    suite.addTests(loader.loadTestsFromTestCase(TestSWIReconstruction))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("[OK] 所有测试通过！")
    else:
        print(f"[ERROR] 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
