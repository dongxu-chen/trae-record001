import backtrader as bt
import pandas as pd
import numpy as np
from itertools import product
from typing import Dict, List, Tuple, Optional, Callable
import warnings
warnings.filterwarnings('ignore')

try:
    from skopt import gp_minimize, forest_minimize
    from skopt.space import Real, Integer
    from skopt.utils import use_named_args
    from skopt.callbacks import VerboseCallback
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False

from backtest_engine import BacktestEngine, MACrossStrategy, RSIStrategy, MACDStrategy, BollingerBandsStrategy


class ParameterOptimizer:
    STRATEGY_PARAMS = {
        '双均线策略': {
            'fast_period': (2, 20, 2),
            'slow_period': (10, 60, 5),
        },
        'RSI策略': {
            'rsi_period': (7, 21, 2),
            'rsi_overbought': (60, 85, 5),
            'rsi_oversold': (15, 40, 5),
        },
        'MACD策略': {
            'macd_fast': (8, 16, 2),
            'macd_slow': (20, 35, 3),
            'macd_signal': (5, 15, 2),
        },
        '布林带策略': {
            'bb_period': (10, 30, 5),
            'bb_dev': (1.0, 3.0, 0.5),
        },
    }
    
    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.001, 
                 slippage: float = 0.001):
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
    
    def _generate_param_combinations(self, param_ranges: Dict) -> List[Dict]:
        param_names = list(param_ranges.keys())
        param_values = []
        
        for param in param_names:
            start, end, step = param_ranges[param]
            if isinstance(step, float):
                values = np.arange(start, end + step, step)
            else:
                values = range(start, end + step, step)
            param_values.append(list(values))
        
        combinations = []
        for combo in product(*param_values):
            param_dict = dict(zip(param_names, combo))
            combinations.append(param_dict)
        
        return combinations
    
    def _evaluate_params(self, strategy_name: str, data: pd.DataFrame, 
                      params: Dict, optimize_by: str) -> float:
        try:
            engine = BacktestEngine(
                initial_cash=self.initial_cash, 
                commission=self.commission,
                slippage=self.slippage
            )
            metrics = engine.run_backtest(strategy_name, data, params)
            score = metrics.get(optimize_by, 0)
            if optimize_by in ['max_drawdown', 'avg_loss']:
                score = -score
            return score if not np.isnan(score) else -float('inf')
        except:
            return -float('inf')
    
    def grid_search(self, strategy_name: str, data: pd.DataFrame, 
                    param_ranges: Dict = None, optimize_by: str = 'sharpe_ratio',
                    progress_callback: Callable = None) -> Dict:
        if param_ranges is None:
            param_ranges = self.STRATEGY_PARAMS.get(strategy_name, {})
        
        if not param_ranges:
            raise ValueError(f"策略 {strategy_name} 没有定义参数范围")
        
        param_combinations = self._generate_param_combinations(param_ranges)
        total_combinations = len(param_combinations)
        
        results = []
        
        for i, params in enumerate(param_combinations):
            try:
                engine = BacktestEngine(
                    initial_cash=self.initial_cash, 
                    commission=self.commission,
                    slippage=self.slippage
                )
                metrics = engine.run_backtest(strategy_name, data, params)
                metrics['params'] = params
                results.append(metrics)
            except Exception as e:
                print(f"参数组合 {params} 失败: {e}")
            
            if progress_callback:
                progress_callback(i + 1, total_combinations)
        
        if not results:
            raise ValueError("没有有效的参数组合")
        
        sorted_results = sorted(
            results, 
            key=lambda x: x.get(optimize_by, 0), 
            reverse=optimize_by in ['sharpe_ratio', 'total_return', 'win_rate', 'profit_factor']
        )
        
        return {
            'best_params': sorted_results[0]['params'],
            'best_metrics': {k: v for k, v in sorted_results[0].items() if k != 'params'},
            'all_results': sorted_results,
            'optimize_by': optimize_by
        }
    
    def bayesian_optimization(self, strategy_name: str, data: pd.DataFrame,
                               param_ranges: Dict = None, optimize_by: str = 'sharpe_ratio',
                               n_calls: int = 50, random_state: int = 42,
                               base_estimator: str = 'gp',
                               progress_callback: Callable = None) -> Dict:
        if not SKOPT_AVAILABLE:
            raise ImportError("请安装 scikit-optimize: pip install scikit-optimize")
        
        if param_ranges is None:
            param_ranges = self.STRATEGY_PARAMS.get(strategy_name, {})
        
        if not param_ranges:
            raise ValueError(f"策略 {strategy_name} 没有定义参数范围")
        
        param_names = list(param_ranges.keys())
        
        space = []
        for param_name in param_names:
            start, end, step = param_ranges[param_name]
            if isinstance(step, float):
                space.append(Real(start, end, name=param_name))
            else:
                space.append(Integer(start, end, name=param_name))
        
        iteration_count = 0
        total_iterations = n_calls
        all_results = []
        
        @use_named_args(space)
        def objective(**params):
            nonlocal iteration_count
            nonlocal all_results
            
            params_dict = {k: int(v) if isinstance(v, np.integer) else round(float(v), 2) for k, v in params.items()}
            score = self._evaluate_params(strategy_name, data, params_dict, optimize_by)
            
            all_results.append({
                'params': params_dict,
                optimize_by: score
            })
            
            if progress_callback:
                progress_callback(iteration_count + 1, total_iterations)
            iteration_count += 1
            
            return -score
        
        if base_estimator == 'gp':
            result = gp_minimize(
                objective, space, n_calls=n_calls, random_state=random_state,
                acq_func='EI', n_initial_points=10, verbose=0
            )
        else:
            result = forest_minimize(
                objective, space, n_calls=n_calls, random_state=random_state,
                verbose=0
            )
        
        best_params = {name: int(val) if isinstance(val, np.integer) else round(float(val), 2) 
                      for name, val in zip(param_names, result.x)}
        
        engine = BacktestEngine(
            initial_cash=self.initial_cash, 
            commission=self.commission,
            slippage=self.slippage
        )
        best_metrics = engine.run_backtest(strategy_name, data, best_params)
        
        full_results = []
        for r in all_results:
            try:
                engine = BacktestEngine(
                    initial_cash=self.initial_cash, 
                    commission=self.commission,
                    slippage=self.slippage
                )
                metrics = engine.run_backtest(strategy_name, data, r['params'])
                metrics['params'] = r['params']
                full_results.append(metrics)
            except:
                pass
        
        sorted_results = sorted(
            full_results, 
            key=lambda x: x.get(optimize_by, 0), 
            reverse=optimize_by in ['sharpe_ratio', 'total_return', 'win_rate', 'profit_factor']
        )
        
        return {
            'best_params': best_params,
            'best_metrics': best_metrics,
            'all_results': sorted_results,
            'n_calls': n_calls,
            'optimize_by': optimize_by
        }
    
    def genetic_algorithm(self, strategy_name: str, data: pd.DataFrame,
                          param_ranges: Dict = None, optimize_by: str = 'sharpe_ratio',
                          population_size: int = 30, generations: int = 8,
                          mutation_rate: float = 0.2, progress_callback: Callable = None) -> Dict:
        if param_ranges is None:
            param_ranges = self.STRATEGY_PARAMS.get(strategy_name, {})
        
        if not param_ranges:
            raise ValueError(f"策略 {strategy_name} 没有定义参数范围")
        
        def create_individual():
            individual = {}
            for param, (start, end, step) in param_ranges.items():
                if isinstance(step, float):
                    n_steps = int((end - start) / step)
                    idx = np.random.randint(0, n_steps + 1)
                    individual[param] = round(start + idx * step, 2)
                else:
                    values = list(range(start, end + step, step))
                    individual[param] = np.random.choice(values)
            return individual
        
        def fitness(individual):
            return self._evaluate_params(strategy_name, data, individual, optimize_by)
        
        def crossover(parent1, parent2):
            child = {}
            for param in param_ranges.keys():
                if np.random.random() < 0.5:
                    child[param] = parent1[param]
                else:
                    child[param] = parent2[param]
            return child
        
        def mutate(individual):
            param = np.random.choice(list(param_ranges.keys()))
            start, end, step = param_ranges[param]
            if isinstance(step, float):
                n_steps = int((end - start) / step)
                idx = np.random.randint(0, n_steps + 1)
                individual[param] = round(start + idx * step, 2)
            else:
                values = list(range(start, end + step, step))
                individual[param] = np.random.choice(values)
            return individual
        
        population = [create_individual() for _ in range(population_size)]
        best_individual = None
        best_fitness = -float('inf')
        all_results = []
        
        total_iterations = generations * population_size
        current_iteration = 0
        
        for gen in range(generations):
            fitness_scores = [fitness(ind) for ind in population]
            
            for i, score in enumerate(fitness_scores):
                if score > best_fitness:
                    best_fitness = score
                    best_individual = population[i].copy()
            
            for ind, score in zip(population, fitness_scores):
                all_results.append({
                    'generation': gen,
                    'params': ind.copy(),
                    'fitness': score
                })
                current_iteration += 1
                if progress_callback:
                    progress_callback(min(current_iteration, total_iterations), total_iterations)
            
            sorted_indices = np.argsort(fitness_scores)[::-1]
            elites = [population[i].copy() for i in sorted_indices[:5]]
            
            new_population = elites.copy()
            
            while len(new_population) < population_size:
                tournament_size = 5
                tournament_indices = np.random.choice(len(population), tournament_size)
                tournament_fitness = [fitness_scores[i] for i in tournament_indices]
                winner_idx = tournament_indices[np.argmax(tournament_fitness)]
                parent1 = population[winner_idx]
                
                tournament_indices = np.random.choice(len(population), tournament_size)
                tournament_fitness = [fitness_scores[i] for i in tournament_indices]
                winner_idx = tournament_indices[np.argmax(tournament_fitness)]
                parent2 = population[winner_idx]
                
                child = crossover(parent1, parent2)
                if np.random.random() < mutation_rate:
                    child = mutate(child)
                
                new_population.append(child)
            
            population = new_population
        
        engine = BacktestEngine(
            initial_cash=self.initial_cash, 
            commission=self.commission,
            slippage=self.slippage
        )
        best_metrics = engine.run_backtest(strategy_name, data, best_individual)
        
        return {
            'best_params': best_individual,
            'best_metrics': best_metrics,
            'all_results': all_results,
            'generations': generations,
            'population_size': population_size,
            'optimize_by': optimize_by
        }
    
    def get_param_heatmap_data(self, optimization_results: Dict, 
                                x_param: str, y_param: str) -> pd.DataFrame:
        df = pd.DataFrame([
            {**r['params'], 'score': r.get(optimization_results['optimize_by'], 0)}
            for r in optimization_results['all_results']
        ])
        
        pivot = df.pivot(index=y_param, columns=x_param, values='score')
        return pivot
