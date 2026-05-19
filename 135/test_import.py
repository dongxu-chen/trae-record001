import sys
sys.path.insert(0, 'd:\\Trae\\project\\record001\\135')

print("Testing imports...")

try:
    from cd_tool.models import UNet, DeepLabV3Plus
    print("✓ Models imported successfully")
except Exception as e:
    print(f"✗ Models import failed: {e}")

try:
    from cd_tool.utils import DifferenceCalculator, ChangeSegmenter, Evaluator
    print("✓ Utils imported successfully")
except Exception as e:
    print(f"✗ Utils import failed: {e}")

try:
    from cd_tool.data import ChangeDetectionDataset, get_transforms
    print("✓ Data imported successfully")
except Exception as e:
    print(f"✗ Data import failed: {e}")

print("\nTesting basic functionality...")

try:
    import torch
    model = UNet(n_channels=6, n_classes=1)
    x = torch.randn(1, 6, 256, 256)
    output = model(x)
    print(f"✓ UNet forward pass successful - output shape: {output.shape}")
except Exception as e:
    print(f"✗ UNet test failed: {e}")

try:
    import numpy as np
    diff_calc = DifferenceCalculator(method='cva')
    img1 = np.random.rand(256, 256, 3)
    img2 = np.random.rand(256, 256, 3)
    diff = diff_calc.compute(img1, img2)
    print(f"✓ Difference calculation successful - diff shape: {diff.shape}")
except Exception as e:
    print(f"✗ Difference calculator test failed: {e}")

try:
    evaluator = Evaluator()
    pred = np.random.rand(100, 100)
    target = np.random.randint(0, 2, (100, 100))
    evaluator.add_batch(pred, target)
    metrics = evaluator.get_metrics()
    print(f"✓ Evaluation successful - IoU: {metrics['IoU']:.4f}, F1: {metrics['F1']:.4f}")
except Exception as e:
    print(f"✗ Evaluation test failed: {e}")

print("\nAll tests completed!")
