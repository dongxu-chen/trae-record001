const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const { PNG } = require('pngjs');
const ImageInpainting = require('./inpainting');
const ImageClassifier = require('./imageClassifier');
const TextDetector = require('./textDetector');
const VideoProcessor = require('./videoProcessor');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(bodyParser.json({ limit: '100mb' }));
app.use(bodyParser.urlencoded({ limit: '100mb', extended: true }));

function base64ToBuffer(base64) {
  const base64Data = base64.replace(/^data:image\/\w+;base64,/, '');
  return Buffer.from(base64Data, 'base64');
}

function loadPNGFromBase64(base64) {
  return new Promise((resolve, reject) => {
    const buffer = base64ToBuffer(base64);
    const png = new PNG();
    png.parse(buffer, (err, data) => {
      if (err) reject(err);
      else resolve(data);
    });
  });
}

function getImageData(png) {
  return {
    data: new Uint8ClampedArray(png.data),
    width: png.width,
    height: png.height
  };
}

function createPNGFromData(imageData, width, height) {
  const png = new PNG({ width, height });
  png.data = Buffer.from(imageData);
  return png;
}

function pngToBase64(png) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    png.on('data', (chunk) => chunks.push(chunk));
    png.on('end', () => {
      const buffer = Buffer.concat(chunks);
      resolve('data:image/png;base64,' + buffer.toString('base64'));
    });
    png.on('error', reject);
    png.pack();
  });
}

function resizeImageData(srcData, srcWidth, srcHeight, dstWidth, dstHeight) {
  const dstData = new Uint8ClampedArray(dstWidth * dstHeight * 4);
  
  for (let y = 0; y < dstHeight; y++) {
    for (let x = 0; x < dstWidth; x++) {
      const srcX = Math.floor((x / dstWidth) * srcWidth);
      const srcY = Math.floor((y / dstHeight) * srcHeight);
      const srcIdx = (srcY * srcWidth + srcX) * 4;
      const dstIdx = (y * dstWidth + x) * 4;
      
      dstData[dstIdx] = srcData[srcIdx];
      dstData[dstIdx + 1] = srcData[srcIdx + 1];
      dstData[dstIdx + 2] = srcData[srcIdx + 2];
      dstData[dstIdx + 3] = srcData[srcIdx + 3];
    }
  }
  
  return dstData;
}

app.post('/api/inpaint', async (req, res) => {
  try {
    const { image, mask, algorithm = 'edge-guided', radius = 3, options = {} } = req.body;

    if (!image || !mask) {
      return res.status(400).json({ error: '图片和掩码都是必需的' });
    }

    const sourcePNG = await loadPNGFromBase64(image);
    const maskPNG = await loadPNGFromBase64(mask);

    const width = sourcePNG.width;
    const height = sourcePNG.height;

    let maskData;
    if (maskPNG.width !== width || maskPNG.height !== height) {
      const resizedMask = resizeImageData(
        new Uint8ClampedArray(maskPNG.data),
        maskPNG.width,
        maskPNG.height,
        width,
        height
      );
      maskData = resizedMask;
    } else {
      maskData = new Uint8ClampedArray(maskPNG.data);
    }

    const sourceData = getImageData(sourcePNG);

    const inpainter = new ImageInpainting(
      sourceData.data,
      maskData,
      width,
      height,
      options
    );

    const resultData = inpainter.inpaint(algorithm, parseInt(radius));

    const resultPNG = createPNGFromData(resultData, width, height);
    const resultBase64 = await pngToBase64(resultPNG);

    res.json({
      success: true,
      result: resultBase64,
      width,
      height,
      algorithm,
      radius
    });
  } catch (error) {
    console.error('图像修复错误:', error);
    res.status(500).json({
      success: false,
      error: '处理图片时发生错误: ' + error.message
    });
  }
});

app.post('/api/classify', async (req, res) => {
  try {
    const { image } = req.body;

    if (!image) {
      return res.status(400).json({ error: '图片数据是必需的' });
    }

    const sourcePNG = await loadPNGFromBase64(image);
    const sourceData = getImageData(sourcePNG);

    const classifier = new ImageClassifier(
      sourceData.data,
      sourcePNG.width,
      sourcePNG.height
    );

    const classification = classifier.classifyComplexity();

    res.json({
      success: true,
      classification,
      width: sourcePNG.width,
      height: sourcePNG.height
    });
  } catch (error) {
    console.error('图像分类错误:', error);
    res.status(500).json({
      success: false,
      error: '分类图片时发生错误: ' + error.message
    });
  }
});

