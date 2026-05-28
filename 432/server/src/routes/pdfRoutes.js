import express from 'express';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = express.Router();

const storage = multer.memoryStorage();
const upload = multer({ storage, limits: { fileSize: 50 * 1024 * 1024 } });

const uploadsDir = path.join(__dirname, '../../uploads');
const exportsDir = path.join(__dirname, '../../exports');

if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir, { recursive: true });
if (!fs.existsSync(exportsDir)) fs.mkdirSync(exportsDir, { recursive: true });

const exportTasks = new Map();

const processExportTask = async (taskId, fileBuffer, annotations, originalName) => {
  try {
    const task = exportTasks.get(taskId);
    if (!task) return;

    task.status = 'processing';
    task.progress = 10;

    const pdfDoc = await PDFDocument.load(fileBuffer);
    const pages = pdfDoc.getPages();
    const helveticaFont = await pdfDoc.embedFont(StandardFonts.Helvetica);

    task.progress = 30;

    for (let i = 0; i < annotations.length; i++) {
      const annotation = annotations[i];
      const page = pages[annotation.pageIndex];
      if (!page) continue;

      const { width, height } = page.getSize();
      const x = annotation.position.x * width;
      const y = height - annotation.position.y * height;
      const w = (annotation.position.width || 0.1) * width;
      const h = (annotation.position.height || 0.05) * height;

      const color = hexToRgb(annotation.color || '#FFEB3B');

      switch (annotation.type) {
        case 'highlight':
          page.drawRectangle({
            x,
            y: y - h,
            width: w,
            height: h,
            color: rgb(color.r, color.g, color.b),
            opacity: 0.5,
          });
          break;

        case 'underline':
          page.drawLine({
            start: { x, y: y - 2 },
            end: { x: x + w, y: y - 2 },
            thickness: 2,
            color: rgb(color.r, color.g, color.b),
          });
          break;

        case 'strikeout':
          page.drawLine({
            start: { x, y: y - h / 2 },
            end: { x: x + w, y: y - h / 2 },
            thickness: 2,
            color: rgb(color.r, color.g, color.b),
          });
          break;

        case 'rectangle':
          page.drawRectangle({
            x,
            y: y - h,
            width: w,
            height: h,
            borderColor: rgb(color.r, color.g, color.b),
            borderWidth: 2,
          });
          break;

        case 'circle':
          page.drawEllipse({
            x: x + w / 2,
            y: y - h / 2,
            xScale: w / 2,
            yScale: h / 2,
            borderColor: rgb(color.r, color.g, color.b),
            borderWidth: 2,
          });
          break;

        case 'arrow':
          page.drawLine({
            start: { x, y: y - h / 2 },
            end: { x: x + w, y: y - h / 2 },
            thickness: 2,
            color: rgb(color.r, color.g, color.b),
          });
          break;

        case 'comment':
          page.drawRectangle({
            x,
            y: y - 30,
            width: 150,
            height: 30,
            color: rgb(color.r, color.g, color.b),
            opacity: 0.2,
          });
          if (annotation.content) {
            page.drawText(annotation.content.substring(0, 20), {
              x: x + 5,
              y: y - 20,
              size: 10,
              font: helveticaFont,
              color: rgb(0, 0, 0),
              maxWidth: 140,
            });
          }
          break;
      }

      task.progress = 30 + Math.floor((i / annotations.length) * 60);
    }

    task.progress = 90;

    const pdfBytes = await pdfDoc.save();
    const exportFileName = `${taskId}_annotated_${originalName}`;
    const exportFilePath = path.join(exportsDir, exportFileName);
    fs.writeFileSync(exportFilePath, pdfBytes);

    task.status = 'completed';
    task.progress = 100;
    task.downloadUrl = `/api/pdf/export/${taskId}/download`;
    task.completedAt = Date.now();
    task.filePath = exportFilePath;

  } catch (error) {
    console.error('Export task failed:', error);
    const task = exportTasks.get(taskId);
    if (task) {
      task.status = 'failed';
      task.error = error.message;
    }
  }
};

const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16) / 255,
    g: parseInt(result[2], 16) / 255,
    b: parseInt(result[3], 16) / 255
  } : { r: 1, g: 0.92, b: 0.23 };
};

router.post('/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const fileId = uuidv4();
    const filePath = path.join(uploadsDir, `${fileId}.pdf`);
    fs.writeFileSync(filePath, req.file.buffer);

    const pdfDoc = await PDFDocument.load(req.file.buffer);
    const numPages = pdfDoc.getPageCount();

    res.json({
      fileId,
      filename: req.file.originalname,
      numPages,
      outlines: [],
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to process PDF' });
  }
});

router.post('/export/start', upload.single('file'), async (req, res) => {
  try {
    let annotations = [];
    let fileBuffer = null;
    let originalName = 'document.pdf';

    if (req.file) {
      fileBuffer = req.file.buffer;
      originalName = req.file.originalname;
      annotations = req.body.annotations ? JSON.parse(req.body.annotations) : [];
    } else if (req.body.annotations) {
      annotations = req.body.annotations;
      const fileId = req.body.fileId;
      const filePath = path.join(uploadsDir, `${fileId}.pdf`);
      if (fs.existsSync(filePath)) {
        fileBuffer = fs.readFileSync(filePath);
        originalName = req.body.fileName || 'document.pdf';
      }
    }

    if (!fileBuffer) {
      return res.status(400).json({ error: 'No file provided' });
    }

    const taskId = uuidv4();
    const task = {
      taskId,
      status: 'pending',
      progress: 0,
      createdAt: Date.now(),
    };
    exportTasks.set(taskId, task);

    setImmediate(() => processExportTask(taskId, fileBuffer, annotations, originalName));

    res.json({ taskId, status: 'pending' });
  } catch (error) {
    console.error('Export start error:', error);
    res.status(500).json({ error: 'Failed to start export' });
  }
});

router.get('/export/:taskId/status', (req, res) => {
  const { taskId } = req.params;
  const task = exportTasks.get(taskId);

  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }

  res.json({
    taskId: task.taskId,
    status: task.status,
    progress: task.progress,
    downloadUrl: task.downloadUrl,
  });
});

router.get('/export/:taskId/download', (req, res) => {
  const { taskId } = req.params;
  const task = exportTasks.get(taskId);

  if (!task || task.status !== 'completed' || !task.filePath) {
    return res.status(404).json({ error: 'Export not ready' });
  }

  if (!fs.existsSync(task.filePath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  res.download(task.filePath, `annotated_${Date.now()}.pdf`, (err) => {
    if (err) {
      console.error('Download error:', err);
    }
  });
});

router.get('/:fileId', (req, res) => {
  const { fileId } = req.params;
  const filePath = path.join(uploadsDir, `${fileId}.pdf`);

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  res.setHeader('Content-Type', 'application/pdf');
  fs.createReadStream(filePath).pipe(res);
});

export default router;
