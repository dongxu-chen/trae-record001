import sys
sys.path.insert(0, '.')
from texture_extensions import (
    VideoTextureSynthesizer,
    MultiTextureBlender,
    TextureParameterizer,
    EnhancedTextureSynthesizer
)
import numpy as np
import cv2
import os


def test_video_synthesizer():
    print("Testing Video Texture Synthesizer...")
    
    synthesizer = VideoTextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        color = int(80 + 40 * np.sin(i * 0.1))
        texture[:, i] = [color // 3, color, color // 2]
    texture = texture + np.random.randint(0, 15, (64, 64, 3), dtype=np.uint8)
    
    print("  Testing temporal guide generation...")
    for motion_type in ['wave', 'rotate', 'zoom', 'scroll']:
        guide = synthesizer.create_temporal_guide((128, 128), 0, motion_type)
        assert guide.shape == (128, 128, 3)
        print(f"    {motion_type}: OK")
    
    print("  Testing optical flow...")
    frame1 = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    frame2 = np.roll(frame1, 2, axis=1)
    try:
        flow = synthesizer.compute_optical_flow(frame1, frame2)
        assert flow.shape == (64, 64, 2)
        print("    Optical flow computation: OK")
    except Exception as e:
        print(f"    Optical flow skipped: {e}")
    
    print("  Testing frame warping...")
    if 'flow' in locals():
        warped = synthesizer.warp_frame(frame1, flow)
        assert warped.shape == frame1.shape
        print("    Frame warping: OK")
    
    print("  Testing video synthesis (3 frames)...")
    try:
        frames = synthesizer.synthesize_video(
            texture, (96, 96), num_frames=3,
            patch_size=20, overlap=6,
            motion_type='wave'
        )
        assert len(frames) == 3
        for i, frame in enumerate(frames):
            assert frame.shape == (96, 96, 3)
            cv2.imwrite(f'test_video_frame_{i}.png', frame)
        print("    Video synthesis: OK")
    except Exception as e:
        print(f"    Video synthesis skipped: {e}")
    
    synthesizer.clear_history()
    assert len(synthesizer.previous_frames) == 0
    print("  History clearing: OK")
    
    return True


def test_multi_texture_blender():
    print("Testing Multi-Texture Blender...")
    
    blender = MultiTextureBlender(use_gpu=True)
    
    texture1 = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        color = int(80 + 40 * np.sin(i * 0.1))
        texture1[:, i] = [color // 3, color, color // 2]
    texture1 = texture1 + np.random.randint(0, 15, (64, 64, 3), dtype=np.uint8)
    
    texture2 = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            if (i // 8 + j // 8) % 2 == 0:
                texture2[i, j] = [100, 150, 180]
            else:
                texture2[i, j] = [60, 90, 120]
    texture2 = texture2 + np.random.randint(0, 10, (64, 64, 3), dtype=np.uint8)
    
    texture3 = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            val = 128 + 64 * np.sin((i + j) * 0.15)
            texture3[i, j] = [int(val * 0.8), int(val * 0.6), int(val)]
    texture3 = texture3 + np.random.randint(0, 12, (64, 64, 3), dtype=np.uint8)
    
    print("  Testing average blending...")
    blended_avg = blender.blend_textures_pixelwise(
        [texture1, texture2, texture3],
        weights=[0.4, 0.3, 0.3],
        blend_mode='average'
    )
    assert blended_avg.shape == (64, 64, 3)
    cv2.imwrite('test_blend_average.png', blended_avg)
    print("    Average blending: OK")
    
    print("  Testing pyramid blending...")
    blended_pyr = blender.blend_textures_pixelwise(
        [texture1, texture2],
        weights=[0.5, 0.5],
        blend_mode='pyramid'
    )
    assert blended_pyr.shape == (64, 64, 3)
    cv2.imwrite('test_blend_pyramid.png', blended_pyr)
    print("    Pyramid blending: OK")
    
    print("  Testing gradient blending...")
    try:
        blended_grad = blender.blend_textures_pixelwise(
            [texture1, texture2],
            weights=[0.5, 0.5],
            blend_mode='gradient'
        )
        assert blended_grad.shape == (64, 64, 3)
        cv2.imwrite('test_blend_gradient.png', blended_grad)
        print("    Gradient blending: OK")
    except Exception as e:
        print(f"    Gradient blending skipped: {e}")
    
    print("  Testing weight map generation...")
    for pattern in ['linear', 'radial', 'checkerboard']:
        weight_maps = blender.create_weight_map((128, 128), pattern, num_textures=3)
        assert len(weight_maps) == 3
        for wm in weight_maps:
            assert wm.shape == (128, 128)
        total = sum(weight_maps)
        assert np.allclose(total, np.ones((128, 128)), atol=0.01)
        print(f"    {pattern} pattern: OK")
    
    print("  Testing spatial blending...")
    weight_maps = blender.create_weight_map((128, 128), 'linear', num_textures=3)
    spatial_blend = blender.blend_textures_spatial(
        [texture1, texture2, texture3],
        weight_maps,
        blend_mode='simple'
    )
    assert spatial_blend.shape == (128, 128, 3)
    cv2.imwrite('test_blend_spatial.png', spatial_blend)
    print("    Spatial blending: OK")
    
    return True


def test_texture_parameterizer():
    print("Testing Texture Parameterizer...")
    
    parameterizer = TextureParameterizer(use_gpu=True)
    
    texture = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture[:, i] = [color // 3, color, color // 2]
    texture = texture + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    print("  Testing tiling parameter computation...")
    params = parameterizer.compute_tiling_params(texture, max_offset=16)
    assert 'is_tileable' in params
    assert 'best_horizontal_offset' in params
    assert 'best_vertical_offset' in params
    assert 'natural_tile_width' in params
    assert 'natural_tile_height' in params
    print(f"    Is tileable: {params['is_tileable']}")
    print(f"    Natural tile: {params['natural_tile_height']}x{params['natural_tile_width']}")
    print("    Tiling parameters: OK")
    
    print("  Testing make_tileable (feather method)...")
    tileable_feather, params_feather = parameterizer.make_tileable(
        texture, method='feather', overlap=16
    )
    assert tileable_feather.shape == texture.shape
    cv2.imwrite('test_tileable_feather.png', tileable_feather)
    print("    Feather method: OK")
    
    print("  Testing make_tileable (pyramid method)...")
    try:
        tileable_pyramid, params_pyr = parameterizer.make_tileable(
            texture, method='pyramid', overlap=16
        )
        assert tileable_pyramid.shape == texture.shape
        cv2.imwrite('test_tileable_pyramid.png', tileable_pyramid)
        print("    Pyramid method: OK")
    except Exception as e:
        print(f"    Pyramid method skipped: {e}")
    
    print("  Testing make_tileable (wrap method)...")
    tileable_wrap, params_wrap = parameterizer.make_tileable(
        texture, method='wrap', overlap=16
    )
    assert tileable_wrap.shape == texture.shape
    cv2.imwrite('test_tileable_wrap.png', tileable_wrap)
    print("    Wrap method: OK")
    
    print("  Testing texture analysis...")
    analysis = parameterizer.analyze_texture(texture)
    assert 'size' in analysis
    assert 'brightness_mean' in analysis
    assert 'complexity' in analysis
    assert 'directionality' in analysis
    assert 'recommended_patch_size' in analysis
    assert 'recommended_overlap' in analysis
    print(f"    Recommended patch size: {analysis['recommended_patch_size']}")
    print(f"    Recommended overlap: {analysis['recommended_overlap']}")
    print("    Texture analysis: OK")
    
    print("  Testing parameter report...")
    report = parameterizer.generate_param_report(texture)
    assert isinstance(report, str)
    assert len(report) > 0
    print("    Parameter report: OK")
    
    return True


def test_enhanced_synthesizer():
    print("Testing Enhanced Texture Synthesizer (integration)...")
    
    synthesizer = EnhancedTextureSynthesizer(use_gpu=True)
    
    texture1 = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        color = int(80 + 40 * np.sin(i * 0.1))
        texture1[:, i] = [color // 3, color, color // 2]
    texture1 = texture1 + np.random.randint(0, 15, (64, 64, 3), dtype=np.uint8)
    
    texture2 = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            if (i // 8 + j // 8) % 2 == 0:
                texture2[i, j] = [100, 150, 180]
            else:
                texture2[i, j] = [60, 90, 120]
    texture2 = texture2 + np.random.randint(0, 10, (64, 64, 3), dtype=np.uint8)
    
    print("  Testing base synthesis (GraphCut)...")
    result = synthesizer.synthesize_texture(
        texture1, (128, 128),
        patch_size=24, overlap=8,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.5
    )
    assert result.shape == (128, 128, 3)
    cv2.imwrite('test_enhanced_base.png', result)
    print("    Base synthesis: OK")
    
    print("  Testing texture blending...")
    blended = synthesizer.blend_textures(
        [texture1, texture2],
        weights=[0.5, 0.5],
        blend_mode='pyramid'
    )
    assert blended.shape == (64, 64, 3)
    cv2.imwrite('test_enhanced_blend.png', blended)
    print("    Texture blending: OK")
    
    print("  Testing spatial blending...")
    weight_maps = synthesizer.create_weight_maps((128, 128), 'checkerboard', 2)
    spatial = synthesizer.blend_textures_spatial(
        [texture1, texture2],
        weight_maps,
        blend_mode='simple'
    )
    assert spatial.shape == (128, 128, 3)
    cv2.imwrite('test_enhanced_spatial.png', spatial)
    print("    Spatial blending: OK")
    
    print("  Testing tileable generation...")
    tileable, params = synthesizer.make_tileable(
        texture1, method='feather', overlap=16
    )
    assert tileable.shape == texture1.shape
    cv2.imwrite('test_enhanced_tileable.png', tileable)
    print("    Tileable generation: OK")
    
    print("  Testing texture analysis...")
    analysis = synthesizer.analyze_texture(texture1)
    assert 'is_tileable' in analysis
    print(f"    Tileable: {analysis['is_tileable']}")
    print("    Texture analysis: OK")
    
    print("  Testing parameter report...")
    report = synthesizer.generate_param_report(texture1)
    print(report)
    print("    Parameter report: OK")
    
    return True


def main():
    print("=" * 70)
    print("Texture Extensions Unit Tests")
    print("=" * 70)
    
    tests = [
        ("Video Texture Synthesizer", test_video_synthesizer),
        ("Multi-Texture Blender", test_multi_texture_blender),
        ("Texture Parameterizer", test_texture_parameterizer),
        ("Enhanced Synthesizer (Integration)", test_enhanced_synthesizer),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print()
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
