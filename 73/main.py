import random
import matplotlib.pyplot as plt

from population import Population
from allele import AllelePool
from drift import WrightFisherSimulation
from plotter import FrequencyPlotter

def demo_single_run():
    print("=== Demo 1: Single Run Simulation ===")
    
    pop = Population(size=100)
    allele_pool = AllelePool({'A': 0.5, 'a': 0.5})
    
    print(f"Population: {pop}")
    print(f"Initial Allele Pool: {allele_pool}")
    
    simulation = WrightFisherSimulation(pop, allele_pool, generations=100, runs=1)
    results = simulation.run()
    
    final_freq = results[0][-1]
    print(f"\nFinal frequencies after 100 generations:")
    for allele, freq in final_freq.items():
        print(f"  {allele}: {freq:.4f}")
    
    plotter = FrequencyPlotter(simulation)
    plotter.plot_single_run(run_index=0, show=False, auto_ylim=True)
    plt.savefig('demo_single_run.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("\nSaved: demo_single_run.png")

def demo_multiple_runs():
    print("\n=== Demo 2: Multiple Runs Simulation ===")
    
    pop = Population(size=100)
    allele_pool = AllelePool({'A': 0.5, 'a': 0.5})
    num_runs = 20
    
    print(f"Population: {pop}")
    print(f"Initial Allele Pool: {allele_pool}")
    print(f"Number of simulation runs: {num_runs}")
    
    simulation = WrightFisherSimulation(pop, allele_pool, generations=100, runs=num_runs,
                                         early_stop_on_fixation=True)
    simulation.run()
    
    fixation_prob = simulation.get_fixation_probability('A')
    loss_prob = simulation.get_loss_probability('A')
    
    fix_times = simulation.get_time_to_fixation('A')
    loss_times = simulation.get_time_to_loss('A')
    
    print(f"\nStatistics for allele 'A':")
    print(f"  Fixation probability: {fixation_prob:.4f}")
    print(f"  Loss probability: {loss_prob:.4f}")
    print(f"  Expected fixation probability (p0): 0.5000")
    
    fixed_runs = [t for t in fix_times if t is not None]
    lost_runs = [t for t in loss_times if t is not None]
    if fixed_runs:
        print(f"  Avg time to fixation: {sum(fixed_runs)/len(fixed_runs):.1f} generations")
    if lost_runs:
        print(f"  Avg time to loss: {sum(lost_runs)/len(lost_runs):.1f} generations")
    
    plotter = FrequencyPlotter(simulation)
    
    plotter.plot_all_runs(allele_name='A', show=False, alpha=0.4, auto_ylim=True)
    plt.savefig('demo_multiple_runs_A.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("\nSaved: demo_multiple_runs_A.png")
    
    plotter.plot_heterozygosity(show=False, alpha=0.3)
    plt.savefig('demo_heterozygosity.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: demo_heterozygosity.png")
    
    plotter.plot_statistics(show=False)
    plt.savefig('demo_statistics.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: demo_statistics.png")

def demo_variable_population_size():
    print("\n=== Demo 3: Variable Population Size ===")
    
    pop = Population(size=100, min_size=50, max_size=200, growth_rate=0.08)
    allele_pool = AllelePool({'A': 0.5, 'a': 0.5})
    num_runs = 10
    
    print(f"Initial Population: {pop}")
    print(f"Reproduction model: poisson")
    print(f"Number of simulation runs: {num_runs}")
    
    simulation = WrightFisherSimulation(pop, allele_pool, generations=80, runs=num_runs,
                                         reproduction_model='poisson')
    simulation.run()
    
    pop_history = simulation.get_population_size_history()
    avg_size = [sum(gen) / num_runs for gen in zip(*pop_history)]
    
    print(f"\nAverage population size:")
    print(f"  Initial: {avg_size[0]:.0f}")
    print(f"  Final: {avg_size[-1]:.0f}")
    print(f"  Range: {min(min(run) for run in pop_history)} - {max(max(run) for run in pop_history)}")
    
    fixation_prob = simulation.get_fixation_probability('A')
    loss_prob = simulation.get_loss_probability('A')
    print(f"\nFixation prob: {fixation_prob:.4f}, Loss prob: {loss_prob:.4f}")
    
    plotter = FrequencyPlotter(simulation)
    plotter.plot_population_size(show=False, alpha=0.4)
    plt.savefig('demo_population_size.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("\nSaved: demo_population_size.png")

def demo_mutation():
    print("\n=== Demo 4: Mutation Simulation ===")
    
    pop = Population(size=150)
    allele_pool = AllelePool({'A': 0.5, 'a': 0.5})
    num_runs = 10
    mutation_rate = 0.01
    
    print(f"Population: {pop}")
    print(f"Initial Allele Pool: {allele_pool}")
    print(f"Mutation rate: {mutation_rate}")
    print(f"Mutation model: reciprocal")
    print(f"Number of simulation runs: {num_runs}")
    
    simulation = WrightFisherSimulation(pop, allele_pool, generations=150, runs=num_runs,
                                         mutation_rate=mutation_rate,
                                         mutation_model='reciprocal')
    simulation.run()
    
    het_history = simulation.get_heterozygosity_history()
    avg_het = [sum(gen) / num_runs for gen in zip(*het_history)]
    
    print(f"\nAverage heterozygosity:")
    print(f"  Initial: {avg_het[0]:.4f}")
    print(f"  Final: {avg_het[-1]:.4f}")
    
    fixation_prob = simulation.get_fixation_probability('A')
    loss_prob = simulation.get_loss_probability('A')
    print(f"\nWith mutation (μ={mutation_rate}):")
    print(f"  Fixation prob: {fixation_prob:.4f}, Loss prob: {loss_prob:.4f}")
    
    plotter = FrequencyPlotter(simulation)
    plotter.plot_all_runs(allele_name='A', show=False, alpha=0.3, auto_ylim=True)
    plt.savefig('demo_mutation_A.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("\nSaved: demo_mutation_A.png")
    
    plotter.plot_heterozygosity(show=False, alpha=0.3, auto_ylim=True)
    plt.savefig('demo_mutation_het.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: demo_mutation_het.png")

def demo_logistic_growth():
    print("\n=== Demo 5: Logistic Growth Model ===")
    
    K = 500
    pop = Population(size=50, min_size=10, max_size=K, growth_rate=0.15, carry_capacity=K)
    allele_pool = AllelePool({'A': 0.6, 'a': 0.4})
    num_runs = 8
    
    print(f"Initial Population: {pop}")
    print(f"Carrying capacity (K): {K}")
    print(f"Reproduction model: logistic")
    print(f"Number of simulation runs: {num_runs}")
    
    simulation = WrightFisherSimulation(pop, allele_pool, generations=100, runs=num_runs,
                                         reproduction_model='logistic')
    simulation.run()
    
    pop_history = simulation.get_population_size_history()
    avg_size = [sum(gen) / num_runs for gen in zip(*pop_history)]
    
    print(f"\nPopulation dynamics:")
    print(f"  Initial size: {avg_size[0]:.0f}")
    print(f"  Final size: {avg_size[-1]:.0f}")
    print(f"  Carrying capacity: {K}")
    
    fixation_prob = simulation.get_fixation_probability('A')
    loss_prob = simulation.get_loss_probability('A')
    print(f"\nFixation prob (A, p0=0.6): {fixation_prob:.4f}")
    print(f"Loss prob (A): {loss_prob:.4f}")
    
    plotter = FrequencyPlotter(simulation)
    plotter.plot_population_size(show=False, alpha=0.4)
    plt.savefig('demo_logistic_growth.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("\nSaved: demo_logistic_growth.png")
    
    plotter.plot_all_alleles(show=False, alpha=0.25, auto_ylim=True)
    plt.savefig('demo_logistic_alleles.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: demo_logistic_alleles.png")

def main():
    random.seed(42)
    
    print("=" * 65)
    print("Genetic Drift Simulator (Wright-Fisher Model) - Enhanced")
    print("=" * 65)
    
    demo_single_run()
    demo_multiple_runs()
    demo_variable_population_size()
    demo_mutation()
    demo_logistic_growth()
    
    print("\n" + "=" * 65)
    print("All enhanced demos completed!")
    print("=" * 65)

if __name__ == "__main__":
    main()
