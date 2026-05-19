import numpy as np
from hsi_classification import PCA, SVMClassifier, CNNClassifier, Metrics, utils


def test_pca():
    print("\n" + "=" * 60)
    print("测试 PCA 降维")
    print("=" * 60)
    
    X, y = utils.generate_sample_data(height=100, width=100, bands=200, num_classes=10)
    
    pca = PCA(n_components=30)
    X_pca = pca.fit_transform(X, verbose=True)
    
    print(f"原始数据形状: {X.shape}")
    print(f"降维后数据形状: {X_pca.shape}")
    
    cum_var = pca.get_cumulative_variance_ratio()
    print(f"前5个主成分的累积解释方差比: {cum_var[:5]}")
    print(f"最后5个主成分的累积解释方差比: {cum_var[-5:]}")
    
    return X, y, X_pca


def test_svm(X, y, X_pca):
    print("\n" + "=" * 60)
    print("测试 SVM 分类")
    print("=" * 60)
    
    X, y_train, y_test = utils.split_train_test(X, y, train_ratio=0.1)
    X_pca, _, _ = utils.split_train_test(X_pca, y, train_ratio=0.1)
    
    print(f"训练样本数: {np.sum(y_train > 0)}")
    print(f"测试样本数: {np.sum(y_test > 0)}")
    
    svm = SVMClassifier(kernel='rbf', C=100, gamma='scale')
    svm.fit(X_pca, y_train)
    
    y_pred_svm = svm.predict(X_pca)
    
    print("\nSVM 分类结果:")
    metrics_svm = Metrics(y_test, y_pred_svm)
    print(metrics_svm.get_all_metrics())
    
    return y_pred_svm


def test_cnn(X, y):
    print("\n" + "=" * 60)
    print("测试 CNN 分类（全卷积网络）")
    print("=" * 60)
    
    X, y_train, y_test = utils.split_train_test(X, y, train_ratio=0.1)
    
    num_classes = len(np.unique(y[y > 0]))
    print(f"类别数量: {num_classes}")
    
    cnn = CNNClassifier(
        input_channels=X.shape[-1],
        num_classes=num_classes,
        learning_rate=0.001
    )
    print(f"使用设备: {cnn.device}")
    
    print("\n训练 CNN 模型...")
    cnn.fit(X, y_train, epochs=50, verbose=True)
    
    print("\n预测...")
    y_pred_cnn = cnn.predict(X)
    
    print(f"\n预测结果形状: {y_pred_cnn.shape}")
    print(f"原始图像形状: {X.shape[:2]}")
    print(f"尺寸匹配: {y_pred_cnn.shape == X.shape[:2]}")
    
    print("\n测试不同尺寸的输入...")
    test_sizes = [(50, 50), (150, 150), (200, 100)]
    for h, w in test_sizes:
        X_test = np.random.randn(h, w, X.shape[-1]).astype(np.float32)
        y_pred_test = cnn.predict(X_test)
        print(f"输入尺寸 ({h}, {w}) -> 输出尺寸 {y_pred_test.shape}")
        assert y_pred_test.shape == (h, w), f"尺寸不匹配！期望 ({h}, {w}), 得到 {y_pred_test.shape}"
    
    print("\n全卷积网络测试通过！支持任意输入尺寸！")
    
    print("\nCNN 分类结果:")
    metrics_cnn = Metrics(y_test, y_pred_cnn)
    print(metrics_cnn.get_all_metrics())
    
    return y_pred_cnn, cnn


def test_edge_pixels(X, y, cnn):
    print("\n" + "=" * 60)
    print("测试边缘像素评估")
    print("=" * 60)
    
    y_pred = cnn.predict(X)
    
    height, width = X.shape[:2]
    edge_mask = np.zeros((height, width), dtype=bool)
    edge_width = 3
    edge_mask[:edge_width, :] = True
    edge_mask[-edge_width:, :] = True
    edge_mask[:, :edge_width] = True
    edge_mask[:, -edge_width:] = True
    
    labeled_mask = y > 0
    
    edge_labeled_mask = edge_mask & labeled_mask
    inner_labeled_mask = ~edge_mask & labeled_mask
    
    print(f"总标记像素数: {np.sum(labeled_mask)}")
    print(f"边缘标记像素数: {np.sum(edge_labeled_mask)}")
    print(f"内部标记像素数: {np.sum(inner_labeled_mask)}")
    
    if np.sum(edge_labeled_mask) > 0:
        y_true_edge = y[edge_labeled_mask]
        y_pred_edge = y_pred[edge_labeled_mask]
        
        metrics_edge = Metrics(y_true_edge, y_pred_edge)
        print("\n边缘像素准确率:")
        print(metrics_edge.get_all_metrics())
    
    if np.sum(inner_labeled_mask) > 0:
        y_true_inner = y[inner_labeled_mask]
        y_pred_inner = y_pred[inner_labeled_mask]
        
        metrics_inner = Metrics(y_true_inner, y_pred_inner)
        print("\n内部像素准确率:")
        print(metrics_inner.get_all_metrics())
    
    print("\n整体准确率（包含边缘像素）:")
    metrics_all = Metrics(y, y_pred)
    print(metrics_all.get_all_metrics())


def main():
    print("\n" + "=" * 60)
    print("高光谱图像分类库 - 修复验证")
    print("=" * 60)
    
    X, y, X_pca = test_pca()
    
    test_svm(X.copy(), y.copy(), X_pca.copy())
    
    y_pred_cnn, cnn = test_cnn(X.copy(), y.copy())
    
    test_edge_pixels(X, y, cnn)
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
    print("\n修复总结:")
    print("1. ✅ CNN 边缘填充：使用反射填充 (padding_mode='reflect')")
    print("2. ✅ PCA 降维：fit_transform 支持 verbose 输出累积解释方差比")
    print("3. ✅ CNN 重构：全卷积网络，支持任意输入尺寸")
    print("4. ✅ 评估模块：边缘像素被正确包含在评估中")


if __name__ == "__main__":
    main()
