import numpy as np
from typing import List, Optional, Tuple, Dict
from diagnostic import effective_sample_size, gelman_rubin, autocorrelation


def summary_stats(samples: np.ndarray) -> Dict:
    """计算样本的汇总统计"""
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    
    n, dim = samples.shape
    ess = effective_sample_size(samples)
    
    stats = {
        'n_samples': n,
        'dim': dim,
        'mean': np.mean(samples, axis=0),
        'std': np.std(samples, axis=0),
        'sd_mean': np.std(samples, axis=0) / np.sqrt(n),
        'ess': ess,
        'ess_ratio': ess / n,
        '2.5%': np.percentile(samples, 2.5, axis=0),
        '25%': np.percentile(samples, 25, axis=0),
        '50%': np.percentile(samples, 50, axis=0),
        '75%': np.percentile(samples, 75, axis=0),
        '97.5%': np.percentile(samples, 97.5, axis=0),
        'mcse': np.std(samples, axis=0) / np.sqrt(np.maximum(ess, 1))
    }
    
    return stats


def print_summary(
    samples: np.ndarray,
    parameter_names: Optional[List[str]] = None
):
    """打印样本汇总表格"""
    stats = summary_stats(samples)
    dim = stats['dim']
    
    if parameter_names is None:
        parameter_names = [f'x{i+1}' for i in range(dim)]
    
    print("=" * 85)
    print(f"{'Parameter':<12} {'Mean':>10} {'sd':>10} {'sd_mean':>10} {'ESS':>10} {'ESS%':>8} {'2.5%':>10} {'97.5%':>10}")
    print("-" * 85)
    
    for i in range(dim):
        print(f"{parameter_names[i]:<12} "
              f"{stats['mean'][i]:>10.4f} "
              f"{stats['std'][i]:>10.4f} "
              f"{stats['sd_mean'][i]:>10.4f} "
              f"{stats['ess'][i]:>10.1f} "
              f"{stats['ess_ratio'][i]*100:>7.1f}% "
              f"{stats['2.5%'][i]:>10.4f} "
              f"{stats['97.5%'][i]:>10.4f}")
    
    print("=" * 85)


def compare_chains(
    chains: List[np.ndarray],
    parameter_names: Optional[List[str]] = None
):
    """比较多条链的收敛性"""
    n_chains = len(chains)
    
    if n_chains < 2:
        print("需要至少 2 条链进行收敛性比较")
        return
    
    r_hat = gelman_rubin(chains)
    dim = len(r_hat)
    
    if parameter_names is None:
        parameter_names = [f'x{i+1}' for i in range(dim)]
    
    print("\n" + "=" * 60)
    print("收敛性诊断")
    print("=" * 60)
    
    print(f"\nGelman-Rubin R-hat (目标 < 1.05):")
    for i in range(dim):
        status = "OK" if r_hat[i] < 1.05 else "WARN"
        print(f"  {parameter_names[i]}: {r_hat[i]:.4f} [{status}]")
    
    print(f"\n各链统计:")
    print("-" * 60)
    
    all_means = []
    all_stds = []
    all_ess = []
    
    for c, chain in enumerate(chains):
        stats = summary_stats(chain)
        all_means.append(stats['mean'])
        all_stds.append(stats['std'])
        all_ess.append(stats['ess'])
        
        print(f"\n链 {c+1}:")
        print(f"  样本均值: {stats['mean']}")
        print(f"  样本标准差: {stats['std']}")
        print(f"  ESS: {stats['ess']}")
        print(f"  ESS%: {np.mean(stats['ess_ratio']) * 100:.1f}%")


def trace_statistics(
    samples: np.ndarray,
    max_lag: int = 50
) -> Dict:
    """计算 trace plot 相关统计"""
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    
    n, dim = samples.shape
    
    acfs = []
    for d in range(dim):
        acf = autocorrelation(samples[:, d], max_lag=max_lag)
        acfs.append(acf)
    
    stats = summary_stats(samples)
    stats['acf'] = np.array(acfs)
    
    return stats


