import { Response, Request } from 'express';
import { v4 as uuidv4 } from 'uuid';
import db from '../db/index.js';
import type { AuthRequest } from '../middleware/auth.js';
import { wsService } from '../websocket/index.js';

const generateShortCode = (): string => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
  let result = '';
  for (let i = 0; i < 6; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
};

export const createDynamicCode = async (req: AuthRequest, res: Response) => {
  try {
    const { name, originalUrl, type, style } = req.body;
    const userId = req.userId;

    if (!name || !originalUrl) {
      return res.status(400).json({
        success: false,
        message: '名称和链接不能为空',
      });
    }

    let shortCode = generateShortCode();
    let exists = db.prepare('SELECT id FROM dynamic_codes WHERE short_code = ?').get(shortCode);
    
    while (exists) {
      shortCode = generateShortCode();
      exists = db.prepare('SELECT id FROM dynamic_codes WHERE short_code = ?').get(shortCode);
    }

    const codeId = uuidv4();

    db.prepare(`
      INSERT INTO dynamic_codes (id, user_id, short_code, name, original_url, type, style_config)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(
      codeId,
      userId,
      shortCode,
      name,
      originalUrl,
      type || 'url',
      style ? JSON.stringify(style) : null
    );

    const newCode = db.prepare('SELECT * FROM dynamic_codes WHERE id = ?').get(codeId) as any;

    const responseData = {
      ...newCode,
      style: newCode.style_config ? JSON.parse(newCode.style_config) : null,
      shortUrl: `${req.protocol}://${req.get('host')}/r/${shortCode}`,
    };

    if (userId) {
      wsService.notifyDynamicCodeCreated(userId, responseData);
    }

    res.json({
      success: true,
      data: responseData,
    });
  } catch (error) {
    console.error('创建动态码错误:', error);
    res.status(500).json({
      success: false,
      message: '创建失败',
    });
  }
};

export const getDynamicCodes = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.userId;
    
    const codes = db.prepare(`
      SELECT * FROM dynamic_codes 
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
    console.error('获取动态码列表错误:', error);
    res.status(500).json({
      success: false,
      message: '获取失败',
    });
  }
};

export const updateDynamicCode = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.userId;
    const { name, originalUrl, isActive, style } = req.body;

    const existing = db.prepare(`
      SELECT * FROM dynamic_codes WHERE id = ? AND user_id = ?
    `).get(id, userId);

    if (!existing) {
      return res.status(404).json({
        success: false,
        message: '动态码不存在',
      });
    }

    const updates: string[] = [];
    const values: any[] = [];

    if (name !== undefined) {
      updates.push('name = ?');
      values.push(name);
    }
    if (originalUrl !== undefined) {
      updates.push('original_url = ?');
      values.push(originalUrl);
    }
    if (isActive !== undefined) {
      updates.push('is_active = ?');
      values.push(isActive ? 1 : 0);
    }
    if (style !== undefined) {
      updates.push('style_config = ?');
      values.push(JSON.stringify(style));
    }
    updates.push('updated_at = CURRENT_TIMESTAMP');

    values.push(id, userId);

    db.prepare(`
      UPDATE dynamic_codes 
      SET ${updates.join(', ')}
      WHERE id = ? AND user_id = ?
    `).run(...values);

    const updated = db.prepare('SELECT * FROM dynamic_codes WHERE id = ?').get(id) as any;

    const responseData = {
      ...updated,
      style: updated.style_config ? JSON.parse(updated.style_config) : null,
    };

    if (userId) {
      wsService.notifyDynamicCodeUpdate(userId, responseData);
    }

    res.json({
      success: true,
      data: responseData,
    });
  } catch (error) {
    console.error('更新动态码错误:', error);
    res.status(500).json({
      success: false,
      message: '更新失败',
    });
  }
};

export const deleteDynamicCode = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.userId;

    const result = db.prepare(`
      DELETE FROM dynamic_codes WHERE id = ? AND user_id = ?
    `).run(id, userId);

    if (result.changes === 0) {
      return res.status(404).json({
        success: false,
        message: '动态码不存在',
      });
    }

    if (userId) {
      wsService.notifyDynamicCodeDeleted(userId, id);
    }

    res.json({
      success: true,
      message: '删除成功',
    });
  } catch (error) {
    console.error('删除动态码错误:', error);
    res.status(500).json({
      success: false,
      message: '删除失败',
    });
  }
};

export const redirectShortCode = async (req: Request, res: Response) => {
  try {
    const { shortCode } = req.params;

    const code = db.prepare(`
      SELECT * FROM dynamic_codes WHERE short_code = ? AND is_active = 1
    `).get(shortCode) as any;

    if (!code) {
      return res.status(404).send('二维码不存在或已停用');
    }

    const logId = uuidv4();
    const userAgent = req.headers['user-agent'] || '';
    const ip = req.ip || req.connection.remoteAddress || '';
    
    let deviceType = 'desktop';
    if (/Mobile|Android|iPhone|iPad|iPod/.test(userAgent)) {
      deviceType = /Tablet|iPad/.test(userAgent) ? 'tablet' : 'mobile';
    }

    db.prepare(`
      INSERT INTO scan_logs (id, dynamic_code_id, ip_address, user_agent, device_type)
      VALUES (?, ?, ?, ?, ?)
    `).run(logId, code.id, ip, userAgent, deviceType);

    db.prepare(`
      UPDATE dynamic_codes 
      SET scan_count = scan_count + 1 
      WHERE id = ?
    `).run(code.id);

    const updatedCode = db.prepare('SELECT scan_count FROM dynamic_codes WHERE id = ?').get(code.id) as any;
    wsService.notifyScanUpdate(code.user_id, code.id, updatedCode.scan_count);

    res.redirect(code.original_url);
  } catch (error) {
    console.error('重定向错误:', error);
    res.status(500).send('服务器错误');
  }
};
