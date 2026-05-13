import numpy as np
import multiprocessing as mp
from typing import Optional, Callable, Tuple, Union, List
from distribution import Distribution
from proposal import Proposal


class MetropolisHastings:
    """Metropolis-Hastings 采样器"""

    def __init__(
        self,
        target: Distribution,
        proposal: Proposal,
        initial: np.ndarray
    ):
        self.target = target
        self.proposal = proposal
        self.current = np.asarray(initial).copy()
        self.current_log_pdf = self.target.log_pdf(self.current)
        self.accepted = 0
        self.total = 0
        self.consecutive_rejections = 0
        self.max_consecutive_rejections = 0
        self.history = {
            'accepted_count': 0,
            'rejected_count': 0
        }

    def step(self) -> Tuple[np.ndarray, bool]:
        """执行一次MH迭代，返回(样本, 是否接受)"""
        proposed = self.proposal.propose(self.current)
        proposed_log_pdf = self.target.log_pdf(proposed)

        log_alpha = proposed_log_pdf - self.current_log_pdf

        if not self.proposal.is_symmetric:
            log_alpha += (
                self.proposal.log_transition_prob(proposed, self.current) -
                self.proposal.log_transition_prob(self.current, proposed)
            )

        accepted = np.log(np.random.uniform()) < log_alpha

        if accepted:
            self.current = proposed
            self.current_log_pdf = proposed_log_pdf
            self.accepted += 1
            self.consecutive_rejections = 0
            self.history['accepted_count'] += 1
        else:
            self.consecutive_rejections += 1
            self.max_consecutive_rejections = max(
                self.max_consecutive_rejections,
                self.consecutive_rejections
            )
            self.history['rejected_count'] += 1

        self.total += 1
        return self.current.copy(), accepted

    def sample(
        self,
        n_samples: int,
        burn_in: int = 0,
        thin: int = 1,
        callback: Optional[Callable[[int, np.ndarray], None]] = None,
        auto_thin: bool = False,
        target_ess_ratio: float = 0.5
    ) -> np.ndarray:
        """执行采样

        参数:
            n_samples: 目标样本数
            burn_in: burn-in 步数
            thin: 抽稀间隔
            callback: 回调函数
            auto_thin: 是否自动调整 thinning
            target_ess_ratio: 目标 ESS/总样本比例
        """
        if auto_thin:
            return self._sample_auto_thin(n_samples, burn_in, callback, target_ess_ratio)

        samples = []
        for i in range(burn_in + n_samples * thin):
            sample, _ = self.step()
            if i >= burn_in and (i - burn_in) % thin == 0:
                samples.append(sample)
                if callback is not None:
                    callback(len(samples) - 1, sample)

        return np.array(samples)

    def _sample_auto_thin(
        self,
        n_samples: int,
        burn_in: int,
        callback: Optional[Callable[[int, np.ndarray], None]],
        target_ess_ratio: float
    ) -> np.ndarray:
        """带自动 thinning 的采样"""
        from diagnostic import effective_sample_size

        pilot_samples = []
        for i in range(burn_in + 500):
            sample, _ = self.step()
            if i >= burn_in:
                pilot_samples.append(sample)

        pilot = np.array(pilot_samples)
        if len(pilot) > 50:
            ess = effective_sample_size(pilot)
            avg_ess = np.mean(ess)
            if avg_ess > 0:
                eff_thin = max(1, int(len(pilot) / avg_ess / target_ess_ratio))
            else:
                eff_thin = 5
        else:
            eff_thin = 5

        samples = []
        total_needed = n_samples * eff_thin

        for i in range(total_needed):
            sample, _ = self.step()
            if i % eff_thin == 0:
                samples.append(sample)
                if callback is not None:
                    callback(len(samples) - 1, sample)

        return np.array(samples[:n_samples])

    def acceptance_rate(self, window: Optional[int] = None) -> float:
        """返回接受率

        参数:
            window: 窗口大小，None 表示所有历史
        """
        if self.total == 0:
            return 0.0
        return self.accepted / self.total

    def reset(self, initial: Optional[np.ndarray] = None):
        """重置采样器"""
        if initial is not None:
            self.current = np.asarray(initial).copy()
        self.current_log_pdf = self.target.log_pdf(self.current)
        self.accepted = 0
        self.total = 0
        self.consecutive_rejections = 0
        self.max_consecutive_rejections = 0
        self.history = {
            'accepted_count': 0,
            'rejected_count': 0
        }


