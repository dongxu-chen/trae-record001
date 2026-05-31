import numpy as np
import pandas as pd
from deap import base, creator, tools, gp
from typing import List, Dict, Callable, Tuple
import operator
import random
from joblib import Parallel, delayed
from config import Config

class GPFactorMiner:
    def __init__(self, n_jobs: int = None):
        self.n_jobs = n_jobs or Config.N_JOBS
        self.pset = self._create_primitive_set()
        self.toolbox = self._create_toolbox()
        self.best_factors = []
        self.diversity_history = []
    
    def _create_primitive_set(self) -> gp.PrimitiveSet:
        pset = gp.PrimitiveSet("MAIN", 5)
        pset.renameArguments(ARG0='close')
        pset.renameArguments(ARG1='open')
        pset.renameArguments(ARG2='high')
        pset.renameArguments(ARG3='low')
        pset.renameArguments(ARG4='volume')
        
        pset.addPrimitive(operator.add, 2)
        pset.addPrimitive(operator.sub, 2)
        pset.addPrimitive(operator.mul, 2)
        pset.addPrimitive(self._protected_div, 2)
        pset.addPrimitive(self._protected_sqrt, 1)
        pset.addPrimitive(self._protected_log, 1)
        pset.addPrimitive(np.abs, 1)
        pset.addPrimitive(np.sign, 1)
        
        pset.addPrimitive(self._ts_mean, 1)
        pset.addPrimitive(self._ts_std, 1)
        pset.addPrimitive(self._ts_max, 1)
        pset.addPrimitive(self._ts_min, 1)
        pset.addPrimitive(self._ts_delay, 1)
        pset.addPrimitive(self._ts_delta, 1)
        pset.addPrimitive(self._ts_rank, 1)
        
        pset.addEphemeralConstant("rand101", lambda: random.uniform(-1, 1))
        
        return pset
    
    def _protected_div(self, x, y):
        return np.where(np.abs(y) > 1e-8, x / y, 0.0)
    
    def _protected_sqrt(self, x):
        return np.sqrt(np.abs(x))
    
    def _protected_log(self, x):
        return np.log(np.abs(x) + 1e-8)
    
    def _ts_mean(self, x):
        if isinstance(x, pd.Series):
            return x.rolling(5, min_periods=1).mean()
        return x
    
    def _ts_std(self, x):
        if isinstance(x, pd.Series):
            return x.rolling(5, min_periods=1).std()
        return x
    
    def _ts_max(self, x):
        if isinstance(x, pd.Series):
            return x.rolling(5, min_periods=1).max()
        return x
    
    def _ts_min(self, x):
        if isinstance(x, pd.Series):
            return x.rolling(5, min_periods=1).min()
        return x
    
    def _ts_delay(self, x):
        if isinstance(x, pd.Series):
            return x.shift(1)
        return x
    
    def _ts_delta(self, x):
        if isinstance(x, pd.Series):
            return x.diff(1)
        return x
    
    def _ts_rank(self, x):
        if isinstance(x, pd.Series):
            return x.rolling(10, min_periods=1).apply(
                lambda y: y.rank(pct=True).iloc[-1]
            )
        return x
    
    def _create_toolbox(self) -> base.Toolbox:
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMax)
        
        toolbox = base.Toolbox()
        toolbox.register("expr", gp.genHalfAndHalf, pset=self.pset, min_=1, max_=3)
        toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("compile", gp.compile, pset=self.pset)
        
        toolbox.register("select", tools.selTournament, tournsize=Config.GP_TOURNAMENT_SIZE)
        toolbox.register("mate", gp.cxOnePoint)
        toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
        toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=self.pset)
        
        toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=Config.GP_MAX_DEPTH))
        toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=Config.GP_MAX_DEPTH))
        
        return toolbox
    
    def _calculate_tree_similarity(self, ind1, ind2) -> float:
        str1 = str(ind1)
        str2 = str(ind2)
        
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        if len(set1.union(set2)) == 0:
            return 0.0
        
        jaccard = len(set1.intersection(set2)) / len(set1.union(set2))
        
        len1 = len(str1)
        len2 = len(str2)
        len_diff = abs(len1 - len2) / max(len1, len2)
        
        return jaccard * (1 - len_diff * 0.3)
    
    def _calculate_population_diversity(self, population) -> float:
        if len(population) < 2:
            return 1.0
        
        similarities = []
        for i in range(len(population)):
            for j in range(i + 1, len(population)):
                sim = self._calculate_tree_similarity(population[i], population[j])
                similarities.append(sim)
        
        if not similarities:
            return 1.0
        
        return 1.0 - np.mean(similarities)
    
    def _niching_selection(self, population, k: int, niche_radius: float = 0.3):
        selected = []
        candidates = population.copy()
        
        while len(selected) < k and candidates:
            best = max(candidates, key=lambda ind: ind.fitness.values[0])
            selected.append(best)
            candidates.remove(best)
            
            candidates = [ind for ind in candidates 
                         if self._calculate_tree_similarity(best, ind) < niche_radius]
        
        if len(selected) < k:
            remaining = k - len(selected)
            remaining_candidates = [ind for ind in population if ind not in selected]
            if remaining_candidates:
                sorted_candidates = sorted(remaining_candidates, 
                                         key=lambda ind: ind.fitness.values[0], 
                                         reverse=True)
                selected.extend(sorted_candidates[:remaining])
        
        return selected
    
    def _preserve_diversity(self, population, elite_ratio: float = 0.1, 
                           bad_ratio: float = 0.05, random_ratio: float = 0.05) -> List:
        n = len(population)
        n_elite = int(n * elite_ratio)
        n_bad = int(n * bad_ratio)
        n_random = int(n * random_ratio)
        
        sorted_pop = sorted(population, key=lambda ind: ind.fitness.values[0], reverse=True)
        
        elites = sorted_pop[:n_elite]
        
        bad_individuals = sorted_pop[-n_bad:] if n_bad > 0 else []
        
        candidates = [ind for ind in population if ind not in elites and ind not in bad_individuals]
        random_individuals = random.sample(candidates, min(n_random, len(candidates))) if candidates else []
        
        return elites + bad_individuals + random_individuals
    
    def _evaluate_factor(self, individual, data: pd.DataFrame, forward_returns: pd.Series) -> Tuple[float]:
        try:
            func = self.toolbox.compile(expr=individual)
            
            factor_values = []
            for asset in data['asset'].unique():
                asset_data = data[data['asset'] == asset].sort_values('date')
                vals = func(
                    asset_data['close'].values,
                    asset_data['open'].values,
                    asset_data['high'].values,
                    asset_data['low'].values,
                    asset_data['volume'].values
                )
                if isinstance(vals, (int, float)):
                    vals = np.full(len(asset_data), vals)
                for i, date in enumerate(asset_data['date']):
                    factor_values.append({
                        'date': date,
                        'asset': asset,
                        'factor': vals[i] if i < len(vals) else np.nan
                    })
            
            factor_df = pd.DataFrame(factor_values)
            factor_df = factor_df.sort_values(['date', 'asset'])
            factor_series = factor_df.set_index(['date', 'asset'])['factor']
            
            factor_series = factor_series.replace([np.inf, -np.inf], np.nan)
            factor_series = factor_series.groupby(level='date').rank(pct=True)
            
            aligned = pd.concat([factor_series, forward_returns], axis=1).dropna()
            if len(aligned) < 100:
                return (-1.0,)
            
            ic = aligned.groupby(level='date').apply(
                lambda x: x.iloc[:, 0].corr(x.iloc[:, 1])
            ).mean()
            
            if np.isnan(ic):
                return (-1.0,)
            
            return (abs(ic),)
            
        except Exception as e:
            return (-1.0,)
    
    def mine_factors(self, data: pd.DataFrame, forward_returns: pd.Series, 
                     population_size: int = None, generations: int = None,
                     use_niching: bool = True, preserve_bad: bool = True) -> List[Dict]:
        pop_size = population_size or Config.GP_POPULATION_SIZE
        n_gen = generations or Config.GP_GENERATIONS
        
        random.seed(Config.RANDOM_SEED)
        np.random.seed(Config.RANDOM_SEED)
        
        pop = self.toolbox.population(n=pop_size)
        hof = tools.HallOfFame(20)
        
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)
        
        self.toolbox.register("evaluate", self._evaluate_factor, data=data, forward_returns=forward_returns)
        
        logbook = tools.Logbook()
        logbook.header = ['gen', 'nevals', 'diversity'] + stats.fields
        
        self.diversity_history = []
        
        for gen in range(n_gen):
            diversity = self._calculate_population_diversity(pop)
            self.diversity_history.append(diversity)
            
            if use_niching:
                offspring = self._niching_selection(pop, len(pop))
            else:
                offspring = self.toolbox.select(pop, len(pop))
            
            offspring = list(map(self.toolbox.clone, offspring))
            
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < Config.GP_CROSSOVER_PROB:
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
            
            for mutant in offspring:
                if random.random() < Config.GP_MUTATION_PROB:
                    self.toolbox.mutate(mutant)
                    del mutant.fitness.values
            
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = Parallel(n_jobs=self.n_jobs)(
                delayed(self.toolbox.evaluate)(ind) for ind in invalid_ind
            )
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
            
            if preserve_bad:
                preserved = self._preserve_diversity(pop)
                offspring[-len(preserved):] = preserved
            
            pop[:] = offspring
            hof.update(pop)
            record = stats.compile(pop)
            logbook.record(gen=gen, nevals=len(invalid_ind), diversity=diversity, **record)
            print(f"Generation {gen}: Max Fitness = {record['max']:.4f}, Diversity = {diversity:.4f}")
        
        self.best_factors = []
        for i, ind in enumerate(hof):
            factor_expr = str(ind)
            fitness = ind.fitness.values[0]
            self.best_factors.append({
                'id': f'FACTOR_{i:03d}',
                'expression': factor_expr,
                'fitness': fitness,
                'individual': ind
            })
        
        return self.best_factors
    
    def calculate_factor_values(self, individual, data: pd.DataFrame) -> pd.Series:
        func = self.toolbox.compile(expr=individual)
        
        factor_values = []
        for asset in data['asset'].unique():
            asset_data = data[data['asset'] == asset].sort_values('date')
            vals = func(
                asset_data['close'].values,
                asset_data['open'].values,
                asset_data['high'].values,
                asset_data['low'].values,
                asset_data['volume'].values
            )
            if isinstance(vals, (int, float)):
                vals = np.full(len(asset_data), vals)
            for i, date in enumerate(asset_data['date']):
                factor_values.append({
                    'date': date,
                    'asset': asset,
                    'factor': vals[i] if i < len(vals) else np.nan
                })
        
        factor_df = pd.DataFrame(factor_values)
        factor_df = factor_df.sort_values(['date', 'asset'])
        factor_series = factor_df.set_index(['date', 'asset'])['factor']
        
        factor_series = factor_series.replace([np.inf, -np.inf], np.nan)
        factor_series = factor_series.groupby(level='date').rank(pct=True)
        
        return factor_series
