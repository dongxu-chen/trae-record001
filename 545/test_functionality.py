import os
import sys
import numpy as np
import cv2
from tone_mapping import ToneMapper, ToneMappingOperator
from presets import PresetManager
from batch_processor import BatchProcessor


def create_test_hdr_image(width: int = 512, height: int = 384) -> np.ndarray:
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)

    hdr = np.zeros((height, width, 3), dtype=np.float32)

    sun_pos = (0.8, 0.2)
    sun_dist = np.sqrt((xx - sun_pos[0])**2 + (yy - sun_pos[1])**2)
    sun = np.exp(-sun_dist * 10) * 10.0

    sky = 0.5 + 0.5 * yy
    ground = 0.1 + 0.2 * (1 - yy)

    gradient = 0.5 + 0.5 * xx

    hdr[:, :, 0] = sun * 1.0 + sky * 0.6 + ground * 0.2 + gradient * 0.3
    hdr[:, :, 1] = sun * 0.9 + sky * 0.7 + ground * 0.3 + gradient * 0.4
    hdr[:, :, 2] = sun * 0.5 + sky * 1.0 + ground * 0.4 + gradient * 0.5

    return hdr


def test_tone_mapping():
    print("=" * 60)
    print("测试1: 色调映射核心功能")
    print("=" * 60)

    hdr_img = create_test_hdr_image()
    print(f"测试HDR图像形状: {hdr_img.shape}, 范围: [{hdr_img.min():.2f}, {hdr_img.max():.2f}]")

    tonemapper = ToneMapper(use_gpu=False)

    for op in ToneMappingOperator:
        print(f"\n  测试算子: {op.value}")
        try:
            result = tonemapper.process(hdr_img, op)
            print(f"    输出形状: {result.shape}, dtype: {result.dtype}")
            print(f"    输出范围: [{result.min()}, {result.max()}]")
            assert result.dtype == np.uint8, "输出类型应为uint8"
            assert result.min() >= 0 and result.max() <= 255, "输出范围应在0-255"
            print("    ✓ 通过")
        except Exception as e:
            print(f"    ✗ 失败: {e}")
            return False

    print("\n✓ 所有色调映射算子测试通过")
    return True


def test_tone_mapping_params():
    print("\n" + "=" * 60)
    print("测试2: 参数调节功能")
    print("=" * 60)

    hdr_img = create_test_hdr_image()
    tonemapper = ToneMapper(use_gpu=False)

    op = ToneMappingOperator.REINHARD
    print(f"\n  测试算子: {op.value}")

    params = tonemapper.get_params(op)
    print(f"  默认参数: {params}")

    tonemapper.set_param(op, 'intensity', 2.0)
    tonemapper.set_param(op, 'gamma', 1.8)

    new_params = tonemapper.get_params(op)
    print(f"  修改后参数: {new_params}")
    assert new_params['intensity'] == 2.0, "参数设置失败"
    assert new_params['gamma'] == 1.8, "参数设置失败"

    result1 = tonemapper.process(hdr_img, op)
    mean1 = result1.mean()

    tonemapper.set_param(op, 'intensity', -2.0)
    result2 = tonemapper.process(hdr_img, op)
    mean2 = result2.mean()

    print(f"  高强度均值: {mean1:.2f}, 低强度均值: {mean2:.2f}")
    assert mean1 > mean2, "参数变化应影响输出结果"

    print("  ✓ 参数调节测试通过")
    return True