app.post('/api/batch-classify', async (req, res) => {
  try {
    const { images } = req.body;

    if (!images || !Array.isArray(images)) {
      return res.status(400).json({ error: '图片列表是必需的' });
    }

    const imagesData = [];

    for (const img of images) {
      try {
        const sourcePNG = await loadPNGFromBase64(img.image);
        const sourceData = getImageData(sourcePNG);
        imagesData.push({
          data: sourceData.data,
          width: sourcePNG.width,
          height: sourcePNG.height,
          name: img.name
        });
      } catch (imgError) {
        imagesData.push({ error: imgError.message, name: img.name });
      }
    }

    const classification = ImageClassifier.classifyImages(imagesData.filter(img => !img.error));

    res.json({
      success: true,
      classification,
      total: images.length,
      classified: classification.images.length
    });
  } catch (error) {
    console.error('批量分类错误:', error);
    res.status(500).json({
      success: false,
      error: '批量分类时发生错误: ' + error.message
    });
  }
});

app.post('/api/batch-inpaint-grouped', async (req, res) => {
  try {
    const { images, groupOverrides = {}, useAutoParams = true } = req.body;

    if (!images || !Array.isArray(images)) {
      return res.status(400).json({ error: '图片列表是必需的' });
    }

    const imagesData = [];

    for (const img of images) {
      try {
        const sourcePNG = await loadPNGFromBase64(img.image);
        const maskPNG = img.mask ? await loadPNGFromBase64(img.mask) : null;
        const sourceData = getImageData(sourcePNG);
        
        imagesData.push({
          imageData: sourceData.data,
          maskData: maskPNG ? new Uint8ClampedArray(maskPNG.data) : null,
          width: sourcePNG.width,
          height: sourcePNG.height,
          name: img.name,
          classification: img.classification
        });
      } catch (imgError) {
        imagesData.push({ error: imgError.message, name: img.name });
      }
    }

    const defaultGroupParams = {
      simple: {
        algorithm: 'telea',
        radius: 2,
        preserveTexture: false,
        guideEdges: false
      },
      medium: {
        algorithm: 'edge-guided',
        radius: 3,
        preserveTexture: true,
        guideEdges: true
      },
      complex: {
        algorithm: 'texture-preserving',
        radius: 4,
        preserveTexture: true,
        guideEdges: true
      },
      'very-complex': {
        algorithm: 'advanced',
        radius: 5,
        preserveTexture: true,
        guideEdges: true
      }
    };

    const mergedGroupParams = {};
    for (const level of ['simple', 'medium', 'complex', 'very-complex']) {
      mergedGroupParams[level] = {
        ...defaultGroupParams[level],
        ...(groupOverrides[level] || {})
      };
    }

    const results = [];

    for (let i = 0; i < imagesData.length; i++) {
      const imgData = imagesData[i];
      
      if (imgData.error) {
        results.push({
          name: imgData.name,
          success: false,
          error: imgData.error
        });
        continue;
      }

      try {
        const complexityLevel = imgData.classification?.level || 'medium';
        const params = useAutoParams ? mergedGroupParams[complexityLevel] : mergedGroupParams.medium;

        const inpainter = new ImageInpainting(
          imgData.imageData,
          imgData.maskData || new Uint8ClampedArray(imgData.width * imgData.height * 4),
          imgData.width,
          imgData.height,
          {
            preserveTexture: params.preserveTexture,
            guideEdges: params.guideEdges
          }
        );

        const resultData = inpainter.inpaint(params.algorithm, params.radius);
        const resultPNG = createPNGFromData(resultData, imgData.width, imgData.height);
        const resultBase64 = await pngToBase64(resultPNG);

        results.push({
          name: imgData.name,
          success: true,
          result: resultBase64,
          complexityLevel,
          algorithm: params.algorithm,
          radius: params.radius
        });
      } catch (processError) {
        results.push({
          name: imgData.name,
          success: false,
          error: processError.message
        });
      }
    }

    const groupStats = {};
    for (const level of ['simple', 'medium', 'complex', 'very-complex']) {
      groupStats[level] = results.filter(r => r.complexityLevel === level).length;
    }

    res.json({
      success: true,
      results,
      groupStats,
      total: images.length,
      successful: results.filter(r => r.success).length
    });
  } catch (error) {
    console.error('分组批量处理错误:', error);
    res.status(500).json({
      success: false,
      error: '分组批量处理时发生错误: ' + error.message
    });
  }
});

