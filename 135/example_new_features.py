"""
遥感图像变化检测库 v0.3.0 - 新功能示例
包括：
1. 注意力可视化与热力图
2. 主动学习与伪标签生成
3. ConvLSTM多时相序列变化检测
4. GeoJSON矢量结果导出
"""

import sys
import os
sys.path.insert(0, '.')

import torch
import numpy as np
import cv2


def example_1_attention_visualization():
    """示例1: 注意力可视化与热力图"""
    print("=" * 80)
    print("EXAMPLE 1: 注意力可视化与热力图")
    print("=" * 80)
    
    from cd_tool.models import UNet
    from cd_tool.utils import AttentionVisualizer
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = UNet(
        n_channels=6,
        n_classes=1,
        use_attention=True,
        use_boundary_attention=True
    ).to(device)
    model.eval()
    
    img1 = torch.randn(1, 3, 256, 256).to(device)
    img2 = torch.randn(1, 3, 256, 256).to(device)
    
    visualizer = AttentionVisualizer(model, device)
    
    att_maps = visualizer.get_attention_maps(img1, img2)
    print(f"检测到的注意力图数量: {len(att_maps)}")
    for name, att_map in att_maps.items():
        print(f"  - {name}: shape={att_map.shape}")
    
    dummy_image = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    att_map_np = list(att_maps.values())[0] if att_maps else np.zeros((256, 256))
    heatmap = visualizer.visualize_heatmap(att_map_np, dummy_image, alpha=0.6)
    print(f"生成热力图 shape={heatmap.shape}, dtype={heatmap.dtype}")
    
    visualizer.save_visualization(heatmap, "attention_heatmap.png")
    print("热力图已保存至 attention_heatmap.png")
    print()


def example_2_pseudo_labeling():
    """示例2: 主动学习与伪标签生成"""
    print("=" * 80)
    print("EXAMPLE 2: 主动学习与伪标签生成")
    print("=" * 80)
    
    from cd_tool.models import UNet
    from cd_tool.utils import PseudoLabeler
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = UNet(n_channels=6, n_classes=1, use_attention=True).to(device)
    model.eval()
    
    labeler = PseudoLabeler(
        model=model,
        device=device,
        strategy='entropy',
        confidence_threshold=0.8
    )
    
    img1 = torch.randn(1, 3, 256, 256).to(device)
    img2 = torch.randn(1, 3, 256, 256).to(device)
    
    pseudo_labels, uncertainty = labeler.generate_pseudo_labels(
        img1, img2, return_uncertainty=True
    )
    
    print(f"伪标签 shape: {pseudo_labels.shape}")
    print(f"置信度均值: {pseudo_labels.float().mean():.4f}")
    print(f"不确定性: {uncertainty:.4f}" if uncertainty is not None else "")
    
    pseudo_np = pseudo_labels.squeeze().cpu().numpy().astype(np.uint8)
    refined = labeler.refine_pseudo_labels(pseudo_labels, None, min_area=50)
    print(f"后处理后变化像素: {np.sum(refined)}")
    
    labeler.save_pseudo_label(refined, "pseudo_label.png", as_image=True)
    print("伪标签已保存至 pseudo_label.png")
    print()


def example_3_temporal_change_detection():
    """示例3: ConvLSTM多时相序列变化检测"""
    print("=" * 80)
    print("EXAMPLE 3: ConvLSTM多时相序列变化检测")
    print("=" * 80)
    
    from cd_tool.models import TemporalChangeDetection, SiameseLSTM
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = TemporalChangeDetection(
        in_channels=3,
        num_classes=1,
        hidden_dims=[64, 128, 256],
        lstm_layers=2,
        use_attention=True
    ).to(device)
    model.eval()
    
    seq_length = 5
    batch_size = 2
    x = torch.randn(batch_size, seq_length, 3, 256, 256).to(device)
    
    with torch.no_grad():
        output, boundary_map = model(x, return_boundary=True)
    
    print(f"时间序列输入 shape: {x.shape}")
    print(f"变化检测结果 shape: {output.shape}")
    print(f"边界注意力图 shape: {boundary_map.shape}")
    
    siamese = SiameseLSTM(
        in_channels=3,
        num_classes=1,
        hidden_dim=128,
        num_layers=2
    ).to(device)
    siamese.eval()
    
    with torch.no_grad():
        output2 = siamese(x)
    
    print(f"SiameseLSTM输出 shape: {output2.shape}")
    print("多时相序列变化检测模型测试完成")
    print()


