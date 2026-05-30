#!/usr/bin/env python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.inpainter import ImageInpainter
from src.utils import load_image, save_image, visualize_results, create_directory
from src.mask_generator import MaskGenerator


def example_single_image():
    print("=" * 60)
    print("Example 1: Single Image Inpainting")
    print("=" * 60)
    
    create_directory('examples/output')
    
    test_img = np.ones((256, 256, 3), dtype=np.float32)
    x = np.linspace(0, 1, 256)
    y = np.linspace(0, 1, 256)
    X, Y = np.meshgrid(x, y)
    
    test_img[:, :, 0] = 0.2 + 0.6 * X
    test_img[:, :, 1] = 0.3 + 0.4 * Y
    test_img[:, :, 2] = 0.5 + 0.3 * (X + Y) / 2
    
    test_img_path = 'examples/output/test_gradient.png'
    save_image(test_img, test_img_path)
    print(f"Created test image: {test_img_path}")
    
    inpainter = ImageInpainter(model_name='partialconv', image_size=(256, 256))
    
    mask_gen = MaskGenerator(256, 256)
    mask = mask_gen.watermark_mask(text='SAMPLE', font_scale=1.5, rotation=15)
    
    result = inpainter.inpaint(test_img, mask)
    
    metrics = inpainter.evaluate_inpainting(test_img, result, mask, only_masked_region=True)
    inpainter.print_evaluation(metrics)
    
    viz_path = 'examples/output/example1_result.png'
    visualize_results(test_img, mask, result, save_path=viz_path)
    print(f"Result saved: {viz_path}")


def example_different_masks():
    print("\n" + "=" * 60)
    print("Example 2: Different Mask Types")
    print("=" * 60)
    
    create_directory('examples/output/masks')
    
    test_img = np.ones((256, 256, 3), dtype=np.float32) * 0.8
    test_img[50:200, 50:200, 0] = 0.3
    test_img[50:200, 50:200, 1] = 0.7
    test_img[50:200, 50:200, 2] = 0.5
    
    inpainter = ImageInpainter(model_name='partialconv', image_size=(256, 256))
    
    mask_types = ['stroke', 'bbox', 'watermark', 'scratch', 'irregular']
    mask_gen = MaskGenerator(256, 256)
    
    for mask_type in mask_types:
        print(f"\nTesting mask type: {mask_type}")
        
        mask = mask_gen.generate_mask(mask_type)
        result = inpainter.inpaint(test_img, mask)
        
        metrics = inpainter.evaluate_inpainting(test_img, result, mask, only_masked_region=True)
        
        viz_path = f'examples/output/masks/{mask_type}_result.png'
        visualize_results(test_img, mask, result, save_path=viz_path)
        
        print(f"  PSNR: {metrics['psnr']:.2f} dB, SSIM: {metrics['ssim']:.4f}")
    
    print(f"\nAll results saved to: examples/output/masks/")


def example_batch_processing():
    print("\n" + "=" * 60)
    print("Example 3: Batch Processing")
    print("=" * 60)
    
    input_dir = 'examples/test_images'
    output_dir = 'examples/output/batch'
    
    create_directory(input_dir)
    create_directory(output_dir)
    
    for i in range(3):
        img = np.random.rand(256, 256, 3).astype(np.float32)
        save_image(img, f'{input_dir}/image_{i+1}.png')
    
    print(f"Created {len(os.listdir(input_dir))} test images in {input_dir}")
    
    inpainter = ImageInpainter(model_name='partialconv', image_size=(256, 256))
    
    results = inpainter.batch_inpaint(
        input_dir=input_dir,
        output_dir=output_dir,
        mask_type='watermark',
        save_visualization=True,
        evaluate=True
    )
    
    print(f"\nBatch processing complete!")
    print(f"Processed {results['num_processed']} images")


def example_edge_connect():
    print("\n" + "=" * 60)
    print("Example 4: Edge-Connect Model")
    print("=" * 60)
    
    create_directory('examples/output')
    
    test_img = np.ones((256, 256, 3), dtype=np.float32)
    for i in range(256):
        for j in range(256):
            if (i // 32 + j // 32) % 2 == 0:
                test_img[i, j] = [0.9, 0.9, 0.9]
            else:
                test_img[i, j] = [0.2, 0.4, 0.6]
    
    test_img_path = 'examples/output/test_checkerboard.png'
    save_image(test_img, test_img_path)
    
    inpainter = ImageInpainter(model_name='edgeconnect', image_size=(256, 256))
    
    mask_gen = MaskGenerator(256, 256)
    mask = mask_gen.bbox_mask(min_size=(40, 40), max_size=(80, 80), num_boxes=2)
    
    result = inpainter.inpaint(test_img, mask)
    
    metrics = inpainter.evaluate_inpainting(test_img, result, mask, only_masked_region=True)
    inpainter.print_evaluation(metrics)
    
    viz_path = 'examples/output/edgeconnect_result.png'
    visualize_results(test_img, mask, result, save_path=viz_path)
    print(f"Result saved: {viz_path}")


def example_watermark_removal():
    print("\n" + "=" * 60)
    print("Example 5: Watermark Removal")
    print("=" * 60)
    
    create_directory('examples/output')
    
    test_img = np.ones((256, 256, 3), dtype=np.float32)
    x = np.linspace(0, 1, 256)
    y = np.linspace(0, 1, 256)
    X, Y = np.meshgrid(x, y)
    
    test_img[:, :, 0] = np.sin(X * np.pi * 3) * 0.3 + 0.5
    test_img[:, :, 1] = np.cos(Y * np.pi * 2) * 0.3 + 0.5
    test_img[:, :, 2] = 0.5
    
    test_img_path = 'examples/output/test_pattern.png'
    save_image(test_img, test_img_path)
    
    inpainter = ImageInpainter(model_name='partialconv', image_size=(256, 256))
    
    image, mask, result = inpainter.inpaint_watermark(
        test_img_path,
        text='COPYRIGHT',
        font_scale=1.2,
        rotation=-20
    )
    
    metrics = inpainter.evaluate_inpainting(image, result, mask, only_masked_region=True)
    inpainter.print_evaluation(metrics)
    
    viz_path = 'examples/output/watermark_removal.png'
    visualize_results(image, mask, result, save_path=viz_path)
    print(f"Result saved: {viz_path}")


if __name__ == '__main__':
    print("Deep Learning Image Inpainting - Examples")
    print("=" * 60)
    
    try:
        example_single_image()
        example_different_masks()
        example_batch_processing()
        example_edge_connect()
        example_watermark_removal()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("Check examples/output/ for results")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
