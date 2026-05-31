import { Router, type Request, type Response } from 'express';
import * as exportService from '../services/exportService.js';
import type { CardData } from '../types/index.js';

const router = Router();

router.post('/card/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const format = (req.query.format as string) || 'png';
    const resolution = parseInt(req.query.resolution as string) || 1;
    const buffer = await exportService.exportCardAsImage(req.params.id, format, resolution);

    const contentTypes: Record<string, string> = {
      png: 'image/png',
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      webp: 'image/webp',
    };

    res.type(contentTypes[format] || 'image/png');
    res.set('Content-Disposition', `attachment; filename="card-${req.params.id}.${format}"`);
    res.send(buffer);
  } catch (error: any) {
    if (error.message?.includes('not found')) {
      res.status(404).json({ success: false, error: error.message });
      return;
    }
    res.status(500).json({ success: false, error: 'Failed to export card' });
  }
});

router.post('/batch', async (req: Request, res: Response): Promise<void> => {
  try {
    const { cardIds, format = 'png', resolution = 1 } = req.body;
    if (!Array.isArray(cardIds) || cardIds.length === 0) {
      res.status(400).json({ success: false, error: 'cardIds must be a non-empty array' });
      return;
    }

    const buffer = await exportService.exportBatchAsZip(cardIds, format, resolution);
    res.type('application/zip');
    res.set('Content-Disposition', 'attachment; filename="cards-export.zip"');
    res.send(buffer);
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to export batch' });
  }
});

router.post('/generate/batch', async (req: Request, res: Response): Promise<void> => {
  try {
    const { cards } = req.body;
    if (!Array.isArray(cards) || cards.length === 0) {
      res.status(400).json({ success: false, error: 'cards must be a non-empty array' });
      return;
    }

    const startTime = Date.now();
    const results = await exportService.batchGenerateCards(cards);
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);

    res.json({
      success: true,
      data: results,
      count: results.length,
      duration: `${duration}s`,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to generate batch cards' });
  }
});

router.post('/print', async (req: Request, res: Response): Promise<void> => {
  try {
    const printOptions = req.body;
    if (!printOptions.cardIds || !Array.isArray(printOptions.cardIds) || printOptions.cardIds.length === 0) {
      res.status(400).json({ success: false, error: 'cardIds must be a non-empty array' });
      return;
    }

    const buffer = await exportService.exportAsPdf(printOptions);
    res.type('application/pdf');
    res.set('Content-Disposition', 'attachment; filename="cards-print.pdf"');
    res.send(buffer);
  } catch (error: any) {
    console.error('PDF export error:', error);
    if (error.message?.includes('No valid cards')) {
      res.status(400).json({ success: false, error: error.message });
      return;
    }
    res.status(500).json({ success: false, error: 'Failed to export PDF: ' + error.message });
  }
});

router.post('/json', async (req: Request, res: Response): Promise<void> => {
  try {
    const { cardIds } = req.body;
    if (!Array.isArray(cardIds) || cardIds.length === 0) {
      res.status(400).json({ success: false, error: 'cardIds must be a non-empty array' });
      return;
    }

    const json = await exportService.exportAsJson(cardIds);
    res.type('application/json');
    res.set('Content-Disposition', 'attachment; filename="cards-export.json"');
    res.send(json);
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to export JSON' });
  }
});

export default router;
