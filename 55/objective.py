import numpy as np


def sphere(x):
    return np.sum(x ** 2)


def rosenbrock(x):
    return np.sum(100.0 * (x[1:] - x[:-1] ** 2) ** 2 + (1 - x[:-1]) ** 2)


def rastrigin(x):
    n = len(x)
    return 10 * n + np.sum(x ** 2 - 10 * np.cos(2 * np.pi * x))


def ackley(x):
    n = len(x)
    sum1 = np.sum(x ** 2)
    sum2 = np.sum(np.cos(2 * np.pi * x))
    return -20 * np.exp(-0.2 * np.sqrt(sum1 / n)) - np.exp(sum2 / n) + 20 + np.e


def griewank(x):
    n = len(x)
    sum_part = np.sum(x ** 2) / 4000
    prod_part = np.prod(np.cos(x / np.sqrt(np.arange(1, n + 1))))
    return sum_part - prod_part + 1


def schwefel(x):
    n = len(x)
    return 418.9829 * n - np.sum(x * np.sin(np.sqrt(np.abs(x))))


def booth(x):
    return (x[0] + 2 * x[1] - 7) ** 2 + (2 * x[0] + x[1] - 5) ** 2


def matyas(x):
    return 0.26 * (x[0] ** 2 + x[1] ** 2) - 0.48 * x[0] * x[1]


def beale(x):
    return (1.5 - x[0] + x[0] * x[1]) ** 2 + (2.25 - x[0] + x[0] * x[1] ** 2) ** 2 + (2.625 - x[0] + x[0] * x[1] ** 3) ** 2


def easom(x):
    return -np.cos(x[0]) * np.cos(x[1]) * np.exp(-((x[0] - np.pi) ** 2 + (x[1] - np.pi) ** 2))


def g01(x):
    f = 5 * np.sum(x[:4]) - 5 * np.sum(x[:4] ** 2) - np.sum(x[4:13])
    return f


def g01_ineq_constraints(x):
    constraints = []
    constraints.append(2 * x[0] + 2 * x[1] + x[9] + x[10] - 10)
    constraints.append(2 * x[0] + 2 * x[2] + x[9] + x[11] - 10)
    constraints.append(2 * x[1] + 2 * x[2] + x[10] + x[11] - 10)
    constraints.append(-8 * x[0] + x[9])
    constraints.append(-8 * x[1] + x[10])
    constraints.append(-8 * x[2] + x[11])
    constraints.append(-2 * x[3] - x[4] + x[9])
    constraints.append(-2 * x[5] - x[6] + x[10])
    constraints.append(-2 * x[7] - x[8] + x[11])
    return constraints


def g04(x):
    f = 5.3578547 * x[2] ** 2 + 0.8356891 * x[0] * x[4] + 37.293239 * x[0] - 40792.141
    return f


def g04_ineq_constraints(x):
    constraints = []
    constraints.append(85.334407 + 0.0056858 * x[1] * x[4] + 0.0006262 * x[0] * x[3] - 0.0022053 * x[2] * x[4] - 92)
    constraints.append(-85.334407 - 0.0056858 * x[1] * x[4] - 0.0006262 * x[0] * x[3] + 0.0022053 * x[2] * x[4])
    constraints.append(80.51249 + 0.0071317 * x[1] * x[4] + 0.0029955 * x[0] * x[1] + 0.0021813 * x[2] ** 2 - 110)
    constraints.append(-80.51249 - 0.0071317 * x[1] * x[4] - 0.0029955 * x[0] * x[1] - 0.0021813 * x[2] ** 2 + 90)
    constraints.append(9.300961 + 0.0047026 * x[2] * x[4] + 0.0012547 * x[0] * x[2] + 0.0019085 * x[2] * x[3] - 25)
    constraints.append(-9.300961 - 0.0047026 * x[2] * x[4] - 0.0012547 * x[0] * x[2] - 0.0019085 * x[2] * x[3] + 20)
    return constraints


def static_penalty(fitness, ineq_constraints=None, eq_constraints=None, penalty_factor=1e6, eq_tolerance=1e-6):
    penalty = 0.0

    if ineq_constraints is not None:
        for g in ineq_constraints:
            if g > 0:
                penalty += penalty_factor * g ** 2

    if eq_constraints is not None:
        for h in eq_constraints:
            if abs(h) > eq_tolerance:
                penalty += penalty_factor * (h ** 2)

    return fitness + penalty


