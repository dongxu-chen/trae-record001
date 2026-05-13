from .kernel import Kernel, RBF, Linear, WhiteKernel, SumKernel
from .gp import GaussianProcess, SparseFITCGaussianProcess
from .optimize import optimize_marginal_likelihood, optimize_fitc_marginal_likelihood
from .predict import predict, predict_with_variance, predict_with_covariance, sample_y
from .sparse import (
    select_inducing_points,
    initialize_inducing_points,
    random_inducing_points,
    uniform_grid_inducing_points,
    kmeans_inducing_points,
    greedy_variance_inducing_points
)

__all__ = [
    'Kernel',
    'RBF',
    'Linear',
    'WhiteKernel',
    'SumKernel',
    'GaussianProcess',
    'SparseFITCGaussianProcess',
    'optimize_marginal_likelihood',
    'optimize_fitc_marginal_likelihood',
    'predict',
    'predict_with_variance',
    'predict_with_covariance',
    'sample_y',
    'select_inducing_points',
    'initialize_inducing_points',
    'random_inducing_points',
    'uniform_grid_inducing_points',
    'kmeans_inducing_points',
    'greedy_variance_inducing_points',
]
