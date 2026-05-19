#!/usr/bin/env python3
"""
分子动力学轨迹分析工具 - 使用示例
包含流式读取、RMSD对齐、氢键分析、PCA分析和自由能形貌图
"""

from md_analysis import (
    TrajectoryReader, 
    RMSDCalculator, 
    RgCalculator, 
    ReportGenerator,
    HydrogenBondAnalyzer,
    XTCParser,
    PrecisionConverter,
    PCAAnalyzer,
    FreeEnergySurface
)


def example_basic_analysis():
    """基本分析流程"""
    topology_file = "your_topology.pdb"
    trajectory_file = "your_trajectory.xtc"
    
    print("=" * 60)
    print("  分子动力学轨迹分析工具 - 基本分析")
    print("=" * 60)
    
    print("\n[1/6] 加载轨迹文件 (流式模式)...")
    reader = TrajectoryReader(topology_file, trajectory_file)
    reader.load(in_memory=False)  # 流式模式，不加载全部到内存
    print(f"  ✓ 加载成功!")
    print(f"    - 帧数: {reader.n_frames}")
    print(f"    - 原子数: {reader.n_atoms}")
    
    print("\n[2/6] 流式逐帧迭代示例...")
    frame_count = 0
    for frame_idx, time, coords in reader.iterate_frames(step=10):
        frame_count += 1
        if frame_count <= 3:
            print(f"    帧 {frame_idx}: 时间={time:.2f} ps, 坐标形状={coords.shape}")
    print(f"  ✓ 迭代了 {frame_count} 帧 (每10帧采样)")
    
    print("\n[3/6] 计算RMSD (使用MDAnalysis align方法)...")
    rmsd_calc = RMSDCalculator(reader)
    
    group_selections = {
        "backbone": "backbone",
        "alpha_carbons": "name CA"
    }
    
    rmsd_results = rmsd_calc.calculate(
        reference_frame=0,
        selection="backbone",
        group_selections=group_selections,
        fit_superposition=True,  # 使用最小二乘拟合对齐
        center=True,
        verbose=True
    )
    
    rmsd_stats = rmsd_calc.get_statistics()
    print(f"  ✓ RMSD计算完成!")
    print(f"    - 平均值: {rmsd_stats['mean']:.4f} Å")
    print(f"    - 标准差: {rmsd_stats['std']:.4f} Å")
    
    print("\n[4/6] 计算回旋半径Rg...")
    rg_calc = RgCalculator(reader)
    
    rg_results = rg_calc.calculate(
        selection="protein",
        use_masses=True
    )
    
    rg_stats = rg_calc.get_statistics()
    print(f"  ✓ Rg计算完成!")
    print(f"    - 平均值: {rg_stats['mean']:.4f} Å")
    print(f"    - 标准差: {rg_stats['std']:.4f} Å")
    
    print("\n[5/6] PCA主成分分析...")
    pca_calc = PCAAnalyzer(reader)
    pca_data = pca_calc.fit(
        selection="name CA",
        fit=True
    )
    
    res_contrib = pca_calc.get_residue_contributions(
        selection="name CA",
        n_components=2
    )
    
    import numpy as np
    key_res_pc1 = []
    top_idx_pc1 = np.argsort(res_contrib['contributions'][:, 0])[-5:][::-1]
    for idx in top_idx_pc1:
        key_res_pc1.append({
            'resname': res_contrib['resnames'][idx],
            'resid': res_contrib['resids'][idx],
            'contribution': res_contrib['contributions'][idx, 0]
        })
    
    pca_results = {
        'variance_ratio': pca_data['variance_ratio'],
        'cumulative_variance': pca_data['cumulative_variance'],
        'projections': pca_data['projections'],
        'residue_contributions': res_contrib,
        'key_residues_pc1': key_res_pc1,
        'selection': "name CA",
        'n_atoms': pca_data['n_atoms'],
        'n_frames': pca_data['n_frames']
    }
    
    print(f"  ✓ PCA计算完成!")
    print(f"    - PC1解释方差: {pca_data['variance_ratio'][0]*100:.2f}%")
    print(f"    - PC2解释方差: {pca_data['variance_ratio'][1]*100:.2f}%")
    print(f"    - 前2个主成分累计解释: {pca_data['cumulative_variance'][1]*100:.2f}%")
    
    print("\n[6/6] 生成完整分析报告...")
    reporter = ReportGenerator(
        trajectory_summary=reader.summary(),
        rmsd_results=rmsd_results,
        rg_results=rg_results,
        pca_results=pca_results
    )
    
    reporter.generate_full_report(
        output_dir="analysis_results",
        output_prefix="md_analysis"
    )
    
    print(f"  ✓ 报告生成完成!")
    
    print("\n" + "=" * 60)
    print("  分析完成! 结果已保存到 analysis_results/ 目录")
    print("=" * 60)


