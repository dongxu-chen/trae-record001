import { Request, Response } from 'express';
import TaskTemplate from '../models/TaskTemplate';
import Task from '../models/Task';
import { addDays } from 'date-fns';

export const getAllTemplates = async (_req: Request, res: Response) => {
  try {
    const templates = await TaskTemplate.find().sort({ createdAt: -1 });
    res.json(templates);
  } catch (error) {
    res.status(500).json({ message: '获取模板列表失败', error });
  }
};

export const getTemplate = async (req: Request, res: Response) => {
  try {
    const template = await TaskTemplate.findById(req.params.id);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }
    res.json(template);
  } catch (error) {
    res.status(500).json({ message: '获取模板失败', error });
  }
};

export const createTemplate = async (req: Request, res: Response) => {
  try {
    const template = new TaskTemplate(req.body);
    const savedTemplate = await template.save();
    res.status(201).json(savedTemplate);
  } catch (error) {
    res.status(500).json({ message: '创建模板失败', error });
  }
};

export const updateTemplate = async (req: Request, res: Response) => {
  try {
    const template = await TaskTemplate.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    );
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }
    res.json(template);
  } catch (error) {
    res.status(500).json({ message: '更新模板失败', error });
  }
};

export const deleteTemplate = async (req: Request, res: Response) => {
  try {
    const template = await TaskTemplate.findByIdAndDelete(req.params.id);
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }
    res.json({ message: '删除成功' });
  } catch (error) {
    res.status(500).json({ message: '删除模板失败', error });
  }
};

export const createTaskFromTemplate = async (req: Request, res: Response) => {
  try {
    const { boardId, overrides } = req.body;
    const template = await TaskTemplate.findById(req.params.id);
    
    if (!template) {
      return res.status(404).json({ message: '模板不存在' });
    }

    const now = new Date();
    const dueDate = addDays(now, template.dueDays);

    const task = new Task({
      boardId,
      title: overrides?.title || template.title,
      description: overrides?.description || template.taskDescription,
      status: 'todo',
      priority: overrides?.priority || template.priority,
      assignee: overrides?.assignee || template.assignee || '',
      tags: overrides?.tags || [...template.tags],
      dueDate: dueDate.toISOString(),
      startDate: now.toISOString(),
      subTasks: template.subTasks.map((title: string, index: number) => ({
        _id: `subtask-${Date.now()}-${index}`,
        title,
        completed: false,
      })),
      comments: [],
      history: [],
      operationLogs: [],
      order: 0,
    });

    const savedTask = await task.save();
    res.status(201).json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '从模板创建任务失败', error });
  }
};
