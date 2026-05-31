import { Request, Response } from 'express';
import {
  loadHistory,
  toggleFavorite,
  deleteHistoryItem,
  clearHistory,
  submitFeedback,
  getSuggestions,
  getPreferredStyle
} from '../services/learningService.js';

export async function getHistory(req: Request, res: Response) {
  try {
    const history = loadHistory();
    res.json({
      success: true,
      data: history
    });
  } catch (error) {
    console.error('获取历史记录错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function toggleHistoryFavorite(req: Request, res: Response) {
  try {
    const { id } = req.params;
    const item = toggleFavorite(id);
    
    if (!item) {
      return res.status(404).json({
        success: false,
        error: '记录不存在'
      });
    }
    
    res.json({
      success: true,
      data: item
    });
  } catch (error) {
    console.error('切换收藏状态错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function deleteHistory(req: Request, res: Response) {
  try {
    const { id } = req.params;
    const deleted = deleteHistoryItem(id);
    
    if (!deleted) {
      return res.status(404).json({
        success: false,
        error: '记录不存在'
      });
    }
    
    res.json({
      success: true
    });
  } catch (error) {
    console.error('删除历史记录错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function clearAllHistory(req: Request, res: Response) {
  try {
    clearHistory();
    res.json({
      success: true
    });
  } catch (error) {
    console.error('清空历史记录错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function submitHistoryFeedback(req: Request, res: Response) {
  try {
    const { id } = req.params;
    const { feedback } = req.body;
    
    submitFeedback(id, feedback);
    
    res.json({
      success: true
    });
  } catch (error) {
    console.error('提交反馈错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function getLearningSuggestions(req: Request, res: Response) {
  try {
    const suggestions = getSuggestions();
    res.json({
      success: true,
      data: suggestions
    });
  } catch (error) {
    console.error('获取学习建议错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}

export async function getUserPreferredStyle(req: Request, res: Response) {
  try {
    const style = getPreferredStyle();
    res.json({
      success: true,
      data: { style }
    });
  } catch (error) {
    console.error('获取偏好风格错误:', error);
    res.status(500).json({
      success: false,
      error: '服务内部错误'
    });
  }
}
