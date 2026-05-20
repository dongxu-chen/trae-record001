#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MS Peak Detector - 使用示例
展示所有修复和增强功能
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from ms_peak_detector import (
    MSPeakAnalysisPipeline,
    BaselineCorrector,
    PeakDetector,
    PeakAligner,
    IsotopeDetector
)

np.random.seed(42)

def example_1_peak_merging():
    """示例1: 相邻峰合并 (距离<0.5Da)"""
    print("=" * 70)
    print("示例1: 相邻峰合并功能")
    print("=" * 70)
    
    pipeline = MSPeakAnalysisPipeline()
    
    # 生成包含相邻峰的谱图
    mz = np.linspace(200, 800, 5000)
    intensity = np.zeros_like(mz)
    
    # 添加几组相邻峰（间距<0.5Da）
    peak_groups = [
        (300.0, [0, 0.2, 0.45]),       # 3个峰，间距<0.5Da
        (500.0, [0, 0.3]),              # 2个峰
        (700.0, [0]),                   # 1个峰
    ]
    
    for base_mz, offsets in peak_groups:
        for i, offset in enumerate(offsets):
            intensity += (1.0 - i * 0.2) * np.exp(-(mz - (base_mz + offset))**2 / (2 * 0.05**2))
    
    # 添加基线和噪声
    intensity += 0.0001 * (mz - 200) + 0.1
    intensity += 0.02 * np.random.randn(len(intensity))
    
    detector = PeakDetector(method="local_max")
    
    # 不合并
    peaks_no_merge = detector.detect(mz, intensity, merge_distance=0)
    print(f"不合并时: 检测到 {len(peaks_no_merge)} 个峰")
    
    # 合并距离<0.5Da的峰
    peaks_merged = detector.detect(mz, intensity, merge_distance=0.5)
    print(f"合并后: 检测到 {len(peaks_merged)} 个峰")
    
    # 显示合并的峰
    merged_peaks = [p for p in peaks_merged if p.get("merged_count", 1) > 1]
    print(f"其中 {len(merged_peaks)} 个是合并后的峰:")
    for i, peak in enumerate(merged_peaks):
        print(f"  峰 {i+1}: m/z={peak['mz']:.2f}, 合并了 {peak['merged_count']} 个原始峰")
    
    print()
    return True

def example_2_segmented_baseline():
    """示例2: 分段非对称最小二乘基线校正"""
    print("=" * 70)
    print("示例2: 分段非对称最小二乘基线校正 (内存优化)")
    print("=" * 70)
    
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
    
    print(f"处理谱图大小: {len(mz)} 个数据点")
    print(f"分段大小: 5000, 重叠: 500")
    print(f"处理耗时: {elapsed:.2f} 秒")
    print(f"基线估计完成: {corrector.get_baseline().shape}")
    
    # 也可以试试传统ASLS对比
    corrector2 = BaselineCorrector(method="asls")
    start2 = time.time()
    corrected2 = corrector2.correct(mz[:10000], intensity[:10000])
    elapsed2 = time.time() - start2
    print(f"传统ASLS (1万点): {elapsed2:.2f} 秒 (对于大数据会显著变慢)")
    
    print()
    return True