def extract_single_chain_stats(
    samples: np.ndarray,
    parameter_names: Optional[List[str]] = None
) -> Dict:
    """提取单链的所有统计信息（用于外部可视化）"""
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    
    n, dim = samples.shape
    
    if parameter_names is None:
        parameter_names = [f'x{i+1}' for i in range(dim)]
    
    acf = autocorrelation(samples[:, 0], max_lag=min(50, n // 2)) if dim > 0 else []
    
    return {
        'samples': samples,
        'parameter_names': parameter_names,
        'n_samples': n,
        'dim': dim,
        'mean': np.mean(samples, axis=0),
        'std': np.std(samples, axis=0),
        'ess': effective_sample_size(samples),
        'acf': acf,
        'percentiles': {
            '2.5%': np.percentile(samples, 2.5, axis=0),
            '25%': np.percentile(samples, 25, axis=0),
            '50%': np.percentile(samples, 50, axis=0),
            '75%': np.percentile(samples, 75, axis=0),
            '97.5%': np.percentile(samples, 97.5, axis=0)
        }
    }


def convergence_check(
    chains: List[np.ndarray],
    r_hat_threshold: float = 1.05,
    min_ess_ratio: float = 0.1
) -> Tuple[bool, Dict]:
    """
    自动化收敛检查
    
    返回:
        (是否收敛, 详细诊断信息)
    """
    diagnostics = {}
    
    if len(chains) >= 2:
        r_hat = gelman_rubin(chains)
        diagnostics['r_hat'] = r_hat
        diagnostics['r_hat_ok'] = all(r < r_hat_threshold for r in r_hat)
    else:
        diagnostics['r_hat'] = None
        diagnostics['r_hat_ok'] = None
    
    all_ess_ok = True
    for i, chain in enumerate(chains):
        stats = summary_stats(chain)
        ess_ratio = stats['ess_ratio']
        all_ess_ok = all_ess_ok and all(er > min_ess_ratio for er in ess_ratio)
        diagnostics[f'chain_{i+1}_ess_ratio'] = ess_ratio
    
    diagnostics['ess_ok'] = all_ess_ok
    
    if len(chains) >= 2:
        converged = diagnostics['r_hat_ok'] and diagnostics['ess_ok']
    else:
        converged = diagnostics['ess_ok']
    
    diagnostics['converged'] = converged
    
    return converged, diagnostics


def generate_test_report(
    chains: List[np.ndarray],
    sampler_name: str = "MCMC",
    parameter_names: Optional[List[str]] = None
) -> str:
    """生成测试报告字符串"""
    report = []
    report.append(f"\n{'='*60}")
    report.append(f"{sampler_name} 采样结果报告")
    report.append(f"{'='*60}")
    
    converged, diagnostics = convergence_check(chains)
    
    if len(chains) >= 2:
        report.append(f"\n链数: {len(chains)}")
        report.append(f"每链样本数: {len(chains[0])}")
    
    if diagnostics.get('r_hat') is not None:
        report.append(f"\nGelman-Rubin R-hat:")
        for i, r in enumerate(diagnostics['r_hat']):
            status = "OK" if r < 1.05 else "WARN"
            name = parameter_names[i] if parameter_names else f'x{i+1}'
            report.append(f"  {name}: {r:.4f} [{status}]")
    
    report.append(f"\n有效样本量 (ESS):")
    for i in range(len(chains)):
        ess_ratio = diagnostics[f'chain_{i+1}_ess_ratio']
        report.append(f"  链 {i+1}: ESS% = {np.mean(ess_ratio) * 100:.1f}%")
    
    conv_status = "已收敛" if converged else "未收敛"
    report.append(f"\n总体收敛: {conv_status}")
    report.append(f"{'='*60}\n")
    
    return "\n".join(report)
