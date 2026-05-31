import numpy as np
import time
from psf_generator import PSFGenerator
from deconvolution import (RichardsonLucy, BlindRichardsonLucy,
                            TiledFFTConvolver, calculate_psnr, calculate_mse)
from image_utils import ImageProcessor
from scipy.signal import fftconvolve


def test_adaptive_convergence():
    print("=" * 60)
    print("测试1: 自适应迭代 - 残差变化率停止准则")
    print("=" * 60)

    ground_truth = ImageProcessor.generate_test_image(size=256, num_spots=15)
    psf = PSFGenerator.gaussian_psf(21, sigma=3.0)
    blurred = fftconvolve(ground_truth, psf, mode='same')
    blurred += np.random.normal(0, 0.005, blurred.shape)
    blurred = np.clip(blurred, 0, 1)

    thresholds = [1e-3, 1e-4, 1e-5, 1e-6]
    for thresh in thresholds:
        rl = RichardsonLucy(psf, num_iterations=200, convergence_threshold=thresh)
        start_time = time.time()
        deconvolved = rl.deconvolve(blurred)
        elapsed = time.time() - start_time

        psnr = calculate_psnr(ground_truth, deconvolved)
        print(f"  阈值={thresh:.0e}: 实际迭代={rl.actual_iterations:3d}, "
              f"PSNR={psnr:.2f}dB, 时间={elapsed:.3f}s")

    return True


def test_blind_deconvolution():
    print("\n" + "=" * 60)
    print("测试2: 盲去卷积 - PSF自估计")
    print("=" * 60)

    ground_truth = ImageProcessor.generate_test_image(size=128, num_spots=8)
    true_psf = PSFGenerator.gaussian_psf(21, sigma=2.5)
    blurred = fftconvolve(ground_truth, true_psf, mode='same')
    blurred += np.random.normal(0, 0.005, blurred.shape)
    blurred = np.clip(blurred, 0, 1)

    rl_known = RichardsonLucy(true_psf, num_iterations=50, convergence_threshold=1e-4)
    result_known = rl_known.deconvolve(blurred)
    psnr_known = calculate_psnr(ground_truth, result_known)

    blind = BlindRichardsonLucy(psf_size=21, num_outer_iterations=5,
                                 num_inner_iterations=20, convergence_threshold=1e-4)
    start_time = time.time()
    result_blind, est_psf = blind.deconvolve(blurred)
    elapsed = time.time() - start_time

    psnr_blind = calculate_psnr(ground_truth, result_blind)
    psf_diff = np.sqrt(np.mean((true_psf - est_psf) ** 2))

    print(f"  已知PSF去卷积 PSNR: {psnr_known:.2f}dB")
    print(f"  盲去卷积 PSNR:      {psnr_blind:.2f}dB (时间={elapsed:.3f}s)")
    print(f"  PSF估计RMSE:         {psf_diff:.6f}")
    print(f"  盲去卷积PSF历史数:    {len(blind.psf_history)}")

    return True


def test_psf_estimation_methods():
    print("\n" + "=" * 60)
    print("测试3: PSF自估计方法对比")
    print("=" * 60)

    ground_truth = ImageProcessor.generate_test_image(size=128, num_spots=8)
    true_psf = PSFGenerator.gaussian_psf(21, sigma=2.0)
    blurred = fftconvolve(ground_truth, true_psf, mode='same')
    blurred = np.clip(blurred, 0, 1)

    methods = ['autocorrelation', 'cepstrum', 'edge_spread']
    for method in methods:
        est_psf = PSFGenerator.estimate_psf_from_image(blurred, method=method, psf_size=21)
        psf_diff = np.sqrt(np.mean((true_psf - est_psf) ** 2))
        rl = RichardsonLucy(est_psf, num_iterations=30)
        result = rl.deconvolve(blurred)
        psnr = calculate_psnr(ground_truth, result)
        print(f"  {method:18s}: PSF RMSE={psf_diff:.6f}, PSNR={psnr:.2f}dB")

    return True