def example_3_single_linkage_alignment():
    """示例3: 单链聚类峰对齐"""
    print("=" * 70)
    print("示例3: 单链聚类峰对齐 (低内存占用)")
    print("=" * 70)
    
    # 生成多个谱图的峰
    peaks_list = []
    num_spectra = 10
    num_peaks_per_spectrum = 20
    
    for spectrum_idx in range(num_spectra):
        peaks = []
        for peak_idx in range(num_peaks_per_spectrum):
            # 基础m/z位置
            base_mz = 200 + peak_idx * 40
            # 每个谱图有微小偏移
            mz = base_mz + np.random.normal(0, 0.03)
            intensity = np.random.uniform(0.5, 1.5)
            peaks.append({
                "mz": mz,
                "intensity": intensity,
                "index": peak_idx,
                "left_index": peak_idx,
                "right_index": peak_idx,
                "snr": 10.0
            })
        peaks_list.append(peaks)
    
    aligner = PeakAligner(tolerance=0.05, tolerance_type="absolute")
    
    import time
    start = time.time()
    aligned = aligner.align(peaks_list, method="single_linkage")
    elapsed = time.time() - start
    
    print(f"对齐 {num_spectra} 个谱图, 每个谱图 {num_peaks_per_spectrum} 个峰")
    print(f"总共 {sum(len(p) for p in peaks_list)} 个峰")
    print(f"发现 {len(aligned)} 个对齐峰组")
    print(f"单链聚类对齐耗时: {elapsed:.4f} 秒")
    
    # 验证共识峰
    consensus = aligner.get_consensus_peaks(min_spectra=8)
    print(f"在至少8个谱图中出现的共识峰: {len(consensus)} 个")
    
    # 显示前3个对齐峰组
    print("\n前3个对齐峰组:")
    for i, group in enumerate(aligned[:3]):
        spectra = set(p["spectrum_idx"] for p in group["peaks"])
        print(f"  组 {i+1}: m/z={group['mz']:.2f}, 出现在 {len(spectra)} 个谱图中")
    
    print()
    return True

def example_4_isotope_charge_validation():
    """示例4: 同位素检测的电荷态验证和评分过滤"""
    print("=" * 70)
    print("示例4: 同位素检测 - 电荷态验证和评分过滤")
    print("=" * 70)
    
    # 生成包含多个电荷态同位素模式的峰
    peaks = []
    
    # 电荷态2的同位素峰
    base_mz = 500.0
    charge = 2
    c13_diff = 1.0033548378 / charge
    for i in range(4):
        peaks.append({
            "mz": base_mz + i * c13_diff,
            "intensity": 1.0 * (0.95 ** i),
            "index": i,
            "left_index": i,
            "right_index": i,
            "snr": 15.0
        })
    
    # 电荷态3的同位素峰
    base_mz2 = 700.0
    charge2 = 3
    c13_diff2 = 1.0033548378 / charge2
    for i in range(3):
        peaks.append({
            "mz": base_mz2 + i * c13_diff2,
            "intensity": 0.8 * (0.95 ** i),
            "index": i + 4,
            "left_index": i + 4,
            "right_index": i + 4,
            "snr": 12.0
        })
    
    # 添加一些噪声峰
    for i in range(10):
        peaks.append({
            "mz": 600 + i * 5.2 + np.random.normal(0, 0.1),
            "intensity": 0.1,
            "index": i + 7,
            "left_index": i + 7,
            "right_index": i + 7,
            "snr": 2.0
        })
    
    detector = IsotopeDetector(tolerance=0.02)
    
    clusters = detector.detect_isotopes(peaks, min_charge=1, max_charge=5, min_score=0.3)
    
    print(f"检测到 {len(clusters)} 个同位素簇")
    
    for i, cluster in enumerate(clusters):
        print(f"\n  簇 {i+1}:")
        print(f"    单同位素m/z: {cluster['monoisotopic_mz']:.4f}")
        print(f"    电荷态: {cluster['charge']}")
        print(f"    峰数量: {cluster['size']}")
        print(f"    总评分: {cluster['score']:.3f}")
        print(f"    评分组件:")
        print(f"      - 峰大小分数: {cluster['score_components']['size_score']:.3f}")
        print(f"      - 电荷惩罚: {cluster['score_components']['charge_penalty']:.3f}")
        print(f"      - 比率分数: {cluster['score_components']['ratio_score']:.3f}")
        print(f"      - 强度递减分数: {cluster['score_components']['intensity_decrease_score']:.3f}")
        
        # 验证电荷态
        is_valid = detector.validate_charge_state(cluster)
        print(f"    电荷态有效性: {'✓ 有效' if is_valid else '✗ 无效'}")
    
    # 过滤高评分的有效簇
    valid_clusters = detector.filter_valid_clusters(min_score=0.6)
    print(f"\n高评分 (≥0.6) 的有效同位素簇: {len(valid_clusters)} 个")
    
    # 测试理论同位素分布
    formula = "C12H22O11"  # 蔗糖
    theoretical = detector.calculate_theoretical_isotope_distribution(formula)
    print(f"\n{formula} 的理论同位素分布:")
    sorted_keys = sorted(theoretical['distribution'].keys())
    for k in sorted_keys[:5]:
        print(f"  +{k}C: {theoretical['distribution'][k]:.4f}")
    
    print()
    return True

