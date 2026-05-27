import { type Request, type Response } from 'express';
import { getWeb3, getAllChains, getChainConfig } from '../services/multichain.js';

export async function getChainsHandler(req: Request, res: Response): Promise<void> {
  try {
    const chains = getAllChains();
    res.json({ success: true, data: chains });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getMultiChainAddressHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const chains = getAllChains();
    const results: any[] = [];

    for (const chain of chains) {
      try {
        const web3 = getWeb3(chain.id);
        const [balance, nonce, code] = await Promise.all([
          web3.eth.getBalance(address).catch(() => 0n),
          web3.eth.getTransactionCount(address).catch(() => 0),
          web3.eth.getCode(address).catch(() => '0x'),
        ]);

        results.push({
          chainId: chain.id,
          chainName: chain.name,
          chainColor: chain.color,
          currency: chain.currency,
          balance: balance.toString(),
          transactionCount: Number(nonce),
          isContract: (code as string) !== '0x',
          explorer: chain.explorer,
        });
      } catch {
        results.push({
          chainId: chain.id,
          chainName: chain.name,
          chainColor: chain.color,
          currency: chain.currency,
          balance: '0',
          transactionCount: 0,
          isContract: false,
          explorer: chain.explorer,
          error: 'Failed to fetch',
        });
      }
    }

    res.json({ success: true, data: results });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getChainBlockHandler(req: Request, res: Response): Promise<void> {
  try {
    const chainId = req.params.chainId;
    const blockNumber = req.params.blockNumber;
    const web3 = getWeb3(chainId);
    const config = getChainConfig(chainId);

    const block = await web3.eth.getBlock(blockNumber === 'latest' ? 'latest' : Number(blockNumber));
    if (!block) {
      res.status(404).json({ success: false, error: 'Block not found' });
      return;
    }

    res.json({
      success: true,
      data: {
        chainId,
        chainName: config?.name,
        number: Number(block.number),
        hash: block.hash,
        timestamp: Number(block.timestamp),
        miner: block.miner,
        gasUsed: block.gasUsed.toString(),
        gasLimit: block.gasLimit.toString(),
        transactionCount: (block.transactions as string[]).length,
        baseFeePerGas: (block.baseFeePerGas || 0n).toString(),
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
