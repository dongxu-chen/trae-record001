import numpy as np
import matplotlib.pyplot as plt
import os
import torch
from hsi_classification import (
    MonaiClassifier,
    MultiModalClassifier,
    ONNXExporter,
    ONNXInference,
    LiDARProcessor,
    Metrics,
    utils,
)


def generate_multimodal_data(n_samples=100, height=64, width=64, hsi_bands=200, lidar_bands=4, num_classes=8):
    hsi_data = []
    lidar_data = []
    labels = []
    
    for _ in range(n_samples):
        hsi = np.random.randn(height, width, hsi_bands).astype(np.float32)
        lidar = np.random.randn(height, width, lidar_bands).astype(np.float32)
        label = np.random.randint(0, num_classes)
        
        for cls in range(num_classes):
            mask = (np.arange(height * width) % num_classes == cls).reshape(height, width)
            hsi[mask, :] += cls * 0.3
            lidar[mask, 0] += cls * 0.1
        
        hsi_data.append(hsi)
        lidar_data.append(lidar)
        labels.append(label)
    
    return np.array(hsi_data), np.array(lidar_data), np.array(labels)


def test_monai_classifier():
    print("\n" + "=" * 60)
    print("测试 MONAI 分类器")
    print("=" * 60)
    
    images, labels = utils.generate_sample_data(
        height=64, width=64, bands=200, num_classes=8, n_samples=200
    )
    labels = labels[:, 0, 0]
    
    split_idx = int(0.8 * len(images))
    train_images, val_images = images[:split_idx], images[split_idx:]
    train_labels, val_labels = labels[:split_idx], labels[split_idx:]
    
    classifier = MonaiClassifier(
        num_classes=8,
        input_channels=200,
        model_name='resnet50',
        spatial_dims=2,
    )
    
    print(f"Model: {classifier.model_name}")
    print(f"Device: {classifier.device}")
    
    train_dataset = classifier.prepare_data(
        train_images,
        train_labels,
        mode='train',
    )
    
    val_dataset = classifier.prepare_data(
        val_images,
        val_labels,
        mode='val',
    )
    
    train_loader = classifier.create_dataloader(
        train_dataset,
        batch_size=16,
        shuffle=True,
    )
    
    val_loader = classifier.create_dataloader(
        val_dataset,
        batch_size=16,
        shuffle=False,
    )
    
    classifier.configure_optimizer(lr=1e-4, optimizer_type='adamw')
    classifier.configure_scheduler(scheduler_type='cosine', T_max=50)
    classifier.configure_loss(loss_type='cross_entropy')
    
    print("\n开始训练...")
    train_losses, val_metrics = classifier.fit(
        train_loader,
        val_loader,
        epochs=20,
        save_dir='./models',
        save_name='monai_best.pth',
        verbose=True,
    )
    
    print("\n训练完成！")
    print(f"最佳验证准确率: {classifier.best_metric:.4f}")
    
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(train_losses)
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.grid(True, alpha=0.3)
    
    if val_metrics:
        plt.subplot(1, 2, 2)
        plt.plot(val_metrics)
        plt.title('Validation Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('./models/monai_training_curves.png', dpi=300)
    print("训练曲线已保存到 ./models/monai_training_curves.png")
    
    return classifier


def test_multimodal_classifier():
    print("\n" + "=" * 60)
    print("测试多模态分类器 (HSI + LiDAR)")
    print("=" * 60)
    
    hsi_data, lidar_data, labels = generate_multimodal_data(
        n_samples=200,
        height=64,
        width=64,
        hsi_bands=200,
        lidar_bands=4,
        num_classes=8,
    )
    
    split_idx = int(0.8 * len(hsi_data))
    train_hsi, val_hsi = hsi_data[:split_idx], hsi_data[split_idx:]
    train_lidar, val_lidar = lidar_data[:split_idx], lidar_data[split_idx:]
    train_labels, val_labels = labels[:split_idx], labels[split_idx:]
    
    fusion_types = ['concatenate', 'attention', 'gated']
    
    for fusion_type in fusion_types:
        print(f"\n{'=' * 50}")
        print(f"融合方式: {fusion_type}")
        print(f"{'=' * 50}")
        
        classifier = MultiModalClassifier(
            num_classes=8,
            hsi_channels=200,
            lidar_channels=4,
            fusion_type=fusion_type,
        )
        
        print(f"模型结构: {classifier.model.__class__.__name__}")
        
        train_dataset = classifier.prepare_data(
            train_hsi,
            train_lidar,
            train_labels,
            mode='train',
        )
        
        val_dataset = classifier.prepare_data(
            val_hsi,
            val_lidar,
            val_labels,
            mode='val',
        )
        
        train_loader = classifier.create_dataloader(
            train_dataset,
            batch_size=16,
            shuffle=True,
        )
        
        val_loader = classifier.create_dataloader(
            val_dataset,
            batch_size=16,
            shuffle=False,
        )
        
        classifier.configure_optimizer(lr=1e-4)
        classifier.configure_scheduler(T_max=30)
        classifier.configure_loss()
        
        print("开始训练...")
        train_losses, val_metrics = classifier.fit(
            train_loader,
            val_loader,
            epochs=20,
            save_dir='./models',
            save_name=f'multimodal_{fusion_type}_best.pth',
            verbose=True,
        )
        
        print(f"最佳验证准确率: {classifier.best_metric:.4f}")
    
    return classifier


def test_onnx_export():
    print("\n" + "=" * 60)
    print("测试 ONNX 模型导出和推理")
    print("=" * 60)
    
    classifier = MonaiClassifier(
        num_classes=8,
        input_channels=200,
        model_name='resnet18',
        spatial_dims=2,
    )
    
    os.makedirs('./models', exist_ok=True)
    
    exporter = ONNXExporter(classifier)
    
    input_shape = (1, 200, 64, 64)
    onnx_path = exporter.export(
        input_shape=input_shape,
        output_path='./models/model.onnx',
        opset_version=17,
        verbose=True,
    )
    
    print(f"\n模型已导出到: {onnx_path}")
    
    print("\n测试 ONNX 推理...")
    try:
        inference = ONNXInference(onnx_path)
        
        test_input = np.random.randn(4, 200, 64, 64).astype(np.float32)
        predictions, probabilities = inference.predict(test_input)
        
        print(f"输入形状: {test_input.shape}")
        print(f"预测结果: {predictions}")
        print(f"概率形状: {probabilities.shape}")
        
        print("\n批量推理测试...")
        batch_predictions, batch_probs = inference.predict_batch(test_input, batch_size=2)
        print(f"批量预测结果: {batch_predictions}")
        
        print("✅ ONNX 推理测试通过!")
        
    except Exception as e:
        print(f"⚠️  ONNX 推理需要安装 onnxruntime:")
        print(f"   pip install onnxruntime-gpu")
        print(f"   错误信息: {str(e)}")


def test_lidar_processor():
    print("\n" + "=" * 60)
    print("测试 LiDAR 点云特征提取")
    print("=" * 60)
    
    n_points = 10000
    point_cloud = np.random.randn(n_points, 4)
    point_cloud[:, :2] = np.abs(point_cloud[:, :2]) * 100
    point_cloud[:, 2] = np.abs(point_cloud[:, 2]) * 20
    point_cloud[:, 3] = np.random.rand(n_points) * 255
    
    print(f"点云形状: {point_cloud.shape}")
    print(f"点云统计:")
    print(f"  X: [{point_cloud[:, 0].min():.2f}, {point_cloud[:, 0].max():.2f}]")
    print(f"  Y: [{point_cloud[:, 1].min():.2f}, {point_cloud[:, 1].max():.2f}]")
    print(f"  Z: [{point_cloud[:, 2].min():.2f}, {point_cloud[:, 2].max():.2f}]")
    print(f"  Intensity: [{point_cloud[:, 3].min():.2f}, {point_cloud[:, 3].max():.2f}]")
    
    features = LiDARProcessor.compute_features(point_cloud, grid_size=(64, 64))
    
    print(f"\n提取的 LiDAR 特征形状: {features.shape}")
    print(f"特征统计:")
    feature_names = ['平均高度', '高度方差', '平均强度', '点密度']
    for i, name in enumerate(feature_names):
        print(f"  {name}: [{features[:, :, i].min():.2f}, {features[:, :, i].max():.2f}]")
    
    plt.figure(figsize=(16, 4))
    for i in range(4):
        plt.subplot(1, 4, i + 1)
        plt.imshow(features[:, :, i], cmap='viridis')
        plt.title(feature_names[i])
        plt.colorbar(label='Value', shrink=0.8)
        plt.axis('off')
    
    plt.tight_layout()
    plt.savefig('./models/lidar_features.png', dpi=300, bbox_inches='tight')
    print("\nLiDAR 特征可视化已保存到 ./models/lidar_features.png")
    
    return features


def main():
    print("\n" + "=" * 60)
    print("高光谱图像分类库 - MONAI 版 v3.0")
    print("=" * 60)
    
    choice = input("\n选择测试功能:\n"
                   "1. MONAI 分类器训练\n"
                   "2. 多模态融合 (HSI + LiDAR)\n"
                   "3. ONNX 导出和推理\n"
                   "4. LiDAR 特征提取\n"
                   "0. 全部测试\n"
                   "输入选项: ").strip()
    
    if choice == '1' or choice == '0' or choice == '':
        test_monai_classifier()
    
    if choice == '2' or choice == '0':
        test_multimodal_classifier()
    
    if choice == '3' or choice == '0':
        test_onnx_export()
    
    if choice == '4' or choice == '0':
        test_lidar_processor()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
