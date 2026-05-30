import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from tqdm import tqdm

from config import Config
from core import (
    ImageEditor, SaliencyInpainter, FillMethod, BlendMode,
    fill_salient_region, blur_salient_region,
    replace_salient_region, adjust_salient_region
)
from utils.helpers import load_image, save_image


def create_test_data():
    print("Creating test image and saliency map...")
    
    image = np.ones((400, 500, 3), dtype=np.uint8) * 220
    
    cv2.rectangle(image, (150, 100), (350, 300), (180, 120, 200), -1)
    cv2.circle(image, (250, 200), 60, (255, 200, 100), -1)
    cv2.putText(image, "Object", (210, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2)
    
    saliency = np.zeros((400, 500), dtype=np.float32)
    for y in range(400):
        for x in range(500):
            dist = np.sqrt((x - 250) ** 2 + (y - 200) ** 2)
            saliency[y, x] = np.exp(-dist ** 2 / (2 * 100 ** 2))
    
    saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-8)
    
    return image, saliency


def example_fill_methods():
    print("\n" + "=" * 60)
    print("EXAMPLE: Salient Region Filling (Inpainting)")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'fill')
    os.makedirs(output_dir, exist_ok=True)
    
    save_image(image, os.path.join(output_dir, 'original.png'))
    save_image((saliency * 255).astype(np.uint8), os.path.join(output_dir, 'saliency.png'))
    
    binary_mask = (saliency > 0.3).astype(np.float32)
    save_image((binary_mask * 255).astype(np.uint8), os.path.join(output_dir, 'mask.png'))
    
    editor = ImageEditor()
    
    fill_methods = [
        (FillMethod.TELEA, "Telea's Algorithm", 3),
        (FillMethod.NS, "Navier-Stokes", 3),
        (FillMethod.POISSON, "Poisson Blending", 3),
        (FillMethod.CONTENT_AWARE, "Content-Aware", 3),
        (FillMethod.SAMPLE, "Sample-Based", 3),
    ]
    
    print("\nApplying different fill methods...")
    results = []
    
    for method, name, radius in tqdm(fill_methods, desc="Filling"):
        result = editor.fill_salient_region(
            image, saliency,
            method=method,
            threshold=0.3,
            feather=5,
            radius=radius
        )
        
        save_image(result.edited_image, os.path.join(output_dir, f'filled_{method.value}.png'))
        results.append((name, result))
    
    print("\nVisual comparison:")
    comparison = np.hstack([
        cv2.cvtColor(image, cv2.COLOR_RGB2BGR),
        cv2.cvtColor(results[0][1].edited_image, cv2.COLOR_RGB2BGR)
    ])
    
    for name, result in results:
        diff = np.abs(image.astype(np.float32) - result.edited_image.astype(np.float32)).mean()
        print(f"  {name:25s} - Avg pixel diff: {diff:.1f}")
    
    print("\nFill methods comparison:")
    print("  - TELEA: Fast, good for small holes, based on Fast Marching")
    print("  - NS: Better texture preservation, solves Navier-Stokes equations")
    print("  - POISSON: Seamless blending, gradient domain reconstruction")
    print("  - CONTENT_AWARE: Pattern matching, copies similar regions")
    print("  - SAMPLE: Simple nearest non-mask pixel sampling")
    
    return results


def example_blur_effects():
    print("\n" + "=" * 60)
    print("EXAMPLE: Salient Region Blurring")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'blur')
    os.makedirs(output_dir, exist_ok=True)
    
    editor = ImageEditor()
    
    blur_types = [
        ('gaussian', 'Gaussian Blur', 25, 10),
        ('median', 'Median Blur', 25, 0),
        ('bilateral', 'Bilateral Blur', 25, 10),
        ('motion', 'Motion Blur', 25, 0),
    ]
    
    print("\nApplying different blur types (on background, invert=True)...")
    results = []
    
    for blur_type, name, kernel, sigma in tqdm(blur_types, desc="Blurring"):
        result = editor.blur_salient_region(
            image, saliency,
            blur_type=blur_type,
            kernel_size=kernel,
            sigma=sigma,
            threshold=0.3,
            invert_mask=True,
            feather=10
        )
        
        save_image(result.edited_image, os.path.join(output_dir, f'blur_{blur_type}.png'))
        results.append((name, result))
    
    print("\nBlur effects on foreground (invert=False)...")
    result_fg = editor.blur_salient_region(
        image, saliency,
        blur_type='gaussian',
        kernel_size=31,
        sigma=15,
        threshold=0.3,
        invert_mask=False,
        feather=5
    )
    save_image(result_fg.edited_image, os.path.join(output_dir, 'blur_foreground.png'))
    
    print("\nBlur types comparison:")
    print("  - gaussian: Uniform blur, natural bokeh effect")
    print("  - median: Removes salt-and-pepper noise, preserves edges")
    print("  - bilateral: Edge-preserving blur, smooths flat regions")
    print("  - motion: Simulates camera/subject motion blur")
    
    return results


