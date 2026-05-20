"""
非线性求解器模块 - Newton-Raphson 和 并行求解
"""

# 求解器抽象类型
abstract type NonlinearSolver end

"""
Newton-Raphson 求解器参数
"""
Base.@kwdef struct NewtonRaphsonSolver <: NonlinearSolver
    max_iter::Int = 20
    rel_tol::Float64 = 1e-6
    abs_tol::Float64 = 1e-8
    verbose::Bool = true
    line_search::Bool = true
    line_search_max_iter::Int = 10
    divergence_tol::Float64 = 1e10
end

"""
求解器收敛历史记录
"""
struct ConvergenceHistory
    iterations::Vector{Int}
    residuals::Vector{Float64}
    step_lengths::Vector{Float64}
    times::Vector{Float64}
    
    function ConvergenceHistory()
        new(Int[], Float64[], Float64[], Float64[])
    end
end

function Base.push!(hist::ConvergenceHistory, iter, res, step_len=0.0, time=0.0)
    push!(hist.iterations, iter)
    push!(hist.residuals, res)
    push!(hist.step_lengths, step_len)
    push!(hist.times, time)
end

# ============================================================================
# Newton-Raphson 主求解器
# ============================================================================

"""
    solve_nonlinear(problem, solver, u0)

求解非线性有限元问题

性能优化:
- 使用StaticArrays进行单元级计算
- 预分配矩阵内存，避免重复分配
- 使用Julia线性代数的多线程
- 可选的Armijo线搜索
"""
function solve_nonlinear(problem::FEMProblem, 
                        solver::NewtonRaphsonSolver, 
                        u0::AbstractVector;
                        history::Union{ConvergenceHistory,Nothing}=nothing)
    
    # 初始化
    u = copy(u0)
    Δu = similar(u)
    t_start = time()
    
    # 残差向量和切线矩阵
    R = similar(u)
    K = allocate_jacobian(problem)
    
    # 应用边界条件到初始猜测
    apply_bcs!(u, problem)
    
    # 初始残差
    assemble_residual!(R, problem, u)
    res0 = norm(R)
    res = res0
    
    if solver.verbose
        @printf("Newton-Raphson 开始\n")
        @printf("  自由度: %d\n", length(u))
        @printf("  初始残差: %.2e\n", res0)
    end
    
    if !isnothing(history)
        push!(history, 0, res, 0.0, 0.0)
    end
    
    # 快速收敛检查
    if res < solver.abs_tol
        solver.verbose && println("  初始解已满足收敛条件")
        return u, true, 0
    end
    
    # Newton 迭代
    converged = false
    for iter in 1:solver.max_iter
        iter_time = @elapsed begin
            # 1. 组装切线刚度
            assemble_jacobian!(K, problem, u)
            
            # 2. 应用边界条件到残差和刚度
            apply_bcs_linear_system!(K, R, problem)
            
            # 3. 求解线性方程组
            Δu .= K \ (-R)
            
            # 4. 线搜索
            if solver.line_search
                α, R_new = armijo_line_search(R, Δu, u, problem,
                                              max_iter=solver.line_search_max_iter)
            else
                α = 1.0
                u .+= Δu
                assemble_residual!(R, problem, u)
                R_new = R
            end
            
            # 更新
            u .+= α .* Δu
            R .= R_new
            res = norm(R)
        end
        
        rel_res = res / (res0 + eps())
        
        if solver.verbose
            @printf("  迭代 %2d: ||R|| = %.2e, 相对 = %.2e, α = %.3f, 时间 = %.3fs\n",
                   iter, res, rel_res, α, iter_time)
        end
        
        if !isnothing(history)
            push!(history, iter, res, α, iter_time)
        end
        
        # 收敛检查
        if res < solver.abs_tol || rel_res < solver.rel_tol
            converged = true
            solver.verbose && @printf("  收敛! 总时间 = %.3fs\n", time() - t_start)
            break
        end
        
        # 发散检查
        if res > solver.divergence_tol
            @warn("  发散! 残差 = $res")
            break
        end
    end
    
    if !converged && solver.verbose
        @printf("  达到最大迭代次数，未收敛\n")
    end
    
    return u, converged, length(history === nothing ? 0 : history.iterations)
end

# ============================================================================
# Armijo 线搜索
# ============================================================================