app.post('/api/batch-inpaint', async (req, res) => {
  try {
    const { images, algorithm = 'edge-guided', radius = 3, options = {} } = req.body;

    if (!images || !Array.isArray(images)) {
      return res.status(400).json({ error: '图片列表是必需的' });
    }

    const results = [];

    for (let i = 0; i < images.length; i++) {
      const { image, mask, name } = images[i];

      try {
        const sourcePNG = await loadPNGFromBase64(image);
        const maskPNG = await loadPNGFromBase64(mask);

        const width = sourcePNG.width;
        const height = sourcePNG.height;

        let maskData;
        if (maskPNG.width !== width || maskPNG.height !== height) {
          const resizedMask = resizeImageData(
            new Uint8ClampedArray(maskPNG.data),
            maskPNG.width,
            maskPNG.height,
            width,
            height
          );
          maskData = resizedMask;
        } else {
          maskData = new Uint8ClampedArray(maskPNG.data);
        }

        const sourceData = getImageData(sourcePNG);

        const inpainter = new ImageInpainting(
          sourceData.data,
          maskData,
          width,
          height,
          options
        );

        const resultData = inpainter.inpaint(algorithm, parseInt(radius));
        const resultPNG = createPNGFromData(resultData, width, height);
        const resultBase64 = await pngToBase64(resultPNG);

        results.push({
          name: name || `image_${i}`,
          success: true,
          result: resultBase64
        });
      } catch (imgError) {
        results.push({
          name: name || `image_${i}`,
          success: false,
          error: imgError.message
        });
      }
    }

    res.json({
      success: true,
      results
    });
  } catch (error) {
    console.error('批量处理错误:', error);
    res.status(500).json({
      success: false,
      error: '批量处理时发生错误: ' + error.message
    });
  }
});

app.post('/api/detect-text', async (req, res) => {
  try {
    const { image, options = {} } = req.body;

    if (!image) {
      return res.status(400).json({ error: '图片数据是必需的' });
    }

    const sourcePNG = await loadPNGFromBase64(image);
    const sourceData = getImageData(sourcePNG);

    const detector = new TextDetector(sourceData.data, sourcePNG.width, sourcePNG.height);
    const result = detector.detectText(options);

    const maskPNG = createPNGFromData(result.mask, sourcePNG.width, sourcePNG.height);
    const maskBase64 = await pngToBase64(maskPNG);

    res.json({
      success: true,
      regions: result.regions,
      mask: maskBase64,
      totalRegions: result.totalRegions,
      averageConfidence: result.averageConfidence,
      width: sourcePNG.width,
      height: sourcePNG.height
    });
  } catch (error) {
    console.error('文字检测错误:', error);
    res.status(500).json({
      success: false,
      error: '文字检测时发生错误: ' + error.message
    });
  }
});

app.post('/api/detect-and-inpaint', async (req, res) => {
  try {
    const { image, algorithm = 'edge-guided', radius = 3, options = {}, detectOptions = {} } = req.body;

    if (!image) {
      return res.status(400).json({ error: '图片数据是必需的' });
    }

    const sourcePNG = await loadPNGFromBase64(image);
    const sourceData = getImageData(sourcePNG);

    const detector = new TextDetector(sourceData.data, sourcePNG.width, sourcePNG.height);
    const detectResult = detector.detectText(detectOptions);

    if (detectResult.totalRegions === 0) {
      res.json({
        success: true,
        result: image,
        regions: [],
        totalRegions: 0,
        message: '未检测到文字区域'
      });
      return;
    }

    const inpainter = new ImageInpainting(
      sourceData.data,
      detectResult.mask,
      sourcePNG.width,
      sourcePNG.height,
      options
    );

    const resultData = inpainter.inpaint(algorithm, parseInt(radius));
    const resultPNG = createPNGFromData(resultData, sourcePNG.width, sourcePNG.height);
    const resultBase64 = await pngToBase64(resultPNG);

    res.json({
      success: true,
      result: resultBase64,
      regions: detectResult.regions,
      totalRegions: detectResult.totalRegions,
      averageConfidence: detectResult.averageConfidence,
      width: sourcePNG.width,
      height: sourcePNG.height
    });
  } catch (error) {
    console.error('自动检测修复错误:', error);
    res.status(500).json({
      success: false,
      error: '自动检测修复时发生错误: ' + error.message
    });
  }
});

const videoProcessors = new Map();

