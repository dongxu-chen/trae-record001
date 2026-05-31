import { Router, type Request, type Response } from 'express';
import * as cardService from '../services/cardService.js';

const router = Router();

router.get('/', async (_req: Request, res: Response): Promise<void> => {
  try {
    const cards = await cardService.getAllCards();
    res.json({ success: true, data: cards });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch cards' });
  }
});

router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const card = await cardService.getCard(req.params.id);
    if (!card) {
      res.status(404).json({ success: false, error: 'Card not found' });
      return;
    }
    res.json({ success: true, data: card });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch card' });
  }
});

router.post('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const card = await cardService.createCard(req.body);
    res.status(201).json({ success: true, data: card });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to create card' });
  }
});

router.put('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const card = await cardService.updateCard(req.params.id, req.body);
    if (!card) {
      res.status(404).json({ success: false, error: 'Card not found' });
      return;
    }
    res.json({ success: true, data: card });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to update card' });
  }
});

router.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const deleted = await cardService.deleteCard(req.params.id);
    if (!deleted) {
      res.status(404).json({ success: false, error: 'Card not found' });
      return;
    }
    res.json({ success: true, message: 'Card deleted' });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to delete card' });
  }
});

export default router;
