import Web3 from 'web3';

export interface ChainConfig {
  id: string;
  name: string;
  chainId: number;
  rpcUrl: string;
  currency: { name: string; symbol: string; decimals: number };
  explorer?: string;
  color: string;
}

export const CHAIN_CONFIGS: ChainConfig[] = [
  {
    id: 'ethereum',
    name: 'Ethereum',
    chainId: 1,
    rpcUrl: process.env.ETHEREUM_RPC || 'https://ethereum-rpc.publicnode.com',
    currency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    explorer: 'https://etherscan.io',
    color: '#627EEA',
  },
  {
    id: 'bsc',
    name: 'BNB Chain',
    chainId: 56,
    rpcUrl: process.env.BSC_RPC || 'https://bsc-rpc.publicnode.com',
    currency: { name: 'BNB', symbol: 'BNB', decimals: 18 },
    explorer: 'https://bscscan.com',
    color: '#F3BA2F',
  },
  {
    id: 'polygon',
    name: 'Polygon',
    chainId: 137,
    rpcUrl: process.env.POLYGON_RPC || 'https://polygon-bor-rpc.publicnode.com',
    currency: { name: 'POL', symbol: 'POL', decimals: 18 },
    explorer: 'https://polygonscan.com',
    color: '#8247E5',
  },
  {
    id: 'arbitrum',
    name: 'Arbitrum',
    chainId: 42161,
    rpcUrl: process.env.ARBITRUM_RPC || 'https://arb1.arbitrum.io/rpc',
    currency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    explorer: 'https://arbiscan.io',
    color: '#28A0F0',
  },
  {
    id: 'optimism',
    name: 'Optimism',
    chainId: 10,
    rpcUrl: process.env.OPTIMISM_RPC || 'https://optimism-rpc.publicnode.com',
    currency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    explorer: 'https://optimistic.etherscan.io',
    color: '#FF0420',
  },
];

const web3Instances: Map<string, Web3> = new Map();

export function getWeb3(chainId: string): Web3 {
  if (web3Instances.has(chainId)) {
    return web3Instances.get(chainId)!;
  }

  const config = CHAIN_CONFIGS.find((c) => c.id === chainId);
  if (!config) {
    throw new Error(`Chain ${chainId} not configured`);
  }

  const web3 = new Web3(new Web3.providers.HttpProvider(config.rpcUrl));
  web3Instances.set(chainId, web3);
  return web3;
}

export function getChainConfig(chainId: string): ChainConfig | undefined {
  return CHAIN_CONFIGS.find((c) => c.id === chainId);
}

export function getAllChains(): ChainConfig[] {
  return [...CHAIN_CONFIGS];
}
