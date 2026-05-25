# 布料仿真系统 (Cloth Simulation System)

基于质点-弹簧模型的布料物理仿真系统，使用Python实现。

## 功能特性

### 物理仿真
- **质点-弹簧模型**: 包含结构弹簧、剪切弹簧、弯曲弹簧三种类型
- **撕裂模拟**: 超过应力阈值时弹簧自动断裂，网格分裂
- **积分器**:
  - 显式欧拉积分器 (Explicit Euler)
  - 半隐式欧拉积分器 (Semi-Implicit Euler)
  - **Verlet积分器** (默认，最稳定，支持约束松弛迭代)
- **力系统**:
  - 重力
  - 风力 (支持**3D Perlin噪声湍流**，位置相关的真实风场)
  - 阻尼 (全局阻尼和弹簧阻尼)
- **GPU加速**: 使用Numba CUDA并行计算，大幅提升性能

### 碰撞检测
- **球体碰撞器**: 可调节位置、半径、恢复系数和摩擦系数
- **平面碰撞器**: 可调节高度、恢复系数和摩擦系数
- **自碰撞检测** (**BVH加速**): 避免布料自穿透，支持暴力检测和BVH加速两种模式
- **布料-刚体耦合**: 双向耦合，布料带动刚体运动，刚体运动影响布料

### 动态刚体系统
- **球体刚体**: 支持质量、半径、位置、速度等参数
- **盒子刚体**: 支持尺寸、旋转、惯性张量等
- **双向耦合**:
  - 布料碰撞刚体时传递力和力矩
  - 刚体运动影响布料的位置和速度
  - 支持附件点约束

### 交互界面 (Dear ImGui)
- 实时参数调节
- 积分器切换
- 布料分辨率调整 (网格密度)
- 弹簧刚度调节
- 力系统参数调节
- 碰撞体参数调节
- 撕裂参数控制
- 刚体参数控制
- GPU加速开关
- 渲染选项控制
- 暂停/单步调试功能
- 实时统计: FPS、碰撞数、断裂弹簧数

### 3D渲染 (PyOpenGL)
- 布料表面渲染 (带光照)
- 应力着色 (蓝-青-绿-黄-红色谱显示应力分布)
- 断裂边可视化 (红色虚线)
- 线框渲染
- 质点渲染
- 碰撞体可视化
- 动态刚体可视化
- 相机控制:
  - 左键拖拽: 环绕视角
  - 右键拖拽: 平移视角
  - 滚轮: 缩放
  - H键: 显示/隐藏GUI

## 项目结构

```
.
├── main.py              # 主程序入口
├── cloth.py             # 质点-弹簧模型核心类（含撕裂）
├── integrators.py       # 积分器实现（三种积分器）
├── forces.py            # 力系统（重力/风力/阻尼）
├── perlin_noise.py      # 3D Perlin噪声实现
├── collision.py         # 碰撞检测系统（球体/平面）
├── bvh.py               # BVH层次结构加速
├── self_collision.py    # 布料自碰撞检测
├── rigid_body.py        # 刚体系统与布料-刚体耦合
├── gpu_accelerator.py   # CUDA GPU加速模块
├── renderer.py          # OpenGL渲染器和相机控制
├── gui.py               # ImGui交互界面
├── requirements.txt     # Python依赖
└── README.md            # 本文件
```

## 环境要求

- Python 3.8 ~ 3.12 (推荐，3.13+可能需要从源码编译部分包)
- Windows / macOS / Linux
- 支持OpenGL的显卡
- **可选**: NVIDIA GPU + CUDA驱动（用于GPU加速）

## 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装:
```bash
pip install numpy PyOpenGL PyOpenGL-accelerate imgui pygame numba
```

**注意**: 
- Python 3.13+ 可能需要从源码编译 `imgui` 和 `pygame`，需要安装C++编译器
- GPU加速需要安装CUDA Toolkit和兼容的NVIDIA驱动
- 如果遇到安装问题，建议使用 Python 3.10 或 3.11

## 运行程序

```bash
python main.py
```

## 使用说明

### 快速开始
1. 运行程序后，布料会在重力作用下下落
2. 默认顶部有几个固定点，布料会悬挂在球体上
3. 在ImGui控制面板中调节各项参数

