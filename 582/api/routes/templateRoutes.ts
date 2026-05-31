import { Router, type Request, type Response } from 'express';
import * as templateService from '../services/templateService.js';

const router = Router();

router.get('/', async (_req: Request, res: Response): Promise<void> => {
  try {
    const templates = await templateService.getAllTemplates();
    res.json({ success: true, data: templates });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch templates' });
  }
});

router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const template = await templateService.getTemplate(req.params.id);
    if (!template) {
      res.status(404).json({ success: false, error: 'Template not found' });
      return;
    }
    res.json({ success: true, data: template });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch template' });
  }
});

router.post('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const template = await templateService.createTemplate(req.body);
    res.status(201).json({ success: true, data: template });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to create template' });
  }
});

router.put('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const template = await templateService.updateTemplate(req.params.id, req.body);
    if (!template) {
      res.status(404).json({ success: false, error: 'Template not found' });
      return;
    }
    res.json({ success: true, data: template });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to update template' });
  }
});

router.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const deleted = await templateService.deleteTemplate(req.params.id);
    if (!deleted) {
      res.status(400).json({ success: false, error: 'Template not found or is built-in and cannot be deleted' });
      return;
    }
    res.json({ success: true, message: 'Template deleted' });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to delete template' });
  }
});

export default router;
