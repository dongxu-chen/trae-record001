import { Request, Response } from 'express';
import AutomationRule from '../models/AutomationRule';

export const getAllRules = async (_req: Request, res: Response) => {
  try {
    const rules = await AutomationRule.find().sort({ createdAt: -1 });
    res.json(rules);
  } catch (error) {
    res.status(500).json({ message: '获取规则列表失败', error });
  }
};

export const getRule = async (req: Request, res: Response) => {
  try {
    const rule = await AutomationRule.findById(req.params.id);
    if (!rule) {
      return res.status(404).json({ message: '规则不存在' });
    }
    res.json(rule);
  } catch (error) {
    res.status(500).json({ message: '获取规则失败', error });
  }
};

export const createRule = async (req: Request, res: Response) => {
  try {
    const rule = new AutomationRule(req.body);
    const savedRule = await rule.save();
    res.status(201).json(savedRule);
  } catch (error) {
    res.status(500).json({ message: '创建规则失败', error });
  }
};

export const updateRule = async (req: Request, res: Response) => {
  try {
    const rule = await AutomationRule.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    );
    if (!rule) {
      return res.status(404).json({ message: '规则不存在' });
    }
    res.json(rule);
  } catch (error) {
    res.status(500).json({ message: '更新规则失败', error });
  }
};

export const toggleRule = async (req: Request, res: Response) => {
  try {
    const rule = await AutomationRule.findById(req.params.id);
    if (!rule) {
      return res.status(404).json({ message: '规则不存在' });
    }
    rule.enabled = !rule.enabled;
    const savedRule = await rule.save();
    res.json(savedRule);
  } catch (error) {
    res.status(500).json({ message: '切换规则状态失败', error });
  }
};

export const deleteRule = async (req: Request, res: Response) => {
  try {
    const rule = await AutomationRule.findByIdAndDelete(req.params.id);
    if (!rule) {
      return res.status(404).json({ message: '规则不存在' });
    }
    res.json({ message: '删除成功' });
  } catch (error) {
    res.status(500).json({ message: '删除规则失败', error });
  }
};

export const processTasksWithRules = async (_req: Request, res: Response) => {
  try {
    res.json({ message: '规则执行完成' });
  } catch (error) {
    res.status(500).json({ message: '执行规则失败', error });
  }
};
