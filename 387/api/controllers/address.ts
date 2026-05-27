import { type Request, type Response } from 'express';
import { getAddressInfo, getAddressTransactions, getERC20Balance } from '../services/web3.js';

const COMMON_TOKENS = [
  { address: '0xdAC17F958D2ee523a2206206994597C13D831ec7', name: 'Tether USD', symbol: 'USDT' },
  { address: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', name: 'USD Coin', symbol: 'USDC' },
  { address: '0xB8c77482e45F1F44dE1745F52C74426C631bDD52', name: 'BNB', symbol: 'BNB' },
  { address: '0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE', name: 'Shiba Inu', symbol: 'SHIB' },
  { address: '0x6B175474E89094C44Da98b954EedeAC495271d0F', name: 'Dai Stablecoin', symbol: 'DAI' },
];

export async function getAddressHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const info = await getAddressInfo(address);
    res.json({ success: true, data: { address, ...info } });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getAddressTransactionsHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const limit = Math.min(Number(req.query.limit) || 20, 50);
    const transactions = await getAddressTransactions(address, limit);
    res.json({ success: true, data: transactions });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}

export async function getAddressTokensHandler(req: Request, res: Response): Promise<void> {
  try {
    const address = req.params.address;
    const tokenBalances = [];

    for (const token of COMMON_TOKENS) {
      const balance = await getERC20Balance(address, token.address);
      if (Number(balance.balance) > 0) {
        tokenBalances.push({
          ...balance,
          tokenAddress: token.address,
          tokenName: token.name,
          tokenSymbol: token.symbol,
        });
      }
    }

    res.json({ success: true, data: tokenBalances });
  } catch (error) {
    res.status(500).json({ success: false, error: (error as Error).message });
  }
}
