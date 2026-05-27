import express, { type Request, type Response } from 'express';
import { generatePythonScript, generateSampleData } from '../services/scriptService.js';
import type { CleaningRules } from '../../src/types';

const router = express.Router();

router.post('/generate-script', (req: Request, res: Response) => {
  try {
    const { rules, columns, columnStats, filename } = req.body as {
      rules: CleaningRules;
      columns: string[];
      columnStats: any[];
      filename?: string;
    };

    if (!rules || !columns || !columnStats) {
      return res.status(400).json({
        success: false,
        error: '缺少必要参数: rules, columns, columnStats',
      });
    }

    const script = generatePythonScript(rules, columns, columnStats, filename || 'your_data.csv');

    res.json({
      success: true,
      data: {
        script,
        filename: 'cleaning_script.py',
      },
    });
  } catch (error) {
    console.error('生成脚本失败:', error);
    res.status(500).json({
      success: false,
      error: '生成脚本时发生错误',
    });
  }
});

router.get('/sample-data/:name', (req: Request, res: Response) => {
  try {
    const { name } = req.params;
    const sample = generateSampleData(name);

    res.json({
      success: true,
      data: sample,
    });
  } catch (error) {
    console.error('获取示例数据失败:', error);
    res.status(500).json({
      success: false,
      error: '获取示例数据时发生错误',
    });
  }
});

router.post('/validate-schema', (req: Request, res: Response) => {
  try {
    const { columns, data } = req.body as {
      columns: string[];
      data: any[][];
    };

    if (!columns || !data) {
      return res.status(400).json({
        success: false,
        error: '缺少必要参数: columns, data',
      });
    }

    const issues: string[] = [];

    if (columns.length === 0) {
      issues.push('未检测到列名');
    }

    if (data.length === 0) {
      issues.push('未检测到数据行');
    }

    data.forEach((row, rowIdx) => {
      if (row.length !== columns.length) {
        issues.push(`第 ${rowIdx + 1} 行列数不匹配: 预期 ${columns.length} 列, 实际 ${row.length} 列`);
      }
    });

    const columnTypes = columns.map((col, colIdx) => {
      const values = data.map((row) => row[colIdx]).filter((v) => v !== null && v !== undefined && v !== '');
      const numericCount = values.filter((v) => !isNaN(Number(v)) && isFinite(Number(v))).length;
      const isNumeric = numericCount / values.length > 0.8;
      return {
        name: col,
        type: isNumeric ? 'numeric' : 'string',
        sampleValues: values.slice(0, 5),
      };
    });

    res.json({
      success: true,
      data: {
        valid: issues.length === 0,
        issues,
        columnTypes,
        rowCount: data.length,
        columnCount: columns.length,
      },
    });
  } catch (error) {
    console.error('验证Schema失败:', error);
    res.status(500).json({
      success: false,
      error: '验证Schema时发生错误',
    });
  }
});

export default router;