def dynamic_penalty(fitness, iteration, ineq_constraints=None, eq_constraints=None, C=0.5, alpha=2, eq_tolerance=1e-6):
    penalty = 0.0
    t = iteration + 1

    if ineq_constraints is not None:
        for g in ineq_constraints:
            if g > 0:
                penalty += (C * t) ** alpha * (g ** 2)

    if eq_constraints is not None:
        for h in eq_constraints:
            if abs(h) > eq_tolerance:
                penalty += (C * t) ** alpha * (h ** 2)

    return fitness + penalty


def adaptive_penalty(fitness, best_fitness, current_fitness, ineq_constraints=None, eq_constraints=None,
                     penalty_factor=1e6, eq_tolerance=1e-6):
    if ineq_constraints is None and eq_constraints is None:
        return fitness

    constraint_violation = 0.0

    if ineq_constraints is not None:
        for g in ineq_constraints:
            if g > 0:
                constraint_violation += g ** 2

    if eq_constraints is not None:
        for h in eq_constraints:
            if abs(h) > eq_tolerance:
                constraint_violation += h ** 2

    if constraint_violation > 0:
        if current_fitness > best_fitness:
            penalty_factor *= 2.0
        else:
            penalty_factor /= 2.0
        penalty = penalty_factor * constraint_violation
    else:
        penalty = 0.0

    return fitness + penalty


def zdt1(x):
    n = len(x)
    f1 = x[0]
    g = 1 + 9 / (n - 1) * np.sum(x[1:])
    f2 = g * (1 - np.sqrt(x[0] / g))
    return np.array([f1, f2])


def zdt2(x):
    n = len(x)
    f1 = x[0]
    g = 1 + 9 / (n - 1) * np.sum(x[1:])
    f2 = g * (1 - (x[0] / g) ** 2)
    return np.array([f1, f2])


def zdt3(x):
    n = len(x)
    f1 = x[0]
    g = 1 + 9 / (n - 1) * np.sum(x[1:])
    f2 = g * (1 - np.sqrt(x[0] / g) - (x[0] / g) * np.sin(10 * np.pi * x[0]))
    return np.array([f1, f2])


def zdt4(x):
    n = len(x)
    f1 = x[0]
    g = 1 + 10 * (n - 1) + np.sum(x[1:] ** 2 - 10 * np.cos(4 * np.pi * x[1:]))
    f2 = g * (1 - np.sqrt(x[0] / g))
    return np.array([f1, f2])


def zdt6(x):
    n = len(x)
    f1 = 1 - np.exp(-4 * x[0]) * np.sin(6 * np.pi * x[0]) ** 6
    g = 1 + 9 * (np.sum(x[1:]) / (n - 1)) ** 0.25
    f2 = g * (1 - (f1 / g) ** 2)
    return np.array([f1, f2])


def dtlz1(x, n_obj=3):
    k = len(x) - n_obj + 1
    g = 100 * (k + np.sum((x[n_obj - 1:] - 0.5) ** 2 - np.cos(20 * np.pi * (x[n_obj - 1:] - 0.5))))
    f = np.zeros(n_obj)
    f[0] = 0.5 * np.prod(x[:n_obj - 1]) * (1 + g)
    for i in range(1, n_obj - 1):
        f[i] = 0.5 * np.prod(x[:n_obj - 1 - i]) * (1 - x[n_obj - 1 - i]) * (1 + g)
    f[-1] = 0.5 * (1 - x[0]) * (1 + g)
    return f


def dtlz2(x, n_obj=3):
    k = len(x) - n_obj + 1
    g = np.sum((x[n_obj - 1:] - 0.5) ** 2)
    f = np.zeros(n_obj)
    f[0] = np.prod(np.cos(x[:n_obj - 1] * np.pi / 2)) * (1 + g)
    for i in range(1, n_obj - 1):
        f[i] = np.prod(np.cos(x[:n_obj - 1 - i] * np.pi / 2)) * np.sin(x[n_obj - 1 - i] * np.pi / 2) * (1 + g)
    f[-1] = np.sin(x[0] * np.pi / 2) * (1 + g)
    return f


def dominates(f1, f2):
    n_obj = len(f1)
    better_in_at_least_one = False
    for i in range(n_obj):
        if f1[i] > f2[i]:
            return False
        if f1[i] < f2[i]:
            better_in_at_least_one = True
    return better_in_at_least_one


def get_pareto_front(objective_values):
    n = len(objective_values)
    is_pareto = np.ones(n, dtype=bool)

    for i in range(n):
        for j in range(n):
            if i != j and dominates(objective_values[j], objective_values[i]):
                is_pareto[i] = False
                break

    return np.where(is_pareto)[0]


