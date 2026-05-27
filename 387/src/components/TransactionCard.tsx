import { Link } from 'react-router-dom';
import { ArrowRightLeft, ExternalLink } from 'lucide-react';
import { formatTimestamp, formatTimeAgo, formatWeiToEth, formatWeiToGwei } from '@/utils/format';

interface TransactionCardProps {
  transaction: {
    hash: string;
    blockNumber: number;
    from: string;
    to: string | null;
    value: string;
    gasPrice: string;
    timestamp: number;
    status: number;
  };
}

export default function TransactionCard({ transaction }: TransactionCardProps) {
  return (
    <Link
      to={`/tx/${transaction.hash}`}
      className="block group p-4 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl hover:border-cyan-500/50 hover:bg-slate-800/50 transition-all duration-300"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
            <ArrowRightLeft className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="text-xs font-mono text-slate-400 truncate max-w-[180px]">
            {transaction.hash.slice(0, 14)}...{transaction.hash.slice(-8)}
          </span>
        </div>
        <span
          className={`px-2 py-0.5 rounded text-xs font-medium ${
            transaction.status === 1
              ? 'bg-emerald-500/20 text-emerald-400'
              : 'bg-red-500/20 text-red-400'
          }`}
        >
          {transaction.status === 1 ? '成功' : '失败'}
        </span>
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-400 mb-3">
        <span className="truncate max-w-[120px] font-mono">{transaction.from.slice(0, 8)}...{transaction.from.slice(-6)}</span>
        <ExternalLink className="w-3 h-3 text-slate-500" />
        <span className="truncate max-w-[120px] font-mono">
          {transaction.to ? `${transaction.to.slice(0, 8)}...${transaction.to.slice(-6)}` : '合约创建'}
        </span>
      </div>
      <div className="flex items-center justify-between pt-2 border-t border-slate-700/30">
        <span className="text-sm font-medium text-amber-400 font-mono">
          {formatWeiToEth(transaction.value)}
        </span>
        <div className="text-right">
          <div className="text-xs text-slate-500">{formatTimeAgo(transaction.timestamp)}</div>
          <div className="text-xs text-cyan-400 font-mono">{formatWeiToGwei(transaction.gasPrice)}</div>
        </div>
      </div>
    </Link>
  );
}
