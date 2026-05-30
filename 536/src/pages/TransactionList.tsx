import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, ChevronLeft, ChevronRight, Eye, Palette, Tag } from 'lucide-react';
import { api } from '@/api';
import { statusColor, modeColor, formatTime, formatDuration } from '@/utils/format';
import type { GlobalTransaction, TransactionMode, TransactionStatus, PageResponse } from '@/types';

const MODES: TransactionMode[] = ['TCC', 'SAGA', 'AT', 'XA'];
const STATUSES: TransactionStatus[] = ['BEGIN', 'COMMITTING', 'COMMITTED', 'ROLLBACKING', 'ROLLEDBACK', 'TIMEOUT', 'FAILED'];
const TRAFFIC_COLORS = ['RED', 'BLUE', 'GREEN', 'YELLOW', 'PURPLE', 'ORANGE', 'GRAY'];

const colorMap: Record<string, string> = {
  RED: 'bg-red-500/20 text-red-400 border-red-500/50',
  BLUE: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
  GREEN: 'bg-green-500/20 text-green-400 border-green-500/50',
  YELLOW: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
  PURPLE: 'bg-purple-500/20 text-purple-400 border-purple-500/50',
  ORANGE: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  GRAY: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
};

export default function TransactionList() {
  const navigate = useNavigate();
  const [data, setData] = useState<PageResponse<GlobalTransaction> | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [mode, setMode] = useState<TransactionMode | ''>('');
  const [status, setStatus] = useState<TransactionStatus | ''>('');
  const [appId, setAppId] = useState('');
  const [trafficColor, setTrafficColor] = useState('');
  const [businessType, setBusinessType] = useState('');
  const [availableBusinessTypes, setAvailableBusinessTypes] = useState<string[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.transactions.search({
        mode: mode || undefined,
        status: status || undefined,
        applicationId: appId || undefined,
        trafficColor: trafficColor || undefined,
        businessType: businessType || undefined,
        page,
        size: 15,
      });
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [mode, status, appId, trafficColor, businessType, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    api.transactions.getBusinessTypes().then(setAvailableBusinessTypes).catch(() => {});
  }, []);

  const totalPages = data?.totalPages || 1;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-sans font-bold text-monitor-text">事务列表</h2>
          <p className="text-monitor-text-muted text-sm mt-1 font-sans">浏览和筛选分布式事务记录</p>
        </div>
        <span className="text-monitor-text-muted text-xs font-mono">
          共 {data?.totalElements || 0} 条记录
        </span>
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl p-5 mb-6">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-monitor-text-muted" />
            <span className="text-monitor-text-muted text-xs font-sans">筛选</span>
          </div>

          <select
            value={mode}
            onChange={(e) => { setMode(e.target.value as TransactionMode | ''); setPage(0); }}
            className="bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text focus:outline-none focus:border-monitor-accent"
          >
            <option value="">全部模式</option>
            {MODES.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value as TransactionStatus | ''); setPage(0); }}
            className="bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text focus:outline-none focus:border-monitor-accent"
          >
            <option value="">全部状态</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <div className="flex items-center gap-2">
            <Palette className="w-4 h-4 text-monitor-text-muted" />
            <select
              value={trafficColor}
              onChange={(e) => { setTrafficColor(e.target.value); setPage(0); }}
              className="bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text focus:outline-none focus:border-monitor-accent"
            >
              <option value="">全部流量</option>
              {TRAFFIC_COLORS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-monitor-text-muted" />
            <select
              value={businessType}
              onChange={(e) => { setBusinessType(e.target.value); setPage(0); }}
              className="bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text focus:outline-none focus:border-monitor-accent"
            >
              <option value="">全部业务</option>
              {availableBusinessTypes.map((bt) => (
                <option key={bt} value={bt}>{bt}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 relative">
            <Search className="w-4 h-4 text-monitor-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="输入 Application ID 搜索..."
              value={appId}
              onChange={(e) => { setAppId(e.target.value); setPage(0); }}
              className="w-full bg-monitor-surface border border-monitor-border rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
            />
          </div>
        </div>
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-monitor-border">
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">XID</th>
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">模式</th>
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">状态</th>
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">流量</th>
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">业务</th>
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">应用</th>
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">开始时间</th>
              <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">持续时间</th>
              <th className="text-right px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-monitor-border/50">
                  {Array.from({ length: 9 }).map((_, j) => (
                    <td key={j} className="px-5 py-4">
                      <div className="h-4 bg-monitor-hover rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data?.content?.length ? (
              data.content.map((tx) => (
                <tr
                  key={tx.xid}
                  className="border-b border-monitor-border/50 hover:bg-monitor-hover/30 transition-colors cursor-pointer"
                  onClick={() => navigate(`/transactions/${encodeURIComponent(tx.xid)}`)}
                >
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs text-monitor-accent">{tx.xid.slice(0, 20)}...</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${modeColor(tx.mode)}`}>
                      {tx.mode}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${statusColor(tx.status)}`}>
                      {tx.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    {tx.trafficColor ? (
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${colorMap[tx.trafficColor] || 'bg-gray-500/20 text-gray-400'}`}>
                        {tx.trafficColor}
                      </span>
                    ) : (
                      <span className="text-[10px] text-monitor-text-muted font-mono">-</span>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs text-monitor-text-dim">
                      {tx.businessType || '-'}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs text-monitor-text-dim">{tx.applicationId}</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs text-monitor-text-dim">{formatTime(tx.beginTime)}</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs text-monitor-text-dim">{formatDuration(tx.beginTime, tx.endTime)}</span>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/transactions/${encodeURIComponent(tx.xid)}`); }}
                      className="p-1.5 rounded-lg hover:bg-monitor-accent/10 text-monitor-text-muted hover:text-monitor-accent transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={9} className="px-5 py-12 text-center text-monitor-text-muted text-sm font-sans">
                  暂无事务数据
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-4 border-t border-monitor-border">
            <span className="text-xs font-mono text-monitor-text-muted">
              第 {page + 1} / {totalPages} 页
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg bg-monitor-surface border border-monitor-border text-monitor-text-muted hover:text-monitor-text hover:border-monitor-accent disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg bg-monitor-surface border border-monitor-border text-monitor-text-muted hover:text-monitor-text hover:border-monitor-accent disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