def crowding_distance(objective_values):
    n = len(objective_values)
    n_obj = len(objective_values[0])
    distances = np.zeros(n)

    for obj in range(n_obj):
        sorted_idx = np.argsort([f[obj] for f in objective_values])
        distances[sorted_idx[0]] = np.inf
        distances[sorted_idx[-1]] = np.inf
        obj_range = objective_values[sorted_idx[-1]][obj] - objective_values[sorted_idx[0]][obj]
        if obj_range > 0:
            for i in range(1, n - 1):
                distances[sorted_idx[i]] += (objective_values[sorted_idx[i + 1]][obj] - objective_values[sorted_idx[i - 1]][obj]) / obj_range

    return distances


TEST_FUNCTIONS = {
    'sphere': {
        'function': sphere,
        'bounds': [(-5.12, 5.12)] * 2,
        'optimal': 0.0,
        'optimal_x': np.zeros(2)
    },
    'rosenbrock': {
        'function': rosenbrock,
        'bounds': [(-2.048, 2.048)] * 2,
        'optimal': 0.0,
        'optimal_x': np.ones(2)
    },
    'rastrigin': {
        'function': rastrigin,
        'bounds': [(-5.12, 5.12)] * 2,
        'optimal': 0.0,
        'optimal_x': np.zeros(2)
    },
    'ackley': {
        'function': ackley,
        'bounds': [(-32.768, 32.768)] * 2,
        'optimal': 0.0,
        'optimal_x': np.zeros(2)
    },
    'griewank': {
        'function': griewank,
        'bounds': [(-600, 600)] * 2,
        'optimal': 0.0,
        'optimal_x': np.zeros(2)
    },
    'schwefel': {
        'function': schwefel,
        'bounds': [(-500, 500)] * 2,
        'optimal': 0.0,
        'optimal_x': np.ones(2) * 420.9687
    },
    'booth': {
        'function': booth,
        'bounds': [(-10, 10)] * 2,
        'optimal': 0.0,
        'optimal_x': np.array([1.0, 3.0])
    },
    'matyas': {
        'function': matyas,
        'bounds': [(-10, 10)] * 2,
        'optimal': 0.0,
        'optimal_x': np.zeros(2)
    },
    'beale': {
        'function': beale,
        'bounds': [(-4.5, 4.5)] * 2,
        'optimal': 0.0,
        'optimal_x': np.array([3.0, 0.5])
    },
    'easom': {
        'function': easom,
        'bounds': [(-100, 100)] * 2,
        'optimal': -1.0,
        'optimal_x': np.array([np.pi, np.pi])
    }
}

CONSTRAINED_FUNCTIONS = {
    'g01': {
        'function': g01,
        'ineq_constraints': g01_ineq_constraints,
        'eq_constraints': None,
        'bounds': [(0, 1)] * 9 + [(0, 100)] * 3 + [(0, 1)],
        'dim': 13,
        'optimal': -15.0,
        'optimal_x': np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 1.0])
    },
    'g04': {
        'function': g04,
        'ineq_constraints': g04_ineq_constraints,
        'eq_constraints': None,
        'bounds': [(78, 102), (33, 45), (27, 45), (27, 45), (27, 45)],
        'dim': 5,
        'optimal': -30665.53867178332,
        'optimal_x': np.array([78.0, 33.0, 29.9952560256815, 45.0, 36.7758129057882])
    }
}

MULTI_OBJECTIVE_FUNCTIONS = {
    'zdt1': {
        'function': zdt1,
        'n_obj': 2,
        'bounds': [(0, 1)] * 30,
        'dim': 30
    },
    'zdt2': {
        'function': zdt2,
        'n_obj': 2,
        'bounds': [(0, 1)] * 30,
        'dim': 30
    },
    'zdt3': {
        'function': zdt3,
        'n_obj': 2,
        'bounds': [(0, 1)] * 30,
        'dim': 30
    },
    'zdt4': {
        'function': zdt4,
        'n_obj': 2,
        'bounds': [(0, 1)] + [(-5, 5)] * 9,
        'dim': 10
    },
    'zdt6': {
        'function': zdt6,
        'n_obj': 2,
        'bounds': [(0, 1)] * 10,
        'dim': 10
    },
    'dtlz1': {
        'function': dtlz1,
        'n_obj': 3,
        'bounds': [(0, 1)] * 12,
        'dim': 12
    },
    'dtlz2': {
        'function': dtlz2,
        'n_obj': 3,
        'bounds': [(0, 1)] * 12,
        'dim': 12
    }
}