def example_5_full_pipeline():
    """示例5: 完整质谱数据处理流程"""
    print("=" * 70)
    print("示例5: 完整质谱数据处理流程 (所有修复整合)")
    print("=" * 70)
    
    pipeline = MSPeakAnalysisPipeline()
    
    # 生成测试谱图
    mz, intensity = pipeline.generate_test_spectrum(
        num_peaks=30,
        mz_range=(100, 1500),
        noise_level=0.04,
        baseline_slope=0.0005
    )
    
    print(f"生成测试谱图: {len(mz)} 个数据点")
    
    # 完整处理流程 - 使用所有新功能
    results = pipeline.process_spectrum(
        mz, intensity,
        baseline_method="segmented_asls",      # 分段基线校正
        peak_detection_method="local_max",
        merge_distance=0.5,                     # 相邻峰合并
        min_isotope_score=0.4,                  # 同位素评分过滤
        min_charge=1,
        max_charge=5,
        segment_size=2000,
        overlap=200
    )
    
    print(f"\n处理结果:")
    print(f"  ✓ 分段基线校正完成")
    print(f"  ✓ 检测到 {len(results['peaks'])} 个峰 (已合并相邻峰)")
    print(f"  ✓ 发现 {len(results['isotope_clusters'])} 个有效同位素簇")
    
    # 显示合并的峰
    merged_count = sum(1 for p in results['peaks'] if p.get('merged_count', 1) > 1)
    print(f"\n  其中 {merged_count} 个峰是合并后的")
    
    # 显示前5个峰
    print("\n前5个峰 (按强度排序):")
    sorted_peaks = sorted(results['peaks'], key=lambda x: x['intensity'], reverse=True)
    for i, peak in enumerate(sorted_peaks[:5]):
        merged_info = f", 合并了 {peak.get('merged_count', 1)} 个峰" if peak.get('merged_count', 1) > 1 else ""
        print(f"  {i+1}. m/z={peak['mz']:.2f}, 强度={peak['intensity']:.3f}, "
              f"SNR={peak.get('snr', 0):.1f}{merged_info}")
    
    # 显示同位素簇
    if results['isotope_clusters']:
        print(f"\n检测到的同位素簇 (共 {len(results['isotope_clusters'])} 个):")
        for i, cluster in enumerate(results['isotope_clusters'][:3]):
            print(f"  {i+1}. m/z={cluster['monoisotopic_mz']:.2f}, "
                  f"电荷={cluster['charge']}, 峰数={cluster['size']}, "
                  f"评分={cluster['score']:.3f}")
    
    print("\n✓ 完整处理流程完成！")
    print()
    return True

def main():
    print("MS Peak Detector - 修复功能演示")
    print("=" * 70)
    print()
    
    examples = [
        example_1_peak_merging,
        example_2_segmented_baseline,
        example_3_single_linkage_alignment,
        example_4_isotope_charge_validation,
        example_5_full_pipeline
    ]
    
    passed = 0
    failed = 0
    
    for example in examples:
        try:
            if example():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ 示例执行失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 70)
    print(f"执行总结: {passed} 个成功, {failed} 个失败")
    print("=" * 70)
    
    if failed == 0:
        print("\n所有示例执行成功! ✓")
        print("\n已实现的修复功能:")
        print("  1. 相邻峰合并 (距离<0.5Da可配置)")
        print("  2. 分段非对称最小二乘基线校正 (内存优化)")
        print("  3. 单链聚类峰对齐 (低内存占用, O(N)复杂度)")
        print("  4. 同位素检测电荷态验证和评分过滤")
        return 0
    else:
        print("\n部分示例执行失败! ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
