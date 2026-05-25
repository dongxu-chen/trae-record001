import { Request, Response } from 'express';
import Board from '../models/Board';
import Task from '../models/Task';

export const getBoards = async (req: Request, res: Response) => {
  try {
    const boards = await Board.find().sort({ createdAt: -1 });
    res.json(boards);
  } catch (error) {
    res.status(500).json({ message: '获取看板列表失败', error });
  }
};

export const getBoard = async (req: Request, res: Response) => {
  try {
    const board = await Board.findById(req.params.id);
    if (!board) {
      return res.status(404).json({ message: '看板不存在' });
    }
    res.json(board);
  } catch (error) {
    res.status(500).json({ message: '获取看板失败', error });
  }
};

export const createBoard = async (req: Request, res: Response) => {
  try {
    const { name, description } = req.body;
    const board = new Board({ name, description });
    const savedBoard = await board.save();
    res.status(201).json(savedBoard);
  } catch (error) {
    res.status(500).json({ message: '创建看板失败', error });
  }
};

export const updateBoard = async (req: Request, res: Response) => {
  try {
    const { name, description } = req.body;
    const board = await Board.findByIdAndUpdate(
      req.params.id,
      { name, description },
      { new: true }
    );
    if (!board) {
      return res.status(404).json({ message: '看板不存在' });
    }
    res.json(board);
  } catch (error) {
    res.status(500).json({ message: '更新看板失败', error });
  }
};

export const deleteBoard = async (req: Request, res: Response) => {
  try {
    const board = await Board.findByIdAndDelete(req.params.id);
    if (!board) {
      return res.status(404).json({ message: '看板不存在' });
    }
    await Task.deleteMany({ boardId: req.params.id });
    res.json({ message: '看板已删除' });
  } catch (error) {
    res.status(500).json({ message: '删除看板失败', error });
  }
};

export const getBoardTasks = async (req: Request, res: Response) => {
  try {
    const tasks = await Task.find({ boardId: req.params.id }).sort({ order: 1, createdAt: -1 });
    res.json(tasks);
  } catch (error) {
    res.status(500).json({ message: '获取任务列表失败', error });
  }
};
