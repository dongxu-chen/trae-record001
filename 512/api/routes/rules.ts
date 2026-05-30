import { Router, type Request, type Response } from 'express';
import { getAllRules, saveRule, getRule, deleteRule, incrementId } from '../services/redis.js';
import { recommendThreshold } from '../services/smart-threshold.js';
import { recordFeedback, adjustThresholdBasedOnFeedback, getFeedbackStats } from '../services/feedback-loop.js';

const router = Router();

router.get('/', async (_req: Request, res: Response): Promise<void> => {
  try {
    const rules = await getAllRules();
    res.json({ success: true, data: rules });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to get rules' });
  }
});

router.post('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const { name, metric, conditions, level, enabled } = req.body;

    if (!name || !metric || !conditions || !level) {
      res.status(400).json({ success: false, error: 'Missing required fields: name, metric, conditions, level' });
      return;
    }

    const id = `rule-${Date.now()}-${await incrementId('rule')}`;
    const now = new Date().toISOString();

    const rule = {
      id,
      name,
      metric,
      conditions,
      level,
      enabled: enabled !== undefined ? enabled : true,
      createdAt: now,
      updatedAt: now,
    };

    await saveRule(rule);
    res.status(201).json({ success: true, data: rule });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to create rule' });
  }
});

router.put('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const existing = await getRule(id);

    if (!existing) {
      res.status(404).json({ success: false, error: 'Rule not found' });
      return;
    }

    const { name, metric, conditions, level, enabled } = req.body;
    const now = new Date().toISOString();

    const updated = {
      ...existing,
      name: name ?? existing.name,
      metric: metric ?? existing.metric,
      conditions: conditions ?? existing.conditions,
      level: level ?? existing.level,
      enabled: enabled !== undefined ? enabled : existing.enabled,
      updatedAt: now,
    };

    await saveRule(updated);
    res.json({ success: true, data: updated });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to update rule' });
  }
});

router.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const deleted = await deleteRule(id);

    if (!deleted) {
      res.status(404).json({ success: false, error: 'Rule not found' });
      return;
    }

    res.json({ success: true, message: 'Rule deleted' });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to delete rule' });
  }
});

router.get('/smart-threshold/:metric', async (req: Request, res: Response): Promise<void> => {
  try {
    const { metric } = req.params;
    const method = (req.query.method as 'zscore' | 'percentile' | 'iqr') || 'zscore';
    const sensitivity = (req.query.sensitivity as 'low' | 'medium' | 'high') || 'medium';

    if (!['zscore', 'percentile', 'iqr'].includes(method)) {
      res.status(400).json({ success: false, error: 'Invalid method. Use zscore, percentile, or iqr' });
      return;
    }

    if (!['low', 'medium', 'high'].includes(sensitivity)) {
      res.status(400).json({ success: false, error: 'Invalid sensitivity. Use low, medium, or high' });
      return;
    }

    const recommendation = await recommendThreshold(metric, method, sensitivity);
    res.json({ success: true, data: recommendation });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to get smart threshold recommendation' });
  }
});

router.put('/:id/feedback', async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const { alertId, type, comment, autoAdjust } = req.body;

    if (!type || !['false_positive', 'true_positive', 'needs_adjustment'].includes(type)) {
      res.status(400).json({ success: false, error: 'Invalid feedback type' });
      return;
    }

    const rule = await getRule(id);
    if (!rule) {
      res.status(404).json({ success: false, error: 'Rule not found' });
      return;
    }

    const feedback = await recordFeedback(alertId || 'unknown', id, type, comment);

    let adjustedRule = null;
    if (autoAdjust) {
      adjustedRule = await adjustThresholdBasedOnFeedback(id);
    }

    const stats = await getFeedbackStats(id);

    res.json({
      success: true,
      data: {
        feedback,
        stats,
        adjustedRule,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to record feedback' });
  }
});

router.get('/:id/feedback-stats', async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const stats = await getFeedbackStats(id);
    res.json({ success: true, data: stats });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to get feedback stats' });
  }
});

export default router;
