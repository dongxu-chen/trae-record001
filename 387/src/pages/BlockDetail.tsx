import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Boxes, Clock, Layers, Hash, Coins } from 'lucide-react';
import { api } from '@/utils/api';
import { formatTimestamp, formatTimeAgo, formatNumber, formatWeiToGwei, formatWeiToEth } from '@/utils/format';
import TransactionCard from '@/components/TransactionCard';

export default function BlockDetail() {
  const { number } = useParams<{ number: string }>();
  const [block, setBlock] = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [blockRes, txRes] = await Promise.all([
          api.getBlock(Number(number)),
          api.getBlockTransactions(Number(number)),
        ]);
        setBlock(blockRes);
        setTransactions(txRes);
      } catch (e) {
        console.error('Failed to load block:', e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [number]);

  if (loading) {
    return <div className="text-center text-slate-500 py-20">加载中...</div>;
  }

  if (!block) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 mb-4">区块未找到</p>
        <Link to="/" className="text-cyan-400 hover:text-cyan-300">返回首页</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        返回首页
      </Link>

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center">
            <Boxes className="w-6 h-6 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">区块 #{formatNumber(block.number)}</h2>
            <p className="text-sm text-slate-500">{formatTimeAgo(block.timestamp)}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <InfoRow icon={<Hash className="w-4 h-4 text-slate-500" />} label="区块哈希" value={block.hash} isHash />
            <InfoRow icon={<Hash className="w-4 h-4 text-slate-500" />} label="父区块哈希" value={block.parentHash} isHash />
            <InfoRow icon={<Clock className="w-4 h-4 text-slate-500" />} label="时间戳" value={formatTimestamp(block.timestamp)} />
            <InfoRow icon={<Coins className="w-4 h-4 text-slate-500" />} label="矿工" value={block.miner} isAddress />
            <InfoRow icon={<Layers className="w-4 h-4 text-slate-500" />} label="难度" value={formatNumber(block.difficulty)} />
          </div>
          <div className="space-y-4">
            <InfoRow icon={<Layers className="w-4 h-4 text-slate-500" />} label="总难度" value={formatNumber(block.totalDifficulty)} />
            <InfoRow icon={<Layers className="w-4 h-4 text-slate-500" />} label="Gas 用量" value={formatNumber(block.gasUsed)} />
            <InfoRow icon={<Layers className="w-4 h-4 text-slate-500" />} label="Gas 限制" value={formatNumber(block.gasLimit)} />
            <InfoRow icon={<Coins className="w-4 h-4 text-slate-500" />} label="Base Fee" value={formatWeiToGwei(block.baseFeePerGas)} />
            <InfoRow icon={<Layers className="w-4 h-4 text-slate-500" />} label="Nonce" value={block.nonce} />
            <InfoRow icon={<Layers className="w-4 h-4 text-slate-500" />} label="大小" value={`${formatNumber(block.size)} bytes`} />
          </div>
        </div>
      </div>

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyan-400" />
          区块内交易 ({transactions.length} 笔)
        </h3>
        <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
          {transactions.map((tx) => (
            <TransactionCard key={tx.hash} transaction={tx} />
          ))}
        </div>
      </div>
    </div>
  );
}

function InfoRow({ icon, label, value, isHash, isAddress }: { icon: React.ReactNode; label: string; value: string; isHash?: boolean; isAddress?: boolean }) {
  const displayValue = isHash && value.length > 20 ? `${value.slice(0, 14)}...${value.slice(-10)}` : isAddress && value.length > 20 ? `${value.slice(0, 8)}...${value.slice(-6)}` : value;

  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5">{icon}</div>
      <div>
        <div className="text-xs text-slate-500">{label}</div>
        <div className="text-sm text-slate-200 font-mono break-all">{displayValue}</div>
      </div>
    </div>
  );
}
