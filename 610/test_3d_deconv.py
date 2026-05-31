import numpy as np
import time
from czi_reader import SimulatedCZIGenerator
from deconvolution_3d import (RichardsonLucy3D, MultiChannelDeconvolver,
                               PSF3DGenerator)
from quality_metrics import (DeconvolutionQualityReport,
                              evaluate_3d_volume, evaluate_multichannel)
from psf_generator import PSFGenerator
from deconvolution import calculate_psnr


def test_3d_deconvolution():
    print("=" * 60)
    print("测试1: 3D去卷积")
    print("=" * 60)

    ground_truth = SimulatedCZIGenerator.generate_test_3d(
        size_z=8, size_y=64, size_x=64, num_channels=1, num_spots_per_slice=5
    )[0]

    psf_3d = PSF3DGenerator.gaussian_3d(size_xy=11, size_z=5, sigma_xy=2.0, sigma_z=1.0)
    from scipy.signal import fftconvolve
    blurred = np.zeros_like(ground_truth)
    for z in range(ground_truth.shape[0]):
        blurred[z] = fftconvolve(ground_truth[z], psf_3d[psf_3d.shape[0]//2], mode='same')
    blurred += np.random.normal(0, 0.005, blurred.shape)
    blurred = np.clip(blurred, 0, 1)

    rl3d = RichardsonLucy3D(psf_3d, num_iterations=20, convergence_threshold=1e-4)
    start = time.time()
    result = rl3d.deconvolve(blurred)
    elapsed = time.time() - start

    psnr_blurred = calculate_psnr(ground_truth, blurred)
    psnr_deconv = calculate_psnr(ground_truth, result)

    print(f"  数据形状: {ground_truth.shape}")
    print(f"  去卷积前PSNR: {psnr_blurred:.2f} dB")
    print(f"  去卷积后PSNR: {psnr_deconv:.2f} dB")
    print(f"  PSNR提升: {psnr_deconv - psnr_blurred:.2f} dB")
    print(f"  实际迭代次数: {rl3d.actual_iterations}")
    print(f"  耗时: {elapsed:.2f}s")

    return True


def test_quality_metrics():
    print("\n" + "=" * 60)
    print("测试2: 质量评估指标")
    print("=" * 60)

    ground_truth = np.zeros((128, 128))
    for _ in range(10):
        x, y = np.random.randint(20, 108, 2)
        r = np.random.randint(2, 5)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx*dx + dy*dy <= r*r:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < 128 and 0 <= nx < 128:
                        ground_truth[ny, nx] = 1.0

    from scipy.ndimage import gaussian_filter
    ground_truth = gaussian_filter(ground_truth, sigma=0.5)

    psf = PSFGenerator.gaussian_psf(21, sigma=2.0)
    from scipy.signal import fftconvolve
    blurred = fftconvolve(ground_truth, psf, mode='same')
    blurred = np.clip(blurred + np.random.normal(0, 0.01, blurred.shape), 0, 1)

    from deconvolution import RichardsonLucy
    rl = RichardsonLucy(psf, num_iterations=30, convergence_threshold=1e-4)
    deconvolved = rl.deconvolve(blurred)

    report = DeconvolutionQualityReport()
    report.evaluate(blurred, deconvolved, ground_truth)

    print(f"  SNR提升: {report.improvements['snr_gain_db']:.2f} dB")
    print(f"  CNR提升: {report.improvements['cnr_gain']:.2f}")
    print(f"  锐度提升: {report.improvements['sharpness_gain_pct']:.1f}%")
    print(f"  参考PSNR: {report.metrics_after['psnr']:.2f} dB")
    print(f"  参考SSIM: {report.metrics_after['ssim']:.4f}")

    print("\n  完整报告:")
    print(report.generate_report_text())

    return True


def test_multichannel_deconv():
    print("\n" + "=" * 60)
    print("测试3: 多通道去卷积")
    print("=" * 60)

    image = SimulatedCZIGenerator.generate_test_3d(
        size_z=1, size_y=64, size_x=64, num_channels=3, num_spots_per_slice=5
    )
    image = image[:, 0, :, :]

    mc = MultiChannelDeconvolver(num_iterations=15, convergence_threshold=1e-4)
    start = time.time()
    result = mc.deconvolve_channels(image)
    elapsed = time.time() - start

    print(f"  通道数: {image.shape[0]}")
    print(f"  输入形状: {image.shape}")
    print(f"  输出形状: {result.shape}")
    print(f"  耗时: {elapsed:.2f}s")

    reports = evaluate_multichannel(image, result)
    for c, rep in enumerate(reports):
        print(f"  通道{c+1} SNR提升: {rep.improvements['snr_gain_db']:.2f} dB")

    return True


def test_3d_quality_evaluation():
    print("\n" + "=" * 60)
    print("测试4: 3D体积质量评估")
    print("=" * 60)

    volume = SimulatedCZIGenerator.generate_test_3d(
        size_z=6, size_y=64, size_x=64, num_channels=1, num_spots_per_slice=4
    )[0]

    psf_3d = PSF3DGenerator.gaussian_3d(11, 5, 2.0, 1.0)
    from scipy.signal import fftconvolve
    blurred = np.zeros_like(volume)
    for z in range(volume.shape[0]):
        blurred[z] = fftconvolve(volume[z], psf_3d[psf_3d.shape[0]//2], mode='same')
    blurred = np.clip(blurred, 0, 1)

    rl3d = RichardsonLucy3D(psf_3d, num_iterations=15, convergence_threshold=1e-4)
    deconvolved = rl3d.deconvolve(blurred)

    slice_reports, avg_imp = evaluate_3d_volume(blurred, deconvolved, volume)

    print(f"  Z层数: {volume.shape[0]}")
    print(f"  平均SNR提升: {avg_imp['snr_gain_db']:.2f} dB")
    print(f"  平均CNR提升: {avg_imp['cnr_gain']:.2f}")
    print(f"  平均锐度提升: {avg_imp['sharpness_gain_pct']:.1f}%")

    return True


def test_czi_reader():
    print("\n" + "=" * 60)
    print("测试5: CZI读取器功能")
    print("=" * 60)

    from czi_reader import CZIReader

    print(f"  czifile库可用: {CZIReader.available()}")

    test_data = SimulatedCZIGenerator.generate_test_3d(
        size_z=8, size_y=128, size_x=128, num_channels=2, num_spots_per_slice=6
    )
    print(f"  模拟CZI形状: {test_data.shape} (C x Z x Y x X)")

    normalized = CZIReader.normalize_to_float(test_data.astype(np.uint16))
    print(f"  归一化后范围: [{normalized.min():.3f} - {normalized.max():.3f}]")

    ch0 = CZIReader.get_channels(test_data, 0)
    print(f"  单通道提取形状: {ch0.shape}")

    z5 = CZIReader.get_zslice(test_data, 3)
    print(f"  Z层提取形状: {z5.shape}")

    return True


def run_all_tests():
    print("荧光显微镜3D多通道去卷积 - 新功能测试\n")

    all_passed = True

    try:
        test_czi_reader()
    except Exception as e:
        print(f"  错误: {e}")
        all_passed = False

    try:
        test_quality_metrics()
    except Exception as e:
        import traceback
        print(f"  错误: {e}\n{traceback.format_exc()}")
        all_passed = False

    try:
        test_3d_deconvolution()
    except Exception as e:
        import traceback
        print(f"  错误: {e}\n{traceback.format_exc()}")
        all_passed = False

    try:
        test_multichannel_deconv()
    except Exception as e:
        import traceback
        print(f"  错误: {e}\n{traceback.format_exc()}")
        all_passed = False

    try:
        test_3d_quality_evaluation()
    except Exception as e:
        import traceback
        print(f"  错误: {e}\n{traceback.format_exc()}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试通过!")
    else:
        print("部分测试失败!")
    print("=" * 60)

    return all_passed


if __name__ == '__main__':
    run_all_tests()
