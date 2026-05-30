import os
import numpy as np
import cv2
from segmentation_postprocessor import SegmentationPostProcessor, create_sample_segmentation


def test_postprocessor():
    print("=" * 70)
    print("测试图像语义分割后处理工具 (完整版)")
    print("=" * 70)
    
    sample_path, processor = create_sample_segmentation('test_sample.png')
    print(f"✓ 示例图像已创建: {sample_path}")
    
    mask = processor.load_segmentation(sample_path)
    print(f"✓ 图像加载成功")
    print(f"  - 图像尺寸: {mask.shape}")
    print(f"  - 类别数量: {processor.num_classes}")
    
    print("\n--- 测试第一部分: 基础后处理 ---")
    
    filled_mask = processor.fill_holes_per_class(mask, min_hole_size=100)
    print(f"✓ 基本孔洞填充完成")
    
    filled_recon = processor.fill_holes_reconstruction(mask, min_hole_size=50, max_hole_size=1000)
    print(f"✓ 形态学重建孔洞填充完成")
    
    cleaned_mask = processor.remove_small_regions(mask, min_area=50)
    print(f"✓ 小区域去除完成")
    
    print("\n--- 测试第二部分: 分割质量评估 ---")
    
    miou, per_class_iou = processor.evaluate_miou(mask, filled_recon)
    print(f"✓ mIoU计算完成: {miou:.4f}")
    for i, iou in enumerate(per_class_iou):
        print(f"    - 类别 {i} IoU: {iou:.4f}")
    
    f_score, precision, recall, per_class_metrics = processor.evaluate_boundary_fscore(
        mask, filled_recon, tolerance=3
    )
    print(f"✓ 边界F-score计算完成")
    print(f"    - F-score: {f_score:.4f}")
    print(f"    - Precision: {precision:.4f}")
    print(f"    - Recall: {recall:.4f}")
    
    metrics = processor.evaluate_segmentation(mask, filled_recon)
    print(f"✓ 综合质量评估完成")
    print(f"    - mIoU: {metrics['mIoU']:.4f}")
    print(f"    - 边界F-score: {metrics['boundary_F_score']:.4f}")
    
    print("\n--- 测试第三部分: 交互式修正工具 ---")
    
    brush_points = [(50, 50), (60, 50), (70, 55), (80, 60), (90, 70)]
    brush_corrected = processor.apply_brush_correction(
        mask, brush_points, target_class=2, brush_size=5, mode='add'
    )
    print(f"✓ 画笔修正完成")
    
    polygon_points = [(100, 100), (150, 100), (150, 150), (100, 150)]
    lasso_corrected = processor.apply_lasso_correction(
        mask, polygon_points, target_class=3, mode='add'
    )
    print(f"✓ 套索修正完成")
    
    seed_point = (100, 100)
    if mask[seed_point[1], seed_point[0]] != 0:
        fill_corrected = processor.fill_holes_interactive(mask, seed_point)
        print(f"✓ 交互式填充完成")
    else:
        print("! 跳过交互式填充测试（种子点在背景）")
    
    brush_mask = processor.create_brush_mask(mask.shape, brush_points, brush_size=5)
    print(f"✓ 画笔掩码创建完成，掩码像素数: {np.sum(brush_mask)}")
    
    lasso_mask = processor.create_lasso_mask(mask.shape, polygon_points)
    print(f"✓ 套索掩码创建完成，掩码像素数: {np.sum(lasso_mask)}")
    
    print("\n--- 测试第四部分: 边缘平滑算法 ---")
    
    edges = processor.compute_class_edges(mask)
    print(f"✓ 类间边界检测完成，边界像素数: {np.sum(edges > 0)}")
    
    edge_guidance = processor.compute_edge_guidance_map(mask, edge_weight=0.7)
    print(f"✓ 边缘引导图计算完成")
    print(f"    - 引导图范围: [{edge_guidance.min():.2f}, {edge_guidance.max():.2f}]")
    
    smoothed_adaptive = processor.smooth_edges_adaptive(
        mask, min_object_area=500, max_kernel=7, edge_preserve=True
    )
    print(f"✓ 自适应平滑完成 (大物体平滑，小物体保持)")
    
    smoothed_edge_guided = processor.smooth_with_edge_guidance(
        mask, sigma=1.5, edge_threshold=0.3, edge_weight=0.7
    )
    print(f"✓ 边缘引导平滑完成 (保留类间边界)")
    
    all_smooth_methods = ['none', 'morphology', 'gaussian', 'distance', 'watershed', 'adaptive', 'edge_guided']
    for method in all_smooth_methods:
        config_test = {
            'fill_holes': False,
            'remove_small': False,
            'smooth_method': method,
            'kernel_size': 3,
            'iterations': 1,
            'sigma': 1.5,
            'min_object_area': 500,
            'max_kernel': 7,
            'edge_preserve': True,
            'edge_threshold': 0.3,
            'edge_weight': 0.7
        }
        result = processor.process(mask, config_test)
        print(f"✓ 平滑方法 '{method}' 测试通过")
    
    print("\n--- 测试第五部分: 视频分割后处理 ---")
    
    if not os.path.exists('test_video_input'):
        os.makedirs('test_video_input')
    
    num_frames = 5
    video_masks = []
    for i in range(num_frames):
        test_mask = mask.copy()
        if i > 0:
            shift = i * 2
            test_mask = np.roll(test_mask, shift, axis=1)
        video_masks.append(test_mask)
        
        test_rgb = processor.mask_to_rgb(test_mask)
        cv2.imwrite(f'test_video_input/frame_{i:04d}.png', 
                   cv2.cvtColor(test_rgb, cv2.COLOR_RGB2BGR))
    
    loaded_masks, filenames = processor.load_video_masks('test_video_input', '*.png')
    print(f"✓ 视频帧加载完成: {len(loaded_masks)} 帧")
    
    video_config = {
        'temporal_window': 3,
        'temporal_alpha': 0.5,
        'use_optical_flow': False,
        'per_frame_postprocess': True
    }
    
    processor.config = {
        'fill_holes': True,
        'hole_method': 'reconstruction',
        'min_hole_size': 50,
        'remove_small': True,
        'min_area': 100,
        'smooth_method': 'edge_guided',
        'sigma': 1.5,
        'edge_threshold': 0.3,
        'edge_weight': 0.7
    }
    
    processed_video = processor.process_video_masks(video_masks, video_config)
    print(f"✓ 视频处理完成，处理了 {len(processed_video)} 帧")
    
    if not os.path.exists('test_video_output'):
        os.makedirs('test_video_output')
    processor.save_video_masks(processed_video, 'test_video_output', filenames)
    print(f"✓ 视频帧已保存")
    
    temporal_smoothed = processor.temporal_smooth_video_masks(video_masks, window_size=3, alpha=0.5)
    print(f"✓ 时间域平滑完成")
    
    if len(video_masks) >= 2:
        flow_consistent = processor.optical_flow_consistency(video_masks[:2])
        print(f"✓ 光流一致性优化完成")
    
    print("\n--- 测试第六部分: 算法组合 ---")
    config = {
        'fill_holes': True,
        'hole_method': 'reconstruction',
        'min_hole_size': 50,
        'max_hole_size': 1000,
        'remove_small': True,
        'min_area': 100,
        'connectivity': 1,
        'smooth_method': 'edge_guided',
        'kernel_size': 3,
        'iterations': 1,
        'sigma': 1.5,
        'threshold': 0.5,
        'min_object_area': 500,
        'max_kernel': 7,
        'edge_preserve': True,
        'edge_threshold': 0.3,
        'edge_weight': 0.7
    }
    
    processed = processor.process(mask, config)
    print(f"✓ 完整组合处理完成")
    
    output_rgb = processor.mask_to_rgb(processed)
    cv2.imwrite('test_processed_full.png', cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR))
    print(f"✓ 完整处理结果已保存: test_processed_full.png")
    
    edges_vis = edges.astype(np.uint8) * 255
    cv2.imwrite('test_edges.png', edges_vis)
    
    edge_guidance_vis = (edge_guidance * 255).astype(np.uint8)
    cv2.imwrite('test_edge_guidance.png', edge_guidance_vis)
    print(f"✓ 边缘可视化图像已保存")
    
    print("\n--- 测试第七部分: 批量处理 ---")
    if not os.path.exists('test_input'):
        os.makedirs('test_input')
    
    for i in range(3):
        test_mask = mask.copy()
        if i == 1:
            test_mask = cv2.rotate(test_mask, cv2.ROTATE_90_CLOCKWISE)
        elif i == 2:
            test_mask = cv2.rotate(test_mask, cv2.ROTATE_180)
        
        test_rgb = processor.mask_to_rgb(test_mask)
        cv2.imwrite(f'test_input/sample_{i}.png', cv2.cvtColor(test_rgb, cv2.COLOR_RGB2BGR))
    
    if not os.path.exists('test_output'):
        os.makedirs('test_output')
    
    results = processor.batch_process('test_input', 'test_output', config)
    success_count = sum(1 for r in results if r['success'])
    print(f"✓ 批量处理完成: {success_count}/{len(results)} 成功")
    
    print("\n" + "=" * 70)
    print("所有测试通过!")
    print("=" * 70)
    print("\n功能总结:")
    print("  ✓ 孔洞填充: 基本填充 + 形态学重建")
    print("  ✓ 质量评估: mIoU + 边界F-score/Precision/Recall")
    print("  ✓ 交互式修正: 画笔 + 套索 + 填充")
    print("  ✓ 边缘平滑: 7种方法，包括自适应和边缘引导")
    print("  ✓ 视频处理: 时间平滑 + 光流一致性 + 逐帧后处理")
    print("  ✓ 支持批量处理和多类分割")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    try:
        test_postprocessor()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
