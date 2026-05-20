import numpy as np
import matplotlib.pyplot as plt
from hsi_classification import (
    PCA, SVMClassifier, CNNClassifier, CNN3DClassifier,
    TransferLearningClassifier, ActiveLearning, ClassificationVisualizer,
    Metrics, utils
)


def test_3d_cnn():
    print("\n" + "=" * 60)
    print("测试 3D CNN - 空谱联合特征提取")
    print("=" * 60)
    
    X, y = utils.generate_sample_data(height=50, width=50, bands=100, num_classes=8)
    X, y_train, y_test = utils.split_train_test(X, y, train_ratio=0.1)
    
    num_classes = len(np.unique(y[y > 0]))
    print(f"数据形状: {X.shape}")
    print(f"类别数: {num_classes}")
    print(f"训练样本数: {np.sum(y_train > 0)}")
    
    model_3d = CNN3DClassifier(
        input_bands=X.shape[-1],
        num_classes=num_classes,
        patch_size=7,
        batch_size=16,
        learning_rate=0.001
    )
    
    print("\n训练 3D CNN...")
    model_3d.fit(X, y_train, epochs=30, verbose=True)
    
    print("\n预测...")
    y_pred_3d = model_3d.predict(X)
    
    metrics_3d = Metrics(y_test, y_pred_3d)
    print("\n3D CNN 分类结果:")
    print(metrics_3d.get_all_metrics())
    
    return X, y, y_pred_3d


def test_transfer_learning():
    print("\n" + "=" * 60)
    print("测试迁移学习 - ImageNet -> 遥感")
    print("=" * 60)
    
    X, y = utils.generate_sample_data(height=50, width=50, bands=100, num_classes=8)
    X, y_train, y_test = utils.split_train_test(X, y, train_ratio=0.1)
    
    num_classes = len(np.unique(y[y > 0]))
    print(f"数据形状: {X.shape}")
    print(f"类别数: {num_classes}")
    
    tl_model = TransferLearningClassifier(
        num_classes=num_classes,
        backbone='resnet18',
        freeze_backbone=True,
        batch_size=8,
        learning_rate=0.001
    )
    
    print(f"\n使用 backbone: {tl_model.backbone}")
    print(f"冻结 backbone: {tl_model.freeze_backbone}")
    
    print("\n训练分类头...")
    tl_model.fit(X, y_train, epochs=20, verbose=True)
    
    print("\n解冻 backbone 微调...")
    tl_model.unfreeze_backbone()
    tl_model.fit(X, y_train, epochs=10, verbose=True)
    
    print("\n预测...")
    y_pred_tl = tl_model.predict(X)
    
    metrics_tl = Metrics(y_test, y_pred_tl)
    print("\n迁移学习分类结果:")
    print(metrics_tl.get_all_metrics())
    
    return X, y, y_pred_tl


def test_active_learning():
    print("\n" + "=" * 60)
    print("测试主动学习样本选择")
    print("=" * 60)
    
    X, y = utils.generate_sample_data(height=50, width=50, bands=100, num_classes=8)
    
    initial_labeled = np.zeros_like(y)
    labeled_coords = np.random.choice(np.arange(50), (30, 2), replace=False)
    for i, j in labeled_coords:
        if y[i, j] > 0:
            initial_labeled[i, j] = y[i, j]
    
    print(f"初始标记样本数: {np.sum(initial_labeled > 0)}")
    
    strategies = ['uncertainty', 'entropy', 'margin', 'diversity', 'random']
    
    num_classes = len(np.unique(y[y > 0]))
    
    for strategy in strategies:
        print(f"\n{'=' * 50}")
        print(f"策略: {strategy}")
        print(f"{'=' * 50}")
        
        al = ActiveLearning(strategy=strategy)
        
        def svm_wrapper(input_bands=None, num_classes=None, **kwargs):
            pca = PCA(n_components=30)
            return SVMClassifier(**kwargs)
        
        y_train_final, labeled_counts, accuracies = al.active_learning_cycle(
            X, initial_labeled,
            model_class=SVMClassifier,
            model_params={'kernel': 'rbf', 'C': 100},
            n_cycles=4,
            n_samples_per_cycle=20,
            strategy=strategy
        )
        
        print(f"最终标记样本数: {labeled_counts[-1]}")
        print(f"最终准确率: {accuracies[-1] * 100:.2f}%")


def test_visualization():
    print("\n" + "=" * 60)
    print("测试分类结果可视化")
    print("=" * 60)
    
    X, y = utils.generate_sample_data(height=60, width=60, bands=100, num_classes=8)
    X, y_train, y_test = utils.split_train_test(X, y, train_ratio=0.15)
    
    num_classes = len(np.unique(y[y > 0]))
    
    cnn = CNNClassifier(
        input_channels=X.shape[-1],
        num_classes=num_classes,
        learning_rate=0.001
    )
    
    print("训练 CNN 模型...")
    cnn.fit(X, y_train, epochs=30, verbose=True)
    
    y_pred = cnn.predict(X)
    
    print("\n创建可视化...")
    visualizer = ClassificationVisualizer(figsize=(14, 10))
    
    print("1. 伪彩色图像...")
    visualizer.plot_pseudocolor_image(
        X,
        bands=[30, 60, 90],
        title='HSI Pseudocolor Composite',
        save_path='pseudocolor.png',
        show=False
    )
    
    print("2. 分类图对比...")
    visualizer.plot_classification_map(
        y_pred,
        y_true=y,
        title='CNN Classification',
        save_path='classification.png',
        show=False
    )
    
    print("3. 综合对比面板...")
    visualizer.plot_comparison_panel(
        X,
        y,
        y_pred,
        rgb_bands=[20, 50, 80],
        save_path='comparison_panel.png',
        show=False
    )
    
    print("4. 光谱曲线...")
    class_coords = []
    class_labels = []
    for cls in range(1, num_classes + 1):
        coords = np.argwhere(y == cls)
        if len(coords) > 0:
            class_coords.append(tuple(coords[0]))
            class_labels.append(f'Class {cls}')
    
    if class_coords:
        visualizer.plot_spectral_signature(
            X,
            class_coords,
            labels=class_labels,
            title='Spectral Signatures by Class',
            save_path='spectral_signatures.png',
            show=False
        )
    
    print("\n可视化图像已保存!")
    
    metrics = Metrics(y_test, y_pred)
    print("\n最终分类结果:")
    print(metrics.get_all_metrics())
    
    return X, y, y_pred


def main():
    print("\n" + "=" * 60)
    print("高光谱图像分类库 - 高级功能演示 v2.0")
    print("=" * 60)
    
    print("\n功能列表:")
    print("1. 3D CNN - 空谱联合特征提取")
    print("2. 迁移学习 - ImageNet -> 遥感")
    print("3. 主动学习 - 多种样本选择策略")
    print("4. 分类结果可视化 - 伪彩色图等")
    
    choice = input("\n选择要测试的功能 (1-4, 0 全部测试): ").strip()
    
    if choice == '0' or choice == '':
        test_3d_cnn()
        test_transfer_learning()
        test_active_learning()
        test_visualization()
    elif choice == '1':
        test_3d_cnn()
    elif choice == '2':
        test_transfer_learning()
    elif choice == '3':
        test_active_learning()
    elif choice == '4':
        test_visualization()
    else:
        print("无效选择!")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
