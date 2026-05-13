import random
from population import Population
from allele import Allele, AllelePool
from drift import WrightFisherSimulation

def test_population():
    print("Testing Population class...")
    pop = Population(size=100)
    assert pop.size == 100
    pop.size = 200
    assert pop.size == 200
    try:
        pop.size = -1
        assert False, "Should raise ValueError"
    except ValueError:
        pass
    
    random.seed(42)
    pop2 = Population(size=100, min_size=50, max_size=200, growth_rate=0.1)
    assert pop2.min_size == 50
    assert pop2.max_size == 200
    assert pop2.growth_rate == 0.1
    
    size_constant = pop2.reproduce('constant')
    assert size_constant == pop2.size
    
    sizes_poisson = [pop2.reproduce('poisson') for _ in range(10)]
    assert all(50 <= s <= 200 for s in sizes_poisson)
    
    sizes_logistic = [pop2.reproduce('logistic') for _ in range(10)]
    assert all(50 <= s <= 200 for s in sizes_logistic)
    
    sizes_rw = [pop2.reproduce('random_walk') for _ in range(10)]
    assert all(50 <= s <= 200 for s in sizes_rw)
    
    print("  Population class: OK")

def test_allele():
    print("Testing Allele class...")
    allele = Allele('A', 0.5)
    assert allele.name == 'A'
    assert allele.frequency == 0.5
    try:
        Allele('B', 1.5)
        assert False, "Should raise ValueError"
    except ValueError:
        pass
    print("  Allele class: OK")

def test_allele_pool():
    print("Testing AllelePool class...")
    pool = AllelePool({'A': 0.5, 'a': 0.5})
    assert pool.get_frequency('A') == 0.5
    assert pool.get_frequency('a') == 0.5
    names = pool.get_allele_names()
    assert 'A' in names and 'a' in names
    
    try:
        AllelePool({'A': 0.5})
        assert False, "Should raise ValueError (frequencies don't sum to 1.0)"
    except ValueError:
        pass
    
    random.seed(42)
    sample = pool.sample_allele()
    assert sample in ['A', 'a']
    print("  AllelePool class: OK")

def test_simulation_basic():
    print("Testing WrightFisherSimulation (basic)...")
    random.seed(42)
    
    pop = Population(size=50)
    pool = AllelePool({'A': 0.5, 'a': 0.5})
    
    sim = WrightFisherSimulation(pop, pool, generations=10, runs=3)
    results = sim.run()
    
    assert len(results) == 3
    assert len(results[0]) == 11
    
    for run in results:
        first_gen = run[0]
        last_gen = run[-1]
        assert abs(sum(first_gen.values()) - 1.0) < 0.001
        assert abs(sum(last_gen.values()) - 1.0) < 0.001
    
    history = sim.get_allele_frequency_history('A')
    assert len(history) == 3
    assert len(history[0]) == 11
    
    avg = sim.get_average_frequency('A')
    assert len(avg) == 11
    
    print("  WrightFisherSimulation (basic): OK")

def test_simulation_mutation():
    print("Testing WrightFisherSimulation (with mutation)...")
    random.seed(42)
    
    pop = Population(size=100)
    pool = AllelePool({'A': 0.5, 'a': 0.5})
    
    sim = WrightFisherSimulation(pop, pool, generations=50, runs=5, 
                                 mutation_rate=0.01, mutation_model='reciprocal')
    results = sim.run()
    
    assert len(results) == 5
    
    het_history = sim.get_heterozygosity_history()
    assert len(het_history) == 5
    assert len(het_history[0]) == 51
    
    for run_het in het_history:
        assert all(0 <= h <= 1 for h in run_het)
    
    print("  WrightFisherSimulation (mutation): OK")

def test_simulation_variable_size():
    print("Testing WrightFisherSimulation (variable size)...")
    random.seed(42)
    
    pop = Population(size=100, min_size=50, max_size=200, growth_rate=0.05)
    pool = AllelePool({'A': 0.5, 'a': 0.5})
    
    sim = WrightFisherSimulation(pop, pool, generations=30, runs=5, 
                                 reproduction_model='poisson')
    results = sim.run()
    
    pop_history = sim.get_population_size_history()
    assert len(pop_history) == 5
    assert len(pop_history[0]) == 31
    
    for run_sizes in pop_history:
        assert all(50 <= s <= 200 for s in run_sizes)
    
    print("  WrightFisherSimulation (variable size): OK")

def test_simulation_early_stop():
    print("Testing WrightFisherSimulation (early stop on fixation)...")
    random.seed(42)
    
    pop = Population(size=20)
    pool = AllelePool({'A': 0.9, 'a': 0.1})
    
    sim = WrightFisherSimulation(pop, pool, generations=200, runs=10,
                                 early_stop_on_fixation=True)
    results = sim.run()
    
    fix_times = sim.get_time_to_fixation('A')
    loss_times = sim.get_time_to_loss('A')
    
    assert len(fix_times) == 10
    assert len(loss_times) == 10
    
    print(f"  Fixation times: {[t for t in fix_times if t is not None]}")
    print(f"  Loss times: {[t for t in loss_times if t is not None]}")
    
    print("  WrightFisherSimulation (early stop): OK")

def test_statistics():
    print("Testing simulation statistics...")
    random.seed(42)
    
    pop = Population(size=100)
    pool = AllelePool({'A': 0.5, 'a': 0.5})
    
    sim = WrightFisherSimulation(pop, pool, generations=200, runs=50)
    sim.run()
    
    fix_prob = sim.get_fixation_probability('A')
    loss_prob = sim.get_loss_probability('A')
    
    print(f"  Fixation probability of 'A': {fix_prob:.4f}")
    print(f"  Loss probability of 'A': {loss_prob:.4f}")
    print(f"  Expected: ~0.5000")
    
    print("  Statistics calculation: OK")

def main():
    print("=" * 60)
    print("Core Module Tests (Updated)")
    print("=" * 60)
    
    test_population()
    test_allele()
    test_allele_pool()
    test_simulation_basic()
    test_simulation_mutation()
    test_simulation_variable_size()
    test_simulation_early_stop()
    test_statistics()
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
