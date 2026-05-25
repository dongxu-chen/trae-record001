import { Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import db from '../db/index.js';
import { AuthRequest } from '../middleware/auth.js';

export const saveQRCode = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.userId;
    const { name, type, content, style } = req.body;

    if (!type || !content) {
      return res.status(400).json({
        success: false,
        message: '类型和内容不能为空',
      });
    }

    const codeId = uuidv4();

    db.prepare(`
      INSERT INTO qr_codes (id, user_id, name, type, content, style_config)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(
      codeId,
      userId,
      name || '未命名二维码',
      type,
      content,
      style ? JSON.stringify(style) : null
    );

    res.json({
      success: true,
      data: { id: codeId },
    });
  } catch (error) {
    console.error('保存二维码错误:', error);
    res.status(500).json({
      success: false,
      message: '保存失败',
    });
  }
};

export const getQRCodes = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.userId;
    
    const codes = db.prepare(`
      SELECT * FROM qr_codes 
      WHERE user_id = ? 
      ORDER BY created_at DESC
    `).all(userId) as any[];

    const formattedCodes = codes.map(code => ({
      ...code,
      style: code.style_config ? JSON.parse(code.style_config) : null,
    }));

    res.json({
      success: true,
      data: formattedCodes,
    });
  } catch (error) {
    console.error('获取二维码列表错误:', error);
    res.status(500).json({
      success: false,
      message: '获取失败',
    });
  }
};

export const deleteQRCode = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.userId;

    const result = db.prepare(`
      DELETE FROM qr_codes WHERE id = ? AND user_id = ?
    `).run(id, userId);

    if (result.changes === 0) {
      return res.status(404).json({
        success: false,
        message: '二维码不存在',
      });
    }

    res.json({
      success: true,
      message: '删除成功',
    });
  } catch (error) {
    console.error('删除二维码错误:', error);
    res.status(500).json({
      success: false,
      message: '删除失败',
    });
  }
};
