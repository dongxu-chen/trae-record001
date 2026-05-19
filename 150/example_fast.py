#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MS Peak Detector - 高性能版本示例
使用 C++ 核心 + Rust FFI 绑定
"""

import numpy as np
import time
import sys

sys.path.insert(0, '.')

import ms_peak_detector as msd

print(f"MS Peak Detector v{msd.__version__}")
print(f"核心库可用: {msd.__core_available__}")
print()


def generate_test_spectrum(num_points=10000, num_peaks=50, noise_level=0.05):
    """生成测试质谱数据"""
    mz = np.linspace(100, 1500, num_points, dtype=np.float64)
    intensity = np.zeros_like(mz)

    # 添加峰
    for i in range(num_peaks):
        peak_mz = np.random.uniform(150, 1450)
        peak_height = np.random.uniform(0.1, 1.0)
        sigma = np.random.uniform(0.1, 0.5)
        intensity += peak_height * np.exp(-(mz - peak_mz)**2 / (2 * sigma**2))

    # 添加一些相邻峰（间距 < 0.5Da）
    for _ in range(10):
        base_mz = np.random.uniform(200, 1400)
        for offset in [0, 0.2, 0.35]:
            peak_height = np.random.uniform(0.2, 0.6)
            intensity += peak_height * np.exp(-(mz - (base_mz + offset))**2 / (2 * 0.05**2))

    # 添加基线
    baseline = 0.1 + 0.0001 * (mz - 100) + 0.00000005 * (mz - 800)**2
    intensity += baseline

    # 添加噪声
    intensity += noise_level * np.random.randn(len(intensity))
    intensity = np.maximum(intensity, 0.01)

    return mz, intensity


def example_1_single_spectrum():
    """示例1: 单谱图处理"""
    print("=" * 60)
    print("示例1: 单谱图处理 (基线校正 + 峰检测)")
    print("=" * 60)

    mz, intensity = generate_test_spectrum(num_points=50000, num_peaks=100)
    print(f"生成谱图: {len(mz)} 个数据点")

    # 基线校正
    corrector = msd.get_baseline_corrector()(method="segmented_asls")

    start = time.time()
    baseline, corrected = corrector.correct(intensity.tolist())
    elapsed = time.time() - start
    print(f"基线校正耗时: {elapsed:.4f}s")
    print(f"基线范围: {min(baseline):.4f} - {max(baseline):.4f}")

    # 峰检测
    detector = msd.get_peak_detector()(method="local_max")

    start = time.time()
    peaks = detector.detect(mz.tolist(), corrected, merge_distance=0.5, snr_threshold=3.0)
    elapsed = time.time() - start

    print(f"峰检测耗时: {elapsed:.4f}s")
    print(f"检测到 {len(peaks)} 个峰")

    # 显示前5个峰
    peaks_sorted = sorted(peaks, key=lambda p: p.intensity, reverse=True)
    print(f"\n前5个峰:")
    for i, peak in enumerate(peaks_sorted[:5]):
        print(f"  {i+1}. m/z={peak.mz:.4f}, 强度={peak.intensity:.4f}, "
              f"SNR={peak.snr:.1f}, 合并={peak.is_merged}")

    print()


def example_2_batch_parallel():
    """示例2: 批量并行处理"""
    print("=" * 60)
    print("示例2: 多谱图并行处理")
    print("=" * 60)

    if not msd.ParallelProcessor:
        print("需要编译Rust核心才能使用并行处理功能")
        print()
        return

    num_spectra = 20
    print(f"生成 {num_spectra} 个谱图用于并行处理...")

    mz_list = []
    intensity_list = []

    for i in range(num_spectra):
        mz, intensity = generate_test_spectrum(num_points=10000, num_peaks=50)
        mz_list.append(mz.tolist())
        intensity_list.append(intensity.tolist())

    processor = msd.ParallelProcessor(num_threads=0)  # 0 = 自动检测

    start = time.time()
    corrected_list, peaks_list = processor.process_pipeline(
        mz_list, intensity_list, merge_distance=0.5, snr_threshold=3.0
    )
    elapsed = time.time() - start

    total_peaks = sum(len(p) for p in peaks_list)
    print(f"并行处理 {num_spectra} 个谱图耗时: {elapsed:.4f}s")
    print(f"平均每个谱图: {elapsed/num_spectra:.4f}s")
    print(f"总共检测到 {total_peaks} 个峰")

    # 显示每个谱图的峰数
    print(f"\n每个谱图的峰数:")
    for i, peaks in enumerate(peaks_list[:10]):
        merged_count = sum(1 for p in peaks if p.is_merged)
        print(f"  谱图 {i}: {len(peaks)} 个峰 ({merged_count} 个合并)")

    print()


def example_3_performance_comparison():
    """示例3: 性能对比 (Python vs C++/Rust)"""
    print("=" * 60)
    print("示例3: Python vs C++/Rust 性能对比")
    print("=" * 60)

    mz, intensity = generate_test_spectrum(num_points=50000, num_peaks=100)
    print(f"测试谱图: {len(mz)} 个数据点")
    print()

    # 测试基线校正
    print("基线校正性能:")
    print("-" * 40)

    # Python版本
    from ms_peak_detector.baseline_correction import BaselineCorrector as BaselineCorrectorPy

    corrector_py = BaselineCorrectorPy(method="segmented_asls")
    start = time.time()
    corrected_py = corrector_py.correct(mz, intensity)
    elapsed_py = time.time() - start
    print(f"  Python:   {elapsed_py:.4f}s")

    # C++/Rust版本（如果可用）
    if msd.__core_available__:
        corrector_fast = msd.get_baseline_corrector()(method="segmented_asls")
        intensity_list = intensity.tolist()
        start = time.time()
        baseline, corrected_fast = corrector_fast.correct(intensity_list)
        elapsed_fast = time.time() - start
        print(f"  C++/Rust: {elapsed_fast:.4f}s")
        print(f"  Speedup:  {elapsed_py / elapsed_fast:.1f}x")
    else:
        print("  C++/Rust: 不可用 (需要编译核心库)")

    print()

    # 测试峰检测
    print("峰检测性能:")
    print("-" * 40)

    # Python版本
    from ms_peak_detector.peak_detection import PeakDetector as PeakDetectorPy

    detector_py = PeakDetectorPy(method="local_max")
    start = time.time()
    peaks_py = detector_py.detect(mz, corrected_py, merge_distance=0.5, snr_threshold=3.0)
    elapsed_py_peak = time.time() - start
    print(f"  Python:   {elapsed_py_peak:.4f}s ({len(peaks_py)} 个峰)")

    # C++/Rust版本
    if msd.__core_available__:
        detector_fast = msd.get_peak_detector()(method="local_max")
        mz_list = mz.tolist()
        start = time.time()
        peaks_fast = detector_fast.detect(mz_list, corrected_fast, merge_distance=0.5, snr_threshold=3.0)
        elapsed_fast_peak = time.time() - start
        print(f"  C++/Rust: {elapsed_fast_peak:.4f}s ({len(peaks_fast)} 个峰)")
        print(f"  Speedup:  {elapsed_py_peak / elapsed_fast_peak:.1f}x")
    else:
        print("  C++/Rust: 不可用 (需要编译核心库)")

    print()


def example_4_pipeline_integration():
    """示例4: 完整分析流程集成"""
    print("=" * 60)
    print("示例4: 完整分析流程集成")
    print("=" * 60)

    pipeline = msd.MSPeakAnalysisPipeline()

    # 生成多谱图数据
    num_spectra = 5
    spectra_data = []
    for i in range(num_spectra):
        mz, intensity = generate_test_spectrum(num_points=20000, num_peaks=50)
        spectra_data.append((mz, intensity))

    print(f"生成 {num_spectra} 个测试谱图")

    # 处理每个谱图
    all_peaks = []
    for i, (mz, intensity) in enumerate(spectra_data):
        # 使用高性能实现
        if msd.__core_available__:
            corrector = msd.get_baseline_corrector()(method="segmented_asls")
            _, corrected = corrector.correct(intensity.tolist())

            detector = msd.get_peak_detector()(method="local_max")
            peaks = detector.detect(mz.tolist(), corrected, merge_distance=0.5, snr_threshold=3.0)
        else:
            # 回退到Python实现
            peaks = pipeline.process_spectrum(mz, intensity)["peaks"]

        all_peaks.append(peaks)
        print(f"  谱图 {i}: {len(peaks)} 个峰")

    # 峰对齐
    print(f"\n峰对齐...")
    aligner = msd.PeakAligner(tolerance=0.01)
    aligned = aligner.align(all_peaks, method="single_linkage")

    print(f"对齐结果: {len(aligned)} 个对齐峰组")

    consensus = aligner.get_consensus_peaks(min_spectra=3)
    print(f"共识峰 (出现在≥3个谱图中): {len(consensus)} 个")

    print()


def main():
    print("MS Peak Detector v0.2.0 - 高性能版本")
    print("架构: C++ 核心算法 + Rust FFI 绑定 + Python PyO3 封装")
    print()

    examples = [
        example_1_single_spectrum,
        example_2_batch_parallel,
        example_3_performance_comparison,
        example_4_pipeline_integration,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"✗ 示例执行失败: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print("所有示例执行完成!")
    print("=" * 60)
    print()
    print("构建说明:")
    print("  cd rust_ffi")
    print("  cargo build --release")
    print("  复制 target/release/ms_peak_detector_core.dll (或 .so/.dylib)")
    print("  到 ms_peak_detector/ 目录下")


if __name__ == "__main__":
    main()