### 撕裂模拟体验
1. 开启 **Enable Tearing**
2. 增加 **Wind Strength** 到 30+，或降低 **Tear Threshold** 到 0.1
3. 观察弹簧断裂，布料分裂成多个部分
4. 开启 **Color by Stress** 可以看到应力分布（蓝色低应力→红色高应力）
5. 开启 **Show Broken Edges** 可以看到断裂位置（红色虚线）

### 刚体耦合体验
1. 展开 **Dynamic Rigid Bodies** 面板
2. 确保 **Dynamic Sphere 1** 和 **Couple with Cloth** 已启用
3. 布料下落时会与球体碰撞，球体会被布料带动运动
4. 可以调节球体质量、摩擦系数等参数观察不同效果
5. 也可以启用 **Dynamic Box** 测试盒子刚体

### GPU加速体验
1. 确保已安装CUDA和numba
2. 在Simulation面板勾选 **GPU Acceleration**
3. 提高布料分辨率到 30×30 或更高
4. 观察FPS提升（高分辨率下提升显著）

### 常用操作
- **Wind Strength**: 增加风力可以看到布料飘动效果
- **Paused**: 暂停仿真，配合Step按钮单步调试
- **Apply Resolution**: 调整布料网格密度后点击应用
- **Wireframe Only**: 只显示线框，观察弹簧结构
- **Show Points**: 显示质点，红色点为固定点
- **Shift+R**: 快速重置仿真

### 积分器选择
- **Verlet** (默认): 最稳定，支持约束松弛迭代，适合布料仿真
- **Semi-Implicit Euler**: 比显式欧拉稳定，速度中等
- **Explicit Euler**: 计算最快，但需要更小的时间步长，容易不稳定

### 风力效果
- **Use Perlin Noise**: 启用3D Perlin噪声产生真实的湍流效果
- **Turbulence Scale**: 噪声尺度，值越小涡流越细密
- **Turbulence Strength**: 湍流强度
- 风力效果建议 Wind Strength 5-20, Wind Turbulence 0.3-0.5

### 自碰撞
- **Self Collision Enabled**: 启用自碰撞检测，防止布料穿透
- **Use BVH Acceleration**: 使用BVH树加速检测，复杂度从O(n²)降到O(n log n)
- **Collision Threshold**: 碰撞检测阈值，建议设为布料间距的1/4~1/2
- 高分辨率布料(>20x20)强烈建议开启BVH加速

### 调参建议
- 如果布料过于"柔软"，增加 Structural Stiffness
- 如果布料过于"僵硬"，减少 Bend Stiffness
- 如果出现爆炸式不稳定，增加 Damping 或使用更小的 Substeps
- 如果布料容易穿透自身，增加自碰撞的 Collision Threshold 或 Stiffness
- Verlet积分器的 Constraint Iterations 设为3-5可显著提升稳定性
- 如果撕裂不明显，降低 Tear Threshold 或增加 Wind Strength
- 如果刚体运动太快，增加刚体质量或增加摩擦系数

## 技术实现细节

### 质点-弹簧模型
每个质点具有:
- 位置 (position)
- 速度 (velocity)
- 质量 (mass)
- 受力 (force)
- 固定标记 (pinned)
- 簇ID (cluster_id)

三种弹簧类型:
1. **结构弹簧**: 连接相邻质点，保持布料结构
2. **剪切弹簧**: 连接对角质点，抵抗剪切变形
3. **弯曲弹簧**: 连接间隔一个的质点，抵抗弯曲

### 撕裂模拟
撕裂检测流程:
1. 每帧计算每个弹簧的应力（应变 = 伸长量/原长）
2. 当应力超过阈值时标记弹簧为断裂
3. 移除断裂弹簧影响的三角形（使布料可见裂口）
4. 使用并查集算法更新布料簇ID
5. 不同簇的布料独立运动

### 积分算法
**显式欧拉**:
```
v(t+Δt) = v(t) + a(t) * Δt
x(t+Δt) = x(t) + v(t+Δt) * Δt
```

**半隐式欧拉**:
```
v(t+Δt) = v(t) + a(t) * Δt
x(t+Δt) = x(t) + v(t+Δt) * Δt
```

**改进Verlet** (推荐):
```
x(t+Δt) = x(t) + v(t)*Δt + 0.5*a(t)*Δt²
x(t+Δt) += (x(t) - x(t-Δt)) * damping
v(t) = (x(t+Δt) - x(t-Δt)) / (2*Δt)
```
Verlet积分器还支持**约束松弛迭代**，通过多次投影修正弹簧长度，防止过度拉伸，显著提升稳定性。

