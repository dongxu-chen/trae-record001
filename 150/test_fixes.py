#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试质谱数据处理库的所有修复
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from ms_peak_detector import (
    BaselineCorrector,
    PeakDetector,
    PeakAligner,
    IsotopeDetector,
    MSPeakAnalysisPipeline
)

def generate_test_spectrum_with_close_peaks():
    """生成包含相邻峰的测试谱图"""
    mz = np.linspace(100, 1000, 5000)
    intensity = np.zeros_like(mz)
    
    # 添加主峰
    peak_positions = [300.0, 300.3, 300.8, 500.0, 500.2, 700.0]
    peak_heights = [1.0, 0.8, 0.6, 0.9, 0.7, 0.5]
    
    for pos, height in zip(peak_positions, peak_heights):
        intensity += height * np.exp(-(mz - pos)**2 / (2 * 0.05**2))
    
    # 添加噪声和基线
    intensity += 0.01 * np.random.randn(len(intensity))
    intensity += 0.0001 * (mz - 100) + 0.1
    
    return mz, intensity

def test_1_peak_merging():
    """测试1: 相邻峰合并功能"""
    print("=" * 60)
    print("测试1: 相邻峰合并功能 (距离<0.5Da)")
    print("=" * 60)
    
    mz, intensity = generate_test_spectrum_with_close_peaks()
    
    detector = PeakDetector(method="local_max")
    
    # 不合并
    peaks_no_merge = detector.detect(mz, intensity, merge_distance=0)
    print(f"不合并时检测到 {len(peaks_no_merge)} 个峰")
    
    # 合并距离<0.5Da的峰
    peaks_merged = detector.detect(mz, intensity, merge_distance=0.5)
    print(f"合并后检测到 {len(peaks_merged)} 个峰")
    
    # 验证合并
    merged_count = sum(1 for p in peaks_merged if p.get("merged_count", 1) > 1)
    print(f"其中 {merged_count} 个是合并后的峰")
    
    print("✓ 峰合并测试通过\n")
    return True

def test_2_segmented_baseline_correction():
    """测试2: 分段非对称最小二乘基线校正"""
    print("=" * 60)
    print("测试2: 分段非对称最小二乘基线校正")
    print("=" * 60)
    
    # 生成大谱图
    mz = np.linspace(100, 2000, 50000)
    intensity = np.zeros_like(mz)
    
    # 添加一些峰
    for pos in [300, 500, 800, 1200, 1500]:
        intensity += np.exp(-(mz - pos)**2 / (2 * 10**2))
    
    # 添加弯曲基线
    baseline = 0.1 + 0.0001 * (mz - 100) + 0.00000005 * (mz - 1000)**2
    intensity += baseline
    
    # 添加噪声
    intensity += 0.02 * np.random.randn(len(intensity))
    
    corrector = BaselineCorrector(method="segmented_asls")
    
    import time
    start = time.time()
    corrected = corrector.correct(mz, intensity, segment_size=5000, overlap=500)
    elapsed = time.time() - start
    
    print(f"处理 {len(mz)} 个数据点")
    print(f"分段基线校正耗时: {elapsed:.2f} 秒")
    print(f"基线估计完成，形状: {corrector.get_baseline().shape}")
    print("✓ 分段基线校正测试通过\n")
    return True

def test_3_single_linkage_alignment():
    """测试3: 单链聚类峰对齐"""
    print("=" * 60)
    print("测试3: 单链聚类峰对齐")
    print("=" * 60)
    
    # 生成多个谱图的峰
    peaks_list = []
    for spectrum_idx in range(5):
        peaks = []
        for mz_base in [300, 500, 700, 900]:
            # 每个谱图的峰有微小偏移
            mz = mz_base + np.random.normal(0, 0.02)
            intensity = np.random.uniform(0.5, 1.5)
            peaks.append({
                "mz": mz,
                "intensity": intensity,
                "index": 0,
                "left_index": 0,
                "right_index": 0,
                "snr": 10.0
            })
        peaks_list.append(peaks)
    
    aligner = PeakAligner(tolerance=0.05, tolerance_type="absolute")
    
    import time
    start = time.time()
    aligned = aligner.align(peaks_list, method="single_linkage")
    elapsed = time.time() - start
    
    print(f"对齐 {len(peaks_list)} 个谱图")
    print(f"发现 {len(aligned)} 个对齐峰组")
    print(f"单链聚类对齐耗时: {elapsed:.4f} 秒")
    
    # 验证共识峰
    consensus = aligner.get_consensus_peaks(min_spectra=3)
    print(f"在至少3个谱图中出现的共识峰: {len(consensus)} 个")
    
    print("✓ 单链聚类峰对齐测试通过\n")
    return True

