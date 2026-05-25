import sys
import time
import numpy as np

print("=" * 60)
print("分形生成器新增功能测试 v2.0")
print("=" * 60)
print()

# 测试1: 3D分形模块
print("1. 测试3D分形模块...")
try:
    from fractal_3d import (
        MandelbulbRenderer, MandelboxRenderer,
        mandelbulb_distance, create_rotation_matrix,
        generate_3d_points
    )
    print("   ✓ 3D分形模块导入成功")
    
    # 测试距离估计
    dist = mandelbulb_distance(0.0, 0.0, 0.0, power=8, max_iter=10)
    print(f"   原点距离估计: {dist:.6f}")
    
    # 测试旋转矩阵
    R = create_rotation_matrix(0.5, 0.3)
    print(f"   旋转矩阵创建成功: {R.shape}")
    
    # 测试Mandelbulb渲染器
    renderer = MandelbulbRenderer(width=100, height=75)
    start = time.perf_counter()
    image = renderer.render(use_ray_march=False)
    render_time = (time.perf_counter() - start) * 1000
    print(f"   Mandelbulb快速渲染: {render_time:.1f}ms, 形状: {image.shape}")
    
    # 测试3D旋转
    renderer.rotate(100, 50)
    print(f"   旋转后角度: ({renderer.rotation_x:.2f}, {renderer.rotation_y:.2f})")
    
    # 测试缩放
    renderer.zoom(1.2)
    print(f"   缩放后距离: {renderer.camera_distance:.2f}")
    
    # 测试生成点云
    start = time.perf_counter()
    points, iters = generate_3d_points(power=8, max_iter=10, num_points=1000)
    gen_time = (time.perf_counter() - start) * 1000
    print(f"   生成点云: {len(points)} 个点, 耗时: {gen_time:.1f}ms")
    
    # 测试Mandelbox
    mb_renderer = MandelboxRenderer(width=80, height=60)
    start = time.perf_counter()
    mb_image = mb_renderer.render()
    mb_time = (time.perf_counter() - start) * 1000
    print(f"   Mandelbox渲染: {mb_time:.1f}ms")
    
    print("   ✓ 3D分形模块测试通过")