def example_streaming_rmsd():
    """流式RMSD计算示例 - 超大数据集"""
    trajectory_file = "your_trajectory.xtc"
    
    print("\n" + "=" * 60)
    print("  流式RMSD计算示例 (超大轨迹专用)")
    print("=" * 60)
    
    print(f"\n检测XTC文件精度信息...")
    with XTCParser(trajectory_file) as parser:
        info = parser.get_precision_info()
        print(f"  - 帧数: {info['n_frames']}")
        print(f"  - 原子数: {info['n_atoms']}")
        print(f"  - 精度: {info['precision']}")
        print(f"  - 文件大小: {info['file_size_mb']:.2f} MB")
        
        memory_est = parser.estimate_memory_usage()
        print(f"  - 预估内存需求: {memory_est['total_mb']:.2f} MB")
        
    print("\n  ✓ 使用流式RMSD可以避免一次性加载全部数据到内存!")


def example_hbond_analysis():
    """氢键分析示例"""
    topology_file = "your_topology.pdb"
    trajectory_file = "your_trajectory.xtc"
    
    print("\n" + "=" * 60)
    print("  氢键分析示例 (距离+角度双重检测)")
    print("=" * 60)
    
    print("\n加载轨迹文件...")
    reader = TrajectoryReader(topology_file, trajectory_file)
    reader.load(in_memory=False)
    
    print("\n检测氢键...")
    print("  - 距离阈值: < 3.5 Å")
    print("  - 角度阈值: > 120.0°")
    
    hbond_calc = HydrogenBondAnalyzer(reader)
    hbond_results = hbond_calc.calculate(
        donor_sel="name N",
        acceptor_sel="name O",
        hydrogen_sel="name H*",
        distance_cutoff=3.5,
        angle_cutoff=120.0,
        track_lifetime=True
    )
    
    hbond_stats = hbond_calc.get_statistics()
    print(f"  ✓ 氢键检测完成!")
    print(f"    - 平均数量: {hbond_stats['mean']:.2f} 个/帧")
    print(f"    - 标准差: {hbond_stats['std']:.2f}")
    
    print("\n氢键频率排名 (Top 5):")
    freq = hbond_calc.get_hbond_frequency()
    for i, (hbond_id, frequency) in enumerate(list(freq.items())[:5]):
        donor_resid, donor_name, acceptor_resid, acceptor_name = hbond_id
        print(f"  {i+1}. {donor_name}{donor_resid} → {acceptor_name}{acceptor_resid}: {frequency:.1%}")
    
    print("\n生成氢键报告...")
    reporter = ReportGenerator(
        trajectory_summary=reader.summary(),
        hbond_results=hbond_results
    )
    
    reporter.generate_full_report(
        output_dir="analysis_results",
        output_prefix="hbond_analysis"
    )
    
    print("  ✓ 氢键分析报告已生成!")


