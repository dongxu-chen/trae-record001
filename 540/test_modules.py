#!/usr/bin/env python3
import sys
import os
import numpy as np
import cv2

print("开始模块测试...")

# ─── 测试 VectorEditor ───
print("\n=== 测试 VectorEditor ===")
try:
    from vector_editor import VectorEditor

    svg_path = 'simple_output.svg'
    if not os.path.exists(svg_path):
        from raster_to_vector import RasterToVector
        h, w = 200, 300
        img = np.ones((h, w, 3), dtype=np.uint8) * 255
        cv2.circle(img, (100, 100), 50, (255, 100, 100), -1)
        cv2.rectangle(img, (180, 50), (260, 150), (100, 200, 100), -1)
        cv2.imwrite('editor_test.png', cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        RasterToVector('editor_test.png').convert(svg_path, n_colors=4)

    editor = VectorEditor(svg_path)
    info = editor.get_edit_info()
    print(f"  加载: {info['total_paths']} 路径, {info['total_anchors']} 锚点")

    # 列出路径
    for i, p in enumerate(editor.paths[:3]):
        print(f"    路径{i}: {len(p['points'])} 锚点")

    # 移动锚点
    if info['total_paths'] > 0 and info['total_anchors'] > 0:
        first_pt = editor.paths[0]['points'][0].copy()
        editor.move_anchor(0, 0, first_pt[0] + 5, first_pt[1] + 5)
        new_pt = editor.paths[0]['points'][0]
        print(f"  ✓ 移动锚点: ({first_pt[0]:.1f},{first_pt[1]:.1f}) -> ({new_pt[0]:.1f},{new_pt[1]:.1f})")

    # 平滑
    if info['total_paths'] > 0:
        editor.smooth_path(0, iterations=3, factor=0.5)
        print("  ✓ 平滑路径0")

    # 简化
    if info['total_paths'] > 0:
        before = len(editor.paths[0]['points'])
        editor.simplify_path(0, tolerance=3.0)
        after = len(editor.paths[0]['points'])
        print(f"  ✓ 简化路径0: {before} -> {after} 锚点")

    # 添加/删除锚点
    if info['total_paths'] > 0 and len(editor.paths[0]['points']) > 1:
        before = len(editor.paths[0]['points'])
        editor.add_anchor(0, 0, 999, 999)
        print(f"  ✓ 添加锚点: {before} -> {len(editor.paths[0]['points'])}")
        editor.remove_anchor(0, 0)
        print(f"  ✓ 删除锚点: -> {len(editor.paths[0]['points'])}")

    # Undo
    editor.undo()
    print(f"  ✓ 撤销操作")

    # 变换
    if info['total_paths'] > 0:
        editor.transform_path(0, translate=(10, 10), scale=(1.1, 1.1), rotate=5)
        print("  ✓ 变换路径0")

    # 修改颜色
    if info['total_paths'] > 0:
        editor.set_path_color(0, fill=(255, 0, 0), stroke=(200, 0, 0))
        print(f"  ✓ 修改颜色: fill={editor.paths[0]['fill']}")

    # 保存
    editor.save_svg('test_edited.svg')
    print("  ✓ 保存编辑结果")

    # 重新加载验证
    editor2 = VectorEditor('test_edited.svg')
    info2 = editor2.get_edit_info()
    print(f"  ✓ 重新加载验证: {info2['total_paths']} 路径, {info2['total_anchors']} 锚点")

    print("✓ VectorEditor 测试通过")
except Exception as e:
    print(f"✗ VectorEditor 测试失败: {e}")
    import traceback
    traceback.print_exc()

# ─── 测试 FormatExporter ───
print("\n=== 测试 FormatExporter ===")
try:
    from format_exporter import FormatExporter

    svg_source = 'simple_output.svg'
    if not os.path.exists(svg_source):
        from raster_to_vector import RasterToVector
        RasterToVector('editor_test.png').convert(svg_source, n_colors=4)

    exporter = FormatExporter(svg_source)

    # EPS
    eps_path = 'test_export.eps'
    exporter.export(eps_path, format='eps')
    assert os.path.exists(eps_path)
    with open(eps_path, 'r', encoding='latin-1') as f:
        header = f.read(100)
    assert '%!PS-Adobe' in header
    print(f"  ✓ EPS导出成功 ({os.path.getsize(eps_path)} bytes)")

    # PDF
    pdf_path = 'test_export.pdf'
    try:
        exporter.export(pdf_path, format='pdf')
        assert os.path.exists(pdf_path)
        with open(pdf_path, 'rb') as f:
            header = f.read(10)
        assert header.startswith(b'%PDF')
        print(f"  ✓ PDF导出成功 ({os.path.getsize(pdf_path)} bytes)")
    except ImportError:
        print("  ⚠ PDF导出跳过 (需要cairosvg)")

    # AI
    ai_path = 'test_export.ai'
    exporter.export(ai_path, format='ai')
    assert os.path.exists(ai_path)
    with open(ai_path, 'r', encoding='latin-1') as f:
        content = f.read(500)
    assert '%!PS-Adobe' in content
    assert 'AI3_ReadAI8_Prolog' in content
    print(f"  ✓ AI导出成功 ({os.path.getsize(ai_path)} bytes)")

    print("✓ FormatExporter 测试通过")
except Exception as e:
    print(f"✗ FormatExporter 测试失败: {e}")
    import traceback
    traceback.print_exc()

# ─── 测试 BatchProcessor ───
print("\n=== 测试 BatchProcessor ===")
try:
    import shutil
    from batch_processor import BatchProcessor

    test_dir = 'test_batch_in'
    out_dir = 'test_batch_out'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(test_dir, exist_ok=True)

    for i in range(3):
        h, w = 150, 200
        img = np.ones((h, w, 3), dtype=np.uint8) * 240
        cv2.circle(img, (60 + i * 30, 75), 30 + i * 5, (255 - i * 50, 100 + i * 30, 100), -1)
        cv2.imwrite(os.path.join(test_dir, f'img_{i}.png'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    processor = BatchProcessor(test_dir, out_dir, max_workers=1)
    results = processor.run(convert_kwargs={'n_colors': 4, 'edge_aware_quant': False})

    summary = processor.get_summary()
    print(f"  总计: {summary['total']}, 成功: {summary['success']}, 失败: {summary['failed']}")
    print(f"  总轮廓数: {summary['total_contours']}")

    assert summary['success'] == 3
    print("✓ BatchProcessor 测试通过")

    shutil.rmtree(test_dir)
    shutil.rmtree(out_dir)
except Exception as e:
    print(f"✗ BatchProcessor 测试失败: {e}")
    import traceback
    traceback.print_exc()

# ─── 清理 ───
for f in ['editor_test.png', 'test_edited.svg', 'test_export.eps', 'test_export.pdf', 'test_export.ai']:
    if os.path.exists(f):
        os.remove(f)

print("\n" + "=" * 50)
print("所有模块测试完成!")
print("=" * 50)