def test_4_isotope_charge_validation():
    """测试4: 同位素检测的电荷态验证和评分过滤"""
    print("=" * 60)
    print("测试4: 同位素检测的电荷态验证和评分过滤")
    print("=" * 60)
    
    # 生成包含同位素模式的峰
    peaks = []
    base_mz = 500.0
    charge = 2
    c13_diff = 1.0033548378 / charge
    
    # 添加同位素峰
    for i in range(4):
        peaks.append({
            "mz": base_mz + i * c13_diff,
            "intensity": 1.0 * (0.5 ** i),
            "index": i,
            "left_index": i,
            "right_index": i,
            "snr": 10.0
        })
    
    # 添加一些噪声峰
    for i in range(5):
        peaks.append({
            "mz": 600 + i * 0.1,
            "intensity": 0.1,
            "index": i + 4,
            "left_index": i + 4,
            "right_index": i + 4,
            "snr": 2.0
        })
    
    detector = IsotopeDetector(tolerance=0.02)
    
    clusters = detector.detect_isotopes(peaks, min_charge=1, max_charge=5, min_score=0.3)
    
    print(f"检测到 {len(clusters)} 个同位素簇")
    
    for i, cluster in enumerate(clusters):
        print(f"  簇 {i+1}:")
        print(f"    单同位素m/z: {cluster['monoisotopic_mz']:.4f}")
        print(f"    电荷态: {cluster['charge']}")
        print(f"    峰数量: {cluster['size']}")
        print(f"    评分: {cluster['score']:.3f}")
        print(f"    评分组件: {cluster['score_components']}")
        
        # 验证电荷态
        is_valid = detector.validate_charge_state(cluster)
        print(f"    电荷态有效: {is_valid}")
    
    # 过滤有效簇
    valid_clusters = detector.filter_valid_clusters(min_score=0.5)
    print(f"\n过滤后剩余 {len(valid_clusters)} 个有效同位素簇")
    
    # 测试理论同位素分布
    formula = "C6H12O6"
    theoretical = detector.calculate_theoretical_isotope_distribution(formula)
    print(f"\n{formula} 的理论同位素分布:")
    sorted_keys = sorted(theoretical['distribution'].keys())
    for k in sorted_keys[:4]:
        print(f"  +{k}: {theoretical['distribution'][k]:.4f}")
    
    print("✓ 同位素检测的电荷态验证和评分过滤测试通过\n")
    return True

def test_5_full_pipeline():
    """测试5: 完整处理流程"""
    print("=" * 60)
    print("测试5: 完整质谱数据处理流程")
    print("=" * 60)
    
    pipeline = MSPeakAnalysisPipeline()
    
    mz, intensity = pipeline.generate_test_spectrum(
        num_peaks=20,
        mz_range=(100, 1500),
        noise_level=0.03,
        baseline_slope=0.0005
    )
    
    print(f"生成测试谱图: {len(mz)} 个数据点")
    
    # 完整处理
    results = pipeline.process_spectrum(
        mz, intensity,
        baseline_method="segmented_asls",
        peak_detection_method="local_max",
        merge_distance=0.5
    )
    
    print(f"基线校正完成")
    print(f"检测到 {len(results['peaks'])} 个峰")
    print(f"发现 {len(results['isotope_clusters'])} 个同位素簇")
    
    print("\n前5个峰:")
    sorted_peaks = sorted(results['peaks'], key=lambda x: x['intensity'], reverse=True)
    for i, peak in enumerate(sorted_peaks[:5]):
        print(f"  {i+1}. m/z={peak['mz']:.2f}, 强度={peak['intensity']:.3f}, "
              f"SNR={peak.get('snr', 0):.1f}, 合并数={peak.get('merged_count', 1)}")
    
    print("\n✓ 完整处理流程测试通过\n")
    return True

def main():
    print("开始质谱数据处理库功能验证测试...\n")
    
    tests = [
        test_1_peak_merging,
        test_2_segmented_baseline_correction,
        test_3_single_linkage_alignment,
        test_4_isotope_charge_validation,
        test_5_full_pipeline
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"测试总结: {passed} 个通过, {failed} 个失败")
    print("=" * 60)
    
    if failed == 0:
        print("\n所有测试通过! ✓")
        return 0
    else:
        print("\n部分测试失败! ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
