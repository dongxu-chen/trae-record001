import multiprocessing

class Config:
    RANDOM_SEED = 42
    N_JOBS = multiprocessing.cpu_count()
    
    GP_POPULATION_SIZE = 100
    GP_GENERATIONS = 20
    GP_TOURNAMENT_SIZE = 3
    GP_CROSSOVER_PROB = 0.7
    GP_MUTATION_PROB = 0.2
    GP_MAX_DEPTH = 5
    
    FACTOR_LOOKBACK_PERIODS = [1, 5, 10, 20]
    FACTOR_FORWARD_PERIODS = [1, 5, 10]
    
    IC_THRESHOLD = 0.03
    IR_THRESHOLD = 0.5
    
    MAX_CORRELATION = 0.7
