import cv2
import numpy as np
from texture_extensions import EnhancedTextureSynthesizer


def example_video_synthesis():
    print("Example 1: Video Texture Synthesis")
    print("-" * 60)
    
    synthesizer = EnhancedTextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture[:, i] = [color // 3, color, color // 2]
    texture = texture + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    cv2.imwrite('example_video_input.png', texture)
    print("  Saved: example_video_input.png")
    
    motion_types = ['wave', 'rotate', 'zoom', 'scroll']
    
    for motion_type in motion_types:
        print(f"  Generating {motion_type} motion video (10 frames)...")
        try:
            frames = synthesizer.synthesize_video(
                texture, (160, 160), num_frames=10,
                patch_size=24, overlap=8,
                motion_type=motion_type,
                output_path=f'example_video_{motion_type}.mp4'
            )
            
            for i, frame in enumerate(frames[:3]):
                cv2.imwrite(f'example_video_{motion_type}_frame_{i:03d}.png', frame)
            
            print(f"    Saved: example_video_{motion_type}.mp4")
        except Exception as e:
            print(f"    Failed: {e}")
    
    print()


def example_multi_texture_blending():
    print("Example 2: Multi-Texture Blending")
    print("-" * 60)
    
    synthesizer = EnhancedTextureSynthesizer(use_gpu=True)
    
    texture1 = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture1[:, i] = [color // 3, color, color // 2]
    texture1 = texture1 + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    texture2 = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            if (i // 8 + j // 8) % 2 == 0:
                texture2[i, j] = [100, 150, 180]
            else:
                texture2[i, j] = [60, 90, 120]
    texture2 = texture2 + np.random.randint(0, 10, (80, 80, 3), dtype=np.uint8)
    
    texture3 = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        for j in range(80):
            val = 128 + 64 * np.sin((i + j) * 0.15)
            texture3[i, j] = [int(val * 0.8), int(val * 0.6), int(val)]
    texture3 = texture3 + np.random.randint(0, 12, (80, 80, 3), dtype=np.uint8)
    
    cv2.imwrite('example_blend_input1.png', texture1)
    cv2.imwrite('example_blend_input2.png', texture2)
    cv2.imwrite('example_blend_input3.png', texture3)
    print("  Saved input textures")
    
    print("  Testing different blend modes...")
    
    for mode in ['average', 'pyramid', 'gradient']:
        try:
            blended = synthesizer.blend_textures(
                [texture1, texture2, texture3],
                weights=[0.4, 0.3, 0.3],
                blend_mode=mode
            )
            cv2.imwrite(f'example_blend_{mode}.png', blended)
            print(f"    {mode} blending: OK")
        except Exception as e:
            print(f"    {mode} blending: {e}")
    
    print()
    print("  Testing spatial blending patterns...")
    
    for pattern in ['linear', 'radial', 'checkerboard']:
        weight_maps = synthesizer.create_weight_maps((200, 200), pattern, num_textures=3)
        spatial = synthesizer.blend_textures_spatial(
            [texture1, texture2, texture3],
            weight_maps,
            blend_mode='simple'
        )
        cv2.imwrite(f'example_spatial_{pattern}.png', spatial)
        
        for i, wm in enumerate(weight_maps):
            wm_viz = (wm * 255).astype(np.uint8)
            cv2.imwrite(f'example_weight_{pattern}_{i}.png', wm_viz)
        
        print(f"    {pattern} pattern: OK")
    
    print()


def example_texture_parameterization():
    print("Example 3: Texture Parameterization and Tiling")
    print("-" * 60)
    
    synthesizer = EnhancedTextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture[:, i] = [color // 3, color, color // 2]
    texture = texture + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    cv2.imwrite('example_param_input.png', texture)
    print("  Saved: example_param_input.png")
    
    print("  Running texture analysis...")
    report = synthesizer.generate_param_report(texture)
    print(report)
    print()
    
    print("  Testing tileable texture generation...")
    
    for method in ['feather', 'pyramid', 'wrap']:
        try:
            tileable, params = synthesizer.make_tileable(
                texture, method=method, overlap=16
            )
            cv2.imwrite(f'example_tileable_{method}.png', tileable)
            print(f"    {method} method: OK")
            
            tiled_2x2 = np.zeros((160, 160, 3), dtype=np.uint8)
            tiled_2x2[:80, :80] = tileable
            tiled_2x2[:80, 80:] = tileable
            tiled_2x2[80:, :80] = tileable
            tiled_2x2[80:, 80:] = tileable
            cv2.imwrite(f'example_tiled_{method}_2x2.png', tiled_2x2)
            print(f"      2x2 tiling: OK")
        except Exception as e:
            print(f"    {method} method: {e}")
    
    print()


def example_auto_parameter_recommendation():
    print("Example 4: Automatic Parameter Recommendations")
    print("-" * 60)
    
    synthesizer = EnhancedTextureSynthesizer(use_gpu=True)
    
    textures = []
    
    texture_simple = np.zeros((64, 64, 3), dtype=np.uint8)
    texture_simple[:] = [100, 150, 100]
    texture_simple = texture_simple + np.random.randint(0, 10, (64, 64, 3), dtype=np.uint8)
    textures.append(("simple", texture_simple))
    
    texture_wood = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture_wood[:, i] = [color // 3, color, color // 2]
    texture_wood = texture_wood + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    textures.append(("wood", texture_wood))
    
    texture_complex = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    textures.append(("complex", texture_complex))
    
    for name, tex in textures:
        analysis = synthesizer.analyze_texture(tex)
        print(f"  {name} texture:")
        print(f"    Size: {analysis['size'][0]}x{analysis['size'][1]}")
        print(f"    Complexity: {analysis['complexity']:.2f}")
        print(f"    Directionality: {analysis['directionality']:.3f}")
        print(f"    Recommended patch size: {analysis['recommended_patch_size']}")
        print(f"    Recommended overlap: {analysis['recommended_overlap']}")
        print()
        
        result = synthesizer.synthesize_texture(
            tex, (256, 256),
            patch_size=analysis['recommended_patch_size'],
            overlap=analysis['recommended_overlap'],
            use_direction=True,
            blend_mode='graphcut',
            structure_weight=0.5 if analysis['directionality'] > 0.1 else 0.0
        )
        cv2.imwrite(f'example_auto_{name}.png', result)
        print(f"    Synthesized with auto params: OK")
        print()
    
    print()


def example_blended_synthesis_workflow():
    print("Example 5: Complete Workflow - Blend then Synthesize")
    print("-" * 60)
    
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
    
    print("  Step 1: Blend source textures...")
    blended_base = synthesizer.blend_textures(
        [texture1, texture2],
        weights=[0.5, 0.5],
        blend_mode='pyramid'
    )
    cv2.imwrite('example_workflow_blended.png', blended_base)
    print("    Blended base texture: OK")
    
    print("  Step 2: Analyze blended texture...")
    analysis = synthesizer.analyze_texture(blended_base)
    print(f"    Recommended patch size: {analysis['recommended_patch_size']}")
    print(f"    Recommended overlap: {analysis['recommended_overlap']}")
    
    print("  Step 3: Synthesize large texture...")
    result = synthesizer.synthesize_texture(
        blended_base, (384, 384),
        patch_size=analysis['recommended_patch_size'],
        overlap=analysis['recommended_overlap'],
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.5
    )
    cv2.imwrite('example_workflow_final.png', result)
    print("    Final synthesized texture: OK")
    
    print("  Step 4: Make result tileable...")
    tileable, params = synthesizer.make_tileable(result, method='feather', overlap=32)
    cv2.imwrite('example_workflow_tileable.png', tileable)
    print(f"    Tileable texture: OK (tileable: {params['is_tileable']})")
    
    print()


if __name__ == '__main__':
    print("=" * 70)
    print("Texture Synthesis Extensions Examples")
    print("=" * 70)
    print()
    
    example_multi_texture_blending()
    example_texture_parameterization()
    example_auto_parameter_recommendation()
    example_blended_synthesis_workflow()
    example_video_synthesis()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print()
    print("Check the output files:")
    print("  - Blended textures: example_blend_*.png")
    print("  - Spatial blends: example_spatial_*.png")
    print("  - Tileable textures: example_tileable_*.png")
    print("  - Auto-parameterized: example_auto_*.png")
    print("  - Workflow outputs: example_workflow_*.png")
    print("  - Video frames: example_video_*.mp4")
    print()
    print("New Features Summary:")
    print("  ✓ Video synthesis with temporal consistency")
    print("  ✓ Multi-texture blending (3 modes)")
    print("  ✓ Spatial blending with weight maps (3 patterns)")
    print("  ✓ Texture analysis and parameter recommendations")
    print("  ✓ Automatic tileable texture generation")
