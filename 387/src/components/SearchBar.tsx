import { useState, useMemo } from 'react';
import { Search, AlertCircle, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/utils/api';

const ETH_ADDRESS_REGEX = /^0x[a-fA-F0-9]{40}$/;
const TX_HASH_REGEX = /^0x[a-fA-F0-9]{64}$/;
const BLOCK_NUMBER_REGEX = /^\d+$/;

function validateInput(input: string): {
  type: 'address' | 'tx' | 'block' | 'unknown';
  valid: boolean;
  message: string;
} {
  const trimmed = input.trim();
  
  if (!trimmed) {
    return { type: 'unknown', valid: false, message: '' };
  }
  
  if (BLOCK_NUMBER_REGEX.test(trimmed)) {
    const num = BigInt(trimmed);
    if (num >= 0n && num < 100000000n) {
      return { type: 'block', valid: true, message: '✓ 有效的区块号' };
    }
    return { type: 'block', valid: false, message: '⚠ 区块号超出合理范围' };
  }
  
  if (TX_HASH_REGEX.test(trimmed)) {
    return { type: 'tx', valid: true, message: '✓ 有效的交易哈希格式' };
  }
  
  if (ETH_ADDRESS_REGEX.test(trimmed)) {
    return { type: 'address', valid: true, message: '✓ 有效的以太坊地址格式' };
  }
  
  if (trimmed.startsWith('0x')) {
    if (trimmed.length < 42) {
      return { type: 'unknown', valid: false, message: '✗ 地址或哈希长度不足' };
    }
    if (trimmed.length > 66) {
      return { type: 'unknown', valid: false, message: '✗ 地址或哈希长度过长' };
    }
    return { type: 'unknown', valid: false, message: '✗ 无效的十六进制格式' };
  }
  
  if (/[a-fA-FxX]/.test(trimmed)) {
    return { type: 'unknown', valid: false, message: '✗ 请输入完整的 0x 开头地址或哈希' };
  }
  
  return { type: 'unknown', valid: false, message: '✗ 请输入区块号、交易哈希或地址' };
}

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const navigate = useNavigate();

  const validation = useMemo(() => validateInput(query), [query]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isSearching || !validation.valid) return;

    setIsSearching(true);
    try {
      const result = await api.search(query.trim());
      if (result.type === 'block') {
        navigate(`/block/${result.result.number}`);
      } else if (result.type === 'transaction') {
        navigate(`/tx/${result.result.hash}`);
      } else if (result.type === 'address') {
        navigate(`/address/${result.result.address}`);
      }
    } catch {
      alert('未找到匹配的结果，请检查输入是否正确');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <form onSubmit={handleSearch} className="relative w-full max-w-2xl">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setShowHint(true)}
          onBlur={() => setTimeout(() => setShowHint(false), 200)}
          placeholder="搜索区块号 / 交易哈希 / 地址"
          className={`w-full bg-slate-800/50 border rounded-xl pl-12 pr-32 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 transition-all ${
            !query.trim()
              ? 'border-slate-700 focus:border-cyan-500/50 focus:ring-cyan-500/20'
              : validation.valid
              ? 'border-emerald-500/50 focus:border-emerald-500 focus:ring-emerald-500/20'
              : 'border-amber-500/50 focus:border-amber-500 focus:ring-amber-500/20'
          }`}
        />
        {query.trim() && (
          <div className="absolute right-20 top-1/2 -translate-y-1/2">
            {validation.valid ? (
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-amber-400" />
            )}
          </div>
        )}
        <button
          type="submit"
          disabled={isSearching || !validation.valid}
          className="absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg text-sm font-medium hover:bg-cyan-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSearching ? '搜索中...' : '搜索'}
        </button>
      </div>
      
      {showHint && (
        <div className="absolute top-full left-0 right-0 mt-2 p-3 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
          {query.trim() ? (
            <div className={`text-xs flex items-center gap-2 ${
              validation.valid ? 'text-emerald-400' : 'text-amber-400'
            }`}>
              {validation.valid ? (
                <CheckCircle className="w-3 h-3" />
              ) : (
                <AlertCircle className="w-3 h-3" />
              )}
              {validation.message}
            </div>
          ) : (
            <div className="text-xs text-slate-500 space-y-1">
              <p>• 区块号: 纯数字 (如 12345678)</p>
              <p>• 交易哈希: 0x 开头 66 字符</p>
              <p>• 地址: 0x 开头 42 字符</p>
            </div>
          )}
        </div>
      )}
    </form>
  );
}
