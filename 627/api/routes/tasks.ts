import { Router } from 'express';
import { tasksRepository, executionsRepository, rulesRepository } from '../db/repositories.js';
import { startScheduledTask, restartTask, stopTask, runTaskExecution } from '../services/scheduler.js';
import type { ScheduledTask } from '../../shared/types.js';

const router = Router();

router.get('/', (_req, res) => {
  const tasks = tasksRepository.getAll();
  res.json(tasks);
});

router.get('/executions', (_req, res) => {
  const executions = executionsRepository.getRecent(50);
  res.json(executions);
});

router.get('/:id', (req, res) => {
  const task = tasksRepository.getById(req.params.id);
  if (!task) {
    res.status(404).json({ error: 'Task not found' });
    return;
  }
  res.json(task);
});

router.post('/', (req, res) => {
  try {
    const taskData = req.body as Omit<ScheduledTask, 'id' | 'createdAt' | 'updatedAt'>;
    const task = tasksRepository.create(taskData);
    startScheduledTask(task);
    res.status(201).json(task);
  } catch (error) {
    console.error('Create task error:', error);
    res.status(400).json({ error: 'Failed to create task' });
  }
});

router.put('/:id', (req, res) => {
  try {
    const task = tasksRepository.update(req.params.id, req.body);
    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }
    restartTask(task);
    res.json(task);
  } catch (error) {
    console.error('Update task error:', error);
    res.status(400).json({ error: 'Failed to update task' });
  }
});

router.post('/:id/run', async (req, res) => {
  const task = tasksRepository.getById(req.params.id);
  if (!task) {
    res.status(404).json({ error: 'Task not found' });
    return;
  }
  await runTaskExecution(task);
  res.json({ message: 'Task executed successfully' });
});

router.delete('/:id', (req, res) => {
  stopTask(req.params.id);
  res.status(204).send();
});

export default router;
