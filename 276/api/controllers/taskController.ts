import { Request, Response } from 'express';
import Task, { ITask, ITaskSnapshot, OperationType, TaskStatus } from '../models/Task';
import mongoose from 'mongoose';

const STATE_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  'todo': ['in-progress'],
  'in-progress': ['todo', 'done'],
  'done': ['in-progress'],
};

const canTransition = (from: TaskStatus, to: TaskStatus): boolean => {
  return STATE_TRANSITIONS[from]?.includes(to) ?? false;
};

const getTaskSnapshot = (task: ITask): ITaskSnapshot => {
  return {
    title: task.title,
    description: task.description,
    status: task.status,
    priority: task.priority,
    assignee: task.assignee,
    tags: [...task.tags],
    dueDate: task.dueDate,
    startDate: task.startDate,
    subTasks: task.subTasks.map(st => ({
      _id: st._id,
      title: st.title,
      completed: st.completed,
      createdAt: st.createdAt,
    })),
  };
};

const addOperationLog = (
  task: ITask,
  operation: OperationType,
  description: string,
  changes?: { field: string; oldValue: any; newValue: any }[],
  operator: string = '当前用户'
) => {
  const snapshotBefore = getTaskSnapshot(task);
  
  const log: any = {
    _id: new mongoose.Types.ObjectId().toString(),
    operation,
    operator,
    timestamp: new Date(),
    description,
    snapshotBefore,
  };

  if (changes && changes.length > 0) {
    log.changes = changes;
  }

  task.operationLogs.push(log);
  return log;
};

const updateSnapshotAfter = (task: ITask, logId: string) => {
  const logIndex = task.operationLogs.findIndex(l => l._id === logId);
  if (logIndex !== -1) {
    task.operationLogs[logIndex].snapshotAfter = getTaskSnapshot(task);
  }
};

const addHistoryEntry = (task: ITask, field: string, oldValue: any, newValue: any) => {
  task.history.push({
    _id: new mongoose.Types.ObjectId().toString(),
    field,
    oldValue,
    newValue,
    changedBy: '用户',
    changedAt: new Date(),
  });
};

export const getTasks = async (req: Request, res: Response) => {
  try {
    const { boardId } = req.query;
    const query = boardId ? { boardId } : {};
    const tasks = await Task.find(query).sort({ order: 1, createdAt: -1 });
    res.json(tasks);
  } catch (error) {
    res.status(500).json({ message: '获取任务列表失败', error });
  }
};

export const getTask = async (req: Request, res: Response) => {
  try {
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }
    res.json(task);
  } catch (error) {
    res.status(500).json({ message: '获取任务失败', error });
  }
};

export const createTask = async (req: Request, res: Response) => {
  try {
    const { boardId, title, description, status, priority, assignee, tags, dueDate, startDate } = req.body;
    const task = new Task({
      boardId,
      title,
      description: description || '',
      status: status || 'todo',
      priority: priority || 'medium',
      assignee: assignee || '',
      tags: tags || [],
      dueDate: dueDate || null,
      startDate: startDate || null,
      order: 0,
      subTasks: [],
      comments: [],
      history: [],
      operationLogs: [],
    });
    
    const log = addOperationLog(task, 'create', `创建了任务「${title}」`);
    const savedTask = await task.save();
    
    updateSnapshotAfter(savedTask, log._id);
    await savedTask.save();
    
    res.status(201).json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '创建任务失败', error });
  }
};

export const updateTask = async (req: Request, res: Response) => {
  try {
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    const fields = ['title', 'description', 'priority', 'assignee', 'tags', 'dueDate', 'startDate'];
    const changes: { field: string; oldValue: any; newValue: any }[] = [];
    
    const snapshotBefore = getTaskSnapshot(task);
    
    fields.forEach(field => {
      if (req.body[field] !== undefined && JSON.stringify(req.body[field]) !== JSON.stringify(task.get(field))) {
        const oldValue = task.get(field);
        const newValue = req.body[field];
        changes.push({ field, oldValue, newValue });
        addHistoryEntry(task, field, oldValue, newValue);
        task.set(field, req.body[field]);
      }
    });

    if (changes.length > 0) {
      const changeDescs = changes.map(c => `${getFieldLabel(c.field)}`).join('、');
      addOperationLog(task, 'update', `更新了 ${changeDescs}`, changes);
    }

    const savedTask = await task.save();
    res.json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '更新任务失败', error });
  }
};

export const updateTaskStatus = async (req: Request, res: Response) => {
  try {
    const { status } = req.body;
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    if (task.status !== status) {
      if (!canTransition(task.status, status)) {
        return res.status(400).json({ 
          message: '状态流转不合法',
          from: task.status,
          to: status,
          allowedTransitions: STATE_TRANSITIONS[task.status]
        });
      }

      const oldStatus = task.status;
      task.status = status;
      addHistoryEntry(task, 'status', oldStatus, status);
      
      const changes = [{ field: 'status', oldValue: oldStatus, newValue: status }];
      addOperationLog(
        task,
        'status_change',
        `将状态从「${getStatusLabel(oldStatus)}」改为「${getStatusLabel(status)}」`,
        changes
      );
    }

    const savedTask = await task.save();
    res.json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '更新任务状态失败', error });
  }
};

