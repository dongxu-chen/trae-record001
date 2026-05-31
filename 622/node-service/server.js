require('dotenv').config();
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const sharp = require('sharp');
const path = require('path');
const fs = require('fs');
const { createClient } = require('redis');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

const UPLOAD_DIR = path.join(__dirname, '../uploads');
const OUTPUT_DIR = path.join(__dirname, '../outputs');
const PROCESSED_DIR = path.join(__dirname, '../processed');

[UPLOAD_DIR, OUTPUT_DIR, PROCESSED_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

app.use('/uploads', express.static(UPLOAD_DIR));
app.use('/outputs', express.static(OUTPUT_DIR));
app.use('/processed', express.static(PROCESSED_DIR));

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, UPLOAD_DIR);
  },
  filename: (req, file, cb) => {
    const uniqueName = `${Date.now()}-${Math.round(Math.random() * 1E9)}${path.extname(file.originalname)}`;
    cb(null, uniqueName);
  }
});

const upload = multer({
  storage: storage,
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Not an image!'), false);
    }
  },
  limits: { fileSize: 10 * 1024 * 1024 }
});

const processingQueue = new Map();
let taskIdCounter = 0;

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'node-image-processor' });
});

app.post('/api/process-image', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const { width = 1024, height = null, format = 'jpeg', quality = 90 } = req.body;
    
    const inputPath = req.file.path;
    const outputFileName = `processed-${path.parse(req.file.filename).name}.${format}`;
    const outputPath = path.join(PROCESSED_DIR, outputFileName);

    let pipeline = sharp(inputPath)
      .resize(parseInt(width), height ? parseInt(height) : null, {
        fit: 'inside',
        withoutEnlargement: true
      });

    if (format === 'jpeg') {
      pipeline = pipeline.jpeg({ quality: parseInt(quality) });
    } else if (format === 'png') {
      pipeline = pipeline.png({ quality: parseInt(quality) });
    } else if (format === 'webp') {
      pipeline = pipeline.webp({ quality: parseInt(quality) });
    }

    await pipeline.toFile(outputPath);

    const stats = fs.statSync(outputPath);

    res.json({
      success: true,
      original: {
        filename: req.file.originalname,
        size: req.file.size,
        path: `/uploads/${req.file.filename}`
      },
      processed: {
        filename: outputFileName,
        size: stats.size,
        path: `/processed/${outputFileName}`,
        width: width,
        format: format
      }
    });
  } catch (error) {
    console.error('Processing error:', error);
    res.status(500).json({ error: 'Failed to process image', details: error.message });
  }
});

app.post('/api/batch-process', upload.array('images', 10), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'No files uploaded' });
    }

    const results = [];
    
    for (const file of req.files) {
      const outputFileName = `batch-${path.parse(file.filename).name}.jpg`;
      const outputPath = path.join(PROCESSED_DIR, outputFileName);

      await sharp(file.path)
        .resize(800, 800, { fit: 'inside' })
        .jpeg({ quality: 85 })
        .toFile(outputPath);

      results.push({
        original: `/uploads/${file.filename}`,
        processed: `/processed/${outputFileName}`
      });
    }

    res.json({ success: true, results });
  } catch (error) {
    console.error('Batch processing error:', error);
    res.status(500).json({ error: 'Batch processing failed' });
  }
});

app.post('/api/generate-thumbnail', upload.single('image'), async (req, res) => {
  try {
    const { size = 256 } = req.body;
    const inputPath = req.file.path;
    const outputFileName = `thumb-${size}-${path.parse(req.file.filename).name}.jpg`;
    const outputPath = path.join(PROCESSED_DIR, outputFileName);

    await sharp(inputPath)
      .resize(parseInt(size), parseInt(size), { fit: 'cover' })
      .jpeg({ quality: 80 })
      .toFile(outputPath);

    res.json({
      success: true,
      thumbnail: `/processed/${outputFileName}`,
      size: size
    });
  } catch (error) {
    res.status(500).json({ error: 'Thumbnail generation failed' });
  }
});

app.post('/api/tasks', (req, res) => {
  const taskId = ++taskIdCounter;
  const { type, params } = req.body;

  processingQueue.set(taskId, {
    id: taskId,
    type: type,
    params: params,
    status: 'pending',
    progress: 0,
    createdAt: new Date().toISOString()
  });

  simulateTaskProcessing(taskId);

  res.json({ taskId, status: 'pending' });
});

app.get('/api/tasks/:taskId', (req, res) => {
  const task = processingQueue.get(parseInt(req.params.taskId));
  
  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }

  res.json(task);
});

function simulateTaskProcessing(taskId) {
  const task = processingQueue.get(taskId);
  if (!task) return;

  task.status = 'processing';
  
  let progress = 0;
  const interval = setInterval(() => {
    progress += 10;
    task.progress = progress;

    if (progress >= 100) {
      clearInterval(interval);
      task.status = 'completed';
      task.completedAt = new Date().toISOString();
      task.result = { outputUrl: `/outputs/result-${taskId}.jpg` };
    }
  }, 200);
}

app.get('/api/image-info/:filename', (req, res) => {
  try {
    const filePath = path.join(UPLOAD_DIR, req.params.filename);
    
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: 'Image not found' });
    }

    sharp(filePath).metadata().then(metadata => {
      res.json({
        filename: req.params.filename,
        width: metadata.width,
        height: metadata.height,
        format: metadata.format,
        size: metadata.size,
        orientation: metadata.orientation
      });
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to get image info' });
  }
});

app.delete('/api/images/:filename', (req, res) => {
  try {
    const filePath = path.join(UPLOAD_DIR, req.params.filename);
    
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
      res.json({ success: true, message: 'Image deleted' });
    } else {
      res.status(404).json({ error: 'Image not found' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete image' });
  }
});

app.listen(PORT, () => {
  console.log(`Node.js image service running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
});
