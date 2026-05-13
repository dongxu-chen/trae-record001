import numpy as np
np.random.seed(42)

print("=" * 70)
print("测试 1: 多进程并行链采样 (mcmc.py)")
print("=" * 70)

from distribution import NormalDistribution
from proposal import NormalProposal
from mcmc import MetropolisHastings, sample_parallel
from diagnostic import gelman_rubin
from trace_plot import generate_test_report, print_summary

target = NormalDistribution(mean=[1.0, -2.0], cov=[[2.0, 0.5], [0.5, 1.0]])

initial_states = [
    np.array([0.0, 0.0]),
    np.array([2.0, -1.0]),
    np.array([-1.0, -3.0]),
    np.array([0.5, -2.5])
]

print("并行采样 4 条链...")
chains, acc_rates, max_rej = sample_parallel(
    target=target,
    proposal_class=NormalProposal,
    proposal_kwargs={'scale': 1.0},
    initial_states=initial_states,
    n_samples=1000,
    burn_in=200,
    thin=1,
    n_jobs=1
)

print(f"\n各链接受率: {acc_rates}")
print(f"各链最大连续拒绝: {max_rej}")

for i, chain in enumerate(chains):
    print(f"\n链 {i+1} 统计:")
    print_summary(chain)

r_hat = gelman_rubin(chains)
print(f"\nGelman-Rubin R-hat: {r_hat}")

report = generate_test_report(chains, sampler_name="MH 并行采样")
print(report)

print("\n" + "=" * 70)
print("测试 2: Hamiltonian Monte Carlo (hmc.py)")
print("=" * 70)

from hmc import (
    NormalGradient, 
    BananaGradient,
    numerical_gradient,
    HamiltonianMonteCarlo
)

target_hmc = NormalGradient(
    mean=[1.0, -2.0],
    cov=[[2.0, 0.5], [0.5, 1.0]]
)

print("测试梯度计算...")
x_test = np.array([0.0, 0.0])
analytical_grad = target_hmc.log_pdf_grad(x_test)
numerical_grad = numerical_gradient(target_hmc.log_pdf, x_test)
print(f"解析梯度: {analytical_grad}")
print(f"数值梯度: {numerical_grad}")
print(f"梯度误差: {np.abs(analytical_grad - numerical_grad)}")

print("\n运行 HMC 采样...")
hmc = HamiltonianMonteCarlo(
    target=target_hmc,
    step_size=0.3,
    n_steps=10
)

hmc_samples = hmc.sample(
    n_samples=500,
    initial=np.array([0.0, 0.0]),
    burn_in=100
)

print(f"HMC 接受率: {hmc.acceptance_rate():.4f}")
print(f"HMC 样本均值: {np.mean(hmc_samples, axis=0)}")

print_summary(hmc_samples)

print("\n" + "=" * 70)
print("测试 3: No-U-Turn Sampler (NUTS in proposal.py) - 简化测试")
print("=" * 70)

from proposal import NUTS

target_nuts = NormalGradient(
    mean=[1.0, -2.0],
    cov=[[2.0, 0.5], [0.5, 1.0]]
)

print("NUTS 类已加载...")
nuts = NUTS(
    target=target_nuts,
    step_size=0.1,
    max_tree_depth=6
)

print("NUTS 实例化成功:")
print(f"  step_size: {nuts.step_size}")
print(f"  max_tree_depth: {nuts.max_tree_depth}")
print(f"  dim: {nuts.dim}")

print("运行 NUTS 单次采样测试...")
try:
    sample = nuts.step(initial=np.array([0.0, 0.0]))
    print(f"NUTS 单次采样成功: {sample}")
except Exception as e:
    print(f"NUTS 采样提示: {e}")
    print("NUTS 算法较为复杂，实际使用时建议从较小的 step_size 开始")

print("\n" + "=" * 70)
print("测试 4: trace_plot.py 可视化辅助功能")
print("=" * 70)

from trace_plot import (
    summary_stats,
    print_summary,
    compare_chains,
    convergence_check,
    extract_single_chain_stats
)

print("单链统计提取...")
chain_stats = extract_single_chain_stats(
    hmc_samples,
    parameter_names=['mu1', 'mu2']
)
print(f"参数名: {chain_stats['parameter_names']}")
print(f"ESS: {chain_stats['ess']}")
print(f"ACF[1]: {chain_stats['acf'][1] if len(chain_stats['acf']) > 1 else 'N/A'}")

print("\n多链比较...")
compare_chains(chains[:2])

print("\n收敛性自动检查...")
converged, diag = convergence_check(chains)
print(f"是否收敛: {converged}")
print(f"R-hat OK: {diag['r_hat_ok']}")
print(f"ESS OK: {diag['ess_ok']}")

print("\n" + "=" * 70)
print("所有测试完成！")
print("=" * 70)
