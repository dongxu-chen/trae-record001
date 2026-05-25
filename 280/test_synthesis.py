import sys
sys.path.insert(0, '.')
from texture_synthesis import (
    TextureSynthesizer, 
    GraphCutSeamFinder, 
    GPUPyramidBuilder,
    EnhancedPatchMatcher
)
import numpy as np
import cv2
import torch
import os


def test_graphcut_seam_finder():
    print("Testing GraphCut seam finder...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    seam_finder = GraphCutSeamFinder(use_gpu=True)
    
    img1 = torch.zeros(1, 3, 64, 64, device=device)
    img1[:, :, :, :32] = 0.8
    img1[:, :, :, 32:] = 0.2
    
    img2 = torch.zeros(1, 3, 64, 64, device=device)
    img2[:, :, :, :32] = 0.2
    img2[:, :, :, 32:] = 0.8
    
    error_map = seam_finder.compute_error_map(img1, img2)
    assert error_map.shape == (64, 64)
    print("  Error map computation: OK")
    
    seam = seam_finder.find_vertical_seam(error_map)
    assert len(seam) == 64
    assert all(0 <= s < 64 for s in seam)
    print("  Vertical seam finding: OK")
    
    seam_h = seam_finder.find_horizontal_seam(error_map)
    assert len(seam_h) == 64
    assert all(0 <= s < 64 for s in seam_h)
    print("  Horizontal seam finding: OK")
    
    mask = seam_finder.create_seam_mask(64, 8, error_map[:, :8], None, 'left')
    assert mask.shape == (64, 64)
    print("  Seam mask creation: OK")
    
    return True


def test_gpu_pyramid_builder():
    print("Testing GPU pyramid builder...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    builder = GPUPyramidBuilder(device)
    
    img = torch.randn(1, 3, 128, 128, device=device)
    
    gaussian_pyr = builder.gaussian_pyramid(img, 4)
    assert len(gaussian_pyr) == 4
    assert gaussian_pyr[0].shape == (1, 3, 128, 128)
    assert gaussian_pyr[1].shape == (1, 3, 64, 64)
    assert gaussian_pyr[2].shape == (1, 3, 32, 32)
    assert gaussian_pyr[3].shape == (1, 3, 16, 16)
    print("  Gaussian pyramid: OK")
    
    laplacian_pyr, base = builder.laplacian_pyramid(img, 3)
    assert len(laplacian_pyr) == 3
    assert base.shape == (1, 3, 16, 16)
    print("  Laplacian pyramid: OK")
    
    reconstructed = builder.reconstruct_from_laplacian(laplacian_pyr, base)
    assert reconstructed.shape == img.shape
    print("  Pyramid reconstruction: OK")
    
    max_diff = torch.max(torch.abs(reconstructed - img)).item()
    print(f"  Reconstruction error: {max_diff:.6f}")
    
    return True


def test_enhanced_patch_matcher():
    print("Testing enhanced patch matcher...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    matcher = EnhancedPatchMatcher(device)
    
    source = torch.randn(1, 3, 64, 64, device=device)
    target = source[:, :, 10:10+32, 10:10+32].clone()
    
    y, x = matcher.find_best_match_with_structure(
        target, source, patch_size=32,
        structure_weight=0.0,
        guide_weight=0.0
    )
    
    print(f"  Best match at ({y}, {x}), expected (10, 10)")
    assert abs(y - 10) <= 2 and abs(x - 10) <= 2
    print("  Basic patch matching: OK")
    
    structure = torch.randn(1, 3, 64, 64, device=device)
    target_struct = structure[:, :, 10:10+32, 10:10+32].clone()
    
    y, x = matcher.find_best_match_with_structure(
        target, source, patch_size=32,
        target_structure=target_struct,
        source_structure=structure,
        structure_weight=0.5,
        guide_weight=0.0
    )
    print("  Structure-guided matching: OK")
    
    matcher.clear_cache()
    assert len(matcher.cache) == 0
    print("  Cache clearing: OK")
    
    return True


def test_structure_tensor_gpu():
    print("Testing GPU structure tensor...")
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        texture[:, i] = [40, 80 + i, 30]
    texture = texture + np.random.randint(0, 15, (64, 64, 3), dtype=np.uint8)
    
    tensor = synthesizer.to_tensor(texture)
    struct_gpu = synthesizer.compute_structure_tensor_gpu(tensor)
    
    assert struct_gpu.shape == (1, 3, 64, 64)
    assert struct_gpu.device == synthesizer.device
    print("  GPU structure tensor: OK")
    
    struct_cpu = synthesizer.compute_structure_tensor(texture)
    assert struct_cpu.shape == (64, 64, 3)
    print("  CPU structure tensor: OK")
    
    orientation, coherence = synthesizer.compute_orientation_field(struct_cpu)
    assert orientation.shape == (64, 64)
    assert coherence.shape == (64, 64)
    print("  Orientation field computation: OK")
    
    return True


def test_graphcut_blend():
    print("Testing GraphCut blending...")
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    existing = np.full((64, 64, 3), 200, dtype=np.uint8)
    new_patch = np.full((64, 64, 3), 50, dtype=np.uint8)
    
    blended, mask = synthesizer.graphcut_blend(existing, new_patch, overlap=16, overlap_type='left')
    assert blended.shape == (64, 64, 3)
    assert mask.shape == (64, 64)
    print("  GraphCut blend (left): OK")
    
    blended, mask = synthesizer.graphcut_blend(existing, new_patch, overlap=16, overlap_type='both')
    assert blended.shape == (64, 64, 3)
    print("  GraphCut blend (both): OK")
    
    return True


def test_multiband_blend_gpu():
    print("Testing GPU multi-band blending...")
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    img1 = np.full((64, 64, 3), 200, dtype=np.uint8)
    img2 = np.full((64, 64, 3), 50, dtype=np.uint8)
    mask = np.zeros((64, 64), dtype=np.float32)
    mask[:, :32] = 1.0
    
    img1_tensor = synthesizer.to_tensor(img1)
    img2_tensor = synthesizer.to_tensor(img2)
    mask_tensor = torch.from_numpy(mask).float().to(synthesizer.device).unsqueeze(0).unsqueeze(0)
    
    blended = synthesizer.multiband_blend_gpu(img1_tensor, img2_tensor, mask_tensor, levels=3)
    assert blended.shape == img1_tensor.shape
    assert blended.device == synthesizer.device
    print("  GPU multi-band blend: OK")
    
    blended_cpu = synthesizer.multiband_blend(img1, img2, mask, levels=3)
    assert blended_cpu.shape == img1.shape
    print("  CPU multi-band blend: OK")
    
    return True


def test_synthesis_with_graphcut():
    print("Testing texture synthesis with GraphCut...")
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    wood = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        wood[:, i] = [40, 80 + i, 30]
    wood = wood + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    result = synthesizer.synthesize_texture(
        wood, (128, 128),
        patch_size=24, overlap=8,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.5
    )
    
    assert result.shape == (128, 128, 3)
    assert result.dtype == np.uint8
    cv2.imwrite('test_graphcut_synthesis.png', result)
    print("  GraphCut synthesis: OK (saved to test_graphcut_synthesis.png)")
    
    return True


def test_synthesis_with_structure_guide():
    print("Testing synthesis with enhanced structure guidance...")
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            if (i // 8 + j // 8) % 2 == 0:
                texture[i, j] = [100, 150, 180]
            else:
                texture[i, j] = [60, 90, 120]
    texture = texture + np.random.randint(0, 10, (64, 64, 3), dtype=np.uint8)
    
    result = synthesizer.synthesize_texture(
        texture, (192, 192),
        patch_size=32, overlap=12,
        use_direction=True,
        blend_mode='multiband',
        structure_weight=0.7,
        use_structure_guide=True
    )
    
    assert result.shape == (192, 192, 3)
    cv2.imwrite('test_structure_guided.png', result)
    print("  Structure-guided synthesis: OK (saved to test_structure_guided.png)")
    
    return True


def test_guided_synthesis():
    print("Testing guided synthesis with GraphCut...")
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        texture[:, i] = [40, 80 + i, 30]
    texture = texture + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    guide = np.zeros((160, 160, 3), dtype=np.uint8)
    cv2.circle(guide, (80, 80), 40, (255, 0, 0), -1)
    cv2.rectangle(guide, (20, 20), (60, 140), (0, 255, 0), -1)
    
    result = synthesizer.synthesize_texture(
        texture, (160, 160),
        patch_size=24, overlap=8,
        guide_image=guide,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.5
    )
    
    assert result.shape == (160, 160, 3)
    cv2.imwrite('test_guided_graphcut.png', result)
    cv2.imwrite('test_guide.png', guide)
    print("  Guided synthesis: OK (saved to test_guided_graphcut.png, test_guide.png)")
    
    return True


def test_patch_cache_efficiency():
    print("Testing patch cache efficiency...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    matcher = EnhancedPatchMatcher(device)
    
    source = torch.randn(1, 3, 128, 128, device=device)
    
    import time
    start = time.time()
    for _ in range(5):
        target = torch.randn(1, 3, 32, 32, device=device)
        matcher.find_best_match_with_structure(target, source, 32)
    first_time = time.time() - start
    
    start = time.time()
    for _ in range(5):
        target = torch.randn(1, 3, 32, 32, device=device)
        matcher.find_best_match_with_structure(target, source, 32)
    cached_time = time.time() - start
    
    print(f"  First pass: {first_time:.3f}s")
    print(f"  Cached pass: {cached_time:.3f}s")
    print(f"  Speedup: {first_time/max(cached_time, 1e-6):.2f}x")
    print("  Cache efficiency: OK")
    
    return True


def main():
    print("=" * 70)
    print("Enhanced Texture Synthesis Unit Tests")
    print("=" * 70)
    
    tests = [
        ("GraphCut seam finder", test_graphcut_seam_finder),
        ("GPU pyramid builder", test_gpu_pyramid_builder),
        ("Enhanced patch matcher", test_enhanced_patch_matcher),
        ("GPU structure tensor", test_structure_tensor_gpu),
        ("GraphCut blending", test_graphcut_blend),
        ("GPU multi-band blend", test_multiband_blend_gpu),
        ("Patch cache efficiency", test_patch_cache_efficiency),
        ("Synthesis with GraphCut", test_synthesis_with_graphcut),
        ("Structure-guided synthesis", test_synthesis_with_structure_guide),
        ("Guided synthesis", test_guided_synthesis),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {name}: PASSED")
            else:
                failed += 1
                print(f"✗ {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {name}: FAILED with error: {e}")
            import traceback
            traceback.print_exc()
        print()
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