def test_tiled_convolution():
    print("\n" + "=" * 60)
    print("测试4: 二维分块FFT卷积")
    print("=" * 60)

    image = np.random.rand(512, 512)
    psf = PSFGenerator.gaussian_psf(21, sigma=2.0)

    start_time = time.time()
    full_result = fftconvolve(image, psf, mode='same')
    full_time = time.time() - start_time

    convolver = TiledFFTConvolver(tile_size=256, overlap=64)
    start_time = time.time()
    tiled_result = convolver.convolve2d_tiled(image, psf)
    tiled_time = time.time() - start_time

    diff = np.sqrt(np.mean((full_result - tiled_result) ** 2))
    print(f"  全图FFT卷积:  {full_time:.3f}s")
    print(f"  分块FFT卷积:  {tiled_time:.3f}s")
    print(f"  分块与全图差异 RMSE: {diff:.6f}")

    tile_sizes = [128, 256, 512]
    for ts in tile_sizes:
        convolver = TiledFFTConvolver(tile_size=ts, overlap=64)
        start_time = time.time()
        _ = convolver.convolve2d_tiled(image, psf)
        t = time.time() - start_time
        print(f"  块大小={ts:4d}: {t:.3f}s")

    return True


def test_tiled_deconvolution():
    print("\n" + "=" * 60)
    print("测试5: 分块去卷积 vs 标准去卷积")
    print("=" * 60)

    ground_truth = ImageProcessor.generate_test_image(size=256, num_spots=10)
    psf = PSFGenerator.gaussian_psf(21, sigma=2.5)
    blurred = fftconvolve(ground_truth, psf, mode='same')
    blurred += np.random.normal(0, 0.005, blurred.shape)
    blurred = np.clip(blurred, 0, 1)

    rl = RichardsonLucy(psf, num_iterations=30, convergence_threshold=1e-4)
    start_time = time.time()
    result_std = rl.deconvolve(blurred)
    std_time = time.time() - start_time

    rl_tiled = RichardsonLucy(psf, num_iterations=30, convergence_threshold=1e-4,
                               tile_size=128)
    start_time = time.time()
    result_tiled = rl_tiled.deconvolve_tiled(blurred)
    tiled_time = time.time() - start_time

    psnr_std = calculate_psnr(ground_truth, result_std)
    psnr_tiled = calculate_psnr(ground_truth, result_tiled)
    diff = np.sqrt(np.mean((result_std - result_tiled) ** 2))

    print(f"  标准去卷积: PSNR={psnr_std:.2f}dB, 时间={std_time:.3f}s, "
          f"迭代={rl.actual_iterations}")
    print(f"  分块去卷积: PSNR={psnr_tiled:.2f}dB, 时间={tiled_time:.3f}s, "
          f"迭代={rl_tiled.actual_iterations}")
    print(f"  结果差异 RMSE: {diff:.6f}")

    return True


def test_convergence_history():
    print("\n" + "=" * 60)
    print("测试6: 收敛历史分析")
    print("=" * 60)

    ground_truth = ImageProcessor.generate_test_image(size=128, num_spots=8)
    psf = PSFGenerator.gaussian_psf(21, sigma=2.5)
    blurred = fftconvolve(ground_truth, psf, mode='same')
    blurred += np.random.normal(0, 0.005, blurred.shape)
    blurred = np.clip(blurred, 0, 1)

    rl = RichardsonLucy(psf, num_iterations=100, convergence_threshold=1e-6)
    rl.deconvolve(blurred)

    history = rl.convergence_history
    print(f"  总迭代次数: {rl.actual_iterations}")
    print(f"  初始变化率: {history[0]:.6f}")
    print(f"  最终变化率: {history[-1]:.6f}")
    if len(history) > 10:
        print(f"  第5次变化率:  {history[4]:.6f}")
        print(f"  第10次变化率: {history[9]:.6f}")
        print(f"  收敛比:       {history[0] / (history[-1] + 1e-15):.1f}x")

    return True


def run_all_tests():
    print("荧光显微镜图像去卷积 - 新特性测试\n")
    test_adaptive_convergence()
    test_blind_deconvolution()
    test_psf_estimation_methods()
    test_tiled_convolution()
    test_tiled_deconvolution()
    test_convergence_history()
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    run_all_tests()
