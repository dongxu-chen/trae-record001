import { Router } from 'express';
import {
  rulesRepository,
  ruleTemplatesRepository,
} from '../db/repositories.js';
import { executeRule, getAvailableTables, getTableColumns } from '../services/ruleEngine.js';
import type { DataQualityRule } from '../../shared/types.js';

const router = Router();

router.get('/templates', (_req, res) => {
  const templates = ruleTemplatesRepository.getAll();
  res.json(templates);
});

router.get('/tables', (_req, res) => {
  const tables = getAvailableTables();
  res.json(tables);
});

router.get('/tables/:name/columns', (req, res) => {
  const columns = getTableColumns(req.params.name);
  res.json(columns);
});

router.get('/', (_req, res) => {
  const rules = rulesRepository.getAll();
  res.json(rules);
});

router.get('/:id', (req, res) => {
  const rule = rulesRepository.getById(req.params.id);
  if (!rule) {
    res.status(404).json({ error: 'Rule not found' });
    return;
  }
  res.json(rule);
});

router.post('/', (req, res) => {
  try {
    const ruleData = req.body as Omit<DataQualityRule, 'id' | 'createdAt' | 'updatedAt'>;
    const rule = rulesRepository.create(ruleData);
    res.status(201).json(rule);
  } catch (error) {
    res.status(400).json({ error: 'Failed to create rule' });
  }
});

router.put('/:id', (req, res) => {
  try {
    const rule = rulesRepository.update(req.params.id, req.body);
    if (!rule) {
      res.status(404).json({ error: 'Rule not found' });
      return;
    }
    res.json(rule);
  } catch (error) {
    res.status(400).json({ error: 'Failed to update rule' });
  }
});

router.delete('/:id', (req, res) => {
  const deleted = rulesRepository.delete(req.params.id);
  if (!deleted) {
    res.status(404).json({ error: 'Rule not found' });
    return;
  }
  res.status(204).send();
});

router.post('/:id/test', (req, res) => {
  const rule = rulesRepository.getById(req.params.id);
  if (!rule) {
    res.status(404).json({ error: 'Rule not found' });
    return;
  }
  const result = executeRule(rule);
  res.json(result);
});

export default router;
