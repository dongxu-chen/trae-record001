import { Router } from 'express';
import { rulesRepository } from '../db/repositories.js';
import { computeHealthScore } from '../services/healthScore.js';

const router = Router();

router.get('/score', (_req, res) => {
  const rules = rulesRepository.getAll();
  const healthScore = computeHealthScore(rules);
  res.json(healthScore);
});

export default router;
