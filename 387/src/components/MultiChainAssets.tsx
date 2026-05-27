import { useState } from 'react';
import { Link2, ExternalLink, Coins, Layers, RefreshCw } from 'lucide-react';

interface ChainAsset {
  chainId: string;
  chainName: string;
  chainColor: string;
  currency: { name: string; symbol: string; decimals: number };
  balance: string;
  transactionCount: number;
  isContract: boolean;
  explorer?: string;
  error?: string;
}

interface MultiChainAssetsProps {
  address: string;
  assets: ChainAsset[];
  loading?: boolean;
  onRefresh?: () => void;
}

export default function MultiChainAssets({
  address,
  assets,
  loading,
  onRefresh,
}: MultiChainAssetsProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-center gap-2 mb-4">
          <Link2 className="w-5 h-5 text-cyan-400" />
          <h3 className="text-lg font-semibold text-white">跨链资产</h3>
          <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />
        </div>
        <div className="space-y-3">
          {Array(5).fill(0).map((_, i) => (
            <div key={i} className="h-16 bg-slate-700/30 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const totalValue = assets.reduce((sum, a) => {
    return sum + (Number(a.balance) / 1e18);
  }, 0);

  return (
    <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Link2 className="w-5 h-5 text-cyan-400" />
          <h3 className="text-lg font-semibold text-white">跨链资产</h3>
          <span className="text-sm text-slate-500">{assets.length} 条链</span>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            刷新
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-4 bg-slate-700/30 rounded-xl border border-slate-600/30">
          <div className="flex items-center gap-2 mb-2">
            <Coins className="w-4 h-4 text-amber-400" />
            <span className="text-xs text-slate-500">总资产 (ETH)</span>
          </div>
          <div className="text-xl font-bold text-amber-400 font-mono">
            {totalValue.toFixed(6)}
          </div>
        </div>
        <div className="p-4 bg-slate-700/30 rounded-xl border border-slate-600/30">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span className="text-xs text-slate-500">活跃链数</span>
          </div>
          <div className="text-xl font-bold text-cyan-400 font-mono">
            {assets.filter((a) => a.transactionCount > 0).length}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {assets.map((asset) => (
          <div
            key={asset.chainId}
            className={`bg-slate-700/20 border rounded-lg overflow-hidden transition-all ${
              asset.error ? 'border-red-500/30' : 'border-slate-600/30 hover:border-slate-500/50'
            }`}
          >
            <button
              onClick={() => setExpanded(expanded === asset.chainId ? null : asset.chainId)}
              className="w-full flex items-center justify-between p-4"
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: asset.chainColor }}
                />
                <div className="text-left">
                  <div className="text-sm font-medium text-slate-200">{asset.chainName}</div>
                  <div className="text-xs text-slate-500">Chain ID: {asset.chainId}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-sm font-bold text-slate-200 font-mono">
                    {(Number(asset.balance) / 1e18).toFixed(6)}
                  </div>
                  <div className="text-xs text-slate-500">{asset.currency.symbol}</div>
                </div>
                <div className="text-xs text-slate-500">
                  {asset.transactionCount} tx
                </div>
                {asset.isContract && (
                  <span className="px-2 py-0.5 rounded text-xs bg-purple-500/20 text-purple-400">
                    合约
                  </span>
                )}
                {asset.error && (
                  <span className="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400">
                    错误
                  </span>
                )}
              </div>
            </button>

            {expanded === asset.chainId && (
              <div className="px-4 pb-4 border-t border-slate-600/30 pt-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">代币名称</div>
                    <div className="text-slate-200">{asset.currency.name}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">代币符号</div>
                    <div className="text-slate-200 font-mono">{asset.currency.symbol}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">交易数</div>
                    <div className="text-slate-200 font-mono">{asset.transactionCount}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">地址类型</div>
                    <div className="text-slate-200">
                      {asset.isContract ? '合约地址' : '普通地址'}
                    </div>
                  </div>
                </div>
                {asset.explorer && (
                  <a
                    href={`${asset.explorer}/address/${address}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 mt-3 text-xs text-cyan-400 hover:text-cyan-300"
                  >
                    在 {asset.chainName} 浏览器中查看 <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
