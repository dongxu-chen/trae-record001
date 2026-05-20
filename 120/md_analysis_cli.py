#!/usr/bin/env python3
"""
分子动力学轨迹分析工具 - 命令行接口
支持流式读取、RMSD对齐、氢键分析和XTC精度检测
"""

import argparse
import sys
import numpy as np
from md_analysis import (
    TrajectoryReader, 
    RMSDCalculator, 
    RgCalculator, 
    ReportGenerator,
    HydrogenBondAnalyzer,
    XTCParser,
    PCAAnalyzer,
    FreeEnergySurface
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="分子动力学轨迹分析工具 - 计算RMSD、Rg和氢键分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本分析 (流式读取 + RMSD + Rg)
  python md_analysis_cli.py -t topology.pdb -x trajectory.xtc

  # 仅RMSD计算，使用MDAlaysis align方法对齐
  python md_analysis_cli.py -t topology.pdb -x trajectory.xtc --no-rg --rmsd-fit

  # 氢键分析 (距离<3.5Å + 角度>120°)
  python md_analysis_cli.py -t topology.pdb -x trajectory.xtc --hbond

  # 检查XTC文件精度和内存需求
  python md_analysis_cli.py -x trajectory.xtc --check-xtc

  # 完整分析：RMSD + Rg + 氢键
  python md_analysis_cli.py -t topology.pdb -x trajectory.xtc --hbond
        """
    )
    
    parser.add_argument("-t", "--topology", required=False,
                       help="拓扑文件 (如 .pdb, .gro)")
    parser.add_argument("-x", "--trajectory", required=True,
                       help="轨迹文件 (如 .xtc, .trr)")
    
    parser.add_argument("--in-memory", action="store_true",
                       help="将轨迹加载到内存中 (默认: 流式读取)")
    
    parser.add_argument("--rmsd-sel", default="backbone",
                       help="RMSD计算的原子选择 (默认: backbone)")
    parser.add_argument("--rmsd-ref", type=int, default=0,
                       help="RMSD参考帧 (默认: 0)")
    parser.add_argument("--rmsd-fit", action="store_true",
                       help="使用MDAnalysis align方法进行最小二乘拟合对齐")
    parser.add_argument("--no-rmsd", action="store_true",
                       help="跳过RMSD计算")
    
    parser.add_argument("--rg-sel", default="protein",
                       help="Rg计算的原子选择 (默认: protein)")
    parser.add_argument("--no-masses", action="store_true",
                       help="不使用质量加权计算Rg")
    parser.add_argument("--no-rg", action="store_true",
                       help="跳过Rg计算")
    
    parser.add_argument("--hbond", action="store_true",
                       help="启用氢键分析")
    parser.add_argument("--hbond-dist", type=float, default=3.5,
                       help="氢键距离阈值 (Å, 默认: 3.5)")
    parser.add_argument("--hbond-angle", type=float, default=120.0,
                       help="氢键角度阈值 (°, 默认: 120.0)")
    parser.add_argument("--hbond-donor", default="name N",
                       help="氢键供体原子选择 (默认: name N)")
    parser.add_argument("--hbond-acceptor", default="name O",
                       help="氢键受体原子选择 (默认: name O)")
    parser.add_argument("--hbond-hydrogen", default="name H*",
                       help="氢原子选择 (默认: name H*)")
    
    parser.add_argument("--pca", action="store_true",
                       help="启用主成分分析 (PCA)")
    parser.add_argument("--pca-sel", default="name CA",
                       help="PCA计算的原子选择 (默认: name CA)")
    parser.add_argument("--pca-fit", action="store_true",
                       help="对齐轨迹后再做PCA (默认: 是)")
    parser.add_argument("--no-pca-fit", action="store_true",
                       help="不对齐轨迹直接做PCA")
    
    parser.add_argument("--fes", action="store_true",
                       help="启用自由能形貌图 (FES) 计算")
    parser.add_argument("--fes-bins", type=int, default=100,
                       help="FES网格数量 (默认: 100)")
    parser.add_argument("--fes-temp", type=float, default=300.0,
                       help="温度 (K, 默认: 300.0)")
    parser.add_argument("--fes-method", default="histogram",
                       choices=["histogram", "kde"],
                       help="FES计算方法 (histogram/kde, 默认: histogram)")
    
    parser.add_argument("--check-xtc", action="store_true",
                       help="仅检查XTC文件信息和内存需求，不进行分析")
    
    parser.add_argument("-o", "--output-dir", default="analysis_results",
                       help="输出目录 (默认: analysis_results)")
    parser.add_argument("-p", "--prefix", default="md_analysis",
                       help="输出文件前缀 (默认: md_analysis)")
    
    return parser.parse_args()


def check_xtc_info(trajectory_file: str):
    """检查XTC文件信息"""
    print("=" * 60)
    print("  XTC文件信息检测")
    print("=" * 60)
    
    print(f"\n文件: {trajectory_file}")
    
    try:
        with XTCParser(trajectory_file) as parser:
            info = parser.get_precision_info()
            memory_est = parser.estimate_memory_usage()
            
            print("\n基本信息:")
            print(f"  - 帧数: {info['n_frames']}")
            print(f"  - 原子数: {info['n_atoms']}")
            print(f"  - 压缩精度: {info['precision']}")
            print(f"  - 文件大小: {info['file_size_mb']:.2f} MB")
            
            print("\n内存需求估算 (全部加载到内存):")
            print(f"  - 坐标数据: {memory_est['coords_mb']:.2f} MB")
            print(f"  - 盒子数据: {memory_est['box_mb']:.2f} MB")
            print(f"  - 总计: {memory_est['total_mb']:.2f} MB")
            
            if memory_est['total_mb'] > 4000:
                print("\n  ⚠️  警告: 内存需求超过4GB，强烈建议使用流式读取!")
                print("     使用 --in-memory=false (默认) 逐帧处理")
            else:
                print("\n  ✓ 内存需求适中，可以正常处理")
                
    except Exception as e:
        print(f"\n  ✗ 读取失败: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)


def main():
    args = parse_args()
    
    if args.check_xtc:
        check_xtc_info(args.trajectory)
        return
    
    if not args.topology:
        print("错误: 进行分析需要拓扑文件 (-t/--topology)")
        print("       或使用 --check-xtc 仅检查轨迹文件")
        sys.exit(1)
    
    if args.no_rmsd and args.no_rg and not args.hbond:
        print("错误: 所有分析都被跳过，请至少启用一种分析!")
        sys.exit(1)
    
    print("=" * 60)
    print("  分子动力学轨迹分析工具 (CLI v2.0)")
    print("=" * 60)
    
    steps = sum([1 for x in [not args.no_rmsd, not args.no_rg, args.hbond, args.pca, args.fes, True]])
    
    print(f"\n[1/{steps}] 加载轨迹文件 (流式模式)...")
    print(f"  拓扑文件: {args.topology}")
    print(f"  轨迹文件: {args.trajectory}")
    print(f"  内存模式: {'全部加载' if args.in_memory else '流式读取'}")
    
    try:
        reader = TrajectoryReader(args.topology, args.trajectory)
        reader.load(in_memory=args.in_memory)
        print(f"  ✓ 加载成功!")
        print(f"    - 帧数: {reader.n_frames}")
        print(f"    - 原子数: {reader.n_atoms}")
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        sys.exit(1)
    
    current_step = 2
    rmsd_results = None
    if not args.no_rmsd:
        print(f"\n[{current_step}/{steps}] 计算RMSD...")
        print(f"  原子选择: {args.rmsd_sel}")
        print(f"  参考帧: {args.rmsd_ref}")
        print(f"  拟合对齐: {'是 (MDAnalysis align)' if args.rmsd_fit else '否'}")
        try:
            rmsd_calc = RMSDCalculator(reader)
            rmsd_results = rmsd_calc.calculate(
                reference_frame=args.rmsd_ref,
                selection=args.rmsd_sel,
                fit_superposition=args.rmsd_fit,
                center=True
            )
            rmsd_stats = rmsd_calc.get_statistics()
            print(f"  ✓ RMSD计算完成!")
            print(f"    - 平均值: {rmsd_stats['mean']:.4f} Å")
            print(f"    - 标准差: {rmsd_stats['std']:.4f} Å")
            current_step += 1
        except Exception as e:
            print(f"  ✗ RMSD计算失败: {e}")
            rmsd_results = None
    
    rg_results = None
    if not args.no_rg:
        print(f"\n[{current_step}/{steps}] 计算回旋半径Rg...")
        print(f"  原子选择: {args.rg_sel}")
        print(f"  质量加权: {'是' if not args.no_masses else '否'}")
        try:
            rg_calc = RgCalculator(reader)
            rg_results = rg_calc.calculate(
                selection=args.rg_sel,
                use_masses=not args.no_masses
            )
            rg_stats = rg_calc.get_statistics()
            print(f"  ✓ Rg计算完成!")
            print(f"    - 平均值: {rg_stats['mean']:.4f} Å")
            print(f"    - 标准差: {rg_stats['std']:.4f} Å")
            current_step += 1
        except Exception as e:
            print(f"  ✗ Rg计算失败: {e}")
            rg_results = None
    
    hbond_results = None
    if args.hbond:
        print(f"\n[{current_step}/{steps}] 氢键分析...")
        print(f"  供体选择: {args.hbond_donor}")
        print(f"  受体选择: {args.hbond_acceptor}")
        print(f"  氢原子选择: {args.hbond_hydrogen}")
        print(f"  距离阈值: < {args.hbond_dist} Å")
        print(f"  角度阈值: > {args.hbond_angle}°")
        try:
            hbond_calc = HydrogenBondAnalyzer(reader)
            hbond_results = hbond_calc.calculate(
                donor_sel=args.hbond_donor,
                acceptor_sel=args.hbond_acceptor,
                hydrogen_sel=args.hbond_hydrogen,
                distance_cutoff=args.hbond_dist,
                angle_cutoff=args.hbond_angle
            )
            hbond_stats = hbond_calc.get_statistics()
            print(f"  ✓ 氢键分析完成!")
            print(f"    - 平均数量: {hbond_stats['mean']:.2f} 个/帧")
            print(f"    - 标准差: {hbond_stats['std']:.2f}")
            current_step += 1
        except Exception as e:
            print(f"  ✗ 氢键分析失败: {e}")
            hbond_results = None
    
    pca_results = None
    if args.pca:
        print(f"\n[{current_step}/{steps}] 主成分分析 (PCA)...")
        print(f"  原子选择: {args.pca_sel}")
        print(f"  轨迹对齐: {'是' if not args.no_pca_fit else '否'}")
        try:
            pca_calc = PCAAnalyzer(reader)
            pca_data = pca_calc.fit(
                selection=args.pca_sel,
                fit=not args.no_pca_fit
            )
            
            res_contrib = pca_calc.get_residue_contributions(
                selection=args.pca_sel,
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
                'selection': args.pca_sel,
                'n_atoms': pca_data['n_atoms'],
                'n_frames': pca_data['n_frames']
            }
            
            print(f"  ✓ PCA计算完成!")
            print(f"    - PC1解释方差: {pca_data['variance_ratio'][0]*100:.2f}%")
            print(f"    - PC2解释方差: {pca_data['variance_ratio'][1]*100:.2f}%")
            print(f"    - 前2个主成分累计解释: {pca_data['cumulative_variance'][1]*100:.2f}%")
            current_step += 1
        except Exception as e:
            print(f"  ✗ PCA计算失败: {e}")
            import traceback
            traceback.print_exc()
            pca_results = None
    
    fes_results = None
    if args.fes and pca_results is not None:
        print(f"\n[{current_step}/{steps}] 自由能形貌图 (FES) 计算...")
        print(f"  网格数量: {args.fes_bins}")
        print(f"  温度: {args.fes_temp} K")
        print(f"  计算方法: {args.fes_method}")
        try:
            fes_calc = FreeEnergySurface(
                pca_results['projections'][:, 0],
                pca_results['projections'][:, 1]
            )
            
            fes_data = fes_calc.calculate(
                bins=args.fes_bins,
                temperature=args.fes_temp,
                method=args.fes_method
            )
            
            minima = fes_calc.find_minima(n_minima=3)
            
            fes_results = {
                'x_grid': fes_data['x_grid'],
                'y_grid': fes_data['y_grid'],
                'fes': fes_data['fes'],
                'minima': minima,
                'temperature': args.fes_temp,
                'method': args.fes_method,
                'bins': args.fes_bins
            }
            
            print(f"  ✓ FES计算完成!")
            print(f"    - 找到 {len(minima)} 个自由能极小值点")
            current_step += 1
        except Exception as e:
            print(f"  ✗ FES计算失败: {e}")
            import traceback
            traceback.print_exc()
            fes_results = None
    
    print(f"\n[{steps}/{steps}] 生成分析报告...")
    print(f"  输出目录: {args.output_dir}")
    print(f"  文件前缀: {args.prefix}")
    try:
        reporter = ReportGenerator(
            trajectory_summary=reader.summary(),
            rmsd_results=rmsd_results,
            rg_results=rg_results,
            hbond_results=hbond_results,
            pca_results=pca_results,
            fes_results=fes_results
        )
        reporter.generate_full_report(
            output_dir=args.output_dir,
            output_prefix=args.prefix
        )
        print(f"  ✓ 报告生成完成!")
    except Exception as e:
        print(f"  ✗ 报告生成失败: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("  分析完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
