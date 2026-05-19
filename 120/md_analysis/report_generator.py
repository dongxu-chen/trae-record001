import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime
from typing import Optional, Dict, Tuple
import os


class ReportGenerator:
    def __init__(self, 
                 trajectory_summary: dict,
                 rmsd_results: Optional[dict] = None,
                 rg_results: Optional[dict] = None,
                 hbond_results: Optional[dict] = None,
                 pca_results: Optional[dict] = None,
                 fes_results: Optional[dict] = None):
        self.trajectory_summary = trajectory_summary
        self.rmsd_results = rmsd_results
        self.rg_results = rg_results
        self.hbond_results = hbond_results
        self.pca_results = pca_results
        self.fes_results = fes_results

    def generate_text_report(self, output_file: str = "analysis_report.txt") -> None:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("    分子动力学轨迹分析报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("-" * 60 + "\n")
            f.write("1. 轨迹文件信息\n")
            f.write("-" * 60 + "\n")
            f.write(f"  拓扑文件: {self.trajectory_summary.get('topology_file', 'N/A')}\n")
            f.write(f"  轨迹文件: {self.trajectory_summary.get('trajectory_file', 'N/A')}\n")
            f.write(f"  帧数: {self.trajectory_summary.get('n_frames', 'N/A')}\n")
            f.write(f"  原子数: {self.trajectory_summary.get('n_atoms', 'N/A')}\n")
            f.write(f"  时间步长: {self.trajectory_summary.get('time_step', 'N/A')} ps\n")
            f.write(f"  总模拟时间: {self.trajectory_summary.get('total_time', 'N/A')} ps\n\n")
            
            if self.rmsd_results:
                f.write("-" * 60 + "\n")
                f.write("2. RMSD (均方根偏差) 分析\n")
                f.write("-" * 60 + "\n")
                f.write(f"  选择原子组: {self.rmsd_results.get('selection', 'N/A')}\n")
                f.write(f"  参考帧: {self.rmsd_results.get('reference_frame', 'N/A')}\n\n")
                
                rmsd_values = self.rmsd_results['rmsd']
                f.write("  统计信息:\n")
                f.write(f"    平均值: {np.mean(rmsd_values):.4f} Å\n")
                f.write(f"    标准差: {np.std(rmsd_values):.4f} Å\n")
                f.write(f"    最小值: {np.min(rmsd_values):.4f} Å\n")
                f.write(f"    最大值: {np.max(rmsd_values):.4f} Å\n")
                f.write(f"    中位数: {np.median(rmsd_values):.4f} Å\n\n")
                
                if 'groups' in self.rmsd_results:
                    f.write("  各基团RMSD统计:\n")
                    for group_name, group_rmsd in self.rmsd_results['groups'].items():
                        f.write(f"    {group_name}:\n")
                        f.write(f"      平均值: {np.mean(group_rmsd):.4f} Å\n")
                        f.write(f"      标准差: {np.std(group_rmsd):.4f} Å\n")
                    f.write("\n")
            
            if self.rg_results:
                f.write("-" * 60 + "\n")
                f.write("3. 回旋半径 (Rg) 分析\n")
                f.write("-" * 60 + "\n")
                f.write(f"  选择原子组: {self.rg_results.get('selection', 'N/A')}\n")
                f.write(f"  质量加权: {self.rg_results.get('use_masses', False)}\n\n")
                
                rg_values = self.rg_results['rg']
                f.write("  统计信息:\n")
                f.write(f"    平均值: {np.mean(rg_values):.4f} Å\n")
                f.write(f"    标准差: {np.std(rg_values):.4f} Å\n")
                f.write(f"    最小值: {np.min(rg_values):.4f} Å\n")
                f.write(f"    最大值: {np.max(rg_values):.4f} Å\n")
                f.write(f"    中位数: {np.median(rg_values):.4f} Å\n\n")
                
                if 'groups' in self.rg_results:
                    f.write("  各基团Rg统计:\n")
                    for group_name, group_rg in self.rg_results['groups'].items():
                        f.write(f"    {group_name}:\n")
                        f.write(f"      平均值: {np.mean(group_rg):.4f} Å\n")
                        f.write(f"      标准差: {np.std(group_rg):.4f} Å\n")
                    f.write("\n")
            
            if self.hbond_results:
                f.write("-" * 60 + "\n")
                f.write("4. 氢键分析\n")
                f.write("-" * 60 + "\n")
                f.write(f"  距离阈值: {self.hbond_results.get('distance_cutoff', 3.5)} Å\n")
                f.write(f"  角度阈值: {self.hbond_results.get('angle_cutoff', 120.0)}°\n\n")
                
                hbond_values = self.hbond_results['hbond_counts']
                f.write("  统计信息:\n")
                f.write(f"    平均值: {np.mean(hbond_values):.2f} 个/帧\n")
                f.write(f"    标准差: {np.std(hbond_values):.2f}\n")
                f.write(f"    最小值: {np.min(hbond_values)} 个\n")
                f.write(f"    最大值: {np.max(hbond_values)} 个\n")
                f.write(f"    中位数: {np.median(hbond_values):.2f} 个\n\n")
            
            if self.pca_results:
                f.write("-" * 60 + "\n")
                f.write("5. 主成分分析 (PCA)\n")
                f.write("-" * 60 + "\n")
                f.write(f"  原子选择: {self.pca_results.get('selection', 'N/A')}\n")
                f.write(f"  原子数: {self.pca_results.get('n_atoms', 'N/A')}\n")
                f.write(f"  帧数: {self.pca_results.get('n_frames', 'N/A')}\n\n")
                
                f.write("  解释方差 (前5个主成分):\n")
                var_ratio = self.pca_results.get('variance_ratio', [])
                cum_var = self.pca_results.get('cumulative_variance', [])
                for i in range(min(5, len(var_ratio))):
                    f.write(f"    PC{i+1}: {var_ratio[i]*100:6.2f}%  (累计: {cum_var[i]*100:6.2f}%)\n")
                f.write("\n")
                
                if 'key_residues_pc1' in self.pca_results:
                    f.write("  PC1 关键残基 (Top 5):\n")
                    for res_info in self.pca_results['key_residues_pc1'][:5]:
                        f.write(f"    {res_info['resname']}{res_info['resid']}: {res_info['contribution']*100:.2f}%\n")
                    f.write("\n")
                
                if 'key_residues_pc2' in self.pca_results:
                    f.write("  PC2 关键残基 (Top 5):\n")
                    for res_info in self.pca_results['key_residues_pc2'][:5]:
                        f.write(f"    {res_info['resname']}{res_info['resid']}: {res_info['contribution']*100:.2f}%\n")
                    f.write("\n")
            
            if self.fes_results:
                f.write("-" * 60 + "\n")
                f.write("6. 自由能形貌图 (FES)\n")
                f.write("-" * 60 + "\n")
                f.write(f"  温度: {self.fes_results.get('temperature', 300)} K\n")
                f.write(f"  计算方法: {self.fes_results.get('method', 'histogram')}\n")
                f.write(f"  网格数: {self.fes_results.get('bins', 100)}\n\n")
                
                if 'minima' in self.fes_results:
                    f.write("  自由能极小值点:\n")
                    for i, (x, y, e) in enumerate(self.fes_results['minima']):
                        f.write(f"    极小值{i+1}: PC1={x:.3f}, PC2={y:.3f}, ΔG={e:.2f} kJ/mol\n")
                f.write("\n")
            
            f.write("=" * 60 + "\n")
            f.write("报告结束\n")
            f.write("=" * 60 + "\n")

    def generate_csv_data(self, output_prefix: str = "analysis") -> None:
        if self.rmsd_results:
            df_rmsd = pd.DataFrame({
                'time_ps': self.rmsd_results['time'],
                'rmsd_Å': self.rmsd_results['rmsd']
            })
            if 'groups' in self.rmsd_results:
                for group_name, group_rmsd in self.rmsd_results['groups'].items():
                    df_rmsd[f'rmsd_{group_name}_Å'] = group_rmsd
            df_rmsd.to_csv(f"{output_prefix}_rmsd.csv", index=False)
        
        if self.rg_results:
            df_rg = pd.DataFrame({
                'time_ps': self.rg_results['time'],
                'rg_Å': self.rg_results['rg']
            })
            if 'groups' in self.rg_results:
                for group_name, group_rg in self.rg_results['groups'].items():
                    df_rg[f'rg_{group_name}_Å'] = group_rg
            df_rg.to_csv(f"{output_prefix}_rg.csv", index=False)
        
        if self.hbond_results:
            df_hbond = pd.DataFrame({
                'time_ps': self.hbond_results['time'],
                'hbond_count': self.hbond_results['hbond_counts']
            })
            df_hbond.to_csv(f"{output_prefix}_hbond.csv", index=False)
        
        if self.pca_results:
            if 'projections' in self.pca_results:
                df_proj = pd.DataFrame({
                    'PC1': self.pca_results['projections'][:, 0],
                    'PC2': self.pca_results['projections'][:, 1]
                })
                df_proj.to_csv(f"{output_prefix}_pca_projections.csv", index=False)
            
            if 'residue_contributions' in self.pca_results:
                res_contrib = self.pca_results['residue_contributions']
                df_res = pd.DataFrame({
                    'resid': res_contrib['resids'],
                    'resname': res_contrib['resnames'],
                    'contribution_PC1': res_contrib['contributions'][:, 0],
                    'contribution_PC2': res_contrib['contributions'][:, 1]
                })
                df_res.to_csv(f"{output_prefix}_residue_contributions.csv", index=False)

    def generate_plots(self, output_prefix: str = "analysis", dpi: int = 300) -> None:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.size'] = 10
        
        if self.rmsd_results:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(self.rmsd_results['time'], self.rmsd_results['rmsd'], 
                   'b-', linewidth=1.5, label='RMSD')
            
            if 'groups' in self.rmsd_results:
                colors = ['r', 'g', 'orange', 'purple']
                for i, (group_name, group_rmsd) in enumerate(self.rmsd_results['groups'].items()):
                    color = colors[i % len(colors)]
                    ax.plot(self.rmsd_results['time'], group_rmsd, 
                           f'{color}-', linewidth=1.2, alpha=0.7, label=group_name)
            
            ax.set_xlabel('Time (ps)', fontsize=12)
            ax.set_ylabel('RMSD (Å)', fontsize=12)
            ax.set_title('Root Mean Square Deviation vs Time', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{output_prefix}_rmsd.png", dpi=dpi)
            plt.close()
        
        if self.rg_results:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(self.rg_results['time'], self.rg_results['rg'], 
                   'g-', linewidth=1.5, label='Rg')
            
            if 'groups' in self.rg_results:
                colors = ['b', 'r', 'orange', 'purple']
                for i, (group_name, group_rg) in enumerate(self.rg_results['groups'].items()):
                    color = colors[i % len(colors)]
                    ax.plot(self.rg_results['time'], group_rg, 
                           f'{color}-', linewidth=1.2, alpha=0.7, label=group_name)
            
            ax.set_xlabel('Time (ps)', fontsize=12)
            ax.set_ylabel('Radius of Gyration (Å)', fontsize=12)
            ax.set_title('Radius of Gyration vs Time', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{output_prefix}_rg.png", dpi=dpi)
            plt.close()
        
        if self.rmsd_results and self.rg_results:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
            
            ax1.plot(self.rmsd_results['time'], self.rmsd_results['rmsd'], 'b-', linewidth=1.5)
            ax1.set_ylabel('RMSD (Å)', fontsize=12)
            ax1.set_title('RMSD and Rg Analysis', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            
            ax2.plot(self.rg_results['time'], self.rg_results['rg'], 'g-', linewidth=1.5)
            ax2.set_xlabel('Time (ps)', fontsize=12)
            ax2.set_ylabel('Rg (Å)', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{output_prefix}_combined.png", dpi=dpi)
            plt.close()
        
        if self.hbond_results:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(self.hbond_results['time'], self.hbond_results['hbond_counts'], 
                   'purple', linewidth=1.5, label='Hydrogen Bonds')
            
            ax.set_xlabel('Time (ps)', fontsize=12)
            ax.set_ylabel('Number of Hydrogen Bonds', fontsize=12)
            ax.set_title('Hydrogen Bond Count vs Time', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{output_prefix}_hbond.png", dpi=dpi)
            plt.close()
        
        if self.pca_results:
            if 'variance_ratio' in self.pca_results:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
                
                n_comp = min(20, len(self.pca_results['variance_ratio']))
                ax1.bar(range(1, n_comp + 1), 
                       self.pca_results['variance_ratio'][:n_comp] * 100,
                       color='steelblue', alpha=0.8)
                ax1.set_xlabel('Principal Component', fontsize=12)
                ax1.set_ylabel('Variance Explained (%)', fontsize=12)
                ax1.set_title('Scree Plot', fontsize=14, fontweight='bold')
                ax1.grid(True, alpha=0.3, axis='y')
                
                ax2.plot(range(1, n_comp + 1),
                        self.pca_results['cumulative_variance'][:n_comp] * 100,
                        'ro-', linewidth=2)
                ax2.set_xlabel('Principal Component', fontsize=12)
                ax2.set_ylabel('Cumulative Variance (%)', fontsize=12)
                ax2.set_title('Cumulative Variance Explained', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3)
                ax2.axhline(y=80, color='gray', linestyle='--', alpha=0.7, label='80% threshold')
                ax2.legend()
                
                plt.tight_layout()
                plt.savefig(f"{output_prefix}_pca_variance.png", dpi=dpi)
                plt.close()
            
            if 'projections' in self.pca_results:
                fig, ax = plt.subplots(figsize=(10, 8))
                
                proj = self.pca_results['projections']
                scatter = ax.scatter(proj[:, 0], proj[:, 1], 
                                    c=np.arange(len(proj)), cmap='viridis',
                                    alpha=0.6, s=20)
                
                cbar = plt.colorbar(scatter, ax=ax)
                cbar.set_label('Frame Index', fontsize=12)
                
                ax.set_xlabel(f"PC1 ({self.pca_results['variance_ratio'][0]*100:.1f}%)", fontsize=12)
                ax.set_ylabel(f"PC2 ({self.pca_results['variance_ratio'][1]*100:.1f}%)", fontsize=12)
                ax.set_title('PCA Projection on PC1 vs PC2', fontsize=14, fontweight='bold')
                ax.grid(True, alpha=0.3)
                
                plt.tight_layout()
                plt.savefig(f"{output_prefix}_pca_projection.png", dpi=dpi)
                plt.close()
            
            if 'residue_contributions' in self.pca_results:
                res_contrib = self.pca_results['residue_contributions']
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
                
                resids = res_contrib['resids']
                contrib_pc1 = res_contrib['contributions'][:, 0] * 100
                contrib_pc2 = res_contrib['contributions'][:, 1] * 100
                
                ax1.bar(resids, contrib_pc1, color='steelblue', alpha=0.8, width=0.8)
                ax1.set_xlabel('Residue Number', fontsize=12)
                ax1.set_ylabel('Contribution to PC1 (%)', fontsize=12)
                ax1.set_title('Residue Contributions to PC1', fontsize=14, fontweight='bold')
                ax1.grid(True, alpha=0.3, axis='y')
                
                top_pc1_idx = np.argsort(contrib_pc1)[-5:][::-1]
                for idx in top_pc1_idx:
                    ax1.annotate(f"{res_contrib['resnames'][idx]}{resids[idx]}",
                                (resids[idx], contrib_pc1[idx]),
                                textcoords="offset points", xytext=(0, 5), ha='center', fontsize=9)
                
                ax2.bar(resids, contrib_pc2, color='coral', alpha=0.8, width=0.8)
                ax2.set_xlabel('Residue Number', fontsize=12)
                ax2.set_ylabel('Contribution to PC2 (%)', fontsize=12)
                ax2.set_title('Residue Contributions to PC2', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3, axis='y')
                
                top_pc2_idx = np.argsort(contrib_pc2)[-5:][::-1]
                for idx in top_pc2_idx:
                    ax2.annotate(f"{res_contrib['resnames'][idx]}{resids[idx]}",
                                (resids[idx], contrib_pc2[idx]),
                                textcoords="offset points", xytext=(0, 5), ha='center', fontsize=9)
                
                plt.tight_layout()
                plt.savefig(f"{output_prefix}_residue_contributions.png", dpi=dpi)
                plt.close()
        
        if self.fes_results:
            fig, ax = plt.subplots(figsize=(10, 8))
            
            colors = ['#3a5f0b', '#6aa84f', '#a2c9ac', '#e69138', '#cc4125', '#741b47']
            n_bin = len(self.fes_results['fes'])
            cmap = LinearSegmentedColormap.from_list('fes_cmap', colors, N=n_bin)
            
            im = ax.contourf(self.fes_results['x_grid'],
                            self.fes_results['y_grid'],
                            self.fes_results['fes'],
                            levels=20,
                            cmap=cmap,
                            alpha=0.9)
            
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Free Energy (kJ/mol)', fontsize=12)
            
            ax.contour(self.fes_results['x_grid'],
                      self.fes_results['y_grid'],
                      self.fes_results['fes'],
                      levels=10,
                      colors='black',
                      linewidths=0.5,
                      alpha=0.5)
            
            if 'minima' in self.fes_results:
                for i, (x, y, e) in enumerate(self.fes_results['minima']):
                    ax.plot(x, y, 'w*', markersize=15, markeredgecolor='black')
                    ax.annotate(f"M{i+1}\n{e:.1f} kJ/mol", (x, y),
                               textcoords="offset points", xytext=(10, 10),
                               ha='center', fontsize=10, fontweight='bold')
            
            ax.set_xlabel('PC1', fontsize=12)
            ax.set_ylabel('PC2', fontsize=12)
            ax.set_title('Free Energy Surface (FES)', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(f"{output_prefix}_fes.png", dpi=dpi)
            plt.close()

    def generate_full_report(self, output_dir: str = "analysis_results", 
                            output_prefix: str = "analysis") -> None:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_prefix)
        
        self.generate_text_report(f"{output_path}_report.txt")
        self.generate_csv_data(output_path)
        self.generate_plots(output_path)
        
        print(f"完整报告已生成到目录: {output_dir}")