def test_preset_manager():
    print("\n" + "=" * 60)
    print("测试3: 预设管理功能")
    print("=" * 60)

    preset_file = "test_presets.json"
    if os.path.exists(preset_file):
        os.remove(preset_file)

    pm = PresetManager(preset_file=preset_file)

    preset_names = pm.get_preset_names()
    print(f"  默认预设数量: {len(preset_names)}")
    assert len(preset_names) > 0, "应有默认预设"

    for name in preset_names:
        preset = pm.load_preset(name)
        assert preset is not None, f"预设 {name} 加载失败"
        print(f"    - {name}: {preset['operator'].value}")

    test_params = {
        'intensity': 1.5,
        'light_adapt': 0.7,
        'color_adapt': 0.3,
        'gamma': 2.0
    }
    pm.save_preset("Test Preset", ToneMappingOperator.REINHARD, test_params)

    loaded = pm.load_preset("Test Preset")
    assert loaded is not None, "保存的预设加载失败"
    assert loaded['operator'] == ToneMappingOperator.REINHARD
    assert loaded['params']['intensity'] == 1.5
    print(f"\n  保存自定义预设 ✓")

    pm.delete_preset("Test Preset")
    assert pm.load_preset("Test Preset") is None, "预设删除失败"
    print(f"  删除自定义预设 ✓")

    export_file = "exported_presets.json"
    assert pm.export_presets(export_file), "导出失败"
    print(f"  导出预设 ✓")

    new_pm = PresetManager(preset_file="new_presets.json")
    assert new_pm.import_presets(export_file, merge=False), "导入失败"
    assert len(new_pm.get_preset_names()) == len(preset_names), "导入预设数量不匹配"
    print(f"  导入预设 ✓")

    for f in [preset_file, export_file, "new_presets.json"]:
        if os.path.exists(f):
            os.remove(f)

    print("\n✓ 预设管理测试通过")
    return True


def test_batch_processor():
    print("\n" + "=" * 60)
    print("测试4: 批量处理功能")
    print("=" * 60)

    test_dir = "test_batch"
    output_dir = "test_batch_output"
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    for i in range(3):
        hdr = create_test_hdr_image(256, 192)
        cv2.imwrite(os.path.join(test_dir, f"test_{i}.hdr"), hdr)
    print(f"  创建了3个测试HDR文件")

    bp = BatchProcessor(use_gpu=False, max_workers=2)

    files = bp.find_hdr_files(test_dir, recursive=False)
    print(f"  找到HDR文件: {len(files)} 个")
    assert len(files) == 3, "应找到3个HDR文件"

    params = bp.tonemapper.get_params(ToneMappingOperator.ACES)
    bp.set_operator_params(ToneMappingOperator.ACES, params)

    print(f"  开始批量处理...")
    results = bp.process_batch(
        files,
        output_dir,
        ToneMappingOperator.ACES,
        output_format='png'
    )

    success_count = sum(1 for r in results if r['success'])
    print(f"  处理结果: 成功 {success_count}/{len(results)}")

    assert success_count == len(results), "所有文件应处理成功"

    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        output_file = os.path.join(output_dir, f"{name}_aces.png")
        assert os.path.exists(output_file), f"输出文件不存在: {output_file}"
    print(f"  所有输出文件已生成 ✓")

    import shutil
    shutil.rmtree(test_dir)
    shutil.rmtree(output_dir)

    print("\n✓ 批量处理测试通过")
    return True


def test_file_io():
    print("\n" + "=" * 60)
    print("测试5: HDR文件读写")
    print("=" * 60)

    hdr_img = create_test_hdr_image()
    test_file = "test_hdr.hdr"

    cv2.imwrite(test_file, hdr_img)
    print(f"  写入HDR文件: {test_file}")

    loaded = ToneMapper.load_hdr(test_file)
    print(f"  读取HDR文件成功，形状: {loaded.shape}")
    assert loaded.shape == hdr_img.shape, "形状不匹配"
    assert loaded.dtype == np.float32, "类型应为float32"

    output_file = "test_output.png"
    tonemapper = ToneMapper()
    result = tonemapper.process(loaded, ToneMappingOperator.REINHARD)
    ToneMapper.save_ldr(output_file, result)
    print(f"  保存LDR文件: {output_file} ✓")

    for f in [test_file, output_file]:
        if os.path.exists(f):
            os.remove(f)

    print("\n✓ 文件读写测试通过")
    return True


def main():
    print("\n" + "=" * 60)
    print("HDR Tone Mapping Tool - 功能测试")
    print("=" * 60)

    tests = [
        ("色调映射核心功能", test_tone_mapping),
        ("参数调节功能", test_tone_mapping_params),
        ("预设管理功能", test_preset_manager),
        ("批量处理功能", test_batch_processor),
        ("文件读写功能", test_file_io),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ 测试 {test_name} 发生异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if os.path.exists("presets.json"):
        os.remove("presets.json")
    if os.path.exists("check_env.py"):
        os.remove("check_env.py")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