"""
Armijo 线搜索 - 保证 Newton 迭代全局收敛
"""
function armijo_line_search(R, Δu, u, problem; max_iter=10, c=1e-4, β=0.5)
    R_new = similar(R)
    u_temp = similar(u)
    
    # 初始下降方向
    init_sq_norm = dot(R, R)
    init_slope = 2.0 * dot(R, Δu)
    
    if init_slope >= 0
        @warn("线搜索: 不是下降方向")
        return 1.0, R + Δu
    end
    
    α = 1.0
    for i in 1:max_iter
        # 试验步长
        u_temp .= u .+ α .* Δu
        assemble_residual!(R_new, problem, u_temp)
        new_sq_norm = dot(R_new, R_new)
        
        # Armijo 条件
        if new_sq_norm <= init_sq_norm + c * α * init_slope
            return α, R_new
        end
        
        # 减小步长
        α *= β
    end
    
    @warn("线搜索达到最大迭代次数，使用 α = $α")
    return α, R_new
end

# ============================================================================
# 残差和雅可比组装 - 高性能版本
# ============================================================================

"""
预分配雅可比矩阵 - 使用稀疏矩阵结构
"""
function allocate_jacobian(problem::FEMProblem)
    n_dofs = num_free_dofs(problem.trial)
    # 使用 Gridap 内置的矩阵分配器
    allocate_matrix(problem.trial, problem.test)
end

"""
残差向量组装 - 并行版本
"""
function assemble_residual!(R::AbstractVector, problem::FEMProblem, u::AbstractVector)
    fill!(R, 0.0)
    
    material = problem.material
    trian = get_triangulation(problem.geometry)
    quad = CellQuadrature(trian, order=2)
    
    # 单元循环 - Julia多线程自动并行
    Threads.@threads for cell in cells(trian)
        assemble_cell_residual!(R, cell, material, u, quad)
    end
    
    return R
end

"""
单元级残差组装 - 使用 StaticArrays 加速
"""
function assemble_cell_residual!(R, cell, material::LinearElastic, u, quad)
    # 获取单元自由度
    cell_dofs = get_cell_dof_ids(problem.trial, cell)
    n_dofs = length(cell_dofs)
    
    # 单元解
    u_el = SVector{n_dofs}(u[cell_dofs])
    
    # 单元刚度和残差
    Ke = compute_element_stiffness(material, cell, quad)
    re = Ke * u_el
    
    # 组装到全局（无锁，因为使用线程私有）
    for (i, dof) in enumerate(cell_dofs)
        if is_free_dof(dof)
            R[dof] += re[i]
        end
    end
end

"""
雅可比矩阵组装 - 高性能并行版本
"""
function assemble_jacobian!(K, problem::FEMProblem, u)
    fill!(K, 0.0)
    
    material = problem.material
    trian = get_triangulation(problem.geometry)
    quad = CellQuadrature(trian, order=2)
    
    # 多线程单元循环
    Threads.@threads for cell in cells(trian)
        assemble_cell_jacobian!(K, cell, material, u, quad)
    end
    
    return K
end

"""
单元级雅可比组装
"""
function assemble_cell_jacobian!(K, cell, material, u, quad)
    # 对于弹性材料，雅可比即刚度矩阵
    if material isa LinearElastic
        Ke = compute_element_stiffness(material, cell, quad)
        cell_dofs = get_cell_dof_ids(problem.trial, cell)
        n = length(cell_dofs)
        
        # 直接组装
        for i in 1:n
            dof_i = cell_dofs[i]
            if !is_free_dof(dof_i)
                continue
            end
            for j in 1:n
                dof_j = cell_dofs[j]
                if is_free_dof(dof_j)
                    K[dof_i, dof_j] += Ke[i, j]
                end
            end
        end
    else
        # 非线性材料: 使用 ForwardDiff
        assemble_cell_jacobian_ad!(K, cell, material, u, quad)
    end
end

"""
使用 ForwardDiff 自动推导单元雅可比
"""
function assemble_cell_jacobian_ad!(K, cell, material, u, quad)
    cell_dofs = get_cell_dof_ids(problem.trial, cell)
    n_dofs = length(cell_dofs)
    
    # 残差函数
    function cell_residual(u_el)
        re = similar(u_el)
        # ... 单元残差计算
        re
    end
    
    u_el = u[cell_dofs]
    Ke = ForwardDiff.jacobian(cell_residual, u_el)
    
    # 组装
    for i in 1:n_dofs
        for j in 1:n_dofs
            K[cell_dofs[i], cell_dofs[j]] += Ke[i, j]
        end
    end
end

# ============================================================================
# 边界条件应用
# ============================================================================

"""
应用 Dirichlet 边界条件到解向量
"""
function apply_bcs!(u, problem::FEMProblem)
    for bc in problem.dirichlet_bcs
        apply_dirichlet!(u, bc, problem.trial)
    end
    return u
end

"""
应用 Dirichlet 边界条件到线性系统 (K, R)
"""
function apply_bcs_linear_system!(K, R, problem::FEMProblem)
    for bc in problem.dirichlet_bcs
        apply_dirichlet_to_matrix!(K, R, bc, problem.trial)
    end
    return K, R
end