export const updateTaskOrder = async (req: Request, res: Response) => {
  try {
    const { order, status } = req.body;
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    if (status && task.status !== status) {
      if (!canTransition(task.status, status)) {
        return res.status(400).json({ 
          message: '状态流转不合法',
          from: task.status,
          to: status,
          allowedTransitions: STATE_TRANSITIONS[task.status]
        });
      }
    }

    const changes: { field: string; oldValue: any; newValue: any }[] = [];

    if (task.order !== order) {
      changes.push({ field: 'order', oldValue: task.order, newValue: order });
      task.order = order;
    }

    if (status && task.status !== status) {
      const oldStatus = task.status;
      changes.push({ field: 'status', oldValue: oldStatus, newValue: status });
      addHistoryEntry(task, 'status', oldStatus, status);
      task.status = status;
    }

    if (changes.length > 0) {
      const hasStatusChange = changes.some(c => c.field === 'status');
      if (hasStatusChange) {
        const statusChange = changes.find(c => c.field === 'status')!;
        addOperationLog(
          task,
          'status_change',
          `将状态从「${getStatusLabel(statusChange.oldValue)}」改为「${getStatusLabel(statusChange.newValue)}」`,
          changes
        );
      }
    }

    const savedTask = await task.save();
    res.json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '更新任务排序失败', error });
  }
};

export const deleteTask = async (req: Request, res: Response) => {
  try {
    const task = await Task.findByIdAndDelete(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }
    res.json({ message: '任务已删除' });
  } catch (error) {
    res.status(500).json({ message: '删除任务失败', error });
  }
};

export const addSubTask = async (req: Request, res: Response) => {
  try {
    const { title } = req.body;
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    const subTask = {
      _id: new mongoose.Types.ObjectId().toString(),
      title,
      completed: false,
      createdAt: new Date(),
    };
    task.subTasks.push(subTask);
    addHistoryEntry(task, 'subTasks', '添加子任务', title);
    
    const changes = [{ field: 'subTasks', oldValue: null, newValue: title }];
    addOperationLog(task, 'subtask_add', `添加了子任务「${title}」`, changes);

    const savedTask = await task.save();
    res.status(201).json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '添加子任务失败', error });
  }
};

export const updateSubTask = async (req: Request, res: Response) => {
  try {
    const { title, completed } = req.body;
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    const subTaskIndex = task.subTasks.findIndex(st => st._id === req.params.subId);
    if (subTaskIndex === -1) {
      return res.status(404).json({ message: '子任务不存在' });
    }

    const changes: { field: string; oldValue: any; newValue: any }[] = [];
    let operationDesc = '';

    if (title !== undefined && task.subTasks[subTaskIndex].title !== title) {
      changes.push({ field: 'subTask.title', oldValue: task.subTasks[subTaskIndex].title, newValue: title });
      task.subTasks[subTaskIndex].title = title;
      operationDesc = `更新了子任务标题`;
    }
    
    if (completed !== undefined && task.subTasks[subTaskIndex].completed !== completed) {
      changes.push({ field: 'subTask.completed', oldValue: task.subTasks[subTaskIndex].completed, newValue: completed });
      task.subTasks[subTaskIndex].completed = completed;
      operationDesc = completed 
        ? `完成了子任务「${task.subTasks[subTaskIndex].title}」` 
        : `重新打开了子任务「${task.subTasks[subTaskIndex].title}」`;
      
      addOperationLog(
        task,
        completed ? 'subtask_complete' : 'update',
        operationDesc,
        changes
      );
    } else if (changes.length > 0) {
      addOperationLog(task, 'update', operationDesc, changes);
    }

    const savedTask = await task.save();
    res.json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '更新子任务失败', error });
  }
};

export const deleteSubTask = async (req: Request, res: Response) => {
  try {
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    const subTask = task.subTasks.find(st => st._id === req.params.subId);
    task.subTasks = task.subTasks.filter(st => st._id !== req.params.subId);
    
    if (subTask) {
      addHistoryEntry(task, 'subTasks', '删除子任务', subTask.title);
      const changes = [{ field: 'subTasks', oldValue: subTask.title, newValue: null }];
      addOperationLog(task, 'subtask_remove', `删除了子任务「${subTask.title}」`, changes);
    }

    const savedTask = await task.save();
    res.json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '删除子任务失败', error });
  }
};

export const addComment = async (req: Request, res: Response) => {
  try {
    const { content, author } = req.body;
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    const comment = {
      _id: new mongoose.Types.ObjectId().toString(),
      content,
      author: author || '匿名用户',
      createdAt: new Date(),
    };
    task.comments.push(comment);
    
    const changes = [{ field: 'comment', oldValue: null, newValue: content }];
    addOperationLog(
      task,
      'comment_add',
      `添加了评论：${content.substring(0, 50)}${content.length > 50 ? '...' : ''}`,
      changes,
      comment.author
    );

    const savedTask = await task.save();
    res.status(201).json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '添加评论失败', error });
  }
};

export const deleteComment = async (req: Request, res: Response) => {
  try {
    const task = await Task.findById(req.params.id);
    if (!task) {
      return res.status(404).json({ message: '任务不存在' });
    }

    const comment = task.comments.find(c => c._id === req.params.commentId);
    task.comments = task.comments.filter(c => c._id !== req.params.commentId);

    if (comment) {
      const changes = [{ field: 'comment', oldValue: comment.content, newValue: null }];
      addOperationLog(task, 'comment_remove', `删除了评论`, changes);
    }

    const savedTask = await task.save();
    res.json(savedTask);
  } catch (error) {
    res.status(500).json({ message: '删除评论失败', error });
  }
};

function getFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    title: '标题',
    description: '描述',
    status: '状态',
    priority: '优先级',
    assignee: '负责人',
    tags: '标签',
    dueDate: '截止日期',
    startDate: '开始日期',
    subTasks: '子任务',
  };
  return labels[field] || field;
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    'todo': '待办',
    'in-progress': '进行中',
    'done': '已完成',
  };
  return labels[status] || status;
}
