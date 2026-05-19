#!/usr/bin/env python3
"""
分子动力学轨迹分布式分析工具 - 命令行接口
基于Dask分布式计算框架，支持TB级数据
"""

import argparse
import sys
import os
import numpy as np

sys.path.insert(0, '.')

from md_analysis.dask_analysis import (
    MemoryMappedTrajectory,
    DistributedAnalyzer,
    DaskPCA,
    estimate_memory_usage,
    create_dask_cluster_info
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="分子动力学轨迹分布式分析工具 - 基于Dask",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 本地集群，分析RMSD和Rg
  python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc \\
      --rmsd --rg --rmsd-sel 'name CA'
  
  # 分布式集群，指定Worker数量
  python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc \\
      --workers 8 --memory-limit 16GB --rmsd
  
  # 内存估算（不执行分析）
  python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc --estimate-memory
  
  # 连接到远程Dask调度器
  python dask_analysis_cli.py -t topology.pdb -x trajectory.xtc \\
      --scheduler tcp://192.168.1.100:8786 --rmsd --rg
        """
    )
    
    parser.add_argument("-t", "--topology", required=True,
                       help="拓扑文件 (如 .pdb, .gro)")
    parser.add_argument("-x", "--trajectory", required=True,
                       help="轨迹文件 (如 .xtc, .trr)")
    
    cluster_group = parser.add_argument_group('集群配置')
    cluster_group.add_argument("--workers", type=int, default=4,
                              help="Worker数量 (默认: 4)")
    cluster_group.add_argument("--threads-per-worker", type=int, default=2,
                              help="每个Worker的线程数 (默认: 2)")
    cluster_group.add_argument("--memory-limit", default="8GB",
                              help="每个Worker的内存限制 (默认: 8GB)")
    cluster_group.add_argument("--scheduler", default=None,
                              help="远程调度器地址 (如 tcp://localhost:8786)")
    cluster_group.add_argument("--chunk-size", type=int, default=1000,
                              help="分块大小，帧数/块 (默认: 1000)")
    
    analysis_group = parser.add_argument_group('分析选项')
    analysis_group.add_argument("--rmsd", action="store_true",
                               help="计算RMSD")
    analysis_group.add_argument("--rmsd-sel", default="name CA",
                               help="RMSD原子选择 (默认: name CA)")
    analysis_group.add_argument("--rmsd-ref", type=int, default=0,
                               help="RMSD参考帧 (默认: 0)")
    
    analysis_group.add_argument("--rg", action="store_true",
                               help="计算回旋半径Rg")
    analysis_group.add_argument("--rg-sel", default="protein",
                               help="Rg原子选择 (默认: protein)")
    analysis_group.add_argument("--no-masses", action="store_true",
                               help="不使用质量加权计算Rg")
    
    analysis_group.add_argument("--pca", action="store_true",
                               help="执行PCA主成分分析")
    analysis_group.add_argument("--pca-sel", default="name CA",
                               help="PCA原子选择 (默认: name CA)")
    analysis_group.add_argument("--n-components", type=int, default=10,
                               help="PCA主成分数量 (默认: 10)")
    
    analysis_group.add_argument("--estimate-memory", action="store_true",
                               help="仅估算内存需求，不执行分析")
    
    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument("-o", "--output-dir", default="dask_results",
                             help="输出目录 (默认: dask_results)")
    output_group.add_argument("--no-plot", action="store_true",
                             help="不生成图表")
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 70)
    print("  🚀 分子动力学轨迹分布式分析工具 (基于Dask)")
    print("=" * 70)
    
    analyzer = DistributedAnalyzer()
    
    if args.scheduler:
        print(f"\n📡 连接到远程调度器: {args.scheduler}")
        client = analyzer.connect_to_cluster(args.scheduler)
    else:
        print(f"\n⚙️  启动本地Dask集群...")
        print(f"  - Worker数量: {args.workers}")
        print(f"  - 线程/Worker: {args.threads_per_worker}")
        print(f"  - 内存限制: {args.memory_limit}")
        client = analyzer.setup_local_cluster(
            n_workers=args.workers,
            threads_per_worker=args.threads_per_worker,
            memory_limit=args.memory_limit
        )
    
    cluster_info = create_dask_cluster_info(client)
    print(f"  ✓ 集群就绪!")
    print(f"  - Dashboard: {cluster_info['dashboard_link']}")
    
    print(f"\n📂 加载轨迹数据...")
    print(f"  - 拓扑文件: {args.topology}")
    print(f"  - 轨迹文件: {args.trajectory}")
    print(f"  - 分块大小: {args.chunk_size} 帧/块")
    
    try:
        traj_mmap = MemoryMappedTrajectory(
            args.topology,
            args.trajectory,
            chunk_size=args.chunk_size
        )
        
        print(f"  ✓ 加载成功!")
        print(f"  - 总帧数: {traj_mmap.n_frames:,}")
        print(f"  - 原子数: {traj_mmap.n_atoms:,}")
        print(f"  - 总模拟时间: {traj_mmap.n_frames * traj_mmap.dt:.2f} ps")
        
        memory_est = estimate_memory_usage(traj_mmap.n_frames, traj_mmap.n_atoms)
        print(f"  - 估算内存需求: {memory_est['total']}")
        
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        analyzer.close()
        sys.exit(1)
    
    if args.estimate_memory:
        print("\n" + "=" * 70)
        print("  📊 内存估算完成")
        print("=" * 70)
        analyzer.close()
        return
    
    results = {}
    times_dask = None
    positions_dask = None
    
    if args.rmsd:
        print(f"\n🧮 分布式计算RMSD...")
        print(f"  - 原子选择: {args.rmsd_sel}")
        print(f"  - 参考帧: {args.rmsd_ref}")
        
        try:
            if positions_dask is None:
                times_dask, positions_dask = traj_mmap.to_dask_array(args.rmsd_sel)
            
            ref_positions = traj_mmap.read_frame(args.rmsd_ref, args.rmsd_sel)
            rmsd_values = analyzer.compute_rmsd_distributed(
                positions_dask,
                ref_positions,
                compute_now=True
            )
            
            results['rmsd'] = rmsd_values
            print(f"  ✓ RMSD计算完成!")
            print(f"    - 平均值: {np.mean(rmsd_values):.4f} Å")
            print(f"    - 标准差: {np.std(rmsd_values):.4f} Å")
        except Exception as e:
            print(f"  ✗ RMSD计算失败: {e}")
    
    if args.rg:
        print(f"\n🧮 分布式计算Rg...")
        print(f"  - 原子选择: {args.rg_sel}")
        print(f"  - 质量加权: {'否' if args.no_masses else '是'}")
        
        try:
            if positions_dask is None:
                times_dask, positions_dask = traj_mmap.to_dask_array(args.rg_sel)
            
            masses = None if args.no_masses else traj_mmap.atom_masses
            rg_values = analyzer.compute_rg_distributed(
                positions_dask,
                masses=masses,
                compute_now=True
            )
            
            results['rg'] = rg_values
            print(f"  ✓ Rg计算完成!")
            print(f"    - 平均值: {np.mean(rg_values):.4f} Å")
            print(f"    - 标准差: {np.std(rg_values):.4f} Å")
        except Exception as e:
            print(f"  ✗ Rg计算失败: {e}")
    
    if args.pca:
        print(f"\n🧮 分布式PCA主成分分析...")
        print(f"  - 原子选择: {args.pca_sel}")
        print(f"  - 主成分数量: {args.n_components}")
        
        try:
            if positions_dask is None:
                times_dask, positions_dask = traj_mmap.to_dask_array(args.pca_sel)
            
            pca = DaskPCA(n_components=args.n_components)
            positions_flat = positions_dask.reshape(positions_dask.shape[0], -1)
            
            pca.fit(positions_flat, compute_now=True)
            projections = pca.transform(positions_flat).compute()
            
            results['pca'] = {
                'projections': projections,
                'explained_variance_ratio': pca.explained_variance_ratio_,
                'components': pca.components_
            }
            
            print(f"  ✓ PCA计算完成!")
            print(f"    - PC1解释方差: {pca.explained_variance_ratio_[0]*100:.2f}%")
            print(f"    - PC2解释方差: {pca.explained_variance_ratio_[1]*100:.2f}%")
            print(f"    - 前2个主成分累计: {np.sum(pca.explained_variance_ratio_[:2])*100:.2f}%")
        except Exception as e:
            print(f"  ✗ PCA计算失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n💾 保存结果...")
    os.makedirs(args.output_dir, exist_ok=True)
    
    import pandas as pd
    
    if times_dask is None:
        times_dask, _ = traj_mmap.to_dask_array('all')
    
    times = times_dask.compute()
    
    data_dict = {'time_ps': times}
    if 'rmsd' in results:
        data_dict['rmsd_angstrom'] = results['rmsd']
    if 'rg' in results:
        data_dict['rg_angstrom'] = results['rg']
    
    df = pd.DataFrame(data_dict)
    csv_path = os.path.join(args.output_dir, 'analysis_results.csv')
    df.to_csv(csv_path, index=False)
    print(f"  ✓ 数值结果: {csv_path}")
    
    if 'pca' in results:
        np.save(os.path.join(args.output_dir, 'pca_projections.npy'), 
                results['pca']['projections'])
        np.save(os.path.join(args.output_dir, 'pca_components.npy'), 
                results['pca']['components'])
        np.save(os.path.join(args.output_dir, 'pca_variance_ratio.npy'), 
                results['pca']['explained_variance_ratio'])
        print(f"  ✓ PCA结果已保存")
    
    if not args.no_plot:
        import matplotlib.pyplot as plt
        print(f"\n🎨 生成图表...")
        
        if 'rmsd' in results:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(times, results['rmsd'], 'b-', linewidth=1.5, alpha=0.8)
            ax.set_xlabel('Time (ps)', fontsize=12)
            ax.set_ylabel('RMSD (Å)', fontsize=12)
            ax.set_title('RMSD vs Simulation Time', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, 'rmsd_plot.png'), dpi=150)
            plt.close()
            print(f"  ✓ RMSD图表已生成")
        
        if 'rg' in results:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(times, results['rg'], 'g-', linewidth=1.5, alpha=0.8)
            ax.set_xlabel('Time (ps)', fontsize=12)
            ax.set_ylabel('Rg (Å)', fontsize=12)
            ax.set_title('Radius of Gyration vs Simulation Time', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, 'rg_plot.png'), dpi=150)
            plt.close()
            print(f"  ✓ Rg图表已生成")
        
        if 'pca' in results:
            proj = results['pca']['projections']
            var_ratio = results['pca']['explained_variance_ratio']
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            scatter = ax1.scatter(proj[:, 0], proj[:, 1], c=np.arange(len(proj)), 
                                cmap='viridis', alpha=0.6, s=10)
            ax1.set_xlabel(f'PC1 ({var_ratio[0]*100:.1f}%)', fontsize=12)
            ax1.set_ylabel(f'PC2 ({var_ratio[1]*100:.1f}%)', fontsize=12)
            ax1.set_title('PCA Projection', fontsize=14, fontweight='bold')
            plt.colorbar(scatter, ax=ax1, label='Frame Index')
            ax1.grid(True, alpha=0.3)
            
            n_comp = min(10, len(var_ratio))
            ax2.bar(range(1, n_comp + 1), var_ratio[:n_comp] * 100, 
                   color='steelblue', alpha=0.8)
            ax2.plot(range(1, n_comp + 1), np.cumsum(var_ratio[:n_comp]) * 100, 
                    'ro-', linewidth=2, markersize=6, label='Cumulative')
            ax2.set_xlabel('Principal Component', fontsize=12)
            ax2.set_ylabel('Variance Explained (%)', fontsize=12)
            ax2.set_title('Scree Plot', fontsize=14, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, 'pca_plots.png'), dpi=150)
            plt.close()
            print(f"  ✓ PCA图表已生成")
    
    print(f"\n✅ 分析完成! 结果保存在: {args.output_dir}/")
    
    print("\n" + "=" * 70)
    print("  📊 分析报告")
    print("=" * 70)
    print(f"  轨迹文件: {args.trajectory}")
    print(f"  总帧数: {traj_mmap.n_frames:,}")
    print(f"  执行的分析: {' + '.join([k.upper() for k in results.keys()])}")
    print(f"  输出目录: {args.output_dir}/")
    print("=" * 70)
    
    analyzer.close()


if __name__ == "__main__":
    main()