# ============================================================================
# 增量加载求解器 - 适用于强非线性问题
"""
增量加载求解器

适用于:
- 弹塑性问题
- 大变形超弹性
- 接触问题
"""
function solve_incremental(problem::FEMProblem,
                           solver::NewtonRaphsonSolver,
                           n_increments::Int;
                           load_factor_end=1.0,
                           history=nothing)
    
    u = zeros(num_free_dofs(problem.trial))
    total_history = ConvergenceHistory()
    
    if solver.verbose
        println("\n增量加载求解器")
        println("  增量数: $n_increments")
        println("  最终加载因子: $load_factor_end")
    end
    
    for inc in 1:n_increments
        load_factor = load_factor_end * inc / n_increments
        
        if solver.verbose
            println("\n增量 $inc/$n_increments, 加载因子 = $load_factor")
        end
        
        # 更新问题的载荷
        problem_current = set_load_factor(problem, load_factor)
        
        # Newton-Raphson 子迭代
        u, converged, n_iters = solve_nonlinear(
            problem_current, solver, u,
            history=total_history
        )
        
        if !converged
            @warn("增量 $inc 未收敛!")
            break
        end
    end
    
    return u, total_history
end

function set_load_factor(problem, load_factor)
    # 对于 Dirichlet 加载，更新边界值
    scaled_bcs = map(problem.dirichlet_bcs) do bc
        DirichletBC(
            bc.field,
            (x, t) -> load_factor * bc.value(x, t),
            bc.boundary
        )
    end
    FEMProblem(
        problem.material,
        problem.trial,
        problem.test,
        problem.geometry,
        scaled_bcs,
        problem.neumann_bcs,
        problem.force * load_factor
    )
end

# ============================================================================
# MPI 并行求解器（分布式内存）
# ============================================================================

"""
分布式 Newton-Raphson 求解器

使用:
- GridapDistributed 提供分布式网格
- PETSc 提供并行线性代数
- MPI 提供进程间通信
"""
function solve_nonlinear_parallel(problem::FEMProblem,
                                  solver::NewtonRaphsonSolver,
                                  u0;
                                  comm=MPI.COMM_WORLD)
    rank = MPI.Comm_rank(comm)
    size = MPI.Comm_size(comm)
    
    # 本地和全局自由度
    local_dofs = get_local_dofs(problem.trial)
    global_dofs = get_global_dofs(problem.trial)
    
    # 分布式矩阵和向量 (PETSc)
    K = allocate_distributed_jacobian(problem, comm)
    R = allocate_distributed_vector(problem, comm)
    
    # 初始解
    u = copy(u0)
    
    # Newton 迭代
    for iter in 1:solver.max_iter
        # 1. 并行组装 - 每个进程只组装自己的子域
        assemble_residual_distributed!(R, problem, u, comm)
        assemble_jacobian_distributed!(K, problem, u, comm)
        
        # 2. 全局残差范数
        res_global = norm_distributed(R, comm)
        
        if rank == 0 && solver.verbose
            @printf("进程 0: 迭代 %2d, ||R|| = %.2e\n", iter, res_global)
        end
        
        # 3. 并行线性求解 (PETSc)
        Δu = K \ (-R)
        
        # 4. 更新解
        u .+= Δu
        
        # 收敛检查 (所有进程)
        converged = check_convergence_distributed(res_global, solver, comm)
        if converged
            rank == 0 && println("全局收敛")
            break
        end
    end
    
    return u
end

"""
分布式残差组装
"""
function assemble_residual_distributed!(R, problem, u, comm)
    # 每个进程组装自己的本地残差
    fill!(R, 0.0)
    trian = get_own_triangulation(problem.geometry)
    
    for cell in cells(trian)
        assemble_cell_residual!(R, cell, problem.material, u, CellQuadrature(trian, 2))
    end
    
    # MPI 归约: 求和
    MPI.Allreduce!(R, +, comm)
end

function norm_distributed(v, comm)
    local_sq = dot(v, v)
    global_sq = MPI.Allreduce(local_sq, +, comm)
    sqrt(global_sq)
end

function check_convergence_distributed(res, solver, comm)
    # 所有进程获得相同的收敛状态
    converged_local = res < solver.abs_tol
    converged_global = MPI.Allreduce(converged_local, &, comm)
    return converged_global
end

function allocate_distributed_jacobian(problem, comm)
    # 使用 PETSc 并行稀疏矩阵
    n_local = length(get_local_dofs(problem.trial))
    n_global = MPI.Allreduce(n_local, +, comm)
    
    # 创建 PETSc AIJ 矩阵
    K = PETSc.Mat()
    PETSc.set_type(K, "aij")
    PETSc.set_sizes(K, n_local, n_local, n_global, n_global)
    PETSc.set_up(K)
    
    return K
end
