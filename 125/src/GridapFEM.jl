module GridapFEM

using Gridap
using Gridap.FESpaces
using Gridap.Geometry
using Gridap.CellData
using ForwardDiff
using LinearAlgebra
using SparseArrays
using StaticArrays
using BenchmarkTools

# 导出公共API
export
    # 材料模型
    MaterialModel,
    LinearElastic,
    NeoHookean,
    SaintVenantKirchhoff,
    VonMisesPlasticity,
    RambergOsgood,

    # 本构关系
    compute_stress,
    compute_tangent,

    # 求解器
    NonlinearSolver,
    NewtonRaphsonSolver,
    solve_nonlinear,

    # 问题定义
    FEMProblem,
    assemble_residual,
    assemble_jacobian,

    # 边界条件
    DirichletBC,
    NeumannBC,

    # 后处理
    compute_stress_field,
    compute_strain_energy,

    # 基准测试
    benchmark_assembly,
    run_benchmarks,

    # 辅助宏
    @material_model,
    @generate_material

include("materials.jl")
include("solvers.jl")
include("problems.jl")
include("benchmarks.jl")

end # module GridapFEM
