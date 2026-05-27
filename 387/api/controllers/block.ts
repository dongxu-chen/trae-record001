import { type Request, type Response } from 'express';
import { getBlockByNumber, getLatestBlocks } from '../services/web3.js';

export async function getLatestBlocksHandler(req: Request, res: Response): Promise<void> {
  try {
    const count = Math.min(Number(req.query.count) || 10, 20);
    const blocks = await getLatestBlocks(count);
    res.json({ success: true, data: blocks });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getBlockHandler(req: Request, res: Response): Promise<void> {
  try {
    const blockNumber = Number(req.params.number);
    const block = await getBlockByNumber(blockNumber);
    if (!block) {
      res.status(404).json({ success: false, error: 'Block not found' });
      return;
    }
    res.json({ success: true, data: block });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
