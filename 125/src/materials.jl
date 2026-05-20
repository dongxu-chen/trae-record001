"""
材料模型系统 - 基于Julia多分派和自动微分

设计理念：
1. 每种材料是一个struct
2. compute_stress和compute_tangent通过多分派实现
3. ForwardDiff自动推导切线刚度，无需手动编写雅可比
"""

# 材料模型抽象类型
abstract type MaterialModel end

# 弹性材料抽象类型
abstract type ElasticModel <: MaterialModel end
abstract type HyperElasticModel <: ElasticModel end

# 塑性材料抽象类型
abstract type PlasticModel <: MaterialModel end

# ============================================================================
# 元编程宏：自动生成材料模型的构造函数和访问器
# ============================================================================

"""
    @material_model Name begin
        param1::Type1 = default1
        param2::Type2 = default2
    end

元编程宏：自动生成材料模型struct和关键字参数构造函数
"""
macro material_model(name, fields_block)
    # 解析字段定义
    fields = []
    kw_params = []
    
    for expr in fields_block.args
        if Meta.isexpr(expr, :(=))
            field_def = expr.args[1]
            default_val = expr.args[2]
            if Meta.isexpr(field_def, :(::))
                field_name = field_def.args[1]
                field_type = field_def.args[2]
                push!(fields, :($field_name::$field_type))
                push!(kw_params, Expr(:kw, field_name, default_val))
            end
        elseif Meta.isexpr(expr, :(::))
            field_name = expr.args[1]
            field_type = expr.args[2]
            push!(fields, :($field_name::$field_type))
            push!(kw_params, field_name)
        end
    end
    
    # 生成struct定义
    struct_def = quote
        struct $(name){T<:Real} <: HyperElasticModel
            $(fields...)
        end
    end
    
    # 生成关键字参数构造函数
    constructor_def = quote
        function $(name)(; $(kw_params...))
            $(name)($([Meta.isexpr(p, :kw) ? p.args[1] : p for p in kw_params]...))
        end
    end
    
    # 生成自动微分切线刚度方法
    ad_tangent_def = quote
        function compute_tangent(material::$(name), F::TensorValue{2,2,T}) where T
            stress_fn(ϵ) = compute_stress(material, ϵ)
            ForwardDiff.jacobian(stress_fn, F)
        end
    end
    
    esc(quote
        $struct_def
        $constructor_def
        $ad_tangent_def
    end)
end

"""
    @generate_material Name stress_expr

从应力表达式自动生成完整的材料模型

示例:
    @generate_material MyElastic begin
        σ = λ*tr(ε)*I + 2μ*ε
    end
"""
macro generate_material(name, stress_block)
    stress_fn = gensym(:stress_fn)
    
    quote
        struct $(name){T} <: HyperElasticModel
            λ::T
            μ::T
        end
        
        function $(name)(E::Real, ν::Real)
            λ = E * ν / ((1 + ν) * (1 - 2ν))
            μ = E / (2(1 + ν))
            $(name){promote_type(typeof(λ), typeof(μ))}(λ, μ)
        end
        
        function compute_stress(material::$(name), ε)
            let λ = material.λ, μ = material.μ
                $stress_block
            end
        end
    end |> esc
end

# ============================================================================
# 线弹性材料
# ============================================================================

struct LinearElastic{T<:Real} <: ElasticModel
    E::T      # 杨氏模量
    ν::T      # 泊松比
    λ::T      # Lamé第一参数
    μ::T      # Lamé第二参数 (剪切模量)
end

function LinearElastic(; E::T, ν::T) where T<:Real
    λ = E * ν / ((1 + ν) * (1 - 2ν))
    μ = E / (2(1 + ν))
    LinearElastic{T}(E, ν, λ, μ)
end

@doc """
线弹性材料模型

参数:
- E: 杨氏模量
- ν: 泊松比
""" LinearElastic

function compute_stress(material::LinearElastic, ε::TensorValue{2,2,T}) where T
    λ, μ = material.λ, material.μ
    I = one(ε)
    return λ * tr(ε) * I + 2μ * ε
end

function compute_tangent(material::LinearElastic, ::TensorValue{2,2,T}) where T
    λ, μ = material.λ, material.μ
    
    # 4阶弹性张量 D_ijkl = λ*δ_ij*δ_kl + μ*(δ_ik*δ_jl + δ_il*δ_jk)
    function tangent(ε)
        I = one(ε)
        return λ ⊗ I + μ * (I ⊗ I + permutedims(I ⊗ I, (1,3,2,4)))
    end
    
    return tangent
end

# ============================================================================
# Saint Venant-Kirchhoff 超弹性材料
# ============================================================================

@material_model SaintVenantKirchhoff begin
    λ::Float64 = 100.0
    μ::Float64 = 40.0
end

function SaintVenantKirchhoff(E::Real, ν::Real)
    λ = E * ν / ((1 + ν) * (1 - 2ν))
    μ = E / (2(1 + ν))
    SaintVenantKirchhoff(λ=λ, μ=μ)
end

function compute_stress(material::SaintVenantKirchhoff, F::TensorValue{2,2,T}) where T
    λ, μ = material.λ, material.μ
    
    # 右柯西-格林变形张量 C = FᵀF
    C = tdot(F)
    
    # Green-Lagrange 应变 E = 1/2 (C - I)
    I = one(C)
    E = 0.5 * (C - I)
    
    # 第二 Piola-Kirchhoff 应力 S = λ tr(E) I + 2μ E
    S = λ * tr(E) * I + 2μ * E
    
    # 第一 Piola-Kirchhoff 应力 P = F S
    P = F ⊡ S
    
    return P
end

