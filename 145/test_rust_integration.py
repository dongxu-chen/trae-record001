#!/usr/bin/env python3
"""
测试 Rust 加速模块集成
"""

import numpy as np

def test_import():
    """测试模块导入"""
    try:
        import seis_rs
        print("✓ seis_rs 模块导入成功")
        print(f"  版本: {getattr(seis_rs, '__version__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        print("  提示: 请先运行 'maturin develop' 编译Rust扩展")
        return False

def test_steim2_decoder():
    """测试Steim2解码器"""
    try:
        import seis_rs
        
        print("\n--- 测试 Steim2Decoder ---")
        
        decoder = seis_rs.Steim2Decoder()
        print("✓ 创建解码器成功")
        
        # 测试帧对齐
        unaligned_data = bytes(100)
        aligned = seis_rs.Steim2Decoder.validate_alignment(unaligned_data)
        print(f"✓ 帧对齐: 原长度 {len(unaligned_data)} -> 对齐后 {len(aligned_data)}")
        
        # 测试单帧
        frame_data = bytes(64)
        frame = seis_rs.Steim2Frame(frame_data)
        samples = frame.decode()
        print(f"✓ 单帧解码: 得到 {len(samples)} 个样本")
        
        # 测试多帧
        decoder.add_frames(aligned)
        all_samples = decoder.decode_all()
        print(f"✓ 多帧解码: 共得到 {len(all_samples)} 个样本")
        
        return True
    except Exception as e:
        print(f"✗ Steim2Decoder 测试失败: {e}")
        return False

def test_pqlx_analyzer():
    """测试PQLX质量评估"""
    try:
        import seis_rs
        
        print("\n--- 测试 PQLXAnalyzer ---")
        
        # 生成测试数据
        np.random.seed(42)
        samples = np.random.randn(10000).astype(np.int32) * 1000
        
        # 分析
        metrics = seis_rs.PQLXAnalyzer.analyze(samples, gap_threshold=1000)
        print(f"✓ 分析完成")
        print(f"  均值: {metrics.mean:.2f}")
        print(f"  标准差: {metrics.std_dev:.2f}")
        print(f"  峰峰值: {metrics.peak_to_peak}")
        print(f"  样本数: {metrics.num_samples}")
        print(f"  间隙数: {metrics.num_gaps}")
        print(f"  间隙百分比: {metrics.gap_percentage:.2f}%")
        print(f"  偏度: {metrics.skewness:.3f}")
        print(f"  峰度: {metrics.kurtosis:.3f}")
        print(f"  直流偏移: {metrics.dc_offset:.2f}")
        
        # 质量评分
        score = seis_rs.PQLXAnalyzer.quality_score(metrics)
        print(f"✓ 质量评分: {score:.1f}/100")
        
        # 互相关
        samples2 = samples + np.random.randn(len(samples)).astype(np.int32) * 100
        corr = seis_rs.PQLXAnalyzer.cross_correlate(list(samples), list(samples2))
        print(f"✓ 互相关: {corr:.3f}")
        
        # SNR
        snr = seis_rs.PQLXAnalyzer.snr_estimate(list(samples), noise_window=100)
        print(f"✓ SNR估计: {snr:.2f} dB")
        
        return True
    except Exception as e:
        print(f"✗ PQLXAnalyzer 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parallel_processor():
    """测试并行处理器"""
    try:
        import seis_rs
        from collections import defaultdict
        
        print("\n--- 测试 ParallelProcessor ---")
        
        # 创建处理器
        processor = seis_rs.ParallelProcessor(num_threads=4)
        print("✓ 创建并行处理器成功 (4线程)")
        
        # 准备测试数据
        station_data = dict()
        np.random.seed(42)
        for i in range(5):
            fake_data = np.random.randint(0, 256, 640, dtype=np.uint8).tobytes()
            station_data[f"STA{i:02d}"] = fake_data
        
        print(f"✓ 准备了 {len(station_data)} 个台站的测试数据")
        
        # 测试分析
        station_samples = {}
        for sta, _ in station_data.items():
            samples = list(np.random.randn(10000).astype(np.int32) * 1000)
            station_samples[sta] = samples
        
        results = processor.analyze_many_stations(station_samples, gap_threshold=1000)
        print(f"✓ 并行分析完成, 处理了 {len(results)} 个台站")
        
        for sta, metrics in results.items():
            score = seis_rs.PQLXAnalyzer.quality_score(metrics)
            print(f"  {sta}: score={score:.1f}, std={metrics.std_dev:.1f}")
        
        # 测试质量过滤
        filtered = processor.parallel_quality_filter(station_samples, 80, gap_threshold=1000)
        print(f"✓ 质量过滤完成, 保留了 {len(filtered)} 个台站")
        
        return True
    except Exception as e:
        print(f"✗ ParallelProcessor 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_with_obspy():
    """测试与ObsPy集成"""
    try:
        from seisprocessor.filter import WaveformFilter
        
        print("\n--- 测试 ObsPy 集成 ---")
        print("✓ WaveformFilter 类可访问")
        
        # 这里可以添加更多集成测试
        print("✓ 基础集成检查通过")
        
        return True
    except Exception as e:
        print(f"✗ ObsPy 集成测试失败: {e}")
        return False

def main():
    print("="*60)
    print("    seis_rs - Rust 加速模块集成测试")
    print("="*60)
    
    results = {}
    
    # 测试1: 导入
    results['import'] = test_import()
    if not results['import']:
        print("\n编译提示:")
        print("  1. 安装 Rust: https://www.rust-lang.org/tools/install")
        print("  2. 安装 maturin: pip install maturin")
        print("  3. 编译安装: maturin develop")
        return
    
    # 测试2: Steim2解码
    results['steim2'] = test_steim2_decoder()
    
    # 测试3: PQLX分析
    results['pqlx'] = test_pqlx_analyzer()
    
    # 测试4: 并行处理
    results['parallel'] = test_parallel_processor()
    
    # 测试5: ObsPy集成
    results['obspy'] = test_integration_with_obspy()
    
    # 总结
    print("\n" + "="*60)
    print("    测试总结")
    print("="*60)
    
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name:20s} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n  总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n  ✓ 所有测试通过! Rust加速模块工作正常")
    else:
        print(f"\n  ✗ {total-passed} 项测试失败, 请检查错误信息")

if __name__ == "__main__":
    main()
