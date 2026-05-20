# 高光谱图像分类库

基于 Spectral + PyTorch 的高光谱图像分类 Python 库。

## 功能特性

### 1. PCA降维 (`hsi_classification/pca.py`)
- 支持数据标准化
- 支持高维数据降维
- 方差解释率分析
- 支持数据重建

### 2. SVM分类器 (`hsi_classification/svm.py`)
- 基于 scikit-learn 的 SVM 实现
- 支持多种核函数 (linear, rbf, poly, sigmoid)
- 支持网格搜索调参
- 支持概率输出

### 3. CNN分类器 (`hsi_classification/cnn.py`)
- 基于 PyTorch 的深度学习分类器
- 支持空间-光谱联合特征提取
- 支持 GPU/CPU 训练
- 模型保存与加载
- 训练过程可视化

### 4. 分类精度评估 (`hsi_classification/metrics.py`)
- 总体精度 (OA)
- 平均精度 (AA)
- Kappa 系数
- Precision, Recall, F1-Score
- 混淆矩阵可视化
- 分类图可视化

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 基本使用示例

```python
import numpy as np
from hsi_classification import PCA, SVMClassifier, CNNClassifier, Metrics, utils

# 1. 加载或生成数据
X, y = utils.generate_sample_data(height=100, width=100, bands=200, num_classes=10)

# 2. 划分训练集和测试集
X, y_train, y_test = utils.split_train_test(X, y, train_ratio=0.1)

# 3. PCA降维
pca = PCA(n_components=30)
X_pca = pca.fit_transform(X)
print(f"累计方差解释率: {pca.get_cumulative_variance_ratio()[-1]:.4f}")

# 4. SVM分类
svm = SVMClassifier(kernel='rbf', C=100, gamma='scale')
svm.fit(X_pca, y_train)
y_pred_svm = svm.predict(X_pca)

# 5. 评估SVM结果
metrics_svm = Metrics(y_test, y_pred_svm)
print(metrics_svm.get_all_metrics())

# 6. CNN分类
num_classes = len(np.unique(y[y > 0]))
cnn = CNNClassifier(
    input_channels=X.shape[-1],
    num_classes=num_classes,
    patch_size=5,
    batch_size=32
)
cnn.fit(X, y_train, epochs=50, verbose=True)
y_pred_cnn = cnn.predict(X)

# 7. 评估CNN结果
metrics_cnn = Metrics(y_test, y_pred_cnn)
print(metrics_cnn.get_all_metrics())

# 8. 可视化混淆矩阵
metrics_cnn.plot_confusion_matrix(save_path='confusion_matrix.png')

# 9. 可视化分类图
metrics_cnn.plot_classification_map(save_path='classification_map.png')

# 10. 保存模型
cnn.save_model('cnn_model.pth')
```

### 数据可视化

```python
# 可视化单个波段
utils.visualize_band(X, band_idx=50)

# 可视化RGB合成图
utils.visualize_rgb(X, r_band=100, g_band=50, b_band=20)

# 可视化像元光谱曲线
utils.visualize_spectrum(X, x=50, y=50)

# 可视化地物真值
utils.visualize_ground_truth(y)
```

### 加载真实数据

```python
# 加载 ENVI 格式数据
X = utils.load_envi_data('data.hdr')

# 加载 MATLAB .mat 格式数据
X, y = utils.load_mat_data('data.mat', data_key='X', label_key='y')
```

## API 参考

### PCA 类

```python
PCA(n_components=None, whiten=False, standardize=True)
```

**方法:**
- `fit(X)`: 拟合 PCA 模型
- `transform(X)`: 对数据进行降维
- `fit_transform(X)`: 拟合并转换
- `inverse_transform(X)`: 重建数据
- `get_explained_variance_ratio()`: 获取方差解释率
- `get_cumulative_variance_ratio()`: 获取累计方差解释率

### SVMClassifier 类

```python
SVMClassifier(kernel='rbf', C=1.0, gamma='scale', standardize=True, random_state=42)
```

**方法:**
- `fit(X, y)`: 训练 SVM 模型
- `predict(X)`: 预测类别
- `predict_proba(X)`: 预测概率
- `score(X, y)`: 计算准确率
- `grid_search(X, y, param_grid, cv=5)`: 网格搜索调参

### CNNClassifier 类

```python
CNNClassifier(input_channels, num_classes, patch_size=5, device=None, 
              learning_rate=0.001, batch_size=64, random_state=42)
```

**方法:**
- `fit(X_train, y_train, X_val=None, y_val=None, epochs=100, verbose=True)`: 训练模型
- `predict(X)`: 预测类别
- `predict_proba(X)`: 预测概率
- `save_model(path)`: 保存模型
- `load_model(path)`: 加载模型

### Metrics 类

```python
Metrics(y_true, y_pred, class_names=None)
```

**方法:**
- `overall_accuracy()`: 总体精度
- `average_accuracy()`: 平均精度和各类精度
- `kappa_coefficient()`: Kappa 系数
- `precision()`: 精确率
- `recall()`: 召回率
- `f1_score()`: F1 分数
- `confusion_matrix()`: 混淆矩阵
- `classification_report()`: 分类报告
- `get_all_metrics()`: 获取所有指标
- `plot_confusion_matrix()`: 绘制混淆矩阵
- `plot_classification_map()`: 绘制分类图

## 项目结构

```
hsi_classification/
├── __init__.py          # 包初始化
├── pca.py              # PCA降维模块
├── svm.py              # SVM分类模块
├── cnn.py              # CNN分类模块
├── metrics.py          # 评估指标模块
└── utils.py            # 工具函数模块
requirements.txt        # 依赖列表
example.py              # 示例代码
README.md               # 说明文档
```

## 注意事项

1. 高光谱图像的标签约定: 0 表示背景/未标记，1~N 表示各类别
2. CNN 训练时，建议使用 GPU 加速
3. PCA 降维后再使用 SVM 可以显著提升速度和效果
4. 建议先对数据进行可视化，了解数据分布

## 许可证

MIT License
