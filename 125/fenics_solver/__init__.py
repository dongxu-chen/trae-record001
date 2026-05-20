from .poisson import PoissonSolver, solve_poisson_simple
from .heat_equation import HeatEquationSolver, solve_heat_simple, solve_heat_adaptive
from .visualization import (
    plot_solution, animate_heat_equation, plot_solution_3d, 
    plot_gradient, plot_mesh, plot_comparison,
    plot_convergence_history, plot_timestep_history,
    plot_nonlinear_comparison, plot_material_property
)
from .boundary_conditions import BoundaryCondition, SmoothBoundary, SmoothBoundary2D, create_unit_square_boundary_markers
from .material_properties import ThermalMaterial, LayeredMaterial, GaussianInclusionMaterial, FunctionGradientMaterial, create_layered_conductivity, create_inclusion_material
from .mesh_adaptation import ErrorEstimator, MeshAdapter, adaptive_solve, PoissonProblem
from .nonlinear_materials import (
    ElasticMaterial, PerfectPlasticMaterial, HardeningPlasticMaterial,
    RambergOsgoodMaterial, ViscoPlasticMaterial, NonlinearThermalMaterial,
    TemperatureDependentConductivity, PhaseChangeMaterial
)
from .nonlinear_solvers import (
    ConvergenceHistory, NewtonRaphsonSolver,
    NonlinearPoissonSolver, NonlinearHeatSolver,
    ParallelUtils, create_parallel_mesh
)

__version__ = "0.3.0"
__all__ = [
    "PoissonSolver",
    "solve_poisson_simple",
    "HeatEquationSolver",
    "solve_heat_simple",
    "solve_heat_adaptive",
    "plot_solution",
    "animate_heat_equation",
    "plot_solution_3d",
    "plot_gradient",
    "plot_mesh",
    "plot_comparison",
    "plot_convergence_history",
    "plot_timestep_history",
    "plot_nonlinear_comparison",
    "plot_material_property",
    "BoundaryCondition",
    "SmoothBoundary",
    "SmoothBoundary2D",
    "create_unit_square_boundary_markers",
    "ThermalMaterial",
    "LayeredMaterial",
    "GaussianInclusionMaterial",
    "FunctionGradientMaterial",
    "create_layered_conductivity",
    "create_inclusion_material",
    "ErrorEstimator",
    "MeshAdapter",
    "adaptive_solve",
    "PoissonProblem",
    "ElasticMaterial",
    "PerfectPlasticMaterial",
    "HardeningPlasticMaterial",
    "RambergOsgoodMaterial",
    "ViscoPlasticMaterial",
    "NonlinearThermalMaterial",
    "TemperatureDependentConductivity",
    "PhaseChangeMaterial",
    "ConvergenceHistory",
    "NewtonRaphsonSolver",
    "NonlinearPoissonSolver",
    "NonlinearHeatSolver",
    "ParallelUtils",
    "create_parallel_mesh",
]
