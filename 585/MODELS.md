# 模型权重下载说明

## 所需模型文件

请按以下步骤下载所需的模型权重文件，并放置到对应的目录中。

### 1. SMPL 模型

**路径**: `models/smpl/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl`

- 下载地址: https://smpl.is.tue.mpg.de/
- 需要注册账号
- 下载 "SMPL for Python" 版本
- 解压后找到 `basicModel_neutral_lbs_10_207_0_v1.0.0.pkl`

### 2. HMR 预训练模型

**路径**: `models/hmr/hmr_pretrained.pt`

- 下载地址: https://github.com/akanazawa/hmr
- 下载预训练的 ResNet-50 模型
- 原始文件名可能是 `hmr_resnet50.pt` 或类似名称
- 重命名为 `hmr_pretrained.pt`

### 3. OpenPose 模型

#### 身体模型

- **Proto**: `models/openpose/pose_deploy_linevec.prototxt`
- **Weights**: `models/openpose/pose_iter_440000.caffemodel`

#### 手部模型

- **Proto**: `models/openpose/pose_deploy.prototxt`
- **Weights**: `models/openpose/pose_iter_102000.caffemodel`

- 下载地址: https://github.com/CMU-Perceptual-Computing-Lab/openpose
- 或使用百度云/Google Drive 镜像

## 目录结构

```
models/
├── smpl/
│   └── basicModel_neutral_lbs_10_207_0_v1.0.0.pkl
├── hmr/
│   └── hmr_pretrained.pt
└── openpose/
    ├── pose_deploy_linevec.prototxt
    ├── pose_iter_440000.caffemodel
    ├── pose_deploy.prototxt
    └── pose_iter_102000.caffemodel
```

## 快速测试

在下载完模型后，运行以下命令验证安装：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行基本测试
python test_simple.py

# 启动 Streamlit 界面
streamlit run app.py
```

## 注意事项

1. 确保所有路径与 `utils/config.py` 中的配置一致
2. 如果模型文件缺失，系统会打印警告但仍可运行（使用随机权重）
3. 推荐使用 CUDA 加速，确保 PyTorch 安装了 CUDA 版本
4. 首次运行会自动创建必要的目录结构