app.post('/api/video-frame', async (req, res) => {
  try {
    const {
      image,
      mask,
      frameIndex,
      sessionId,
      algorithm = 'edge-guided',
      radius = 3,
      options = {},
      detectText = false,
      detectOptions = {}
    } = req.body;

    if (!image || frameIndex === undefined || !sessionId) {
      return res.status(400).json({ error: '图片、帧索引和会话ID是必需的' });
    }

    if (!videoProcessors.has(sessionId)) {
      videoProcessors.set(sessionId, new VideoProcessor({
        algorithm,
        radius,
        guideEdges: options.guideEdges !== false,
        preserveTexture: options.preserveTexture !== false
      }));
    }

    const processor = videoProcessors.get(sessionId);

    const sourcePNG = await loadPNGFromBase64(image);
    const sourceData = getImageData(sourcePNG);

    let maskData;
    if (mask) {
      const maskPNG = await loadPNGFromBase64(mask);
      maskData = new Uint8ClampedArray(maskPNG.data);
    } else if (detectText) {
      const detector = new TextDetector(sourceData.data, sourcePNG.width, sourcePNG.height);
      const detectResult = detector.detectText(detectOptions);
      maskData = detectResult.mask;

      if (detectResult.totalRegions === 0) {
        res.json({
          success: true,
          result: image,
          regions: [],
          frameIndex,
          message: '此帧未检测到文字'
        });
        return;
      }
    } else {
      maskData = new Uint8ClampedArray(sourcePNG.width * sourcePNG.height * 4);
      for (let i = 3; i < maskData.length; i += 4) {
        maskData[i] = 255;
      }
    }

    const resultData = processor.processFrame(
      sourceData.data,
      maskData,
      sourcePNG.width,
      sourcePNG.height,
      frameIndex
    );

    const resultPNG = createPNGFromData(resultData, sourcePNG.width, sourcePNG.height);
    const resultBase64 = await pngToBase64(resultPNG);

    res.json({
      success: true,
      result: resultBase64,
      frameIndex,
      width: sourcePNG.width,
      height: sourcePNG.height
    });
  } catch (error) {
    console.error('视频帧处理错误:', error);
    res.status(500).json({
      success: false,
      error: '视频帧处理时发生错误: ' + error.message
    });
  }
});

app.post('/api/video-reset', (req, res) => {
  const { sessionId } = req.body;
  if (sessionId && videoProcessors.has(sessionId)) {
    videoProcessors.get(sessionId).reset();
    videoProcessors.delete(sessionId);
  }
  res.json({ success: true, message: '视频处理器已重置' });
});

app.get('/api/algorithms', (req, res) => {
  res.json({
    algorithms: [
      { id: 'telea', name: 'Telea 算法', description: '快速修复，适合简单背景', complexity: 'simple' },
      { id: 'edge-guided', name: '边缘引导修复', description: '边缘感知，恢复自然纹理', complexity: 'medium' },
      { id: 'texture-preserving', name: '纹理保持修复', description: '复杂背景，保持图案', complexity: 'complex' },
      { id: 'ns', name: 'Navier-Stokes', description: '流体力学模型，高质量', complexity: 'complex' },
      { id: 'hybrid', name: '混合算法', description: '边缘+纹理，平衡质量', complexity: 'complex' },
      { id: 'advanced', name: '高级修复', description: '三级递进，最佳质量', complexity: 'very-complex' }
    ],
    complexityLevels: [
      { level: 'simple', name: '简单背景', color: '#28a745' },
      { level: 'medium', name: '中等复杂度', color: '#ffc107' },
      { level: 'complex', name: '复杂背景', color: '#fd7e14' },
      { level: 'very-complex', name: '非常复杂', color: '#dc3545' }
    ]
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    message: '图像修复服务运行正常',
    features: [
      '边缘引导修复',
      '纹理保持修复',
      '图像复杂度预分类',
      '分组批量处理',
      '文字自动检测',
      '视频帧处理',
      '帧间一致性修复'
    ],
    endpoints: [
      '/api/inpaint - 单图修复',
      '/api/classify - 单图分类',
      '/api/detect-text - 文字检测',
      '/api/detect-and-inpaint - 自动检测并修复',
      '/api/batch-classify - 批量分类',
      '/api/batch-inpaint - 批量修复',
      '/api/batch-inpaint-grouped - 分组批量修复',
      '/api/video-frame - 视频帧处理',
      '/api/video-reset - 重置视频处理器',
      '/api/algorithms - 算法列表',
      '/api/health - 健康检查'
    ]
  });
});

app.listen(PORT, () => {
  console.log(`🚀 服务器运行在 http://localhost:${PORT}`);
  console.log(`📡 健康检查: http://localhost:${PORT}/api/health`);
  console.log(`🔧 算法列表: http://localhost:${PORT}/api/algorithms`);
});
