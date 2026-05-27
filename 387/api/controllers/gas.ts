import { type Request, type Response } from 'express';
import { getCurrentGas, getGasHistory } from '../services/gas.js';

export async function getLatestGasHandler(req: Request, res: Response): Promise<void> {
  try {
    const gas = await getCurrentGas();
    res.json({ success: true, data: { ...gas, timestamp: Math.floor(Date.now() / 1000) } });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getGasHistoryHandler(req: Request, res: Response): Promise<void> {
  try {
    const days = Math.min(Number(req.query.days) || 7, 30);
    const history = await getGasHistory(days);
    res.json({ success: true, data: history });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
