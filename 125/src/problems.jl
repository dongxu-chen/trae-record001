"""
有限元问题定义模块 - 基于Gridap.jl的符号化有限元
"""

# 边界条件类型
struct DirichletBC
    field::Symbol
    component::Union{Int,Nothing}
    value::Function
    boundary
end

DirichletBC(field, value, boundary) = DirichletBC(field, nothing, value, boundary)

struct NeumannBC
    field::Symbol
    value::Function
    boundary
end

"""
有限元问题的核心结构体
"""
struct FEMProblem{Mat<:MaterialModel,Trial,Test,Geo,BCList}
    material::Mat
    trial::Trial
    test::Test
    geometry::Geo
    dirichlet_bcs::BCList
    neumann_bcs::Vector{NeumannBC}
    force::Vector{Float64}
end

function FEMProblem(material::MaterialModel, trial, test, geometry;
                     dirichlet_bcs=[], neumann_bcs=[], force=zeros(0))
    FEMProblem(material, trial, test, geometry, dirichlet_bcs, neumann_bcs, force)
end

# ============================================================================
# 符号化残差与雅可比构建 - 元编程核心
# ============================================================================

"""
    @generate_residual material_type

元编程宏：根据材料模型自动生成残差形式

利用Gridap的符号化DSL，在编译期生成弱形式
"""
macro generate_residual(material_type)
    quote
        function residual(problem::FEMProblem{<:$material_type}, u)
            # 符号化弱形式 - Gridap在编译期优化
            δu = problem.test
            material = problem.material
            
            # 基于材料模型类型的多分派
            _residual(material, u, δu, problem)
        end
    end |> esc
end

# 弹性材料残差
function _residual(::LinearElastic, u, δu, problem)
    ε = ε(u)  # 小应变
    σ = compute_stress(problem.material, ε)
    inner(σ, ε(δu))
end

# 超弹性材料残差
function _residual(::HyperElasticModel, u, δu, problem)
    F = F(u)  # 变形梯度
    P = compute_stress(problem.material, F)
    inner(P, ∇(δu))
end

# ============================================================================
# 自动微分切线刚度 - 核心创新点
# ============================================================================

"""
自动推导雅可比（切线刚度矩阵）
利用ForwardDiff + Gridap的符号化自动微分
"""
function assemble_jacobian(problem::FEMProblem, u)
    # 1. 定义残差函数
    function R(δu)
        assemble_vector(δu, problem.trial) do u_el
            F_el = F(u_el)
            P_el = compute_stress(problem.material, F_el)
            sum(P_el ⊡ ∇(δu))
        end
    end
    
    # 2. ForwardDiff自动求导 - 无需手动推导雅可比
    ForwardDiff.jacobian(R, u)
end

"""
符号化雅可比生成宏
"""
macro generate_jacobian(material_type)
    quote
        function jacobian(problem::FEMProblem{<:$material_type}, u, δu, du)
            material = problem.material
            
            # 对于弹性材料，使用解析雅可比
            if material isa LinearElastic
                ε_u = ε(u)
                ε_du = ε(du)
                σ = compute_stress(material, ε_u)
                D = compute_tangent(material, ε_u)
                inner(D ⊡ ε_du, ε(δu))
            else
                # 对于一般材料，使用自动微分
                stress_fn(ϵ) = compute_stress(material, ϵ)
                ∂σ∂ε = ForwardDiff.jacobian(stress_fn, ε(u))
                inner(∂σ∂ε ⊡ ε(du), ε(δu))
            end
        end
    end |> esc
end

# ============================================================================
# 高性能单元循环 - 利用Julia循环加速和SIMD
# ============================================================================

"""
单元级残差组装 - @simd 和 @inbounds 优化
"""
function element_residual(material::LinearElastic{T}, 
                         Ke::SMatrix{Ndof,Ndof,T}, 
                         re::SVector{Ndof,T},
                         u_el::SVector{Ndof,T}) where {T,Ndof}
    Base.@inbounds Base.@simd for i in 1:Ndof
        re_i = zero(T)
        Base.@simd for j in 1:Ndof
            re_i += Ke[i,j] * u_el[j]
        end
        re = setindex(re, re_i, i)
    end
    return re
end

