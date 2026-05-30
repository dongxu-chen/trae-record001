import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from config import Config
from core import SaliencyInferencer, BatchProcessor
from utils import save_image

Config.ensure_dirs()


def create_test_images(input_dir, num_images=5):
    print(f"创建 {num_images} 张测试图像...")
    
    image_paths = []
    
    for i in range(num_images):
        img = np.zeros((300, 400, 3), dtype=np.uint8)
        
        bg_color = np.random.randint(50, 150, 3)
        img[:] = bg_color
        
        for _ in range(np.random.randint(1, 4)):
            obj_color = np.random.randint(180, 255, 3)
            shape_type = np.random.choice(['circle', 'rect', 'ellipse'])
            
            if shape_type == 'circle':
                center = (np.random.randint(80, 320), np.random.randint(80, 220))
                radius = np.random.randint(30, 80)
                cv2.circle(img, center, radius, tuple(int(c) for c in obj_color), -1)
            elif shape_type == 'rect':
                x1, y1 = np.random.randint(50, 200), np.random.randint(50, 150)
                x2, y2 = x1 + np.random.randint(60, 150), y1 + np.random.randint(60, 150)
                cv2.rectangle(img, (x1, y1), (x2, y2), tuple(int(c) for c in obj_color), -1)
            else:
                center = (np.random.randint(80, 320), np.random.randint(80, 220))
                axes = (np.random.randint(30, 80), np.random.randint(30, 80))
                cv2.ellipse(img, center, axes, 0, 0, 360, tuple(int(c) for c in obj_color), -1)
        
        image_path = os.path.join(input_dir, f'test_batch_{i:02d}.png')
        save_image(img, image_path)
        image_paths.append(image_path)
        print(f"  创建: {image_path}")
    
    return image_paths


def example_batch_demo():
    print("=" * 60)
    print("显著性目标检测 - 批量处理示例")
    print("=" * 60)
    
    input_dir = os.path.join(Config.INPUT_DIR, 'batch_test')
    output_dir = os.path.join(Config.OUTPUT_DIR, 'batch_results')
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    create_test_images(input_dir, num_images=5)
    
    inferencer = SaliencyInferencer(model_name='basnet', pretrained=False)
    batch_processor = BatchProcessor(inferencer)
    
    print(f"\n当前模型: {inferencer.model_name}")
    print(f"批量大小: {Config.BATCH_SIZE}")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    
    print("\n开始批量处理...")
    result = batch_processor.process_directory(
        input_dir=input_dir,
        output_dir=output_dir,
        batch_size=2,
        threshold=0.5,
        edge_refinement=True,
        save_maps=True,
        save_masks=True,
        save_segmented=True,
        save_overlay=True,
        format='png'
    )
    
    print(f"\n批量处理完成!")
    print(f"处理图像数: {result['total_images']}")
    
    print("\n处理结果统计:")
    for i, item in enumerate(result['results']):
        print(f"\n  图像 {i+1}: {item['filename']}")
        print(f"    尺寸: {item['original_size']}")
        print(f"    平均显著值: {item['stats']['mean_saliency']:.4f}")
        print(f"    掩膜面积比: {item['stats']['mask_area_ratio']:.4f}")
        if 'segmentation' in item:
            print(f"    检测到目标数: {item['segmentation']['num_objects']}")
    
    print("\n生成对比网格...")
    grid_path = batch_processor.generate_comparison_grid(
        input_dir=input_dir,
        output_dir=output_dir,
        num_samples=3,
        cols=4
    )
    print(f"对比网格已保存: {grid_path}")
    
    print("\n" + "=" * 60)
    print("批量处理示例完成!")
    print(f"所有结果保存在: {output_dir}")
    print("=" * 60)


def example_custom_processing():
    print("\n" + "=" * 60)
    print("显著性目标检测 - 自定义处理函数示例")
    print("=" * 60)
    
    input_dir = os.path.join(Config.INPUT_DIR, 'batch_test')
    output_dir = os.path.join(Config.OUTPUT_DIR, 'custom_results')
    os.makedirs(output_dir, exist_ok=True)
    
    inferencer = SaliencyInferencer(model_name='basnet', pretrained=False)
    batch_processor = BatchProcessor(inferencer)
    
    def draw_bounding_boxes(result, output_dir):
        if 'segmentation' in result and len(result['segmentation']['bounding_boxes']) > 0:
            img = result['original_image'].copy()
            for bbox_info in result['segmentation']['bounding_boxes']:
                x, y, w, h = bbox_info['bbox']
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                
                cx, cy = bbox_info['centroid']
                cv2.circle(img, (cx, cy), 5, (0, 255, 0), -1)
            
            name = os.path.splitext(result['filename'])[0]
            bbox_path = os.path.join(output_dir, f'{name}_bboxes.png')
            save_image(img, bbox_path)
            print(f"    保存边界框: {bbox_path}")
    
    print("\n使用自定义处理函数进行批量处理...")
    result = batch_processor.process_with_custom_function(
        input_dir=input_dir,
        output_dir=output_dir,
        custom_func=draw_bounding_boxes,
        save_segmented=True
    )
    
    print(f"\n自定义处理完成!")
    print(f"处理图像数: {result['total_images']}")
    
    print("\n" + "=" * 60)
    print("自定义处理示例完成!")
    print("=" * 60)


if __name__ == '__main__':
    example_batch_demo()
    example_custom_processing()
