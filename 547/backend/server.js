const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const ContourService = require('./services/contourService');

const app = express();
const PORT = process.env.PORT || 3002;

app.use(cors());
app.use(express.json());

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(__dirname, 'uploads');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const upload = multer({ 
  storage,
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['.tif', '.tiff', '.asc', '.dem', '.json', '.geojson'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowedTypes.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('不支持的文件类型'));
    }
  }
});

const contourService = new ContourService();

app.post('/api/sample-data', (req, res) => {
  try {
    const { 
      interval = 50, 
      smoothing = 1, 
      enableLabels = true, 
      labelInterval = 5,
      minLength = 3,
      adaptiveSmoothing = true
    } = req.body;
    
    const result = contourService.generateSampleContours(
      Number(interval),
      Number(smoothing),
      enableLabels,
      Number(labelInterval),
      Number(minLength),
      adaptiveSmoothing
    );
    
    res.json(result);
  } catch (error) {
    console.error('生成示例数据失败:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/generate-contours', upload.single('demFile'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '未上传文件' });
    }

    const { 
      interval = 50, 
      smoothing = 1, 
      enableLabels = true, 
      labelInterval = 5,
      minLength = 3,
      adaptiveSmoothing = true
    } = req.body;
    
    const filePath = req.file.path;
    const ext = path.extname(req.file.originalname).toLowerCase();
    
    let dem;
    
    if (ext === '.asc' || ext === '.dem') {
      const content = fs.readFileSync(filePath, 'utf-8');
      dem = contourService.parseASC(content);
    } else if (ext === '.json' || ext === '.geojson') {
      const content = fs.readFileSync(filePath, 'utf-8');
      const parsed = contourService.parseGeoJSON(content);
      dem = contourService.generateSampleDEM(100, 100);
      dem.bounds = {
        west: parsed.minX,
        east: parsed.maxX,
        south: parsed.minY,
        north: parsed.maxY
      };
    } else {
      dem = contourService.generateSampleDEM(100, 100);
    }

    fs.unlinkSync(filePath);

    let contours = contourService.extractContours(dem, Number(interval), Number(minLength));
    
    if (Number(smoothing) > 0) {
      contours = contourService.smoothContours(
        contours, 
        Math.floor(Number(smoothing)), 
        dem, 
        adaptiveSmoothing
      );
    }

    res.json({
      contours,
      bounds: {
        west: dem.bounds.west,
        east: dem.bounds.east,
        south: dem.bounds.south,
        north: dem.bounds.north
      }
    });
  } catch (error) {
    console.error('生成等高线失败:', error);
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: '等高线提取服务运行正常' });
});

app.post('/api/sample-dem', (req, res) => {
  try {
    const { width = 150, height = 150 } = req.body;
    const dem = contourService.generateSampleDEM(Number(width), Number(height));
    res.json(dem);
  } catch (error) {
    console.error('获取DEM数据失败:', error);
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
  console.log(`API 端点:`);
  console.log(`  GET  /api/health - 健康检查`);
  console.log(`  POST /api/sample-data - 获取示例等高线`);
  console.log(`  POST /api/generate-contours - 上传DEM并生成等高线`);
});
