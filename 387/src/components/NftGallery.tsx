import { useState } from 'react';
import { Gem, ExternalLink, Eye, Grid3X3 } from 'lucide-react';

interface NftAsset {
  contractAddress: string;
  tokenId: string;
  tokenType: 'ERC721' | 'ERC1155';
  name: string;
  symbol: string;
  tokenURI?: string;
  balance?: string;
}

interface NftGalleryProps {
  nfts: NftAsset[];
  loading?: boolean;
}

export default function NftGallery({ nfts, loading }: NftGalleryProps) {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  if (loading) {
    return (
      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-center gap-2 mb-4">
          <Gem className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">NFT 资产</h3>
          <span className="text-sm text-slate-500">加载中...</span>
        </div>
        <div className="grid grid-cols-4 gap-4">
          {Array(8).fill(0).map((_, i) => (
            <div key={i} className="aspect-square bg-slate-700/30 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (nfts.length === 0) {
    return (
      <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
        <div className="flex items-center gap-2 mb-4">
          <Gem className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">NFT 资产</h3>
        </div>
        <p className="text-center text-slate-500 py-12">该地址暂无 NFT 资产</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Gem className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">NFT 资产</h3>
          <span className="text-sm text-slate-500">{nfts.length} 个</span>
        </div>
        <div className="flex items-center gap-1 bg-slate-700/30 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-slate-600 text-cyan-400' : 'text-slate-400'}`}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-slate-600 text-cyan-400' : 'text-slate-400'}`}
          >
            <Eye className="w-4 h-4" />
          </button>
        </div>
      </div>

      {viewMode === 'grid' ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {nfts.map((nft, idx) => (
            <div
              key={`${nft.contractAddress}-${nft.tokenId}-${idx}`}
              className="group bg-slate-700/20 border border-slate-600/30 rounded-xl overflow-hidden hover:border-purple-500/50 transition-all"
            >
              <div className="aspect-square bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent" />
                <Gem className="w-12 h-12 text-purple-400/50" />
                <div className="absolute top-2 right-2 px-2 py-0.5 bg-slate-900/80 rounded text-xs text-purple-400 font-mono">
                  #{nft.tokenId}
                </div>
              </div>
              <div className="p-3">
                <div className="text-sm font-medium text-slate-200 truncate">{nft.name}</div>
                <div className="text-xs text-slate-500 truncate">{nft.symbol}</div>
                <a
                  href={`https://etherscan.io/token/${nft.contractAddress}?a=${nft.tokenId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 mt-2"
                >
                  查看详情 <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {nfts.map((nft, idx) => (
            <div
              key={`${nft.contractAddress}-${nft.tokenId}-${idx}`}
              className="flex items-center gap-4 p-3 bg-slate-700/20 border border-slate-600/30 rounded-lg hover:border-purple-500/30 transition-all"
            >
              <div className="w-12 h-12 bg-gradient-to-br from-slate-700 to-slate-800 rounded-lg flex items-center justify-center">
                <Gem className="w-6 h-6 text-purple-400/50" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-200 truncate">{nft.name}</div>
                <div className="text-xs text-slate-500 font-mono truncate">
                  {nft.symbol} #{nft.tokenId}
                </div>
              </div>
              <div className="text-xs text-slate-500 font-mono">
                {nft.tokenType}
              </div>
              <a
                href={`https://etherscan.io/token/${nft.contractAddress}?a=${nft.tokenId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-slate-400 hover:text-cyan-400"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
