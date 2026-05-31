import { Router, Request, Response } from 'express';
import { store } from '../store/memoryStore';

const router = Router();

const sampleChartData = {
  xAxis: {
    type: 'category',
    data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  },
  yAxis: {
    type: 'value'
  },
  series: [{
    data: [820, 932, 901, 934, 1290, 1330, 1320],
    type: 'line',
    smooth: true,
    areaStyle: {}
  }]
};

router.post('/', (req: Request, res: Response) => {
  try {
    const { chartData = sampleChartData, chartType = 'line' } = req.body;
    const session = store.createSession(chartData, chartType);
    res.json({ sessionId: session.id });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create session' });
  }
});

router.get('/:id', (req: Request, res: Response) => {
  try {
    const session = store.getSession(req.params.id);
    if (session) {
      res.json(session);
    } else {
      res.status(404).json({ error: 'Session not found' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to get session' });
  }
});

router.get('/:id/annotations', (req: Request, res: Response) => {
  try {
    const annotations = store.getAnnotations(req.params.id);
    if (annotations) {
      res.json(annotations);
    } else {
      res.status(404).json({ error: 'Session not found' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to get annotations' });
  }
});

export default router;