# ============================================================================
# Neo-Hookean 超弹性材料
# ============================================================================

@material_model NeoHookean begin
    μ::Float64 = 40.0
    λ::Float64 = 100.0
end

function NeoHookean(E::Real, ν::Real)
    μ = E / (2(1 + ν))
    λ = E * ν / ((1 + ν) * (1 - 2ν))
    NeoHookean(μ=μ, λ=λ)
end

function compute_stress(material::NeoHookean, F::TensorValue{2,2,T}) where T
    μ, λ = material.μ, material.λ
    
    # 变形梯度行列式
    J = det(F)
    
    # 右柯西-格林 C = FᵀF
    C = tdot(F)
    C_inv = inv(C)
    
    # 第二 Piola-Kirchhoff 应力 (Neo-Hookean)
    # S = μ(I - C⁻¹) + λ ln J C⁻¹
    I = one(C)
    S = μ * (I - C_inv) + λ * log(J) * C_inv
    
    # 第一 Piola-Kirchhoff 应力
    P = F ⊡ S
    
    return P
end

# ============================================================================
# Von Mises 理想弹塑性材料
# ============================================================================

struct VonMisesPlasticity{T<:Real} <: PlasticModel
    E::T
    ν::T
    σ_y::T   # 屈服应力
    λ::T
    μ::T
end

function VonMisesPlasticity(; E::T, ν::T, σ_y::T) where T<:Real
    λ = E * ν / ((1 + ν) * (1 - 2ν))
    μ = E / (2(1 + ν))
    VonMisesPlasticity{T}(E, ν, σ_y, λ, μ)
end

function compute_stress(material::VonMisesPlasticity, ε::TensorValue{2,2,T}) where T
    λ, μ, σ_y = material.λ, material.μ, material.σ_y
    
    # 弹性预测
    I = one(ε)
    σ_el = λ * tr(ε) * I + 2μ * ε
    
    # 偏应力
    dev_σ = σ_el - (1/2) * tr(σ_el) * I
    
    # Von Mises 等效应力
    σ_vm = sqrt(1.5 * inner(dev_σ, dev_σ))
    
    # 径向返回映射
    if σ_vm > σ_y
        # 塑性一致性参数增量
        Δγ = (σ_vm - σ_y) / (3μ)
        
        # 更新应力
        σ = (σ_y / σ_vm) * dev_σ + (1/2) * tr(σ_el) * I
    else
        σ = σ_el
    end
    
    return σ
end

# ============================================================================
# Ramberg-Osgood 非线性弹性材料
# ============================================================================

struct RambergOsgood{T<:Real} <: ElasticModel
    E::T
    α::T
    n::T
end

function RambergOsgood(; E::T, α::T, n::T) where T<:Real
    RambergOsgood{T}(E, α, n)
end

function compute_stress(material::RambergOsgood, ε::TensorValue{2,2,T}) where T
    E, α, n = material.E, material.α, material.n
    
    # 等效应变
    ε_eq = sqrt(2/3 * inner(ε, ε))
    
    # 非线性应力-应变关系
    # ε_eq = σ_eq / E + α * (σ_eq / E)^n
    # 使用牛顿迭代求解σ_eq
    function residual(σ)
        σ / E + α * (σ / E)^n - ε_eq
    end
    
    function residual_deriv(σ)
        1/E + α * n * (σ / E)^(n-1) / E
    end
    
    # 牛顿迭代
    σ_eq = ε_eq * E  # 初始猜测
    for _ in 1:10
        σ_eq = σ_eq - residual(σ_eq) / residual_deriv(σ_eq)
    end
    
    # 方向缩放
    factor = σ_eq / max(ε_eq, 1e-10) / E
    return factor * E * ε
end

# ============================================================================
# 通用材料模型接口
# ============================================================================

"""
    compute_stress(material, ε)

多分派：根据材料模型类型调用对应的应力计算

支持的材料类型:
- LinearElastic
- SaintVenantKirchhoff
- NeoHookean
- VonMisesPlasticity
- RambergOsgood
"""
compute_stress

"""
    compute_tangent(material, ε)

计算材料切线刚度

对于复杂材料模型，使用ForwardDiff自动推导
"""
function compute_tangent(material::MaterialModel, ε)
    # 默认：使用ForwardDiff自动微分
    stress_fn(ϵ) = compute_stress(material, ϵ)
    return ForwardDiff.jacobian(stress_fn, ε)
end

# ============================================================================
# 3D版本（自动生成，代码复用）
# ============================================================================

for dim in [3]
    @eval begin
        function compute_stress(material::LinearElastic, ε::TensorValue{$dim,$dim,T}) where T
            λ, μ = material.λ, material.μ
            I = one(ε)
            return λ * tr(ε) * I + 2μ * ε
        end
        
        function compute_stress(material::SaintVenantKirchhoff, F::TensorValue{$dim,$dim,T}) where T
            λ, μ = material.λ, material.μ
            C = tdot(F)
            I = one(C)
            E = 0.5 * (C - I)
            S = λ * tr(E) * I + 2μ * E
            return F ⊡ S
        end
    end
end

# ============================================================================
# 类型稳定化优化
# ============================================================================

# 编译期优化：@inline 和 @fastmath
Base.@inline function compute_stress_fast(material::LinearElastic{T}, 
                                         ε::TensorValue{2,2,T}) where T<:AbstractFloat
    Base.@fastmath begin
        λ, μ = material.λ, material.μ
        trace_ε = ε[1,1] + ε[2,2]
        return TensorValue{2,2,T}(
            λ*trace_ε + 2μ*ε[1,1],      μ*ε[1,2],
            μ*ε[2,1],               λ*trace_ε + 2μ*ε[2,2]
        )
    end
end