### 3D Perlin噪声风力
使用3D Perlin噪声生成空间和时间上连续的湍流风场:
- 每个质点根据其空间位置采样不同的风力值
- 噪声随时间演化，产生自然的飘动效果
- 支持多倍频叠加(fractal Brownian motion)
- 三个独立的噪声生成器分别控制x、y、z方向

### BVH自碰撞加速
边界层次结构(Bounding Volume Hierarchy)将自碰撞检测从O(n²)优化到O(n log n):
1. 自顶向下构建AABB包围盒树
2. 每帧重新拟合(refit)包围盒
3. 遍历树进行碰撞查询，只对相交的包围盒进行精确检测
4. 跳过相邻质点(索引差<=2)避免误检测

### 布料-刚体双向耦合
耦合流程:
1. 检测布料质点与刚体的碰撞
2. 应用位置修正防止穿透
3. 计算相对速度和法向冲量
4. 将冲量反向应用到刚体（施加力和力矩）
5. 更新刚体的线速度和角速度
6. 积分刚体运动
7. 如果有附件点约束，将布料质点绑定到刚体表面

### CUDA GPU加速
使用Numba CUDA实现并行计算:
1. 弹簧力计算并行化（每个CUDA线程处理一个弹簧）
2. 质点位置更新并行化（每个CUDA线程处理一个质点）
3. 使用原子操作累加力到质点
4. 内存管理优化，减少GPU-CPU数据传输
5. 优雅降级：GPU不可用时自动回退到CPU

性能提升参考（理论值）:
| 布料分辨率 | CPU | GPU (RTX 3090) | 加速比 |
|-----------|-----|-----------------|--------|
| 15×15=225 | 60 FPS | 60+ FPS | 1× |
| 30×30=900 | 25 FPS | 60 FPS | 2.4× |
| 50×50=2500 | 8 FPS | 55 FPS | 6.9× |
| 100×100=10000 | 2 FPS | 30 FPS | 15× |

### 碰撞响应
采用位置修正 + 速度反射的方式:
1. 检测质点是否穿透碰撞体
2. 将质点位置修正到碰撞体表面
3. 根据恢复系数反射法向速度
4. 根据摩擦系数衰减切向速度

## 新增文件说明

| 文件 | 功能 |
|------|------|
| **perlin_noise.py** | 3D Perlin噪声实现，包括分形布朗运动 |
| **bvh.py** | 边界层次结构实现，AABB包围盒、BVH树构建、碰撞查询 |
| **self_collision.py** | 布料自碰撞检测与响应，支持BVH加速和暴力检测 |
| **rigid_body.py** | 刚体系统，球体/盒子刚体、布料-刚体双向耦合 |
| **gpu_accelerator.py** | CUDA GPU加速，并行弹簧力和积分计算 |

## 新增功能文件详解

### cloth.py 扩展
- 新增 `broken` 标记、`stress` 应力记录、`spring_type` 类型
- 新增 `Triangle` 类管理三角形激活状态
- `check_and_tear()` 检测应力并断裂弹簧
- `_update_clusters()` 并查集算法更新撕裂后的布料簇
- `get_stress_array()` 获取每个质点的平均应力用于可视化
- `get_broken_edges()` 获取断裂边用于渲染
- `get_spring_data()` 获取GPU加速所需的弹簧数据

### rigid_body.py 详解
- `RigidBodyState` 数据类管理刚体状态
- `RigidBody` 抽象基类定义刚体接口
- `RigidSphere` 球体刚体实现
- `RigidBox` 盒子刚体实现（支持旋转）
- `ClothRigidCoupling` 双向耦合管理类
  - `compute_coupling_forces()` 计算碰撞力和力矩
  - `update_attachments()` 更新附件点约束
  - `integrate_rigid_bodies()` 积分刚体运动

### gpu_accelerator.py 详解
- `is_cuda_available()` 检测CUDA可用性
- `GPUAccelerator` 核心GPU加速类
  - 内存管理（设备数组分配、数据传输）
  - `compute_spring_forces_gpu()` 并行弹簧力计算
  - `integrate_euler_gpu()` 并行欧拉积分
  - CPU回退实现
- `GPUForceSystem` 无缝集成到现有力系统架构
- CUDA核函数:
  - `_cuda_compute_spring_forces` 每个线程处理一个弹簧
  - `_cuda_integrate_euler` 每个线程处理一个质点

## 许可证

MIT License
