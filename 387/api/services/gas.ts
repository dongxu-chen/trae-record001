import { web3 } from '../config/index.js';
import { getBlockByNumber } from './web3.js';

interface GasHistoryPoint {
  timestamp: number;
  baseFee: string;
  average: string;
  low: string;
  high: string;
  peakBaseFee?: string;
  peakTimestamp?: number;
}

interface HourlyWindow {
  hourStart: number;
  samples: GasHistoryPoint[];
}

const gasHistoryCache: GasHistoryPoint[] = [];
const cacheLimit = 10000;

export async function getCurrentGas(): Promise<{ low: string; average: string; high: string; baseFee: string }> {
  const latestBlock = await web3.eth.getBlock('latest');
  const baseFee = (latestBlock?.baseFeePerGas || 0n).toString();

  const gasPrice = await web3.eth.getGasPrice();
  const avgGas = Number(gasPrice);

  return {
    low: Math.floor(avgGas * 0.8).toString(),
    average: avgGas.toString(),
    high: Math.floor(avgGas * 1.2).toString(),
    baseFee,
  };
}

export async function getGasHistory(hours: number = 168): Promise<GasHistoryPoint[]> {
  const now = Math.floor(Date.now() / 1000);
  const blockInterval = 12;
  const blocksPerHour = Math.floor(3600 / blockInterval);
  const latestBlock = await web3.eth.getBlockNumber();
  const startBlock = Math.max(0, Number(latestBlock) - hours * blocksPerHour);
  
  const hourlyWindows: Map<number, HourlyWindow> = new Map();
  
  for (let blockNum = Number(latestBlock); blockNum >= startBlock; blockNum -= Math.floor(blocksPerHour / 12)) {
    const block = await getBlockByNumber(blockNum);
    if (!block) continue;

    const baseFee = block.baseFeePerGas;
    const avgGas = Math.floor(Number(baseFee) * 1.2);
    const timestamp = Number(block.timestamp);
    
    const hourStart = Math.floor(timestamp / 3600) * 3600;
    
    if (!hourlyWindows.has(hourStart)) {
      hourlyWindows.set(hourStart, {
        hourStart,
        samples: [],
      });
    }
    
    const window = hourlyWindows.get(hourStart)!;
    window.samples.push({
      timestamp,
      baseFee,
      average: avgGas.toString(),
      low: Math.floor(avgGas * 0.85).toString(),
      high: Math.floor(avgGas * 1.3).toString(),
    });
  }
  
  const result: GasHistoryPoint[] = [];
  
  for (const window of hourlyWindows.values()) {
    if (window.samples.length === 0) continue;
    
    window.samples.sort((a, b) => a.timestamp - b.timestamp);
    
    const midSample = window.samples[Math.floor(window.samples.length / 2)];
    const peakSample = window.samples.reduce((peak, sample) => 
      BigInt(sample.baseFee) > BigInt(peak.baseFee) ? sample : peak
    );
    
    result.push({
      ...midSample,
      peakBaseFee: peakSample.baseFee,
      peakTimestamp: peakSample.timestamp,
    });
  }
  
  result.sort((a, b) => a.timestamp - b.timestamp);
  
  return result;
}

export function addGasPoint(point: GasHistoryPoint): void {
  gasHistoryCache.push(point);
  if (gasHistoryCache.length > cacheLimit) {
    gasHistoryCache.shift();
  }
}

export function getCachedGasHistory(): GasHistoryPoint[] {
  return [...gasHistoryCache];
}
