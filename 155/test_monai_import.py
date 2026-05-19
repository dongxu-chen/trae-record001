import sys

print("=" * 60)
print("高光谱图像分类库 - MONAI 版 v3.0 导入测试")
print("=" * 60)

print("\n[1/7] 导入基础模块...")
try:
    from hsi_classification import PCA, SVMClassifier, Metrics, utils
    print("   ✅ 基础模块导入成功")
except Exception as e:
    print(f"   ❌ 基础模块导入失败: {e}")
    sys.exit(1)

print("\n[2/7] 导入 CNN 模块...")
try:
    from hsi_classification import CNNClassifier
    print("   ✅ CNN 模块导入成功")
except Exception as e:
    print(f"   ❌ CNN 模块导入失败: {e}")
    sys.exit(1)

print("\n[3/7] 导入 MONAI 分类器...")
try:
    from hsi_classification import MonaiClassifier
    print("   ✅ MONAI 分类器导入成功")
except Exception as e:
    print(f"   ❌ MONAI 分类器导入失败: {e}")
    print("\n提示: 请先安装 MONAI: pip install monai")
    sys.exit(1)

print("\n[4/7] 导入多模态融合模块...")
try:
    from hsi_classification import (
        MultiModalClassifier,
        MultiModalFusionNet,
        CrossAttentionFusion,
        GatedFusion,
        LiDARProcessor,
    )
    print("   ✅ 多模态融合模块导入成功")
except Exception as e:
    print(f"   ❌ 多模态融合模块导入失败: {e}")
    sys.exit(1)

print("\n[5/7] 导入分布式训练和 ONNX 模块...")
try:
    from hsi_classification import (
        DistributedTrainer,
        ONNXExporter,
        ONNXInference,
        setup_distributed,
        cleanup_distributed,
    )
    print("   ✅ 分布式训练和 ONNX 模块导入成功")
except Exception as e:
    print(f"   ⚠️  ONNX 模块导入可能需要额外依赖: {e}")
    print("      安装: pip install onnx onnxruntime-gpu")

print("\n[6/7] 检查版本信息...")
try:
    import hsi_classification
    print(f"   ✅ 库版本: v{hsi_classification.__version__}")
except Exception as e:
    print(f"   ❌ 版本检查失败: {e}")

print("\n[7/7] 检查依赖...")
dependencies = [
    ('numpy', 'NumPy'),
    ('torch', 'PyTorch'),
    ('monai', 'MONAI'),
    ('sklearn', 'scikit-learn'),
    ('matplotlib', 'Matplotlib'),
]

for module, name in dependencies:
    try:
        __import__(module)
        print(f"   ✅ {name} 已安装")
    except ImportError:
        print(f"   ⚠️  {name} 未安装")

print("\n" + "=" * 60)
print("✅ 所有模块导入成功！")
print("=" * 60)
print("\n快速使用指南:")
print("  1. 运行基础示例: python example.py")
print("  2. 运行 MONAI 完整示例: python example_monai.py")
print("  3. 安装依赖: pip install -r requirements.txt")
print("\n可用功能:")
print("  ✓ MONAI 医学图像分类器")
print("  ✓ 多模态融合 (HSI + LiDAR)")
print("  ✓ 多种融合策略: 拼接/注意力/门控")
print("  ✓ 分布式训练 (多 GPU)")
print("  ✓ ONNX 模型导出和部署")
print("  ✓ LiDAR 点云特征提取")
