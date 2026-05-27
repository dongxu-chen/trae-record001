import { type Request, type Response } from 'express';
import {
  getContractInfo,
  verifyContract,
  callContractMethod,
  readContractMethod,
  getContractEvents,
  estimateGas,
} from '../services/contract.js';

export async function getContractHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const info = await getContractInfo(address);
    res.json({ success: true, data: info });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function verifyContractHandler(req: Request, res: Response): Promise<void> {
  try {
    const { address, source, compilerVersion, name, optimization, runs } = req.body;
    if (!address || !source) {
      res.status(400).json({ success: false, error: 'Address and source are required' });
      return;
    }
    const result = await verifyContract(
      address,
      source,
      compilerVersion || 'v0.8.19',
      name || 'Contract',
      optimization ?? true,
      runs || 200,
    );
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function callContractHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const { method, params, from, value } = req.body;
    if (!method) {
      res.status(400).json({ success: false, error: 'Method name is required' });
      return;
    }
    const result = await callContractMethod(address, method, params || [], from, value);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function readContractHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const { abi, method, params } = req.body;
    if (!abi || !method) {
      res.status(400).json({ success: false, error: 'ABI and method are required' });
      return;
    }
    const result = await readContractMethod(address, abi, method, params || []);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getContractEventsHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const { abi, eventName, fromBlock } = req.body;
    if (!abi) {
      res.status(400).json({ success: false, error: 'ABI is required' });
      return;
    }
    const events = await getContractEvents(address, abi, eventName, fromBlock || 'latest');
    res.json({ success: true, data: events });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function estimateGasHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const { abi, method, params, from, value } = req.body;
    if (!abi || !method) {
      res.status(400).json({ success: false, error: 'ABI and method are required' });
      return;
    }
    const result = await estimateGas(address, abi, method, params || [], from, value);
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
