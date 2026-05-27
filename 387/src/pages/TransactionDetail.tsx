import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRightLeft, Clock, Hash, Coins, AlertCircle } from 'lucide-react';
import { api } from '@/utils/api';
import { formatTimestamp, formatTimeAgo, formatWeiToEth, formatWeiToGwei, formatNumber } from '@/utils/format';

export default function TransactionDetail() {
  const { hash } = useParams<{ hash: string }>();
  const [tx, setTx] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await api.getTransaction(hash!);
        setTx(data);
      } catch (e) {
        console.error('Failed to load transaction:', e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [hash]);

  if (loading) {
    return <div className="text-center text-slate-500 py-20">加载中...</div>;
  }

  if (!tx) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 mb-4">交易未找到</p>
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
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
              <ArrowRightLeft className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">交易详情</h2>
              <p className="text-sm text-slate-500">{formatTimeAgo(tx.timestamp)}</p>
            </div>
          </div>
          <span
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
              tx.status === 1
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-red-500/20 text-red-400'
            }`}
          >
            {tx.status === 1 ? '交易成功' : '交易失败'}
          </span>
        </div>

        <div className="border-t border-slate-700/30 pt-6 space-y-5">
          <InfoItem icon={<Hash className="w-4 h-4" />} label="交易哈希" value={tx.hash} fullWidth />
          <InfoItem icon={<Hash className="w-4 h-4" />} label="区块号" value={
            <Link to={`/block/${tx.blockNumber}`} className="text-cyan-400 hover:text-cyan-300 font-mono">
              #{formatNumber(tx.blockNumber)}
            </Link>
          } />

          <div className="grid grid-cols-2 gap-8 py-4 border-y border-slate-700/30">
            <div className="space-y-2">
              <span className="text-xs text-slate-500">发送方</span>
              <Link
                to={`/address/${tx.from}`}
                className="block p-3 bg-slate-700/30 rounded-lg border border-slate-600/30 hover:border-cyan-500/50 transition-colors"
              >
                <span className="text-sm font-mono text-slate-200">{tx.from}</span>
              </Link>
            </div>
            <div className="space-y-2">
              <span className="text-xs text-slate-500">接收方</span>
              <Link
                to={tx.to ? `/address/${tx.to}` : '#'}
                className="block p-3 bg-slate-700/30 rounded-lg border border-slate-600/30 hover:border-cyan-500/50 transition-colors"
              >
                <span className="text-sm font-mono text-slate-200">
                  {tx.to || '合约创建'}
                </span>
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <InfoItem icon={<Coins className="w-4 h-4" />} label="交易金额" value={formatWeiToEth(tx.value)} highlight />
            <InfoItem icon={<Clock className="w-4 h-4" />} label="时间" value={formatTimestamp(tx.timestamp)} />
            <InfoItem icon={<Coins className="w-4 h-4" />} label="Gas 价格" value={formatWeiToGwei(tx.gasPrice)} />
            <InfoItem icon={<Coins className="w-4 h-4" />} label="Gas 用量" value={formatNumber(tx.gasUsed)} />
            <InfoItem icon={<Coins className="w-4 h-4" />} label="Gas 限制" value={formatNumber(tx.gas)} />
            <InfoItem icon={<Coins className="w-4 h-4" />} label="Nonce" value={formatNumber(tx.nonce)} />
          </div>

          {tx.maxFeePerGas && (
            <div className="grid grid-cols-2 gap-6">
              <InfoItem icon={<Coins className="w-4 h-4" />} label="最大 Gas 费" value={formatWeiToGwei(tx.maxFeePerGas)} />
              <InfoItem icon={<Coins className="w-4 h-4" />} label="优先费" value={formatWeiToGwei(tx.maxPriorityFeePerGas || '0')} />
            </div>
          )}

          {tx.input && tx.input !== '0x' && (
            <div className="space-y-2">
              <span className="text-xs text-slate-500">输入数据</span>
              <div className="p-3 bg-slate-700/30 rounded-lg border border-slate-600/30">
                <code className="text-xs text-slate-400 font-mono break-all">{tx.input}</code>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoItem({ icon, label, value, fullWidth, highlight }: { icon: React.ReactNode; label: string; value: React.ReactNode; fullWidth?: boolean; highlight?: boolean }) {
  return (
    <div className={`flex items-center gap-3 ${fullWidth ? 'col-span-2' : ''}`}>
      <div className="text-slate-500">{icon}</div>
      <div>
        <div className="text-xs text-slate-500">{label}</div>
        <div className={`text-sm font-mono ${highlight ? 'text-amber-400 font-semibold' : 'text-slate-200'}`}>
          {value}
        </div>
      </div>
    </div>
  );
}