class AdaptiveMetropolisHastings(MetropolisHastings):
    """自适应Metropolis-Hastings采样器"""

    def __init__(
        self,
        target: Distribution,
        proposal: Proposal,
        initial: np.ndarray,
        adaptation_start: int = 100,
        adaptation_window: int = 50,
        target_acceptance: float = 0.234,
        min_scale: float = 1e-6,
        max_scale: float = 1e6,
        adaptation_rate: Callable[[int], float] = None
    ):
        super().__init__(target, proposal, initial)
        self.adaptation_start = adaptation_start
        self.adaptation_window = adaptation_window
        self.target_acceptance = target_acceptance
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.adaptation_rate = adaptation_rate if adaptation_rate is not None else (
            lambda k: min(0.1, 1.0 / np.sqrt(k + 1))
        )
        self.adaptation_step = 0
        self._recent_accepts = []

    def step(self) -> Tuple[np.ndarray, bool]:
        """执行一次自适应MH迭代"""
        result, accepted = super().step()
        self._recent_accepts.append(accepted)
        if len(self._recent_accepts) > self.adaptation_window:
            self._recent_accepts.pop(0)

        if (self.total >= self.adaptation_start and
            len(self._recent_accepts) >= self.adaptation_window):
            self.adaptation_step += 1
            current_rate = sum(self._recent_accepts) / len(self._recent_accepts)
            rate = self.adaptation_rate(self.adaptation_step)
            diff = current_rate - self.target_acceptance

            if hasattr(self.proposal, 'scale'):
                adjustment = np.exp(rate * np.sign(diff))
                new_scale = self.proposal.scale * adjustment
                self.proposal.scale = np.clip(new_scale, self.min_scale, self.max_scale)
            elif hasattr(self.proposal, 'width'):
                adjustment = np.exp(rate * np.sign(diff))
                new_width = self.proposal.width * adjustment
                self.proposal.width = np.clip(new_width, self.min_scale, self.max_scale)
                self.proposal.half_width = self.proposal.width / 2.0

        return result, accepted


def _sample_single_chain(args):
    """单链采样的辅助函数（用于多进程）"""
    target, proposal_class, proposal_kwargs, initial, n_samples, burn_in, thin, seed = args
    
    np.random.seed(seed)
    
    proposal = proposal_class(**proposal_kwargs)
    
    mh = MetropolisHastings(target, proposal, initial)
    samples = mh.sample(n_samples=n_samples, burn_in=burn_in, thin=thin)
    
    return samples, mh.acceptance_rate(), mh.max_consecutive_rejections


def sample_parallel(
    target: Distribution,
    proposal_class,
    proposal_kwargs: dict,
    initial_states: List[np.ndarray],
    n_samples: int,
    burn_in: int = 0,
    thin: int = 1,
    n_jobs: Optional[int] = None,
    seeds: Optional[List[int]] = None
) -> Tuple[List[np.ndarray], List[float], List[int]]:
    """
    多进程并行采样多条 MCMC 链
    
    参数:
        target: 目标分布
        proposal_class: 提议分布类（必须可序列化）
        proposal_kwargs: 提议分布的初始化参数
        initial_states: 各链的初始状态列表
        n_samples: 每条链的样本数
        burn_in: burn-in 步数
        thin: 抽稀间隔
        n_jobs: 进程数，None 表示使用所有 CPU 核心
        seeds: 随机种子列表
    
    返回:
        (samples_list, acceptance_rates, max_rejections)
    """
    n_chains = len(initial_states)
    
    if seeds is None:
        seeds = [np.random.randint(0, 2**31) for _ in range(n_chains)]
    
    if n_jobs is None:
        n_jobs = min(mp.cpu_count(), n_chains)
    else:
        n_jobs = min(n_jobs, n_chains)
    
    args_list = []
    for i in range(n_chains):
        args_list.append((
            target,
            proposal_class,
            proposal_kwargs,
            initial_states[i],
            n_samples,
            burn_in,
            thin,
            seeds[i]
        ))
    
    if n_jobs == 1:
        results = [_sample_single_chain(args) for args in args_list]
    else:
        with mp.Pool(processes=n_jobs) as pool:
            results = pool.map(_sample_single_chain, args_list)
    
    samples_list = [r[0] for r in results]
    acceptance_rates = [r[1] for r in results]
    max_rejections = [r[2] for r in results]
    
    return samples_list, acceptance_rates, max_rejections