"""
预计算单元刚度矩阵 - 使用StaticArrays获得堆上分配
"""
function compute_element_stiffness(material::LinearElastic{T}, 
                                   cell, quad_rule) where T
    # 获取单元节点坐标
    coords = get_cell_coordinates(cell)
    
    # 预分配静态数组（栈上分配，零开销）
    n = length(coords)
    Ke = @MMatrix zeros(T, 2n, 2n)
    
    # 数值积分
    for q in quad_rule
        # 形函数导数
        ∇N = gradient(q, coords)
        J = det(jacobian(q, coords))
        w = weight(q) * J
        
        # B矩阵
        for i in 1:n
            for j in 1:n
                # 小应变 B矩阵
                B_i = @SMatrix [
                    ∇N[i][1] 0;
                    0 ∇N[i][2];
                    ∇N[i][2] ∇N[i][1]
                ]
                B_j = @SMatrix [
                    ∇N[j][1] 0;
                    0 ∇N[j][2];
                    ∇N[j][2] ∇N[j][1]
                ]
                
                # D矩阵 - 平面应力
                E, ν = material.E, material.ν
                D = E/(1-ν^2) * @SMatrix [
                    1 ν 0;
                    ν 1 0;
                    0 0 (1-ν)/2
                ]
                
                Ke[2i-1:2i, 2j-1:2j] += w * B_i' * D * B_j
            end
        end
    end
    
    return SMatrix(Ke)
end

# ============================================================================
# 应变和变形梯度的符号化计算
# ============================================================================

"""
符号化小应变计算
"""
function ε(u)
    ∇u = ∇(u)
    0.5 * (∇u + transpose(∇u))
end

"""
符号化变形梯度计算
"""
function F(u)
    I = one(∇(u))
    I + ∇(u)
end

"""
符号化Green-Lagrange应变
"""
function E(u)
    F_u = F(u)
    0.5 * (F_u' * F_u - one(F_u))
end

# ============================================================================
# 后处理函数
# ============================================================================

"""
计算应力场
"""
function compute_stress_field(problem::FEMProblem, uh)
    function σ_cell(u)
        ε_u = ε(u)
        compute_stress(problem.material, ε_u)
    end
    σ_field = CellField(σ_cell, problem.trial)
    return σ_field
end

"""
计算应变能
"""
function compute_strain_energy(problem::FEMProblem, uh)
    function energy_density(u)
        ε_u = ε(u)
        σ_u = compute_stress(problem.material, ε_u)
        0.5 * inner(σ_u, ε_u)
    end
    ∑(energy_density(uh))
end

# ============================================================================
# 网格和空间生成辅助函数
# ============================================================================

"""
生成结构化四边形网格
"""
function generate_mesh(domain::Tuple{Tuple{Float64,Float64},Tuple{Float64,Float64}},
                       n::Tuple{Int,Int}; order=1)
    CartesianDiscreteModel(domain, n)
end

"""
生成有限元空间
"""
function create_fe_space(model::DiscreteModel, order; dirichlet_tags=[])
    # 向量值有限元空间
    reffe = ReferenceFE(lagrangian, VectorValue{2,Float64}, order)
    V = TestFESpace(model, reffe; conformity=:H1, dirichlet_tags=dirichlet_tags)
    U = TrialFESpace(V)
    U, V
end

"""
生成简单拉伸问题
"""
function simple_tension_problem(nx, ny; E=1e6, ν=0.3, order=1)
    # 网格
    domain = ((0.0, 1.0), (0.0, 1.0))
    model = generate_mesh(domain, (nx, ny))
    
    # 边界标签
    labels = get_face_labeling(model)
    add_tag_from_tags!(labels, "left", [1])
    add_tag_from_tags!(labels, "right", [2])
    
    # FE空间
    U, V = create_fe_space(model, order; dirichlet_tags=["left", "right"])
    
    # 材料
    material = LinearElastic(E=E, ν=ν)
    
    # 边界条件
    bcs = [
        DirichletBC(:displacement, (x, t) -> VectorValue(0.0, 0.0), "left"),
        DirichletBC(:displacement, (x, t) -> VectorValue(0.1, 0.0), "right")
    ]
    
    FEMProblem(material, U, V, model, dirichlet_bcs=bcs)
end
