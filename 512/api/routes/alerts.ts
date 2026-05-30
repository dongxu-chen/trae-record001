import { Router, type Request, type Response } from 'express';
import { getAlerts, getAlertById, acknowledgeAlert } from '../services/redis.js';
import { recordFeedback, getFeedbackStats } from '../services/feedback-loop.js';
import { getRelatedMetrics } from '../services/alert-correlation.js';

const router = Router();

router.get('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const page = Number(req.query.page) || 1;
    const pageSize = Number(req.query.pageSize) || 20;
    const level = req.query.level as string | undefined;
    const metric = req.query.metric as string | undefined;
    const startTime = req.query.startTime as string | undefined;
    const endTime = req.query.endTime as string | undefined;
    const acknowledged = req.query.acknowledged as string | undefined;

    const result = await getAlerts({
      page,
      pageSize,
      level,
      metric,
      startTime,
      endTime,
      acknowledged,
    });

    res.json({
      success: true,
      data: result.data,
      pagination: {
        page,
        pageSize,
        total: result.total,
        totalPages: Math.ceil(result.total / pageSize),
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to get alerts' });
  }
});

router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const alert = await getAlertById(id);

    if (!alert) {
      res.status(404).json({ success: false, error: 'Alert not found' });
      return;
    }

    res.json({ success: true, data: alert });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to get alert' });
  }
});

router.put('/:id/acknowledge', async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const alert = await acknowledgeAlert(id);

    if (!alert) {
      res.status(404).json({ success: false, error: 'Alert not found' });
      return;
    }

    res.json({ success: true, data: alert });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to acknowledge alert' });
  }
});

router.post('/:id/feedback', async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const { type, comment } = req.body;

    if (!type || !['false_positive', 'true_positive', 'needs_adjustment'].includes(type)) {
      res.status(400).json({ success: false, error: 'Invalid feedback type' });
      return;
    }

    const alert = await getAlertById(id);
    if (!alert) {
      res.status(404).json({ success: false, error: 'Alert not found' });
      return;
    }

    const feedback = await recordFeedback(id, alert.ruleId, type, comment);
    const stats = await getFeedbackStats(alert.ruleId);

    res.json({
      success: true,
      data: {
        feedback,
        stats,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to record feedback' });
  }
});

router.get('/related/:metric', async (req: Request, res: Response): Promise<void> => {
  try {
    const { metric } = req.params;
    const related = getRelatedMetrics(metric);
    res.json({ success: true, data: related });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to get related metrics' });
  }
});

export default router;
