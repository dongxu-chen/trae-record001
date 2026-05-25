import cv2
import numpy as np
from texture_synthesis import TextureSynthesizer, GraphCutSeamFinder, GPUPyramidBuilder
import torch


def example_graphcut_vs_feather():
    print("Example 1: GraphCut vs Feather Blending Comparison")
    print("-" * 60)
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        color = int(100 + 50 * np.sin(i * 0.05))
        texture[:, i] = [color // 2, color, color // 3]
    texture = texture + np.random.randint(0, 20, (100, 100, 3), dtype=np.uint8)
    
    print("  Synthesizing with GraphCut blending...")
    result_graphcut = synthesizer.synthesize_texture(
        texture, output_size=(256, 256),
        patch_size=32, overlap=10,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.7
    )
    cv2.imwrite('example_graphcut.png', result_graphcut)
    print("  Saved: example_graphcut.png")
    
    print("  Synthesizing with feather blending...")
    result_feather = synthesizer.synthesize_texture(
        texture, output_size=(256, 256),
        patch_size=32, overlap=10,
        use_direction=True,
        blend_mode='feather',
        structure_weight=0.7
    )
    cv2.imwrite('example_feather.png', result_feather)
    print("  Saved: example_feather.png")
    
    print("  Synthesizing with multiband blending...")
    result_multiband = synthesizer.synthesize_texture(
        texture, output_size=(256, 256),
        patch_size=32, overlap=10,
        use_direction=True,
        blend_mode='multiband',
        structure_weight=0.7
    )
    cv2.imwrite('example_multiband.png', result_multiband)
    print("  Saved: example_multiband.png")
    print()


def example_directional_texture_preservation():
    print("Example 2: Directional Texture Preservation (Wood Grain)")
    print("-" * 60)
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    wood = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        for j in range(80):
            wave = int(5 * np.sin((i + j) * 0.1))
            wood[j, i] = [max(20, color // 3 + wave), 
                          max(40, color + wave), 
                          max(30, color // 2 + wave)]
    
    wood = wood + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    cv2.imwrite('example_wood_input.png', wood)
    print("  Saved: example_wood_input.png")
    
    print("  With structure tensor guidance (structure_weight=0.7)...")
    result_with_struct = synthesizer.synthesize_texture(
        wood, (256, 256),
        patch_size=24, overlap=8,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.7,
        use_structure_guide=True
    )
    cv2.imwrite('example_wood_with_struct.png', result_with_struct)
    print("  Saved: example_wood_with_struct.png")
    
    print("  Without structure tensor guidance...")
    result_without_struct = synthesizer.synthesize_texture(
        wood, (256, 256),
        patch_size=24, overlap=8,
        use_direction=False,
        blend_mode='graphcut',
        structure_weight=0.0,
        use_structure_guide=False
    )
    cv2.imwrite('example_wood_without_struct.png', result_without_struct)
    print("  Saved: example_wood_without_struct.png")
    print()


def example_weave_pattern():
    print("Example 3: Weave Pattern with GraphCut")
    print("-" * 60)
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    weave = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            if (i // 8 + j // 8) % 2 == 0:
                weave[i, j] = [100, 150, 180]
            else:
                weave[i, j] = [60, 90, 120]
    
    for i in range(64):
        for j in range(64):
            if i % 8 == 0 or j % 8 == 0:
                weave[i, j] = [int(c * 0.8) for c in weave[i, j]]
    
    weave = weave + np.random.randint(0, 10, (64, 64, 3), dtype=np.uint8)
    cv2.imwrite('example_weave_input.png', weave)
    print("  Saved: example_weave_input.png")
    
    print("  Synthesizing large weave pattern (512x512)...")
    result = synthesizer.synthesize_texture(
        weave, (512, 512),
        patch_size=48, overlap=16,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.5
    )
    cv2.imwrite('example_weave_large.png', result)
    print("  Saved: example_weave_large.png")
    print()


def example_gpu_performance():
    print("Example 4: GPU Acceleration Demo")
    print("-" * 60)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"  Device: {device}")
    
    if torch.cuda.is_available():
        print(f"  CUDA Device: {torch.cuda.get_device_name(0)}")
        print(f"  CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    builder = GPUPyramidBuilder(device)
    
    import time
    
    test_sizes = [(256, 256), (512, 512), (1024, 1024)]
    
    for H, W in test_sizes:
        img = torch.randn(1, 3, H, W, device=device)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        
        start = time.time()
        for _ in range(10):
            pyr = builder.gaussian_pyramid(img, 5)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        
        elapsed = time.time() - start
        print(f"  Gaussian pyramid {H}x{W}: {elapsed/10*1000:.2f} ms per build")
    
    print()


def example_guided_synthesis_comparison():
    print("Example 5: Guided Synthesis with GraphCut")
    print("-" * 60)
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture[:, i] = [color // 3, color, color // 2]
    texture = texture + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    guide = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.circle(guide, (100, 150), 50, (255, 0, 0), -1)
    cv2.rectangle(guide, (200, 80), (350, 220), (0, 255, 0), -1)
    cv2.ellipse(guide, (200, 250), (80, 40), 30, 0, 360, (0, 0, 255), -1)
    
    cv2.imwrite('example_guide_map.png', guide)
    print("  Saved: example_guide_map.png")
    
    print("  Guided synthesis with GraphCut...")
    result_graphcut = synthesizer.synthesize_texture(
        texture, (300, 400),
        patch_size=24, overlap=8,
        guide_image=guide,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.5
    )
    cv2.imwrite('example_guided_graphcut.png', result_graphcut)
    print("  Saved: example_guided_graphcut.png")
    
    print("  Guided synthesis with multiband...")
    result_multiband = synthesizer.synthesize_texture(
        texture, (300, 400),
        patch_size=24, overlap=8,
        guide_image=guide,
        use_direction=True,
        blend_mode='multiband',
        structure_weight=0.5
    )
    cv2.imwrite('example_guided_multiband.png', result_multiband)
    print("  Saved: example_guided_multiband.png")
    print()


def example_structure_orientation():
    print("Example 6: Structure Tensor Orientation Field")
    print("-" * 60)
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((128, 128, 3), dtype=np.uint8)
    for i in range(128):
        texture[:, i] = [40, 80 + int(i * 0.5), 30]
    texture = texture + np.random.randint(0, 15, (128, 128, 3), dtype=np.uint8)
    
    structure = synthesizer.compute_structure_tensor(texture)
    orientation, coherence = synthesizer.compute_orientation_field(structure)
    
    orientation_viz = ((orientation + np.pi) / (2 * np.pi) * 255).astype(np.uint8)
    orientation_viz = cv2.applyColorMap(orientation_viz, cv2.COLORMAP_HSV)
    
    coherence_viz = (coherence * 255).astype(np.uint8)
    coherence_viz = cv2.applyColorMap(coherence_viz, cv2.COLORMAP_JET)
    
    cv2.imwrite('example_orientation.png', orientation_viz)
    cv2.imwrite('example_coherence.png', coherence_viz)
    print("  Saved: example_orientation.png (orientation field)")
    print("  Saved: example_coherence.png (coherence map)")
    print()


def example_custom_texture():
    print("Example 7: Custom Diagonal Texture")
    print("-" * 60)
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    diagonal = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            val = 128 + 64 * np.sin((i + j) * 0.2)
            diagonal[i, j] = [int(val * 0.7), int(val), int(val * 0.8)]
    
    diagonal = diagonal + np.random.randint(0, 12, (64, 64, 3), dtype=np.uint8)
    cv2.imwrite('example_diagonal_input.png', diagonal)
    print("  Saved: example_diagonal_input.png")
    
    print("  Synthesizing diagonal pattern with structure guidance...")
    result = synthesizer.synthesize_texture(
        diagonal, (384, 384),
        patch_size=32, overlap=12,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.8
    )
    cv2.imwrite('example_diagonal_output.png', result)
    print("  Saved: example_diagonal_output.png")
    print()


def interactive_demo():
    print("Example 8: Interactive Guided Synthesis")
    print("-" * 60)
    print("  This will open a window for interactive drawing.")
    print("  Press ESC to skip this example.")
    print()
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    texture = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture[:, i] = [color // 3, color, color // 2]
    texture = texture + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    print("  Starting interactive mode...")
    print("  Controls:")
    print("    - Left mouse: Draw guide lines")
    print("    - 1/2/3: Switch colors")
    print("    - SPACE: Run synthesis with GraphCut")
    print("    - ESC: Exit")
    print()
    
    synthesizer.interactive_guided_synthesis(texture, (400, 400), patch_size=24, overlap=8)


if __name__ == '__main__':
    print("=" * 70)
    print("Enhanced Texture Synthesis Examples")
    print("=" * 70)
    print()
    
    example_graphcut_vs_feather()
    example_directional_texture_preservation()
    example_weave_pattern()
    example_gpu_performance()
    example_guided_synthesis_comparison()
    example_structure_orientation()
    example_custom_texture()
    
    print("=" * 70)
    print("All non-interactive examples completed!")
    print("=" * 70)
    print()
    print("To run the interactive example, call:")
    print("  interactive_demo()")
    print()
    print("Key improvements in this version:")
    print("  ✓ GraphCut minimum error seam finding for seamless blending")
    print("  ✓ Enhanced structure tensor guidance for directional textures")
    print("  ✓ Full GPU acceleration for pyramids and patch matching")
    print("  ✓ Patch caching for improved performance")
    print("  ✓ Support for multiple blending modes (graphcut, multiband, feather)")
