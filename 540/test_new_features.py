#!/usr/bin/env python3
import sys
import os
import shutil
import numpy as np
import cv2

print("=" * 60)
print("测试新增功能: 批量处理 / 编辑器 / 格式导出")
print("=" * 60)

# ─── 准备测试数据 ───
test_dir = 'test_batch_input'
output_dir = 'test_batch_output'
os.makedirs(test_dir, exist_ok=True)

for i in range(3):
    h, w = 200, 300
    img = np.ones((h, w, 3), dtype=np.uint8) * 240
    cv2.circle(img, (80 + i * 40, 100), 40 + i * 10, (255 - i * 50, 100 + i * 30, 100), -1)
    cv2.rectangle(img, (180, 50 + i * 20), (270, 150 + i * 10), (100, 200 - i * 30, 100 + i * 50), -1)
    for _ in range(100):
        x = np.random.randint(0, w)
        y = np.random.randint(0, h)
        img[y, x] = np.random.randint(0, 255, 3)
    cv2.imwrite(os.path.join(test_dir, f'test_{i}.png'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
print(f"✓ 创建 {3} 个测试图像于 {test_dir}/")

# ─── 测试1: 批量矢量化 ───
print("\n" + "-" * 60)
print("测试1: 批量矢量化 + 并行处理")
print("-" * 60)
try:
    from batch_processor import BatchProcessor

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    processor = BatchProcessor(test_dir, output_dir, max_workers=2)
    results = processor.run(convert_kwargs={'n_colors': 4, 'use_curve_fitting': True})

    summary = processor.get_summary()
    print(f"\n  总计: {summary['total']}, 成功: {summary['success']}, 失败: {summary['failed']}")
    print(f"  总轮廓数: {summary['total_contours']}")

    svg_files = [f for f in os.listdir(output_dir) if f.endswith('.svg')]
    print(f"  输出文件: {svg_files}")

    assert summary['success'] == 3, f"预期3个成功，实际{summary['success']}"
    print("✓ 批量矢量化测试通过")
except Exception as e:
    print(f"✗ 批量矢量化测试失败: {e}")
    import traceback
    traceback.print_exc()

# ─── 测试2: 矢量化编辑器 ───
print("\n" + "-" * 60)
print("测试2: 矢量化编辑器 - 锚点/曲线调整")
print("-" * 60)
try:
    from vector_editor import VectorEditor

    svg_file = os.path.join(output_dir, 'test_0.svg')
    if not os.path.exists(svg_file):
        from raster_to_vector import RasterToVector
        RasterToVector(os.path.join(test_dir, 'test_0.png')).convert(svg_file, n_colors=4)

    editor = VectorEditor(svg_file)
    info = editor.get_edit_info()
    print(f"  加载: {info['total_paths']} 路径, {info['total_anchors']} 锚点")

    # 测试列出路径
    print("  路径列表:")
    for i, p in enumerate(editor.paths[:3]):
        print(f"    路径{i}: {len(p['points'])} 锚点, fill={p['fill']}")

    # 测试移动锚点
    if info['total_anchors'] > 0 and info['total_paths'] > 0:
        first_pt = editor.paths[0]['points'][0].copy()
        editor.move_anchor(0, 0, first_pt[0] + 5, first_pt[1] + 5)
        new_pt = editor.paths[0]['points'][0]
        moved = not np.array_equal(first_pt, new_pt)
        print(f"  ✓ 移动锚点: ({first_pt[0]:.1f},{first_pt[1]:.1f}) -> ({new_pt[0]:.1f},{new_pt[1]:.1f})")

    # 测试平滑路径
    if info['total_paths'] > 0:
        before_pts = [p.copy() for p in editor.paths[0]['points']]
        editor.smooth_path(0, iterations=3, factor=0.5)
        after_pts = editor.paths[0]['points']
        smoothed = any(not np.array_equal(b, a) for b, a in zip(before_pts, after_pts))
        print(f"  ✓ 平滑路径0: {'曲线已变化' if smoothed else '无变化'}")

    # 测试简化路径
    if info['total_paths'] > 0:
        before_count = len(editor.paths[0]['points'])
        editor.simplify_path(0, tolerance=3.0)
        after_count = len(editor.paths[0]['points'])
        print(f"  ✓ 简化路径0: {before_count} -> {after_count} 锚点")

    # 测试添加/删除锚点
    if info['total_paths'] > 0 and len(editor.paths[0]['points']) > 0:
        before_count = len(editor.paths[0]['points'])
        editor.add_anchor(0, 0, 999, 999)
        after_add = len(editor.paths[0]['points'])
        print(f"  ✓ 添加锚点: {before_count} -> {after_add}")

        editor.remove_anchor(0, 0)
        after_remove = len(editor.paths[0]['points'])
        print(f"  ✓ 删除锚点: {after_add} -> {after_remove}")

    # 测试Undo
    editor.undo()
    print(f"  ✓ 撤销操作 (历史深度: {len(editor._history)})")

    # 测试变换
    if info['total_paths'] > 0:
        editor.transform_path(0, translate=(10, 10), scale=(1.1, 1.1), rotate=5)
        print(f"  ✓ 变换路径0 (平移+缩放+旋转)")

    # 测试修改颜色
    if info['total_paths'] > 0:
        editor.set_path_color(0, fill=(255, 0, 0), stroke=(200, 0, 0))
        print(f"  ✓ 修改路径0颜色: fill={editor.paths[0]['fill']}")

    # 保存
    edited_svg = 'test_edited.svg'
    editor.save_svg(edited_svg)
    assert os.path.exists(edited_svg)
    print(f"  ✓ 保存编辑结果: {edited_svg}")

    # 验证保存的内容可重新加载
    editor2 = VectorEditor(edited_svg)
    info2 = editor2.get_edit_info()
    print(f"  ✓ 重新加载验证: {info2['total_paths']} 路径, {info2['total_anchors']} 锚点")

    print("✓ 矢量化编辑器测试通过")
except Exception as e:
    print(f"✗ 编辑器测试失败: {e}")
    import traceback
    traceback.print_exc()

# ─── 测试3: 格式导出 ───
print("\n" + "-" * 60)
print("测试3: 格式导出 (EPS/PDF/AI)")
print("-" * 60)
try:
    from format_exporter import FormatExporter

    svg_source = os.path.join(output_dir, 'test_0.svg')
    if not os.path.exists(svg_source):
        from raster_to_vector import RasterToVector
        RasterToVector(os.path.join(test_dir, 'test_0.png')).convert(svg_source, n_colors=4)

    exporter = FormatExporter(svg_source)

    # EPS 导出
    eps_path = 'test_export.eps'
    exporter.export(eps_path, format='eps')
    assert os.path.exists(eps_path)
    eps_size = os.path.getsize(eps_path)
    with open(eps_path, 'r', encoding='latin-1') as f:
        header = f.read(100)
    assert '%!PS-Adobe' in header, "EPS头部验证失败"
    print(f"  ✓ EPS导出: {eps_path} ({eps_size} bytes, 头部验证通过)")

    # PDF 导出
    pdf_path = 'test_export.pdf'
    try:
        exporter.export(pdf_path, format='pdf')
        assert os.path.exists(pdf_path)
        pdf_size = os.path.getsize(pdf_path)
        with open(pdf_path, 'rb') as f:
            header = f.read(10)
        assert header.startswith(b'%PDF'), "PDF头部验证失败"
        print(f"  ✓ PDF导出: {pdf_path} ({pdf_size} bytes, 头部验证通过)")
    except ImportError as ie:
        print(f"  ⚠ PDF导出跳过 (需要cairosvg): {ie}")

    # AI 导出
    ai_path = 'test_export.ai'
    exporter.export(ai_path, format='ai')
    assert os.path.exists(ai_path)
    ai_size = os.path.getsize(ai_path)
    with open(ai_path, 'r', encoding='latin-1') as f:
        header = f.read(100)
    assert '%!PS-Adobe' in header, "AI头部验证失败"
    assert 'AI3_ReadAI8_Prolog' in open(ai_path, 'r', encoding='latin-1').read(), "AI标识验证失败"
    print(f"  ✓ AI导出: {ai_path} ({ai_size} bytes, 头部验证通过)")

    # SVG 复制导出
    svg_copy = 'test_export_copy.svg'
    exporter.export(svg_copy, format='svg')
    assert os.path.exists(svg_copy)
    print(f"  ✓ SVG导出: {svg_copy}")

    print("✓ 格式导出测试通过")
except Exception as e:
    print(f"✗ 格式导出测试失败: {e}")
    import traceback
    traceback.print_exc()

# ─── 测试4: CLI子命令 ───
print("\n" + "-" * 60)
print("测试4: CLI子命令")
print("-" * 60)
try:
    import subprocess

    # single
    r = subprocess.run(
        [sys.executable, 'cli.py', 'single',
         os.path.join(test_dir, 'test_0.png'), 'cli_test.svg', '-c', '4'],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    assert r.returncode == 0, f"single命令失败: {r.stderr}"
    assert os.path.exists('cli_test.svg'), "single输出不存在"
    print("  ✓ cli single 命令通过")

    # export
    r = subprocess.run(
        [sys.executable, 'cli.py', 'export', 'cli_test.svg', '-f', 'eps'],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    assert r.returncode == 0, f"export命令失败: {r.stderr}"
    assert os.path.exists('cli_test.eps'), "export EPS输出不存在"
    print("  ✓ cli export 命令通过")

    # edit --list-paths
    r = subprocess.run(
        [sys.executable, 'cli.py', 'edit', 'cli_test.svg', '--list-paths'],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    assert r.returncode == 0, f"edit命令失败: {r.stderr}"
    print("  ✓ cli edit --list-paths 命令通过")

    print("✓ CLI子命令测试通过")
except Exception as e:
    print(f"✗ CLI测试失败: {e}")
    import traceback
    traceback.print_exc()

# ─── 清理 ───
print("\n" + "-" * 60)
print("清理临时文件...")
for f in ['cli_test.svg', 'cli_test.eps', 'test_edited.svg',
          'test_export.eps', 'test_export.pdf', 'test_export.ai', 'test_export_copy.svg']:
    if os.path.exists(f):
        os.remove(f)
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
print("✓ 清理完成")

print("\n" + "=" * 60)
print("所有测试完成!")
print("=" * 60)
