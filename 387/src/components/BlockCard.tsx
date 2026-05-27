import { Link } from 'react-router-dom';
import { Boxes, Clock, Layers } from 'lucide-react';
import { formatTimestamp, formatTimeAgo, formatNumber, formatWeiToGwei } from '@/utils/format';

interface BlockCardProps {
  block: {
    number: number;
    hash: string;
    timestamp: number;
    miner: string;
    gasUsed: string;
    gasLimit: string;
    transactionCount: number;
    baseFeePerGas: string;
  };
}

export default function BlockCard({ block }: BlockCardProps) {
  return (
    <Link
      to={`/block/${block.number}`}
      className="block group p-5 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl hover:border-cyan-500/50 hover:bg-slate-800/50 transition-all duration-300"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center group-hover:bg-cyan-500/20 transition-colors">
            <Boxes className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="text-lg font-semibold text-slate-100 font-mono">#{formatNumber(block.number)}</div>
            <div className="text-xs text-slate-500">{formatTimeAgo(block.timestamp)}</div>
          </div>
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-400">
          <Clock className="w-3 h-3" />
          {formatTimestamp(block.timestamp)}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 pt-3 border-t border-slate-700/30">
        <div>
          <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">
            <Layers className="w-3 h-3" /> 交易数
          </div>
          <div className="text-sm font-medium text-slate-200 font-mono">{block.transactionCount}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Gas 用量</div>
          <div className="text-sm font-medium text-slate-200 font-mono">{formatNumber(block.gasUsed)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Base Fee</div>
          <div className="text-sm font-medium text-cyan-400 font-mono">{formatWeiToGwei(block.baseFeePerGas)}</div>
        </div>
      </div>
    </Link>
  );
}
