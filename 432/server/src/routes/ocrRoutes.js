import express from 'express';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';
import { PDFDocument } from 'pdf-lib';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = express.Router();

const storage = multer.memoryStorage();
const upload = multer({ storage, limits: { fileSize: 50 * 1024 * 1024 } });

const ocrTasks = new Map();

const processOcrTask = async (taskId, fileBuffer, pages) => {
  try {
    const task = ocrTasks.get(taskId);
    if (!task) return;

    task.status = 'processing';
    task.progress = 10;

    const pdfDoc = await PDFDocument.load(fileBuffer);
    const totalPages = pdfDoc.getPageCount();
    const pagesToProcess = pages || Array.from({ length: totalPages }, (_, i) => i);

    const results = [];

    for (let i = 0; i < pagesToProcess.length; i++) {
      const pageIndex = pagesToProcess[i];
      const page = pdfDoc.getPage(pageIndex);
      const { width, height } = page.getSize();

      const textContent = await page.getTextContent?.();
      
      if (textContent && textContent.items) {
        textContent.items.forEach((item) => {
          if (item.str && item.str.trim()) {
            const transform = item.transform || [1, 0, 0, 1, 0, 0];
            const itemX = transform[4] || 0;
            const itemY = transform[5] || 0;
            const itemWidth = item.width || (item.str.length * 6);
            const itemHeight = item.height || 12;

            results.push({
              pageIndex,
              text: item.str,
              position: {
                x: itemX / width,
                y: (height - itemY - itemHeight) / height,
                width: itemWidth / width,
                height: itemHeight / height,
              },
              confidence: 0.95,
            });
          }
        });
      }

      task.progress = Math.round(10 + (i / pagesToProcess.length) * 85);
    }

    task.results = results;
    task.status = 'completed';
    task.progress = 100;

  } catch (error) {
    console.error('OCR task failed:', error);
    const task = ocrTasks.get(taskId);
    if (task) {
      task.status = 'failed';
      task.error = error.message;
    }
  }
};

router.post('/recognize', upload.single('file'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    let pages = null;
    if (req.body.pages) {
      try {
        pages = JSON.parse(req.body.pages);
      } catch (e) {
        return res.status(400).json({ error: 'Invalid pages parameter' });
      }
    }

    const taskId = uuidv4();
    const task = {
      taskId,
      status: 'pending',
      progress: 0,
      results: [],
    };
    ocrTasks.set(taskId, task);

    setImmediate(() => processOcrTask(taskId, req.file.buffer, pages));

    res.json({ taskId, status: 'pending' });
  } catch (error) {
    console.error('OCR start error:', error);
    res.status(500).json({ error: 'Failed to start OCR' });
  }
});

router.get('/:taskId/status', (req, res) => {
  const { taskId } = req.params;
  const task = ocrTasks.get(taskId);

  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }

  res.json({
    taskId: task.taskId,
    status: task.status,
    progress: task.progress,
    results: task.results,
  });
});

export default router;
