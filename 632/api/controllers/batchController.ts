import { Request, Response } from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';
import JSZip from 'jszip';
import { processImage, ProcessResult } from '../utils/imageProcessor.js';
import { ProcessingParams } from '../../src/types/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const uploadDir = path.join(__dirname, '../uploads');
const outputDir = path.join(__dirname, '../processed');

interface BatchTask {
  taskId: string;
  total: number;
  completed: number;
  results: ProcessResult[];
  createdAt: number;
}

const batchTasks = new Map<string, BatchTask>();

export const createBatchProcess = async (req: Request, res: Response) => {
  try {
    const { fileNames, params } = req.body as {
      fileNames: string[];
      params: ProcessingParams;
    };

    if (!fileNames || fileNames.length === 0) {
      return res.status(400).json({
        success: false,
        error: '请提供要处理的文件列表'
      });
    }

    const taskId = Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    const task: BatchTask = {
      taskId,
      total: fileNames.length,
      completed: 0,
      results: [],
      createdAt: Date.now()
    };

    batchTasks.set(taskId, task);

    processBatchInBackground(taskId, fileNames, params);

    res.status(202).json({
      success: true,
      taskId,
      total: fileNames.length,
      message: '批量处理任务已创建'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: (error as Error).message
    });
  }
};

async function processBatchInBackground(
  taskId: string,
  fileNames: string[],
  params: ProcessingParams
) {
  const task = batchTasks.get(taskId);
  if (!task) return;

  try {
    await fs.mkdir(outputDir, { recursive: true });

    for (let i = 0; i < fileNames.length; i++) {
      const fileName = fileNames[i];
      const inputPath = path.join(uploadDir, fileName);
      const outputName = `${path.basename(fileName, path.extname(fileName))}_antialiased${path.extname(fileName)}`;
      const outputPath = path.join(outputDir, outputName);

      const result = await processImage(inputPath, outputPath, params);
      task.results.push(result);
      task.completed = i + 1;

      batchTasks.set(taskId, task);
    }
  } catch (error) {
    console.error('批量处理失败:', error);
  }
}

export const getBatchProgress = async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;
    const task = batchTasks.get(taskId);

    if (!task) {
      return res.status(404).json({
        success: false,
        error: '任务不存在'
      });
    }

    res.json({
      success: true,
      taskId,
      total: task.total,
      completed: task.completed,
      progress: Math.round((task.completed / task.total) * 100),
      results: task.results
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: (error as Error).message
    });
  }
};

export const downloadBatchResults = async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;
    const task = batchTasks.get(taskId);

    if (!task) {
      return res.status(404).json({
        success: false,
        error: '任务不存在'
      });
    }

    if (task.completed < task.total) {
      return res.status(400).json({
        success: false,
        error: '处理尚未完成'
      });
    }

    const zip = new JSZip();
    const successResults = task.results.filter(r => r.success);

    for (const result of successResults) {
      const fileName = path.basename(result.processedPath);
      const fileContent = await fs.readFile(result.processedPath);
      zip.file(fileName, fileContent);
    }

    const zipContent = await zip.generateAsync({ type: 'nodebuffer' });

    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="antialiased_${taskId}.zip"`);
    res.send(zipContent);
  } catch (error) {
    res.status(500).json({
      success: false,
      error: (error as Error).message
    });
  }
};

export const processSingleImage = async (req: Request, res: Response) => {
  try {
    const file = req.file;
    const params = JSON.parse(req.body.params || '{}') as ProcessingParams;

    if (!file) {
      return res.status(400).json({
        success: false,
        error: '请上传图片'
      });
    }

    await fs.mkdir(outputDir, { recursive: true });

    const outputName = `${path.basename(file.filename, path.extname(file.filename))}_antialiased${path.extname(file.filename)}`;
    const outputPath = path.join(outputDir, outputName);

    const result = await processImage(file.path, outputPath, params);

    if (!result.success) {
      return res.status(500).json({
        success: false,
        error: result.error || '处理失败'
      });
    }

    const fileContent = await fs.readFile(outputPath);
    const base64 = `data:image/${path.extname(file.filename).slice(1)};base64,${fileContent.toString('base64')}`;

    res.json({
      success: true,
      originalName: file.originalname,
      processedName: outputName,
      imageUrl: base64
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: (error as Error).message
    });
  }
};
