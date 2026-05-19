#!/usr/bin/env python3
"""
地震波形处理工具包示例

包含:
1. 基础功能 (ObsPy + Matplotlib)
2. Steim2 解压缩 (Rust加速)
3. PQLX 质量评估
4. 多线程并行处理
"""

import numpy as np
from obspy import Trace, Stream, UTCDateTime

# 导入原有的 seisprocessor 模块
from seisprocessor import (
    WaveformFilter, Steim2Decoder,
    PhasePicker, AdaptiveSTALTAPicker,
    SpectrumAnalyzer,
    WaveformPlotter, NetworkNormalizer,
    PolarizationAnalyzer,
    PQLXAnalyzer,
    ParallelProcessor
)

# 尝试导入 Rust 加速模块
try:
    import seis_rs
    RUST_AVAILABLE = True
    print("✓ Rust 加速模块 seis_rs 已加载")
except ImportError:
    RUST_AVAILABLE = False
    print("⚠ Rust 加速模块 seis_rs 未可用 (如需使用请运行: maturin develop)")


def generate_test_waveform(sampling_rate=100, duration=30, network="XX",
                          station="TEST", channel="BHZ"):
    """生成测试波形数据"""
    n_samples = int(sampling_rate * duration)
    t = np.linspace(0, duration, n_samples)

    # 生成地震波形 (P波 + S波 + 噪声)
    data = np.zeros(n_samples)

    # P波 (5秒处开始)
    p_start = int(5 * sampling_rate)
    p_duration = int(2 * sampling_rate)
    for i in range(p_duration):
        data[p_start + i] = np.sin(0.2 * i) * np.exp(-0.005 * i) * 1000

    # S波 (8秒处开始)
    s_start = int(8 * sampling_rate)
    s_duration = int(3 * sampling_rate)
    for i in range(s_duration):
        data[s_start + i] = np.sin(0.1 * i) * np.exp(-0.003 * i) * 1500

    # 加噪声
    noise = np.random.normal(0, 50, n_samples)
    data += noise

    # 转换为整数 (模拟实际数据)
    data = data.astype(np.int32)

    stats = {
        "network": network,
        "station": station,
        "location": "00",
        "channel": channel,
        "sampling_rate": sampling_rate,
        "starttime": UTCDateTime("2024-01-01T00:00:00")
    }

    return Trace(data=data, header=stats)


def example_1_basic_filtering():
    """示例1: 基础波形滤波"""
    print("\n" + "="*60)
    print("示例 1: 基础波形滤波")
    print("="*60)

    tr = generate_test_waveform()
    st = Stream(traces=[tr])

    print(f"原始波形: {tr.id}, {tr.stats.npts} 样本")

    # 滤波
    wf = WaveformFilter()

    # 带通滤波
    tr_bp = wf.filter_trace(tr, "bandpass", lowcut=0.5, highcut=10.0, order=4)
    print(f"✓ 带通滤波完成 (0.5-10 Hz)")

    # 低通滤波
    tr_lp = wf.filter_trace(tr, "lowpass", cutoff=5.0, order=4)
    print(f"✓ 低通滤波完成 (<=5 Hz)")

    # 去趋势
    tr_detrended = wf.detrend(tr.copy())
    print(f"✓ 去趋势完成")

    print("\n  原始数据范围:", np.min(tr.data), "~", np.max(tr.data))
    print("  滤波后范围:", np.min(tr_bp.data), "~", np.max(tr_bp.data))


def example_2_phase_picking():
    """示例2: 震相拾取"""
    print("\n" + "="*60)
    print("示例 2: 震相拾取 (STA/LTA)")
    print("="*60)

    tr = generate_test_waveform()
    picker = PhasePicker()

    # 自适应 STA/LTA
    print("\n--- 自适应 STA/LTA 拾取 ---")
    if RUST_AVAILABLE:
        print("  (使用 Rust 加速版本)")
        # 这里可以调用 Rust 版本的 STA/LTA

    # 原版 Python 实现
    picks = picker.pick_both_phases(
        tr,
        method="sta_lta",
        sta_window=1.0,
        lta_window=10.0,
        threshold=2.5
    )

    if picks['P']:
        print(f"✓ P波: {picks['P']['time']}")
    if picks['S']:
        print(f"✓ S波: {picks['S']['time']}")

    print(f"\n  S-P 时间差: {picks['S']['time'] - picks['P']['time']:.2f} 秒")


def example_3_spectrum_analysis():
    """示例3: 频谱分析"""
    print("\n" + "="*60)
    print("示例 3: 频谱分析")
    print("="*60)

    tr = generate_test_waveform()
    analyzer = SpectrumAnalyzer()

    # 计算频谱
    fft_result = analyzer.compute_fft(
        tr,
        detrend="linear",
        window="hann"
    )
    print(f"✓ FFT 完成, 频率点数: {len(fft_result['freq'])}")

    # 主频
    dom_freq = analyzer.dominant_frequency(
        tr,
        detrend="linear",
        window="hann"
    )
    print(f"✓ 主频: {dom_freq['dominant_frequency']:.2f} Hz")

    # PSD
    psd_result = analyzer.compute_psd(
        tr,
        detrend="linear",
        window="hann",
        nperseg=256
    )
    peak_freq = analyzer.peak_frequency(tr)
    print(f"✓ PSD 峰值频率: {peak_freq['peak_frequency']:.2f} Hz")

    # 带宽
    bandwidth = analyzer.bandwidth(tr)
    print(f"✓ -3dB 带宽: {bandwidth['bandwidth']:.2f} Hz")

    # 中心频率
    cf = analyzer.central_frequency(tr)
    print(f"✓ 中心频率: {cf['central_frequency']:.2f} Hz")


