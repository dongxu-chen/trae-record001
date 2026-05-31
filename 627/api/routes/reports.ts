import { Router } from 'express';
import { executionsRepository } from '../db/repositories.js';

const router = Router();

router.get('/', (_req, res) => {
  const executions = executionsRepository.getRecent(20);
  res.json(executions);
});

router.get('/:id', (req, res) => {
  const executions = executionsRepository.getRecent(100);
  const execution = executions.find(e => e.id === req.params.id);
  if (!execution) {
    res.status(404).json({ error: 'Report not found' });
    return;
  }
  res.json(execution);
});

export default router;
