import { type Request, type Response } from 'express';
import { getTransactionByHash, getLatestTransactions, getBlockTransactions } from '../services/web3.js';

export async function getLatestTransactionsHandler(req: Request, res: Response): Promise<void> {
  try {
    const count = Math.min(Number(req.query.count) || 10, 20);
    const transactions = await getLatestTransactions(count);
    res.json({ success: true, data: transactions });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getTransactionHandler(req: Request, res: Response): Promise<void> {
  try {
    const hash = req.params.hash;
    const transaction = await getTransactionByHash(hash);
    if (!transaction) {
      res.status(404).json({ success: false, error: 'Transaction not found' });
      return;
    }
    res.json({ success: true, data: transaction });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getBlockTransactionsHandler(req: Request, res: Response): Promise<void> {
  try {
    const blockNumber = Number(req.params.blockNumber);
    const transactions = await getBlockTransactions(blockNumber);
    res.json({ success: true, data: transactions });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