except Exception as e:
    print(f"   ✗ 3D分形模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试2: 分形动画模块
print("2. 测试分形动画模块...")
try:
    from fractal_animation import (
        AnimationCurve, Keyframe, AnimationTrack,
        FractalAnimation, PresetAnimations
    )
    print("   ✓ 动画模块导入成功")
    
    # 测试动画曲线
    curves = ['linear', 'ease_in', 'ease_out', 'ease_in_out', 'sinusoidal', 'bounce', 'elastic']
    for curve_name in curves:
        curve_fn = getattr(AnimationCurve, curve_name)
        val = curve_fn(0.5)
        print(f"   {curve_name}(0.5) = {val:.4f}")
    
    # 测试关键帧和轨道
    kf1 = Keyframe(0, {'cx': -0.7}, 'ease_in_out')
    kf2 = Keyframe(100, {'cx': 0.7}, 'ease_in_out')
    track = AnimationTrack('cx', [kf1, kf2])
    
    v0 = track.get_value(0)
    v50 = track.get_value(50)
    v100 = track.get_value(100)
    print(f"   轨道插值: frame0={v0:.2f}, frame50={v50:.2f}, frame100={v100:.2f}")
    
    # 测试动画类
    class MockRenderer:
        def __init__(self):
            self.cx = 0.0
            self.cy = 0.0
            self.render_count = 0
            
        def render(self):
            self.render_count += 1
            return np.zeros((100, 100, 4))
        
        def update_parameters(self, params):
            for k, v in params.items():
                setattr(self, k, v)
    
    mock_renderer = MockRenderer()
    anim = PresetAnimations.create_julia_rotation(
        mock_renderer, cx_start=-0.7, cx_end=0.7,
        cy_start=-0.3, cy_end=0.3, duration=2.0, fps=30
    )
    
    print(f"   动画总帧数: {anim.total_frames}")
    print(f"   动画轨道: {list(anim.tracks.keys())}")
    
    # 测试渲染单帧
    frame_data = anim.get_parameters(30)
    print(f"   第30帧参数: cx={frame_data['cx']:.4f}, cy={frame_data['cy']:.4f}")
    
    img = anim.render_frame(0)
    print(f"   帧渲染成功: {img.shape}")
    
    # 测试帧缓存
    img2 = anim.render_frame(0)
    print(f"   帧缓存生效: {np.allclose(img, img2)}")
    
    print("   ✓ 动画模块测试通过")
except Exception as e:
    print(f"   ✗ 动画模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试3: 公式编辑器模块
print("3. 测试公式编辑器模块...")
try:
    from formula_editor import (
        ComplexFormula, CustomFractalGenerator,
        FormulaEditor, FormulaPresetLibrary
    )
    print("   ✓ 公式编辑器模块导入成功")
    
    # 测试公式验证
    formulas = [
        ('z*z + c', True),
        ('z**3 + z + c', True),
        ('sin(z) + c', True),
        ('z * z + )', False),  # 语法错误
        ('exp(z) + c', True),
        ('z*z*z - z*z + z + c', True),
    ]
    
    for formula, should_valid in formulas:
        cf = ComplexFormula(formula)
        valid = cf.validate()
        status = "✓" if valid == should_valid else "✗"
        print(f"   {status} '{formula}' -> {'有效' if valid else '无效'}{' (错误)' if valid != should_valid else ''}")
    
    # 测试公式计算
    cf = ComplexFormula('z*z + c')
    z = complex(1.0, 0.5)
    c = complex(-0.7, 0.27015)
    result = cf.evaluate(z, c)
    expected = z * z + c
    print(f"   z*z + c 计算: {result} == {expected}: {abs(result - expected) < 1e-10}")
    
    # 测试预设公式库
    categories = FormulaPresetLibrary.get_categories()
    print(f"   预设分类: {len(categories)} 个")
    for cat_name, formulas in categories.items():
        print(f"     - {cat_name}: {len(formulas)} 个公式")
    
    # 测试自定义分形生成器
    gen = CustomFractalGenerator('z*z + c')
    print(f"   生成器公式: {gen.formula.formula_str}")
    
    # 测试公式验证
    valid, error = gen.validate_formula('z*z + c')
    print(f"   验证 'z*z + c': {'有效' if valid else f'无效: {error}'}")
    
    # 测试生成自定义分形
    start = time.perf_counter()
    data = gen.generate_set(
        -2.0, 1.0, -1.5, 1.5,
        200, 150, 0.0, 0.0,
        max_iter=50, is_mandelbrot=True
    )
    gen_time = (time.perf_counter() - start) * 1000
    print(f"   自定义分形生成: {data.shape}, 耗时: {gen_time:.1f}ms")
    
    # 测试FormulaEditor
    editor = FormulaEditor()
    valid, error = editor.apply_formula('z*z*z + c')
    print(f"   编辑器应用公式: {'成功' if valid else f'失败: {error}'}")
    
    # 测试公式测试
    valid, error, results = editor.test_formula('z*z + c')
    print(f"   编辑器测试公式: {'有效' if valid else f'无效: {error}'}")
    if valid:
        print(f"   测试结果: {len(results)} 个值")
    
    print("   ✓ 公式编辑器模块测试通过")
except Exception as e:
    print(f"   ✗ 公式编辑器模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试4: Plotter扩展功能
print("4. 测试Plotter扩展功能...")
try:
    from fractal_plotter import FractalPlotter
    
    plotter = FractalPlotter(width=300, height=225)
    print("   ✓ Plotter创建成功")
    
    # 测试3D分形渲染
    for fractal_type in ['mandelbulb', 'mandelbox']:
        plotter.set_fractal_type(fractal_type)
        # 调整3D渲染器分辨率
        if fractal_type == 'mandelbulb':
            plotter.mandelbulb_renderer.width = 150
            plotter.mandelbulb_renderer.height = 112
        else:
            plotter.mandelbox_renderer.width = 100
            plotter.mandelbox_renderer.height = 75
        
        start = time.perf_counter()
        plotter.render()
        render_time = (time.perf_counter() - start) * 1000
        print(f"   {fractal_type}渲染: {render_time:.1f}ms")
        
        # 测试3D旋转
        plotter.rotate_3d(100, 50)
        print(f"   {fractal_type}旋转后渲染成功")
        
        # 测试3D缩放
        plotter.zoom_3d(1.2)
        print(f"   {fractal_type}缩放后渲染成功")
        
        # 测试状态信息
        info = plotter.get_status_info()
        print(f"   {fractal_type}状态: is_3d={info.get('is_3d')}")
    
    # 测试自定义公式
    plotter.set_fractal_type('custom')
    valid, error = plotter.set_custom_formula('z*z*z + c')
    print(f"   设置自定义公式: {'成功' if valid else f'失败: {error}'}")
    
    if valid:
        start = time.perf_counter()
        plotter.render()
        render_time = (time.perf_counter() - start) * 1000
        print(f"   自定义分形渲染: {render_time:.1f}ms")
    
    # 测试update_parameters (动画支持)
    params = {'max_iter': 100, 'julia_cx': -0.5}
    plotter.update_parameters(params)
    print(f"   批量更新参数成功")
    
    print("   ✓ Plotter扩展功能测试通过")
except Exception as e:
    print(f"   ✗ Plotter扩展功能测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试5: 综合性能测试（降低分辨率加快测试）
print("5. 综合性能测试...")
try:
    from fractal_plotter import FractalPlotter
    
    plotter = FractalPlotter(width=400, height=300)
    
    tests = [
        ('Mandelbrot', 'mandelbrot', True),
        ('Julia', 'julia', True),
        ('自定义 z^3+c', 'custom', True),
    ]
    
    print(f"   分辨率: 400x300")
    print(f"   {'分形类型':<20} {'渲染时间':>12}")
    print("   " + "-" * 35)
    
    for name, ftype, test_zoom in tests:
        plotter.set_fractal_type(ftype)
        if ftype == 'custom':
            plotter.set_custom_formula('z*z*z + c')
        
        start = time.perf_counter()
        plotter.render()
        elapsed = (time.perf_counter() - start) * 1000
        
        print(f"   {name:<20} {elapsed:>10.1f}ms")
    
    print()
    print("   ✓ 综合性能测试通过")
except Exception as e:
    print(f"   ✗ 综合性能测试失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("所有新增功能测试完成！")
print("=" * 60)
print()
print("新增功能总结:")
print("  1. 3D分形: Mandelbulb、Mandelbox，支持旋转和缩放")
print("  2. 动画系统: 关键帧动画、多曲线插值、导出GIF/视频")
print("  3. 公式编辑器: 自定义复数迭代公式、预设库、历史记录")
print("  4. GUI扩展: 3D分形控制、动画控制、公式编辑器界面")
print()
print("运行方式:")
print("  python main.py")
