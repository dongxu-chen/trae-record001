import pandas as pd
import numpy as np
import random
import copy
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass
from factor_engine import FactorEngine
from performance import PerformanceAnalyzer


@dataclass
class FactorIndividual:
    expression: str
    fitness: float = 0.0
    ic_mean: float = 0.0
    ic_ir: float = 0.0
    overfitting_score: float = 0.0
    is_valid: bool = True


class GeneticFactorMiner:
    def __init__(self, factor_data: Dict[str, pd.DataFrame],
                 returns: pd.DataFrame,
                 rebalance_dates: pd.DatetimeIndex,
                 base_factors: List[str] = None,
                 population_size: int = 50,
                 max_generations: int = 20,
                 mutation_rate: float = 0.3,
                 crossover_rate: float = 0.7,
                 max_expression_depth: int = 3):
        
        self.factor_data = factor_data
        self.returns = returns
        self.rebalance_dates = rebalance_dates
        self.base_factors = base_factors or list(factor_data.keys())
        self.population_size = population_size
        self.max_generations = max_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.max_expression_depth = max_expression_depth
        
        self.engine = FactorEngine(factor_data)
        self.analyzer = PerformanceAnalyzer(returns)
        
        self.operators = ['+', '-', '*', '/']
        self.functions = ['rank', 'zscore', 'abs', 'log', 'sqrt', 'delta', 'mean', 'std', 'pct_change']
        
        self.train_ratio = 0.7
        self.best_factors = []
        
        random.seed(42)
        np.random.seed(42)

    def _random_terminal(self) -> str:
        return random.choice(self.base_factors)

    def _random_function(self) -> str:
        return random.choice(self.functions)

    def _random_operator(self) -> str:
        return random.choice(self.operators)

    def _generate_expression(self, depth: int = 0) -> str:
        if depth >= self.max_expression_depth:
            return self._random_terminal()
        
        choice = random.random()
        
        if choice < 0.3:
            return self._random_terminal()
        elif choice < 0.6:
            func = self._random_function()
            arg = self._generate_expression(depth + 1)
            if func in ['mean', 'std', 'delta', 'pct_change']:
                period = random.randint(5, 60)
                return f'{func}({arg}, {period})'
            return f'{func}({arg})'
        else:
            left = self._generate_expression(depth + 1)
            op = self._random_operator()
            right = self._generate_expression(depth + 1)
            return f'({left} {op} {right})'

    def _init_population(self) -> List[FactorIndividual]:
        population = []
        for _ in range(self.population_size):
            expr = self._generate_expression()
            population.append(FactorIndividual(expression=expr))
        return population

    def _evaluate_fitness(self, individual: FactorIndividual, 
                          is_train: bool = True) -> Tuple[float, float, float, bool]:
        try:
            factor_values = self.engine.calculate_factor(individual.expression)
            
            if factor_values.isnull().all().all():
                return 0.0, 0.0, 0.0, False
            
            if is_train:
                split_idx = int(len(self.rebalance_dates) * self.train_ratio)
                eval_dates = self.rebalance_dates[:split_idx]
            else:
                split_idx = int(len(self.rebalance_dates) * self.train_ratio)
                eval_dates = self.rebalance_dates[split_idx:]
            
            if len(eval_dates) < 3:
                return 0.0, 0.0, 0.0, False
            
            temp_dates = pd.DatetimeIndex(eval_dates)
            ic_series = self.analyzer.calculate_ic_by_rebalance(
                factor_values, self.returns, temp_dates
            )
            
            valid_ic = ic_series.dropna()
            if len(valid_ic) < 5:
                return 0.0, 0.0, 0.0, False
            
            ic_mean = valid_ic.mean()
            ic_std = valid_ic.std()
            ic_ir = ic_mean / ic_std if ic_std > 0 else 0
            
            fitness = ic_ir * (1 + ic_mean * 10)
            
            return fitness, ic_mean, ic_ir, True
            
        except Exception as e:
            return 0.0, 0.0, 0.0, False

    def _crossover(self, parent1: FactorIndividual, 
                   parent2: FactorIndividual) -> FactorIndividual:
        expr1 = parent1.expression
        expr2 = parent2.expression
        
        if random.random() < 0.5:
            child_expr = f'({expr1} + {expr2})'
        else:
            child_expr = f'({expr1} - {expr2})'
        
        return FactorIndividual(expression=child_expr)

    def _mutate(self, individual: FactorIndividual) -> FactorIndividual:
        expr = individual.expression
        
        if random.random() < 0.4:
            new_subexpr = self._generate_expression(depth=1)
            return FactorIndividual(expression=f'{random.choice(self.functions)}({expr})')
        elif random.random() < 0.7:
            new_subexpr = self._generate_expression(depth=1)
            op = random.choice(self.operators)
            return FactorIndividual(expression=f'({expr} {op} {new_subexpr})')
        else:
            return FactorIndividual(expression=self._generate_expression())

    def _select_parents(self, population: List[FactorIndividual], 
                        tournament_size: int = 5) -> Tuple[FactorIndividual, FactorIndividual]:
        def tournament():
            candidates = random.sample(population, tournament_size)
            candidates = [c for c in candidates if c.is_valid]
            if not candidates:
                return random.choice(population)
            return max(candidates, key=lambda x: x.fitness)
        
        return tournament(), tournament()

    def _calculate_overfitting(self, individual: FactorIndividual) -> float:
        train_fitness, _, _, _ = self._evaluate_fitness(individual, is_train=True)
        test_fitness, _, _, _ = self._evaluate_fitness(individual, is_train=False)
        
        if train_fitness <= 0:
            return 1.0
        
        overfitting = max(0, (train_fitness - test_fitness) / train_fitness)
        return overfitting

    def mine_factors(self, verbose: bool = True) -> List[FactorIndividual]:
        if verbose:
            print("=" * 70)
            print("遗传编程因子挖掘开始")
            print(f"种群大小: {self.population_size}, 最大迭代: {self.max_generations}")
            print(f"基础因子: {self.base_factors}")
            print("=" * 70)
        
        population = self._init_population()
        
        for generation in range(self.max_generations):
            if verbose:
                print(f"\n第 {generation + 1}/{self.max_generations} 代")
            
            for individual in population:
                if not individual.is_valid or individual.fitness == 0:
                    fitness, ic_mean, ic_ir, is_valid = self._evaluate_fitness(individual)
                    individual.fitness = fitness
                    individual.ic_mean = ic_mean
                    individual.ic_ir = ic_ir
                    individual.is_valid = is_valid
            
            valid_individuals = [ind for ind in population if ind.is_valid and ind.fitness > 0]
            
            if not valid_individuals:
                if verbose:
                    print("  没有有效个体，重新初始化...")
                population = self._init_population()
                continue
            
            valid_individuals.sort(key=lambda x: x.fitness, reverse=True)
            
            best = valid_individuals[0]
            if verbose:
                print(f"  最佳适应度: {best.fitness:.4f}, IC Mean: {best.ic_mean:.4f}, IC IR: {best.ic_ir:.4f}")
                print(f"  最佳表达式: {best.expression}")
            
            new_population = valid_individuals[:int(self.population_size * 0.2)]
            
            while len(new_population) < self.population_size:
                parent1, parent2 = self._select_parents(valid_individuals)
                
                if random.random() < self.crossover_rate:
                    child = self._crossover(parent1, parent2)
                else:
                    child = copy.deepcopy(random.choice(valid_individuals))
                
                if random.random() < self.mutation_rate:
                    child = self._mutate(child)
                
                new_population.append(child)
            
            population = new_population
        
        if verbose:
            print("\n计算过拟合风险...")
        
        final_valid = [ind for ind in population if ind.is_valid]
        for ind in final_valid:
            ind.overfitting_score = self._calculate_overfitting(ind)
        
        final_valid.sort(key=lambda x: x.fitness * (1 - x.overfitting_score), reverse=True)
        
        self.best_factors = final_valid[:10]
        
        if verbose:
            print("\n" + "=" * 70)
            print("挖掘完成! 最佳因子:")
            print("=" * 70)
            for i, factor in enumerate(self.best_factors[:5]):
                print(f"\n{i+1}. 适应度: {factor.fitness:.4f}")
                print(f"   IC Mean: {factor.ic_mean:.4f}")
                print(f"   IC IR: {factor.ic_ir:.4f}")
                print(f"   过拟合分数: {factor.overfitting_score:.4f}")
                print(f"   表达式: {factor.expression}")
        
        return self.best_factors

    def get_top_factors(self, n: int = 5, 
                        max_overfitting: float = 0.5) -> List[FactorIndividual]:
        filtered = [f for f in self.best_factors 
                   if f.overfitting_score <= max_overfitting]
        return filtered[:n]


if __name__ == '__main__':
    from data_loader import DataLoader
    
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=50, start_date='2021-01-01', end_date='2023-12-31')
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    
    from backtest import BacktestEngine
    bt = BacktestEngine(returns, suspend, delist, industry, factors.get('MKT_CAP'))
    rebalance_dates = bt.get_rebalance_dates(freq='M')
    
    miner = GeneticFactorMiner(
        factors, returns, rebalance_dates,
        base_factors=['PE', 'PB', 'ROE'],
        population_size=30,
        max_generations=5
    )
    
    best_factors = miner.mine_factors()
    print("\n挖掘完成!")
