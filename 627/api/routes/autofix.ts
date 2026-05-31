import { Router } from 'express';
import { issuesRepository } from '../db/repositories.js';
import { previewAutoFix, executeAutoFix } from '../services/autoFix.js';

const router = Router();

router.post('/preview', (_req, res) => {
  const openIssues = issuesRepository.getAll({ status: 'open' });
  const preview = previewAutoFix(openIssues);
  res.json(preview);
});

router.post('/execute', (req, res) => {
  const { issueIds } = req.body as { issueIds?: string[] };
  if (!issueIds || !Array.isArray(issueIds)) {
    res.status(400).json({ error: 'issueIds is required' });
    return;
  }
  const results = executeAutoFix(issueIds);
  res.json({ results, fixedCount: results.filter(r => r.fixed).length });
});

export default router;