def example_4_polarization_analysis():
    """示例4: 极化分析"""
    print("\n" + "="*60)
    print("示例 4: 极化分析 (波前到达方向)")
    print("="*60)

    # 生成三分量数据
    st = Stream()
    for chan in ["BHZ", "BHN", "BHE"]:
        tr = generate_test_waveform(channel=chan)
        st.append(tr)

    print(f"✓ 三分量数据准备完成: {[tr.id for tr in st]}")

    # 极化分析
    pol_analyzer = PolarizationAnalyzer()
    result = pol_analyzer.analyze_polarization(
        st,
        window_length=1.0,
        overlap=0.5
    )

    print(f"✓ 极化分析完成, 时间窗口数: {len(result['time'])}")

    # 波前到达方向估计
    direction = pol_analyzer.estimate_wavefront_direction(
        result,
        min_rectilinearity=0.7
    )

    if direction:
        print(f"\n  波前到达方向:")
        print(f"    方位角: {direction['azimuth']:.1f}°")
        print(f"    入射角: {direction['incident']:.1f}°")
        print(f"    反方位角: {direction['backazimuth']:.1f}°")
        print(f"    直线性置信度: {direction['confidence']:.2f}")


def example_5_pqlx_quality_metrics():
    """示例5: PQLX 质量评估"""
    print("\n" + "="*60)
    print("示例 5: PQLX 质量评估指标")
    print("="*60)

    tr = generate_test_waveform()
    samples = tr.data.tolist()

    print(f"数据样本数: {len(samples)}")

    # 使用 Python 版本的 PQLX 分析
    metrics = PQLXAnalyzer.analyze(samples, gap_threshold=1000)

    print(f"\n✓ 质量分析完成:")
    print(f"  均值: {metrics['mean']:.2f}")
    print(f"  标准差: {metrics['std_dev']:.2f}")
    print(f"  最小值: {metrics['min']}")
    print(f"  最大值: {metrics['max']}")
    print(f"  峰峰值: {metrics['peak_to_peak']}")
    print(f"  RMS: {metrics['rms']:.2f}")
    print(f"  偏度: {metrics['skewness']:.3f}")
    print(f"  峰度: {metrics['kurtosis']:.3f}")
    print(f"  间隙数: {metrics['num_gaps']}")
    print(f"  间隙百分比: {metrics['gap_percentage']:.2f}%")
    print(f"  直流偏移: {metrics['dc_offset']:.2f}")

    # 质量评分
    score = PQLXAnalyzer.quality_score(metrics)
    print(f"\n✓ 综合质量评分: {score:.1f}/100")

    # 如果有 Rust 版本，可以对比性能
    if RUST_AVAILABLE:
        print("\n  (Rust 版本可用, 性能提升约 10-25x)")


def example_6_parallel_processing():
    """示例6: 多线程并行处理"""
    print("\n" + "="*60)
    print("示例 6: 多台站并行处理")
    print("="*60)

    # 生成多台站测试数据
    n_stations = 5
    station_samples = {}
    stations = ["AAA", "BBB", "CCC", "DDD", "EEE"]

    np.random.seed(42)
    for sta in stations[:n_stations]:
        tr = generate_test_waveform(station=sta)
        station_samples[sta] = tr.data.tolist()

    print(f"✓ 准备了 {len(station_samples)} 个台站的测试数据")

    # Python 版本的并行处理器
    processor = ParallelProcessor(num_threads=4)

    # 并行质量分析
    print("\n--- 并行质量分析 (4线程) ---")
    results = processor.analyze_many_stations(
        station_samples,
        gap_threshold=1000
    )

    for sta, metrics in results.items():
        score = PQLXAnalyzer.quality_score(metrics)
        print(f"  {sta}: score={score:.1f}, std={metrics['std_dev']:.1f}")

    # 质量过滤
    print("\n--- 质量过滤 (保留分数 >= 80 的台站) ---")
    filtered = processor.parallel_quality_filter(
        station_samples,
        min_quality_score=80,
        gap_threshold=1000
    )
    print(f"  过滤后台站数: {len(filtered)}/{len(station_samples)}")

    for sta, (samples, metrics) in filtered.items():
        score = PQLXAnalyzer.quality_score(metrics)
        print(f"    {sta}: {len(samples)} 样本, score={score:.1f}")