def example_adjustments():
    print("\n" + "=" * 60)
    print("EXAMPLE: Salient Region Color Adjustment")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'adjust')
    os.makedirs(output_dir, exist_ok=True)
    
    editor = ImageEditor()
    
    adjustments = [
        ('brightness', {'brightness': 1.5, 'contrast': 1.0, 'saturation': 1.0}),
        ('contrast', {'brightness': 1.0, 'contrast': 1.5, 'saturation': 1.0}),
        ('saturation', {'brightness': 1.0, 'contrast': 1.0, 'saturation': 2.0}),
        ('cool', {'brightness': 1.0, 'contrast': 1.0, 'saturation': 1.0, 'hue_shift': 120}),
        ('warm', {'brightness': 1.0, 'contrast': 1.0, 'saturation': 1.0, 'hue_shift': -30}),
        ('dramatic', {'brightness': 1.2, 'contrast': 1.8, 'saturation': 1.5}),
    ]
    
    print("\nApplying color adjustments...")
    for name, params in tqdm(adjustments, desc="Adjusting"):
        result = editor.adjust_salient_region(
            image, saliency,
            threshold=0.3,
            feather=8,
            **params
        )
        save_image(result.edited_image, os.path.join(output_dir, f'adjust_{name}.png'))
    
    print("\nAdjustment examples saved.")
    print("  - Brightness/Contrast: Basic exposure control")
    print("  - Saturation: Vibrance adjustment")
    print("  - Hue shift: Color temperature (cool/warm)")
    
    return adjustments


def example_replace_and_blend():
    print("\n" + "=" * 60)
    print("EXAMPLE: Region Replacement and Blending")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'replace')
    os.makedirs(output_dir, exist_ok=True)
    
    editor = ImageEditor()
    
    replacement = np.zeros_like(image)
    for y in range(replacement.shape[0]):
        for x in range(replacement.shape[1]):
            replacement[y, x] = [
                int(128 + 127 * np.sin(x * 0.05)),
                int(128 + 127 * np.sin(y * 0.05)),
                int(128 + 127 * np.sin((x + y) * 0.03))
            ]
    
    blend_modes = [
        (BlendMode.NORMAL, 'Normal'),
        (BlendMode.MULTIPLY, 'Multiply'),
        (BlendMode.SCREEN, 'Screen'),
        (BlendMode.OVERLAY, 'Overlay'),
        (BlendMode.SOFT_LIGHT, 'Soft Light'),
        (BlendMode.ALPHA, 'Alpha'),
    ]
    
    print("\nTesting blend modes...")
    for mode, name in tqdm(blend_modes, desc="Blending"):
        result = editor.replace_salient_region(
            image, replacement, saliency,
            threshold=0.3,
            feather=10,
            blend_mode=mode
        )
        save_image(result.edited_image, os.path.join(output_dir, f'blend_{mode.value}.png'))
    
    print("\nBlend modes comparison:")
    print("  - NORMAL: Direct replacement with alpha")
    print("  - MULTIPLY: Darkens, multiplies color values")
    print("  - SCREEN: Brightens, inverse of multiply")
    print("  - OVERLAY: Combines multiply and screen")
    print("  - SOFT_LIGHT: Gentle version of overlay")
    print("  - ALPHA: Alpha channel blending (default)")
    
    return blend_modes


def example_stylization():
    print("\n" + "=" * 60)
    print("EXAMPLE: Salient Region Stylization")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'style')
    os.makedirs(output_dir, exist_ok=True)
    
    editor = ImageEditor()
    
    styles = ['sketch', 'cartoon', 'sepia']
    
    print("\nApplying artistic styles...")
    for style in tqdm(styles, desc="Styling"):
        try:
            result = editor.stylize_salient_region(
                image, saliency,
                style=style,
                threshold=0.3,
                feather=5,
                invert_mask=False
            )
            save_image(result.edited_image, os.path.join(output_dir, f'style_{style}.png'))
            print(f"  {style:10s}: OK")
        except Exception as e:
            print(f"  {style:10s}: {e}")
    
    print("\nStyle effects:")
    print("  - sketch: Pencil sketch effect")
    print("  - cartoon: Cartoon/anime style")
    print("  - sepia: Vintage brown tone")
    
    return styles


