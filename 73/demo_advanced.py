import random
import matplotlib.pyplot as plt

from population import Population, MetaPopulation
from allele import AllelePool
from selection import Fitness, SelectionModel
from drift import WrightFisherSimulation, MetaPopulationSimulation
from plotter import FrequencyPlotter, MetaPopulationPlotter
from parallel_replicates import ParallelReplicates

def demo_natural_selection():
    print("\n" + "=" * 60)
    print("Demo 1: Natural Selection")
    print("=" * 60)
    
    pop = Population(size=200)
    pool = AllelePool({'A': 0.2, 'a': 0.8})
    
    fitness = Fitness({'A': 1.0, 'a': 0.7})
    selection = SelectionModel(fitness=fitness)
    
    print(f"Initial: A={0.2}, a={0.8}")
    print(f"Fitness: A=1.0, a=0.7")
    print(f"Selection coefficient for 'a': {fitness.get_selection_coefficient('a'):.4f}")
    
    sim = WrightFisherSimulation(
        pop, pool, generations=100, runs=5,
        selection_model=selection
    )
    sim.run()
    
    final_avg_A = sim.get_average_frequency('A')[-1]
    final_avg_a = sim.get_average_frequency('a')[-1]
    
    print(f"Final average: A={final_avg_A:.4f}, a={final_avg_a:.4f}")
    
    plotter = FrequencyPlotter(sim)
    plotter.plot_all_alleles(save_path='demo_selection_alleles.png', show=False, auto_ylim=True)
    plt.close()
    print("\nSaved: demo_selection_alleles.png")

def demo_migration():
    print("\n" + "=" * 60)
    print("Demo 2: Population Migration (Meta-Population)")
    print("=" * 60)
    
    pop1 = Population(size=100, population_id=0)
    pop2 = Population(size=150, population_id=1)
    pop3 = Population(size=80, population_id=2)
    
    migration_matrix = [
        [0.9, 0.05, 0.05],
        [0.05, 0.9, 0.05],
        [0.05, 0.05, 0.9]
    ]
    
    meta_pop = MetaPopulation([pop1, pop2, pop3], migration_matrix)
    
    pools = [
        AllelePool({'A': 0.9, 'a': 0.1}),
        AllelePool({'A': 0.5, 'a': 0.5}),
        AllelePool({'A': 0.1, 'a': 0.9})
    ]
    
    print(f"Number of populations: {meta_pop.num_populations}")
    print(f"Initial frequencies:")
    print(f"  Pop1: A=0.9, a=0.1")
    print(f"  Pop2: A=0.5, a=0.5")
    print(f"  Pop3: A=0.1, a=0.9")
    print(f"Migration rate between populations: 5%")
    
    sim = MetaPopulationSimulation(
        meta_pop, pools, generations=80, runs=3,
        migration_enabled=True
    )
    sim.run()
    
    plotter = MetaPopulationPlotter(sim)
    plotter.plot_all_populations('A', save_path='demo_migration_all_pops.png', show=False)
    plt.close()
    print("\nSaved: demo_migration_all_pops.png")
    
    plotter.plot_fst(save_path='demo_migration_fst.png', show=False, alpha=0.5)
    plt.close()
    print("Saved: demo_migration_fst.png")

def demo_selection_vs_drift():
    print("\n" + "=" * 60)
    print("Demo 3: Selection vs Genetic Drift")
    print("=" * 60)
    
    pop_small = Population(size=50)
    pop_large = Population(size=1000)
    pool = AllelePool({'A': 0.1, 'a': 0.9})
    
    fitness = Fitness({'A': 1.0, 'a': 0.9})
    selection = SelectionModel(fitness=fitness)
    
    print(f"Initial: A=0.1, a=0.9")
    print(f"Fitness: A=1.0, a=0.9 (s=0.1)")
    
    sim_small = WrightFisherSimulation(
        pop_small, pool, generations=100, runs=10,
        selection_model=selection
    )
    sim_small.run()
    
    sim_large = WrightFisherSimulation(
        pop_large, pool, generations=100, runs=10,
        selection_model=selection
    )
    sim_large.run()
    
    fix_small = sim_small.get_fixation_probability('A')
    fix_large = sim_large.get_fixation_probability('A')
    
    print(f"Small population (N=50):  Fixation prob = {fix_small:.4f}")
    print(f"Large population (N=1000): Fixation prob = {fix_large:.4f}")
    
    plotter_small = FrequencyPlotter(sim_small)
    plotter_small.plot_all_runs('A', save_path='demo_selection_small.png', show=False, alpha=0.4)
    plt.close()
    print("\nSaved: demo_selection_small.png")
    
    plotter_large = FrequencyPlotter(sim_large)
    plotter_large.plot_all_runs('A', save_path='demo_selection_large.png', show=False, alpha=0.4)
    plt.close()
    print("Saved: demo_selection_large.png")

