#!/usr/bin/env julia
"""
GridapFEM 基础使用示例

本示例展示:
1. 创建简单的有限元问题
2. 使用不同的材料模型
3. 运行 Newton-Raphson 非线性求解
4. 后处理和可视化
"""

using Gridap
using GridapGmsh
using Gridap.Visualization

# 引入我们的模块（假设在 src 目录下）
push!(LOAD_PATH, "../src")
using GridapFEM

println("="^60)
println("GridapFEM 基础使用示例")
println("="^60)

# -----------------------------------------------------------------------------
# 示例 1: 简单线弹性拉伸问题
# -----------------------------------------------------------------------------
println("\n示例 1: 简单线弹性拉伸")

# 定义网格
domain = (0.0, 1.0, 0.0, 1.0)
partition = (10, 10)
model = CartesianDiscreteModel(domain, partition)

# 定义有限元空间
order = 1
reffe = ReferenceFE(lagrangian, VectorValue{2,Float64}, order)
V = TestFESpace(model, reffe; conformity=:H1, dirichlet_tags="boundary")
U = TrialFESpace(V)

# 材料模型
material = LinearElastic(E=1.0e6, ν=0.3)

# 创建问题（简化版，使用Gridap内置功能）
println("  材料: 线弹性, E=$(material.E), ν=$(material.ν)")
println("  网格: $(partition[1])x$(partition[2]), 阶数: $order")
println("  自由度: $(num_free_dofs(V))")

# Gridap 内置的弹性求解
function solve_elasticity()
    # 变分形式
    μ = material.E / (2(1 + material.ν))
    λ = material.E * material.ν / ((1 + material.ν) * (1 - 2material.ν))
    
    ε(u) = 0.5 * (∇(u) + transpose(∇(u)))
    σ(ε) = λ * tr(ε) * I + 2μ * ε
    
    a(u, v) = ∫( ε(v) ⊙ σ(ε(u)) )dΩ
    l(v) = ∫(0.0)dΩ  # 零载荷，Dirichlet BC 驱动
    
    # 边界条件
    u0(x) = VectorValue(0.0, 0.0)
    
    # 求解
    op = AffineFEOperator(a, l, U, V)
    uh = solve(op)
    
    return uh
end

uh = solve_elasticity()

println("  求解完成!")
println("  最大位移: $(maximum(norm.(uh.free_values)))")

# 可视化
writevtk(get_triangulation(model), "elasticity_result", cellfields=["u" => uh])
println("  结果已写入: elasticity_result.vtu")

# -----------------------------------------------------------------------------
# 示例 2: 超弹性大变形
# -----------------------------------------------------------------------------
println("\n示例 2: 超弹性大变形 (Neo-Hookean)")

material_hyper = NeoHookean(E=1.0e6, ν=0.3)
println("  材料: Neo-Hookean 超弹性")

# 简单的非线性残差（使用 ForwardDiff）
function nonlinear_elasticity_demo()
    # 演示材料应力计算
    F = TensorValue{2,2}(1.1, 0.02, 0.01, 1.05)  # 变形梯度
    σ = compute_stress(material_hyper, F)
    
    println("  变形梯度: ", F)
    println("  Piola 应力: ", σ)
    
    # 切线刚度（自动微分）
    stress_fn(F) = compute_stress(material_hyper, F)
    dσdF = ForwardDiff.jacobian(stress_fn, F)
    println("  切线刚度计算完成 (使用 ForwardDiff)")
end

nonlinear_elasticity_demo()

# -----------------------------------------------------------------------------
# 示例 3: 弹塑性材料
# -----------------------------------------------------------------------------
println("\n示例 3: 弹塑性材料模型")

material_plastic = VonMisesPlasticity(E=2.0e5, ν=0.3, σ_y=200.0)
println("  材料: Von Mises 理想弹塑性")
println("  E=$(material_plastic.E), ν=$(material_plastic.ν), σ_y=$(material_plastic.σ_y)")

# 演示弹性预测和塑性修正
function plasticity_demo()
    # 小应变
    ε_elastic = TensorValue{2,2}(0.001, 0.0, 0.0, 0.0005)
    σ_el = compute_stress(material_plastic, ε_elastic)
    
    # 验证屈服状态
    dev_σ = σ_el - (1/2) * tr(σ_el) * I
    σ_vm = sqrt(1.5 * inner(dev_σ, dev_σ))
    
    println("  小应变 (弹性区):")
    println("    等效应力: $(σ_vm), 屈服应力: $(material_plastic.σ_y)")
    println("    状态: ", σ_vm < material_plastic.σ_y ? "弹性" : "塑性")
    
    # 大应变
    ε_plastic = TensorValue{2,2}(0.005, 0.0, 0.0, 0.0025)
    σ_pl = compute_stress(material_plastic, ε_plastic)
    
    dev_σ_pl = σ_pl - (1/2) * tr(σ_pl) * I
    σ_vm_pl = sqrt(1.5 * inner(dev_σ_pl, dev_σ_pl))
    
    println("  大应变 (塑性区):")
    println("    等效应力: $(σ_vm_pl), 屈服应力: $(material_plastic.σ_y)")
    println("    状态: ", σ_vm_pl < material_plastic.σ_y ? "弹性" : "塑性")
end

plasticity_demo()

# -----------------------------------------------------------------------------
# 示例 4: Newton-Raphson 求解器演示
# -----------------------------------------------------------------------------
println("\n示例 4: Newton-Raphson 求解器")

# 演示残差收敛历史
history = ConvergenceHistory()

# 模拟收敛过程（示例数据）
for iter in 0:5
    res = 10.0 * exp(-iter * 1.5)  # 指数收敛
    push!(history, iter, res, 1.0, 0.01 * (iter + 1))
end

println("  迭代收敛历史:")
for (i, res) in enumerate(history.residuals)
    @printf("    迭代 %d: ||R|| = %.2e\n", i-1, res)
end

println("  理论收敛率: 二次")

# -----------------------------------------------------------------------------
# 示例 5: 性能基准
# -----------------------------------------------------------------------------
println("\n示例 5: 简单性能基准")

using BenchmarkTools

# 材料应力计算基准
ε = TensorValue{2,2}(0.001, 0.0, 0.0, 0.0005)
bench = @benchmark compute_stress($material, $ε)
println("  线弹性应力计算:")
println("    中位数时间: $(median(bench.times) / 1e3) μs")
println("    内存分配: $(bench.allocs) 次")

bench_plastic = @benchmark compute_stress($material_plastic, $ε)
println("  弹塑性应力计算:")
println("    中位数时间: $(median(bench_plastic.times) / 1e3) μs")
println("    内存分配: $(bench_plastic.allocs) 次")

println("\n"^2 * "="^60)
println("所有示例运行完成!")
println("="^60)
println("\n下一步:")
println("  - 查看生成的 VTK 文件 (使用 ParaView)")
println("  - 修改 examples/plasticity.jl 了解更多功能")
println("  - 运行 benchmarks/performance.jl 进行完整性能测试")