def example_composite():
    print("\n" + "=" * 60)
    print("EXAMPLE: Background Composition")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'composite')
    os.makedirs(output_dir, exist_ok=True)
    
    editor = ImageEditor()
    
    backgrounds = []
    
    bg_gradient = np.zeros_like(image)
    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            bg_gradient[y, x] = [
                int(200 * (y / image.shape[0])),
                int(150 + 100 * np.sin(x * 0.02)),
                int(255 * (1 - y / image.shape[0]))
            ]
    backgrounds.append(('gradient', bg_gradient))
    
    bg_checker = np.zeros_like(image)
    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            if (x // 20 + y // 20) % 2 == 0:
                bg_checker[y, x] = [255, 255, 255]
            else:
                bg_checker[y, x] = [200, 200, 200]
    backgrounds.append(('checkerboard', bg_checker))
    
    bg_blur = cv2.GaussianBlur(image, (51, 51), 30)
    backgrounds.append(('blurred', bg_blur))
    
    print("\nCreating composites...")
    for name, bg in tqdm(backgrounds, desc="Compositing"):
        result = editor.create_composite(
            image, saliency, bg,
            threshold=0.3,
            feather=15
        )
        save_image(result.edited_image, os.path.join(output_dir, f'composite_{name}.png'))
        save_image(bg, os.path.join(output_dir, f'bg_{name}.png'))
    
    print("\nCompositing techniques:")
    print("  - Feathered edges for seamless blending")
    print("  - Alpha matte extracted from saliency map")
    print("  - Foreground kept, background replaced")
    
    return backgrounds


def example_inpainter_class():
    print("\n" + "=" * 60)
    print("EXAMPLE: Direct Inpainter Usage")
    print("=" * 60)
    
    image, saliency = create_test_data()
    mask = (saliency > 0.3).astype(np.uint8) * 255
    
    inpainter = SaliencyInpainter(default_radius=5)
    
    print("\nTesting direct inpainter methods...")
    result_telea = inpainter.inpaint(image, mask, method=FillMethod.TELEA, radius=5)
    result_ns = inpainter.inpaint(image, mask, method=FillMethod.NS, radius=5)
    
    print(f"  TELEA result shape: {result_telea.shape}")
    print(f"  NS result shape: {result_ns.shape}")
    
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'direct')
    os.makedirs(output_dir, exist_ok=True)
    save_image(result_telea, os.path.join(output_dir, 'direct_telea.png'))
    save_image(result_ns, os.path.join(output_dir, 'direct_ns.png'))


def example_convenience_functions():
    print("\n" + "=" * 60)
    print("EXAMPLE: Convenience Functions")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo', 'quick')
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nUsing convenience functions...")
    
    result_fill = fill_salient_region(
        image, saliency,
        method=FillMethod.TELEA,
        threshold=0.3
    )
    save_image(result_fill.edited_image, os.path.join(output_dir, 'quick_fill.png'))
    
    result_blur = blur_salient_region(
        image, saliency,
        blur_type='gaussian',
        kernel_size=35,
        sigma=15,
        invert_mask=True
    )
    save_image(result_blur.edited_image, os.path.join(output_dir, 'quick_blur.png'))
    
    result_adj = adjust_salient_region(
        image, saliency,
        brightness=1.3,
        contrast=1.5,
        saturation=1.8
    )
    save_image(result_adj.edited_image, os.path.join(output_dir, 'quick_adj.png'))
    
    print("  All convenience functions executed successfully!")
    
    return result_fill, result_blur, result_adj


def create_comparison_grid():
    print("\n" + "=" * 60)
    print("CREATING COMPARISON GRID")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'editing_demo')
    os.makedirs(output_dir, exist_ok=True)
    
    editor = ImageEditor()
    
    operations = [
        ('Original', image),
        ('Fill', editor.fill_salient_region(image, saliency, method=FillMethod.TELEA, threshold=0.3).edited_image),
        ('Blur BG', editor.blur_salient_region(image, saliency, invert_mask=True, threshold=0.3).edited_image),
        ('Bright', editor.adjust_salient_region(image, saliency, brightness=1.5, threshold=0.3).edited_image),
        ('Sat+', editor.adjust_salient_region(image, saliency, saturation=2.0, threshold=0.3).edited_image),
        ('Composite', editor.create_composite(image, saliency, np.ones_like(image)*200, threshold=0.3).edited_image),
    ]
    
    rows = 2
    cols = 3
    h, w = image.shape[:2]
    
    grid = np.zeros((h * rows, w * cols, 3), dtype=np.uint8)
    
    for i, (name, img) in enumerate(operations):
        r = i // cols
        c = i % cols
        
        if img.max() <= 1.0:
            img_disp = (img * 255).astype(np.uint8)
        else:
            img_disp = img.astype(np.uint8)
        
        if img_disp.shape[2] == 4:
            img_disp = cv2.cvtColor(img_disp, cv2.COLOR_RGBA2RGB)
        
        grid[r*h:(r+1)*h, c*w:(c+1)*w] = img_disp
        cv2.putText(grid, name, (c*w + 10, r*h + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(grid, name, (c*w + 10, r*h + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    grid_path = os.path.join(output_dir, 'comparison_grid.png')
    save_image(grid, grid_path)
    print(f"Comparison grid saved to: {grid_path}")
    
    return grid


def main():
    print("\n" + "=" * 60)
    print("IMAGE EDITING WITH SALIENCY - COMPREHENSIVE DEMO")
    print("=" * 60)
    
    try:
        example_fill_methods()
        example_blur_effects()
        example_adjustments()
        example_replace_and_blend()
        example_stylization()
        example_composite()
        example_inpainter_class()
        example_convenience_functions()
        create_comparison_grid()
        
        print("\n" + "=" * 60)
        print("ALL IMAGE EDITING EXAMPLES COMPLETE")
        print("=" * 60)
        
        print(f"\nAll outputs saved to: {os.path.join(Config.OUTPUT_DIR, 'editing_demo')}")
        
    except Exception as e:
        print(f"\nError during examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