def example_4_geojson_export():
    """示例4: GeoJSON矢量结果导出"""
    print("=" * 80)
    print("EXAMPLE 4: GeoJSON矢量结果导出")
    print("=" * 80)
    
    from cd_tool.utils import GeoJSONExporter, ChangeStatistics, MultiTemporalChangeAnalyzer
    
    mask = np.zeros((256, 256), dtype=np.uint8)
    cv2.rectangle(mask, (50, 50), (150, 150), 1, -1)
    cv2.circle(mask, (200, 200), 30, 1, -1)
    
    transform = (116.0, 0.0001, 0.0, 39.0, 0.0, -0.0001)
    
    exporter = GeoJSONExporter(crs="EPSG:4326", min_area=10)
    
    confidence = np.random.rand(256, 256).astype(np.float32)
    feature_ids = exporter.add_from_mask(
        mask=mask,
        transform=transform,
        change_type="building",
        confidence=confidence,
        properties={"source": "deep_learning", "method": "UNet"}
    )
    
    print(f"添加的变化特征数量: {len(feature_ids)}")
    
    geojson = exporter.export("change_detection_result.geojson", pretty=True)
    print("GeoJSON已保存至 change_detection_result.geojson")
    print(f"GeoJSON结构: {geojson.keys()}")
    print(f"Features数量: {len(geojson['features'])}")
    
    if geojson['features']:
        print(f"第一个Feature属性: {geojson['features'][0]['properties'].keys()}")
    
    stats = ChangeStatistics()
    pixel_area = 100
    stats.calculate(mask, pixel_area=pixel_area)
    print(f"\n变化统计:")
    print(f"  总像素: {stats.stats['total_pixels']}")
    print(f"  变化像素: {stats.stats['changed_pixels']}")
    print(f"  变化比例: {stats.stats['change_ratio']:.2%}")
    print(f"  变化区域数: {stats.stats['change_regions_count']}")
    print(f"  最大区域面积: {stats.stats['largest_region_area']:.1f} 平方米")
    
    analyzer = MultiTemporalChangeAnalyzer()
    for i in range(3):
        mask_t = np.zeros((256, 256), dtype=np.uint8)
        cv2.rectangle(mask_t, (50 + i*20, 50 + i*20), (150, 150), 1, -1)
        analyzer.add_temporal_change(mask_t, f"202{i}")
    
    prog_stats = analyzer.analyze_progression()
    print(f"\n时序分析:")
    print(f"  时间点: {prog_stats['timestamps']}")
    print(f"  每时期变化像素: {prog_stats['changes_per_timestamp']}")
    print(f"  持续变化区域: {prog_stats['persistent_change_regions']}")
    print()


def example_5_complete_pipeline():
    """示例5: 完整的变化检测流程"""
    print("=" * 80)
    print("EXAMPLE 5: 完整变化检测流程演示")
    print("=" * 80)
    
    from cd_tool.models import UNet
    from cd_tool.utils import (
        ChangeSegmenter,
        AttentionVisualizer,
        PseudoLabeler,
        GeoJSONExporter,
        ChangeStatistics
    )
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print("1. 初始化模型...")
    model = UNet(
        n_channels=6,
        n_classes=1,
        use_attention=True,
        use_boundary_attention=True
    ).to(device)
    
    print("2. 生成模拟输入...")
    img1 = torch.randn(1, 3, 256, 256).to(device)
    img2 = torch.randn(1, 3, 256, 256).to(device)
    
    print("3. 模型推理...")
    model.eval()
    with torch.no_grad():
        pred = model.predict(img1, img2)
    
    pred_np = pred.squeeze().cpu().numpy()
    
    print("4. 变化区域分割与后处理...")
    segmenter = ChangeSegmenter(threshold=0.5)
    mask = (pred_np > 0.5).astype(np.uint8)
    clean_mask = segmenter.post_process(mask, min_area=100)
    regions = segmenter.get_change_regions(clean_mask)
    print(f"   检测到 {len(regions)} 个变化区域")
    
    print("5. 注意力可视化...")
    visualizer = AttentionVisualizer(model, device)
    att_maps = visualizer.get_attention_maps(img1, img2)
    print(f"   可视化 {len(att_maps)} 层注意力图")
    
    print("6. GeoJSON导出...")
    exporter = GeoJSONExporter()
    transform = (116.0, 0.0001, 0.0, 39.0, 0.0, -0.0001)
    exporter.add_from_mask(clean_mask, transform, confidence=pred_np)
    exporter.export("complete_pipeline_result.geojson")
    print("   结果已导出至 complete_pipeline_result.geojson")
    
    print("7. 变化统计...")
    stats = ChangeStatistics()
    stats.calculate(clean_mask, pixel_area=100)
    print(f"   变化比例: {stats.stats['change_ratio']:.2%}")
    print(f"   变化区域数: {stats.stats['change_regions_count']}")
    
    print("\n完整流程测试完成!")
    print()


def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 8 + "遥感图像变化检测库 v0.3.0 - 新功能演示" + " " * 20 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    example_1_attention_visualization()
    example_2_pseudo_labeling()
    example_3_temporal_change_detection()
    example_4_geojson_export()
    example_5_complete_pipeline()
    
    print("=" * 80)
    print("所有示例测试完成!")
    print("=" * 80)
    print("\n新增功能汇总:")
    print("  ✓ 注意力可视化与热力图生成")
    print("  ✓ 多种主动学习策略 (Entropy, Margin, LeastConfidence, BALD)")
    print("  ✓ 伪标签生成与后处理优化")
    print("  ✓ ConvLSTM多时相序列变化检测模型")
    print("  ✓ GeoJSON矢量结果导出 (支持地理坐标变换)")
    print("  ✓ 变化区域统计分析")
    print("  ✓ 多时相变化时序分析")
    print("\n")


if __name__ == "__main__":
    main()