def demo_parallel_replicates():
    print("\n" + "=" * 60)
    print("Demo 4: Parallel Replicates")
    print("=" * 60)
    
    pop = Population(size=100)
    pool = AllelePool({'A': 0.5, 'a': 0.5})
    
    num_replicates = 20
    num_workers = 2
    
    print(f"Number of replicates: {num_replicates}")
    print(f"Number of workers: {num_workers}")
    print(f"Initial: A=0.5, a=0.5")
    
    parallel = ParallelReplicates(
        num_replicates=num_replicates,
        num_workers=num_workers,
        use_processes=False
    )
    
    results = parallel.run_single_population(
        pop, pool, generations=80,
        base_seed=42
    )
    
    summary = parallel.get_summary_statistics('A')
    
    print(f"\nSummary Statistics for allele 'A':")
    print(f"  Initial frequency: {summary['initial_frequency']:.4f}")
    print(f"  Final mean: {summary['final_frequency_mean']:.4f}")
    print(f"  Final variance: {summary['final_frequency_variance']:.4f}")
    print(f"  Fixation probability: {summary['fixation_probability']:.4f}")
    print(f"  Loss probability: {summary['loss_probability']:.4f}")

def demo_hybrid_model():
    print("\n" + "=" * 60)
    print("Demo 5: Hybrid Model (Selection + Migration + Mutation)")
    print("=" * 60)
    
    pop1 = Population(size=100, population_id=0)
    pop2 = Population(size=100, population_id=1)
    
    migration_matrix = [
        [0.95, 0.05],
        [0.05, 0.95]
    ]
    
    meta_pop = MetaPopulation([pop1, pop2], migration_matrix)
    
    pools = [
        AllelePool({'A': 0.9, 'a': 0.1}),
        AllelePool({'A': 0.1, 'a': 0.9})
    ]
    
    fitness1 = Fitness({'A': 1.0, 'a': 0.8})
    fitness2 = Fitness({'A': 0.8, 'a': 1.0})
    selection1 = SelectionModel(fitness=fitness1)
    selection2 = SelectionModel(fitness=fitness2)
    
    print(f"Populations: 2 (N=100 each)")
    print(f"Migration: 5% between populations")
    print(f"Mutation rate: 0.001")
    print(f"Pop1 fitness: A=1.0, a=0.8 (A favored)")
    print(f"Pop2 fitness: A=0.8, a=1.0 (a favored)")
    
    sim = MetaPopulationSimulation(
        meta_pop, pools, generations=100, runs=5,
        mutation_rate=0.001,
        mutation_model='reciprocal',
        selection_models=[selection1, selection2],
        migration_enabled=True
    )
    sim.run()
    
    plotter = MetaPopulationPlotter(sim)
    plotter.plot_all_populations('A', save_path='demo_hybrid_A.png', show=False)
    plt.close()
    print("\nSaved: demo_hybrid_A.png")
    
    plotter.plot_fst(save_path='demo_hybrid_fst.png', show=False)
    plt.close()
    print("Saved: demo_hybrid_fst.png")

def main():
    random.seed(42)
    
    print("=" * 60)
    print("Advanced Features Demo")
    print("=" * 60)
    
    demo_natural_selection()
    demo_migration()
    demo_selection_vs_drift()
    demo_parallel_replicates()
    demo_hybrid_model()
    
    print("\n" + "=" * 60)
    print("All advanced demos completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
