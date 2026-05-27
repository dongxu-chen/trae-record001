import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, User, Coins, Layers, ArrowRightLeft } from 'lucide-react';
import { api } from '@/utils/api';
import { formatWeiToEth, formatNumber } from '@/utils/format';
import TransactionCard from '@/components/TransactionCard';
import NftGallery from '@/components/NftGallery';
import TransactionFlowChart from '@/components/TransactionFlowChart';
import MultiChainAssets from '@/components/MultiChainAssets';

export default function AddressDetail() {
  const { address } = useParams<{ address: string }>();
  const [info, setInfo] = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [tokens, setTokens] = useState<any[]>([]);
  const [nfts, setNfts] = useState<any[]>([]);
  const [multiChainAssets, setMultiChainAssets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'nft' | 'flow' | 'multichain'>('overview');

  useEffect(() => {
    const loadData = async () => {
      try {
        const [infoRes, txRes, tokensRes, nftsRes, multiChainRes] = await Promise.all([
          api.getAddress(address!),
          api.getAddressTransactions(address!, 20),
          api.getAddressTokens(address!),
          api.getAddressNFTs(address!).catch(() => []),
          api.getMultiChainAddress(address!).catch(() => []),
        ]);
        setInfo(infoRes);
        setTransactions(txRes);
        setTokens(tokensRes);
        setNfts(nftsRes);
        setMultiChainAssets(multiChainRes);
      } catch (e) {
        console.error('Failed to load address:', e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [address]);

  if (loading) {
    return <div className="text-center text-slate-500 py-20">加载中...</div>;
  }

  const isContract = info?.code && info.code !== '0x';

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        返回首页
      </Link>

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${isContract ? 'bg-purple-500/10' : 'bg-blue-500/10'}`}>
              <User className={`w-6 h-6 ${isContract ? 'text-purple-400' : 'text-blue-400'}`} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white font-mono break-all">{address}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${isContract ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'}`}>
                  {isContract ? '合约地址' : '普通地址'}
                </span>
                {isContract && (
                  <Link to={`/contract/${address}`} className="text-xs text-cyan-400 hover:text-cyan-300">
                    查看合约 →
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 bg-slate-700/30 rounded-xl border border-slate-600/30">
            <div className="flex items-center gap-2 mb-2">
              <Coins className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-slate-500">ETH 余额</span>
            </div>
            <div className="text-xl font-bold text-amber-400 font-mono">{formatWeiToEth(info?.balance || '0')}</div>
          </div>
          <div className="p-4 bg-slate-700/30 rounded-xl border border-slate-600/30">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-slate-500">交易数</span>
            </div>
            <div className="text-xl font-bold text-cyan-400 font-mono">{formatNumber(info?.transactionCount || 0)}</div>
          </div>
          <div className="p-4 bg-slate-700/30 rounded-xl border border-slate-600/30">
            <div className="flex items-center gap-2 mb-2">
              <ArrowRightLeft className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-slate-500">ERC20 代币</span>
            </div>
            <div className="text-xl font-bold text-emerald-400 font-mono">{tokens.length}</div>
          </div>
        </div>
      </div>

      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-center gap-1 mb-6 border-b border-slate-700/50">
          {[
            { key: 'overview', label: '概览' },
            { key: 'nft', label: `NFT (${nfts.length})` },
            { key: 'flow', label: '资金流向' },
            { key: 'multichain', label: `跨链 (${multiChainAssets.filter((a: any) => a.transactionCount > 0).length})` },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'overview' && (
          <div className="space-y-6">
            {tokens.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Coins className="w-5 h-5 text-emerald-400" />
                  ERC20 代币余额
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {tokens.map((token, idx) => (
                    <div key={idx} className="p-4 bg-slate-700/30 rounded-xl border border-slate-600/30">
                      <div className="text-sm font-medium text-slate-200">{token.tokenName}</div>
                      <div className="text-xs text-slate-500 mb-2">{token.tokenSymbol}</div>
                      <div className="text-lg font-bold text-cyan-400 font-mono">
                        {(Number(token.balance) / Math.pow(10, token.decimals || 18)).toLocaleString('zh-CN', { maximumFractionDigits: 4 })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <ArrowRightLeft className="w-5 h-5 text-cyan-400" />
                最近交易
              </h3>
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                {transactions.length > 0 ? (
                  transactions.map((tx) => <TransactionCard key={tx.hash} transaction={tx} />)
                ) : (
                  <p className="text-center text-slate-500 py-8">暂无交易记录</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'nft' && (
          <NftGallery nfts={nfts} />
        )}

        {activeTab === 'flow' && (
          <TransactionFlowChart
            transactions={transactions}
            currentAddress={address}
          />
        )}

        {activeTab === 'multichain' && (
          <MultiChainAssets
            address={address!}
            assets={multiChainAssets}
            onRefresh={async () => {
              const res = await api.getMultiChainAddress(address!);
              setMultiChainAssets(res);
            }}
          />
        )}
      </div>
    </div>
  );
}
