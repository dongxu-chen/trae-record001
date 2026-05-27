import { useEffect, useState } from 'react';
import { RefreshCw, Boxes, ArrowRightLeft, Flame } from 'lucide-react';
import SearchBar from '@/components/SearchBar';
import BlockCard from '@/components/BlockCard';
import TransactionCard from '@/components/TransactionCard';
import GasChart from '@/components/GasChart';
import { api } from '@/utils/api';
import { formatWeiToGwei } from '@/utils/format';

export default function Home() {
  const [blocks, setBlocks] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [gasData, setGasData] = useState<any[]>([]);
  const [latestGas, setLatestGas] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [blocksRes, txRes, gasHistoryRes, latestGasRes] = await Promise.all([
        api.getLatestBlocks(10),
        api.getLatestTransactions(10),
        api.getGasHistory(7),
        api.getLatestGas(),
      ]);
      setBlocks(blocksRes);
      setTransactions(txRes);
      setGasData(gasHistoryRes);
      setLatestGas(latestGasRes);
    } catch (e) {
      console.error('Failed to load data:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(), 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2">以太坊区块链浏览器</h2>
        <p className="text-slate-400">实时查询链上数据 · 区块 · 交易 · 地址 · 智能合约</p>
      </div>

      <div className="flex justify-center mb-8">
        <SearchBar />
      </div>

      {latestGas && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <Flame className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-slate-500">低 Gas</span>
            </div>
            <div className="text-xl font-bold text-emerald-400 font-mono">{formatWeiToGwei(latestGas.low)}</div>
          </div>
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <Flame className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-slate-500">平均 Gas</span>
            </div>
            <div className="text-xl font-bold text-amber-400 font-mono">{formatWeiToGwei(latestGas.average)}</div>
          </div>
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <Flame className="w-4 h-4 text-red-400" />
              <span className="text-xs text-slate-500">高 Gas</span>
            </div>
            <div className="text-xl font-bold text-red-400 font-mono">{formatWeiToGwei(latestGas.high)}</div>
          </div>
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <Flame className="w-4 h-4 text-purple-400" />
              <span className="text-xs text-slate-500">Base Fee</span>
            </div>
            <div className="text-xl font-bold text-purple-400 font-mono">{formatWeiToGwei(latestGas.baseFee)}</div>
          </div>
        </div>
      )}

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl mb-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Flame className="w-5 h-5 text-cyan-400" />
            Gas 费趋势 (近7天)
          </h3>
          <button
            onClick={() => loadData(true)}
            className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
        {gasData.length > 0 ? (
          <GasChart data={gasData} />
        ) : (
          <div className="h-[300px] flex items-center justify-center text-slate-500">加载中...</div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Boxes className="w-5 h-5 text-cyan-400" />
              最新区块
            </h3>
            <button
              onClick={() => loadData(true)}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
            {loading ? (
              <div className="text-center text-slate-500 py-8">加载中...</div>
            ) : (
              blocks.map((block) => <BlockCard key={block.number} block={block} />)
            )}
          </div>
        </div>

        <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <ArrowRightLeft className="w-5 h-5 text-emerald-400" />
              最新交易
            </h3>
            <button
              onClick={() => loadData(true)}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
            {loading ? (
              <div className="text-center text-slate-500 py-8">加载中...</div>
            ) : (
              transactions.map((tx) => <TransactionCard key={tx.hash} transaction={tx} />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
