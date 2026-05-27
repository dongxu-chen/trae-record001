import { useEffect, useState } from 'react';
import { Flame, RefreshCw } from 'lucide-react';
import GasChart from '@/components/GasChart';
import { api } from '@/utils/api';
import { formatWeiToGwei } from '@/utils/format';

export default function GasTrend() {
  const [gasData, setGasData] = useState<any[]>([]);
  const [latestGas, setLatestGas] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [history, latest] = await Promise.all([
        api.getGasHistory(days),
        api.getLatestGas(),
      ]);
      setGasData(history);
      setLatestGas(latest);
    } catch (e) {
      console.error('Failed to load gas data:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [days]);

  const timeRanges = [
    { label: '1 天', value: 1 },
    { label: '7 天', value: 7 },
    { label: '14 天', value: 14 },
    { label: '30 天', value: 30 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Flame className="w-6 h-6 text-cyan-400" />
          Gas 费趋势
        </h2>
        <button
          onClick={() => loadData(true)}
          className="flex items-center gap-1 px-4 py-2 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      {latestGas && (
        <div className="grid grid-cols-4 gap-4">
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="text-xs text-slate-500 mb-2">低 Gas</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">{formatWeiToGwei(latestGas.low)}</div>
          </div>
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="text-xs text-slate-500 mb-2">平均 Gas</div>
            <div className="text-2xl font-bold text-amber-400 font-mono">{formatWeiToGwei(latestGas.average)}</div>
          </div>
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="text-xs text-slate-500 mb-2">高 Gas</div>
            <div className="text-2xl font-bold text-red-400 font-mono">{formatWeiToGwei(latestGas.high)}</div>
          </div>
          <div className="p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
            <div className="text-xs text-slate-500 mb-2">Base Fee</div>
            <div className="text-2xl font-bold text-purple-400 font-mono">{formatWeiToGwei(latestGas.baseFee)}</div>
          </div>
        </div>
      )}

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Gas 费历史趋势</h3>
          <div className="flex items-center gap-1">
            {timeRanges.map((range) => (
              <button
                key={range.value}
                onClick={() => setDays(range.value)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  days === range.value
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                }`}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>
        {loading ? (
          <div className="h-[400px] flex items-center justify-center text-slate-500">加载中...</div>
        ) : gasData.length > 0 ? (
          <GasChart data={gasData} height={400} />
        ) : (
          <div className="h-[400px] flex items-center justify-center text-slate-500">暂无数据</div>
        )}
      </div>

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <h3 className="text-lg font-semibold text-white mb-4">Gas 费说明</h3>
        <div className="space-y-4 text-sm text-slate-400">
          <div>
            <span className="text-emerald-400 font-medium">低 Gas：</span>
            适合不紧急的交易，可能需要较长时间确认
          </div>
          <div>
            <span className="text-amber-400 font-medium">平均 Gas：</span>
            适合普通交易，通常在几个区块内确认
          </div>
          <div>
            <span className="text-red-400 font-medium">高 Gas：</span>
            适合紧急交易，确认速度最快
          </div>
          <div>
            <span className="text-purple-400 font-medium">Base Fee：</span>
            网络基础费用，由网络自动调整，所有交易都需要支付
          </div>
        </div>
      </div>
    </div>
  );
}
