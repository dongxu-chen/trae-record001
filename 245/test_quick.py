import os
import sys
import numpy as np
import torch
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.model import create_model


def test_model_forward():
    print("Testing RCAN model forward pass...")
    
    config = {
        'scale': 4,
        'num_channels': 1,
        'num_features': 32,
        'num_groups': 3,
        'num_blocks': 5,
        'reduction': 16
    }
    
    model = create_model(config)
    
    batch_size = 1
    h, w = 64, 64
    input_tensor = torch.randn(batch_size, 1, h, w)
    
    with torch.no_grad():
        output = model(input_tensor)
    
    expected_h = h * config['scale']
    expected_w = w * config['scale']
    
    assert output.shape == (batch_size, 1, expected_h, expected_w), \
        f"Output shape mismatch: {output.shape} vs expected ({batch_size}, 1, {expected_h}, {expected_w})"
    
    print(f"  Input shape: {input_tensor.shape}")
    print(f"  Output shape: {output.shape}")
    print("  Model forward pass: PASSED")
    return True


def test_data_augmentation():
    print("\nTesting data augmentation...")
    
    from src.dataset import FLIRDataset
    
    test_img = np.random.randint(0, 256, (200, 200), dtype=np.uint8)
    os.makedirs('data/test_temp', exist_ok=True)
    cv2.imwrite('data/test_temp/test.png', test_img)
    
    dataset = FLIRDataset(
        root_dir='data/test_temp',
        scale=4,
        patch_size=64,
        is_train=True
    )
    
    lr, hr = dataset[0]
    print(f"  LR patch shape: {lr.shape}")
    print(f"  HR patch shape: {hr.shape}")
    print("  Data augmentation: PASSED")
    
    import shutil
    shutil.rmtree('data/test_temp')
    return True


def test_metrics():
    print("\nTesting PSNR and SSIM metrics...")
    
    from src.utils import calculate_psnr, calculate_ssim
    
    img1 = np.random.rand(1, 100, 100)
    img2 = img1 + 0.01 * np.random.randn(1, 100, 100)
    
    psnr = calculate_psnr(img1, img2)
    ssim = calculate_ssim(img1, img2)
    
    print(f"  PSNR: {psnr:.4f} dB")
    print(f"  SSIM: {ssim:.4f}")
    print("  Metrics calculation: PASSED")
    return True


def main():
    print("=" * 60)
    print("RCAN Infrared Super-Resolution - Quick Test")
    print("=" * 60)
    
    all_passed = True
    
    try:
        test_model_forward()
    except Exception as e:
        print(f"  Model forward pass: FAILED - {e}")
        all_passed = False
    
    try:
        test_data_augmentation()
    except Exception as e:
        print(f"  Data augmentation: FAILED - {e}")
        all_passed = False
    
    try:
        test_metrics()
    except Exception as e:
        print(f"  Metrics calculation: FAILED - {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")
    print("=" * 60)


if __name__ == '__main__':
    main()
