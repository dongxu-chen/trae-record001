import express from 'express';
import {
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  updateTaskStatus,
  updateTaskOrder,
  addSubTask,
  updateSubTask,
  deleteSubTask,
  addComment,
  deleteComment,
} from '../controllers/taskController';

const router = express.Router();

router.get('/', getTasks);
router.get('/:id', getTask);
router.post('/', createTask);
router.put('/:id', updateTask);
router.delete('/:id', deleteTask);
router.patch('/:id/status', updateTaskStatus);
router.patch('/:id/order', updateTaskOrder);
router.post('/:id/subtasks', addSubTask);
router.put('/:id/subtasks/:subId', updateSubTask);
router.delete('/:id/subtasks/:subId', deleteSubTask);
router.post('/:id/comments', addComment);
router.delete('/:id/comments/:commentId', deleteComment);

export default router;