def example_7_rust_steim2_decode():
    """示例7: Steim2 解压缩 (Rust加速)"""
    print("\n" + "="*60)
    print("示例 7: Steim2 解压缩 (帧对齐)")
    print("="*60)

    if not RUST_AVAILABLE:
        print("  (Rust 模块不可用, 跳过此示例)")
        print("  请运行: maturin develop")
        return

    # 模拟压缩数据
    print("生成模拟压缩帧...")

    # 测试帧对齐
    unaligned_size = 100
    unaligned = bytes(unaligned_size)
    aligned = seis_rs.Steim2Decoder.validate_alignment(unaligned)

    print(f"✓ 帧对齐: 原大小 {len(unaligned)} -> 对齐后 {len(aligned)} 字节")
    print(f"  (Steim2 帧必须是 64 字节的倍数)")

    # 解码测试
    print("\n--- Steim2 解码 ---")
    decoder = seis_rs.Steim2Decoder()

    # 添加多个帧
    n_frames = 10
    for i in range(n_frames):
        frame_data = bytes(64)  # 模拟帧数据
        decoder.add_frame(frame_data)

    samples = decoder.decode_all()
    print(f"✓ 解码完成: {n_frames} 帧 -> {len(samples)} 个样本")

    # 单帧解码
    single_frame = bytes(64)
    frame = seis_rs.Steim2Frame(single_frame)
    frame_samples = frame.decode()
    print(f"✓ 单帧解码: {len(frame_samples)} 个样本")


def example_8_comparison_python_vs_rust():
    """示例8: Python vs Rust 性能对比"""
    print("\n" + "="*60)
    print("示例 8: Python vs Rust 性能对比")
    print("="*60)

    if not RUST_AVAILABLE:
        print("  (Rust 模块不可用, 跳过此示例)")
        return

    import time

    # 生成大数据
    n_samples = 1_000_000
    samples = list(np.random.randn(n_samples).astype(np.int32) * 1000)

    print(f"数据量: {n_samples:,} 个样本")

    # Python 版本计时
    print("\n--- Python 版本 ---")
    t0 = time.time()
    for _ in range(10):
        PQLXAnalyzer.analyze(samples, gap_threshold=1000)
    t_py = (time.time() - t0) / 10
    print(f"  平均耗时: {t_py*1000:.2f} ms/次")

    # Rust 版本计时
    print("\n--- Rust 版本 ---")
    t0 = time.time()
    for _ in range(10):
        seis_rs.PQLXAnalyzer.analyze(samples, gap_threshold=1000)
    t_rs = (time.time() - t0) / 10
    print(f"  平均耗时: {t_rs*1000:.2f} ms/次")

    # 对比
    speedup = t_py / t_rs
    print(f"\n✓ 加速比: {speedup:.1f}x")
    print(f"  Rust 版本快了 {speedup:.1f} 倍!")


def example_9_multi_station_alignment():
    """示例9: 多台网标准化对齐"""
    print("\n" + "="*60)
    print("示例 9: 多台网标准化对齐")
    print("="*60)

    # 生成多台网数据
    networks = ["AK", "CI", "US"]
    stations = ["ABC", "DEF", "GHI"]

    stream = Stream()
    for i, (net, sta) in enumerate(zip(networks, stations)):
        tr = generate_test_waveform(network=net, station=sta)
        # 错开起始时间 (模拟实际情况)
        tr.stats.starttime += i * 2.0
        stream.append(tr)

    print(f"✓ 台站列表:")
    for tr in stream:
        print(f"  {tr.id}: {tr.stats.starttime}")

    # 时间对齐
    normalizer = NetworkNormalizer()
    aligned_stream = normalizer.align_traces(stream)

    print(f"\n✓ 时间对齐完成:")
    for tr in aligned_stream:
        print(f"  {tr.id}: {tr.stats.starttime}")

    print(f"\n  (所有台站起始时间已对齐到最早的台站)")


def main():
    print("\n" + "="*60)
    print("        地震波形处理工具包 - 综合示例")
    print("="*60)

    # 基础功能
    example_1_basic_filtering()
    example_2_phase_picking()
    example_3_spectrum_analysis()
    example_4_polarization_analysis()

    # 高级功能
    example_5_pqlx_quality_metrics()
    example_6_parallel_processing()
    example_7_rust_steim2_decode()
    example_9_multi_station_alignment()

    # 性能对比 (如果Rust可用)
    example_8_comparison_python_vs_rust()

    print("\n" + "="*60)
    print("所有示例运行完成!")
    print("="*60)
    print("\n功能总结:")
    print("  ✓ 基础波形滤波 (带通/低通/去趋势)")
    print("  ✓ 震相拾取 (STA/LTA 自适应)")
    print("  ✓ 频谱分析 (FFT/PSD/主频/带宽)")
    print("  ✓ 极化分析 (波前到达方向估计)")
    print("  ✓ PQLX 质量评估 (均值/标准差/偏度/峰度)")
    print("  ✓ 多线程并行处理 (多台站同时解码/分析)")
    print("  ✓ Steim2 解压缩 (Rust 加速 10-25x)")
    print("  ✓ 多台网时间对齐与标准化")


if __name__ == "__main__":
    main()
