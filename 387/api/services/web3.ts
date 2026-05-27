import { web3 } from '../config/index.js';

export interface BlockInfo {
  number: number;
  hash: string;
  parentHash: string;
  timestamp: number;
  miner: string;
  gasUsed: string;
  gasLimit: string;
  transactionCount: number;
  difficulty: string;
  totalDifficulty: string;
  size: number;
  nonce: string;
  baseFeePerGas: string;
}

export interface TransactionInfo {
  hash: string;
  blockNumber: number;
  blockHash: string;
  from: string;
  to: string | null;
  value: string;
  gas: string;
  gasPrice: string;
  gasUsed: string;
  input: string;
  nonce: number;
  transactionIndex: number;
  status: number;
  timestamp: number;
  type: number;
  maxFeePerGas?: string;
  maxPriorityFeePerGas?: string;
  creates?: string | null;
}

export async function getLatestBlockNumber(): Promise<number> {
  return Number(await web3.eth.getBlockNumber());
}

export async function getBlockByNumber(blockNumber: number): Promise<BlockInfo | null> {
  try {
    const block = await web3.eth.getBlock(blockNumber);
    if (!block) return null;

    return {
      number: Number(block.number),
      hash: block.hash as string,
      parentHash: block.parentHash as string,
      timestamp: Number(block.timestamp),
      miner: block.miner as string,
      gasUsed: block.gasUsed.toString(),
      gasLimit: block.gasLimit.toString(),
      transactionCount: (block.transactions as string[]).length,
      difficulty: block.difficulty.toString(),
      totalDifficulty: (block.totalDifficulty || '0').toString(),
      size: Number(block.size || 0),
      nonce: (block.nonce as string) || '0x',
      baseFeePerGas: (block.baseFeePerGas || '0').toString(),
    };
  } catch (error) {
    console.error('Error fetching block:', error);
    return null;
  }
}

export async function getLatestBlocks(count: number = 10): Promise<BlockInfo[]> {
  const latest = await getLatestBlockNumber();
  const blocks: BlockInfo[] = [];

  for (let i = 0; i < count; i++) {
    const block = await getBlockByNumber(latest - i);
    if (block) blocks.push(block);
  }

  return blocks;
}

export async function getTransactionByHash(hash: string): Promise<TransactionInfo | null> {
  try {
    const tx = await web3.eth.getTransaction(hash);
    if (!tx) return null;

    const receipt = await web3.eth.getTransactionReceipt(hash);
    const block = await web3.eth.getBlock(tx.blockNumber as number);

    return {
      hash: tx.hash as string,
      blockNumber: Number(tx.blockNumber),
      blockHash: tx.blockHash as string,
      from: tx.from as string,
      to: tx.to as string | null,
      value: tx.value.toString(),
      gas: tx.gas.toString(),
      gasPrice: tx.gasPrice?.toString() || '0',
      gasUsed: receipt?.gasUsed?.toString() || '0',
      input: tx.input as string,
      nonce: Number(tx.nonce),
      transactionIndex: Number(tx.transactionIndex),
      status: receipt?.status ? 1 : 0,
      timestamp: block ? Number(block.timestamp) : 0,
      type: Number(tx.type || 0),
      maxFeePerGas: tx.maxFeePerGas?.toString(),
      maxPriorityFeePerGas: tx.maxPriorityFeePerGas?.toString(),
      creates: receipt?.contractAddress as string | undefined || undefined,
    };
  } catch (error) {
    console.error('Error fetching transaction:', error);
    return null;
  }
}

export async function getLatestTransactions(count: number = 10): Promise<TransactionInfo[]> {
  const latest = await getLatestBlockNumber();
  const transactions: TransactionInfo[] = [];

  for (let i = 0; i < count && transactions.length < count; i++) {
    const block = await web3.eth.getBlock(latest - i);
    if (!block) continue;

    const txHashes = block.transactions as string[];
    for (const txHash of txHashes.slice(0, count - transactions.length)) {
      const tx = await getTransactionByHash(txHash);
      if (tx) transactions.push(tx);
    }
  }

  return transactions;
}

export async function getBlockTransactions(blockNumber: number): Promise<TransactionInfo[]> {
  const block = await web3.eth.getBlock(blockNumber);
  if (!block) return [];

  const txHashes = block.transactions as string[];
  const transactions: TransactionInfo[] = [];

  for (const txHash of txHashes) {
    const tx = await getTransactionByHash(txHash);
    if (tx) transactions.push(tx);
  }

  return transactions;
}

export async function getAddressInfo(address: string): Promise<{ balance: string; transactionCount: number; code: string }> {
  const [balance, nonce, code] = await Promise.all([
    web3.eth.getBalance(address),
    web3.eth.getTransactionCount(address),
    web3.eth.getCode(address),
  ]);

  return {
    balance: balance.toString(),
    transactionCount: Number(nonce),
    code: code as string,
  };
}

export async function getAddressTransactions(address: string, limit: number = 20): Promise<TransactionInfo[]> {
  const latest = await getLatestBlockNumber();
  const transactions: TransactionInfo[] = [];
  const startBlock = Math.max(0, latest - 1000);

  for (let i = latest; i >= startBlock && transactions.length < limit; i--) {
    const block = await web3.eth.getBlock(i);
    if (!block) continue;

    const txHashes = block.transactions as string[];
    for (const txHash of txHashes) {
      const tx = await getTransactionByHash(txHash);
      if (tx && (tx.from.toLowerCase() === address.toLowerCase() || (tx.to && tx.to.toLowerCase() === address.toLowerCase()))) {
        transactions.push(tx);
        if (transactions.length >= limit) break;
      }
    }
  }

  return transactions;
}

export async function getERC20Balance(address: string, tokenAddress: string): Promise<{ balance: string; symbol: string; name: string; decimals: number }> {
  try {
    const contract = new web3.eth.Contract(
      [
        { name: 'balanceOf', type: 'function', inputs: [{ name: '_owner', type: 'address' }], outputs: [{ name: 'balance', type: 'uint256' }] },
        { name: 'symbol', type: 'function', inputs: [], outputs: [{ name: '', type: 'string' }] },
        { name: 'name', type: 'function', inputs: [], outputs: [{ name: '', type: 'string' }] },
        { name: 'decimals', type: 'function', inputs: [], outputs: [{ name: '', type: 'uint8' }] },
      ] as any,
      tokenAddress,
    );

    const [balance, symbol, name, decimals] = await Promise.all([
      contract.methods.balanceOf(address).call(),
      contract.methods.symbol().call(),
      contract.methods.name().call(),
      contract.methods.decimals().call(),
    ]);

    return {
      balance: (balance as bigint).toString(),
      symbol: symbol as string,
      name: name as string,
      decimals: Number(decimals),
    };
  } catch (error) {
    return { balance: '0', symbol: '', name: '', decimals: 18 };
  }
}
