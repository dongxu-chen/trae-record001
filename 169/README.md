# 🚗 车牌识别系统 (License Plate Recognition System)

基于 Python + OpenCV + PaddleOCR 实现的高性能车牌识别系统后端，支持蓝牌、绿牌、黄牌、新能源车牌的检测与识别。

## ✨ 功能特性

- **低光照图像增强**: 自适应伽马校正、CLAHE对比度增强、双边滤波去噪
- **多角度车牌校正**: 仿射变换、透视变换、霍夫变换倾斜校正
- **多类型车牌检测**: 支持蓝牌、绿牌、黄牌、新能源小车/大车
- **高精度字符识别**: 基于PaddleOCR的中文字符识别，支持字符纠错
- **RESTful API**: 完整的Flask后端服务，支持单张/批量识别
- **高识别率**: 优化的算法流程，白天识别率可达98%以上

## 📁 项目结构

```
.
├── app.py                      # Flask后端API服务
├── config.py                   # 配置文件
├── license_plate_recognition.py # 主流程整合模块
├── image_enhancer.py           # 低光照图像增强模块
├── plate_detector.py           # 车牌检测模块
├── plate_corrector.py          # 车牌校正模块
├── ocr_recognizer.py           # OCR字符识别模块
├── plate_classifier.py         # 车牌类型分类模块
├── test_lpr.py                 # 测试脚本
├── requirements.txt            # Python依赖
├── uploads/                    # 上传图片目录
├── outputs/                    # 处理结果目录
└── temp/                       # 临时文件目录
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动

### 3. 测试系统

```bash
# 查看系统信息
python test_lpr.py --test-info

# 创建测试图片并测试
python test_lpr.py --create-test

# 测试单张图片
python test_lpr.py --image your_image.jpg

# 测试目录下所有图片
python test_lpr.py --dir /path/to/images

# 测试低光照增强
python test_lpr.py --image your_image.jpg --test-enhance
```

## 🔌 API 接口

### 健康检查
```http
GET /api/health
```

### 系统信息
```http
GET /api/info
```

### 单张图片识别
```http
POST /api/recognize
Content-Type: multipart/form-data

参数:
- image: 图片文件
- save_images: 是否保存处理结果 (可选, 默认: true)
```

### 批量图片识别
```http
POST /api/recognize_batch
Content-Type: multipart/form-data

参数:
- images: 多个图片文件
- save_images: 是否保存处理结果 (可选, 默认: true)
```

### 获取处理后的图片
```http
GET /api/output/<filename>
```

## 📝 响应格式

```json
{
  "success": true,
  "code": 200,
  "message": "识别成功",
  "data": {
    "request_id": "uuid-string",
    "timestamp": "20240101_120000",
    "success": true,
    "plate_count": 1,
    "results": [
      {
        "plate_index": 0,
        "bbox": [x, y, width, height],
        "ocr_text": "京A12345",
        "ocr_confidence": 0.95,
        "plate_type": "blue",
        "plate_type_name": "蓝牌",
        "detection_confidence": 90.5
      }
    ],
    "best_result": { ... },
    "overall_confidence": 0.95
  },
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

## 🎯 支持的车牌类型

| 类型 | 代码 | 字符数 | 说明 |
|------|------|--------|------|
| 蓝牌 | blue | 7 | 普通小型汽车 |
| 绿牌 | green | 8 | 新能源汽车 |
| 黄牌 | yellow | 7 | 大型汽车、教练车等 |
| 新能源小车 | new_energy_small | 8 | 小型新能源汽车 |
| 新能源大车 | new_energy_large | 8 | 大型新能源汽车 |

## ⚙️ 配置说明

在 `config.py` 中可以调整以下参数：

- **HSV颜色范围**: 调整不同车牌类型的颜色检测阈值
- **OCR配置**: PaddleOCR模型路径、语言设置
- **图像增强参数**: 伽马值、CLAHE限制、滤波参数
- **检测参数**: 最小/最大面积、长宽比范围

## 🔧 技术栈

- **Python 3.8+**: 开发语言
- **OpenCV**: 图像处理、特征提取
- **PaddleOCR**: 字符识别
- **Flask**: Web框架
- **NumPy/SciPy**: 数值计算

## 📊 性能优化建议

1. **模型优化**: 使用轻量化PaddleOCR模型提高速度
2. **缓存策略**: 对重复请求结果进行缓存
3. **批量处理**: 使用批量识别提高吞吐量
4. **硬件加速**: 使用GPU加速PaddleOCR推理
5. **图片尺寸**: 合理限制上传图片大小

## 🐛 常见问题

### 1. PaddleOCR 安装失败
```bash
# 先安装paddlepaddle
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
# 再安装paddleocr
pip install paddleocr
```

### 2. 识别率低
- 检查图片清晰度和光照条件
- 调整HSV颜色阈值
- 尝试不同的增强参数

### 3. 服务启动慢
- PaddleOCR首次初始化需要下载模型
- 可以预下载模型到本地并配置路径

## 📄 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