def example_pca_fes_analysis():
    """PCA分析 + 自由能形貌图示例"""
    topology_file = "your_topology.pdb"
    trajectory_file = "your_trajectory.xtc"
    
    print("\n" + "=" * 60)
    print("  PCA主成分分析 + 自由能形貌图示例")
    print("=" * 60)
    
    print("\n加载轨迹文件...")
    reader = TrajectoryReader(topology_file, trajectory_file)
    reader.load(in_memory=False)
    
    print("\n[1/3] 主成分分析 (PCA)...")
    pca_calc = PCAAnalyzer(reader)
    pca_data = pca_calc.fit(
        selection="name CA",
        fit=True
    )
    
    import numpy as np
    res_contrib = pca_calc.get_residue_contributions(
        selection="name CA",
        n_components=2
    )
    
    key_res_pc1 = []
    key_res_pc2 = []
    top_idx_pc1 = np.argsort(res_contrib['contributions'][:, 0])[-5:][::-1]
    top_idx_pc2 = np.argsort(res_contrib['contributions'][:, 1])[-5:][::-1]
    
    for idx in top_idx_pc1:
        key_res_pc1.append({
            'resname': res_contrib['resnames'][idx],
            'resid': res_contrib['resids'][idx],
            'contribution': res_contrib['contributions'][idx, 0]
        })
    
    for idx in top_idx_pc2:
        key_res_pc2.append({
            'resname': res_contrib['resnames'][idx],
            'resid': res_contrib['resids'][idx],
            'contribution': res_contrib['contributions'][idx, 1]
        })
    
    pca_results = {
        'variance_ratio': pca_data['variance_ratio'],
        'cumulative_variance': pca_data['cumulative_variance'],
        'projections': pca_data['projections'],
        'residue_contributions': res_contrib,
        'key_residues_pc1': key_res_pc1,
        'key_residues_pc2': key_res_pc2,
        'selection': "name CA",
        'n_atoms': pca_data['n_atoms'],
        'n_frames': pca_data['n_frames']
    }
    
    print(f"  ✓ PCA计算完成!")
    print(f"    - PC1解释方差: {pca_data['variance_ratio'][0]*100:.2f}%")
    print(f"    - PC2解释方差: {pca_data['variance_ratio'][1]*100:.2f}%")
    
    print("\n[2/3] 自由能形貌图 (FES)...")
    fes_calc = FreeEnergySurface(
        pca_data['projections'][:, 0],
        pca_data['projections'][:, 1]
    )
    
    fes_data = fes_calc.calculate(
        bins=100,
        temperature=300.0,
        method="histogram"
    )
    
    minima = fes_calc.find_minima(n_minima=3)
    
    fes_results = {
        'x_grid': fes_data['x_grid'],
        'y_grid': fes_data['y_grid'],
        'fes': fes_data['fes'],
        'minima': minima,
        'temperature': 300.0,
        'method': "histogram",
        'bins': 100
    }
    
    print(f"  ✓ FES计算完成!")
    print(f"    - 找到 {len(minima)} 个自由能极小值点")
    
    print("\n[3/3] 生成报告...")
    reporter = ReportGenerator(
        trajectory_summary=reader.summary(),
        pca_results=pca_results,
        fes_results=fes_results
    )
    
    reporter.generate_full_report(
        output_dir="analysis_results",
        output_prefix="pca_fes_analysis"
    )
    
    print("  ✓ PCA+FES分析报告已生成!")


def example_precision_levels():
    """XTC精度级别示例"""
    print("\n" + "=" * 60)
    print("  XTC文件精度级别说明")
    print("=" * 60)
    
    levels = PrecisionConverter.get_precision_levels()
    print("\n可用精度级别:")
    for name, prec in levels.items():
        print(f"  {name:8s}: precision={prec:.0f} → 实际精度={1/prec:.5f} Å")
    
    print("\n压缩比例估算 (100,000原子):")
    ratio = PrecisionConverter.estimate_compression_ratio(100000)
    print(f"  - XTC压缩比: {ratio:.2f}: 1")
    print(f"  - 相比未压缩的float32格式，节省{(1-1/ratio)*100:.1f}%空间")


if __name__ == "__main__":
    try:
        example_basic_analysis()
        print("\n" + "=" * 60 + "\n")
    except Exception as e:
        print(f"  基本分析示例跳过: {e}")
    
    try:
        example_streaming_rmsd()
        print("\n" + "=" * 60 + "\n")
    except Exception as e:
        print(f"  流式RMSD示例跳过: 需要XTC轨迹文件")
    
    try:
        example_hbond_analysis()
        print("\n" + "=" * 60 + "\n")
    except Exception as e:
        print(f"  氢键分析示例跳过: 需要拓扑和轨迹文件")
    
    try:
        example_pca_fes_analysis()
        print("\n" + "=" * 60 + "\n")
    except Exception as e:
        print(f"  PCA+FES分析示例跳过: 需要拓扑和轨迹文件")
    
    example_precision_levels()
    
    print("\n全部示例运行完成!")
