import { type Request, type Response } from 'express';
import { getBlockByNumber, getTransactionByHash, getAddressInfo } from '../services/web3.js';

export async function searchHandler(req: Request, res: Response): Promise<void> {
  try {
    const query = (req.query.q as string) || '';
    if (!query) {
      res.status(400).json({ success: false, error: 'Query parameter is required' });
      return;
    }

    const trimmed = query.trim();

    if (/^\d+$/.test(trimmed)) {
      const block = await getBlockByNumber(Number(trimmed));
      if (block) {
        res.json({ success: true, data: { type: 'block', result: block } });
        return;
      }
    }

    if (/^0x[a-fA-F0-9]{64}$/.test(trimmed)) {
      const tx = await getTransactionByHash(trimmed);
      if (tx) {
        res.json({ success: true, data: { type: 'transaction', result: tx } });
        return;
      }
    }

    if (/^0x[a-fA-F0-9]{40}$/.test(trimmed)) {
      const info = await getAddressInfo(trimmed);
      res.json({ success: true, data: { type: 'address', result: { address: trimmed, ...info } } });
      return;
    }

    res.status(404).json({ success: false, error: 'No results found for the given query' });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
