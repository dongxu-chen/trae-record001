import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Network,
  Stethoscope,
  Clock,
  Hash,
  Server,
  Layers,
  GitBranch,
  AlertCircle,
  Palette,
  Tag,
  Edit2,
  Check,
  X,
} from 'lucide-react';
import { api } from '@/api';
import { statusColor, modeColor, alertLevelColor, formatTime, formatDuration } from '@/utils/format';
import type { GlobalTransaction, BranchTransaction, TransactionEvent } from '@/types';

function InfoRow({ icon: Icon, label, value, mono = false }: { icon: React.ElementType; label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <Icon className="w-4 h-4 text-monitor-text-muted flex-shrink-0" />
      <span className="text-monitor-text-muted text-xs font-sans w-28 flex-shrink-0">{label}</span>
      <span className={`text-sm ${mono ? 'font-mono' : 'font-sans'} text-monitor-text`}>{value}</span>
    </div>
  );
}

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

export default function TransactionDetail() {
  const { xid } = useParams<{ xid: string }>();
  const navigate = useNavigate();
  const [tx, setTx] = useState<GlobalTransaction | null>(null);
  const [branches, setBranches] = useState<BranchTransaction[]>([]);
  const [events, setEvents] = useState<TransactionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'branches' | 'events'>('branches');
  const [editingTraffic, setEditingTraffic] = useState(false);
  const [editColor, setEditColor] = useState('');
  const [editBusinessType, setEditBusinessType] = useState('');
  const [editTags, setEditTags] = useState<{ key: string; value: string }[]>([]);
  const [savingTraffic, setSavingTraffic] = useState(false);

  useEffect(() => {
    if (!xid) return;
    setLoading(true);
    Promise.all([
      api.transactions.getById(xid),
      api.transactions.getBranches(xid),
      api.transactions.getEvents(xid),
    ])
      .then(([txData, branchData, eventData]) => {
        setTx(txData);
        setBranches(branchData);
        setEvents(eventData);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [xid]);

  const startEditTraffic = () => {
    if (!tx) return;
    setEditColor(tx.trafficColor || '');
    setEditBusinessType(tx.businessType || '');
    setEditTags(Object.entries(tx.tags || {}).map(([key, value]) => ({ key, value })));
    setEditingTraffic(true);
  };

  const cancelEditTraffic = () => {
    setEditingTraffic(false);
  };

  const saveTrafficInfo = async () => {
    if (!tx || !xid) return;
    setSavingTraffic(true);
    try {
      const tags: Record<string, string> = {};
      editTags.forEach((t) => {
        if (t.key.trim()) tags[t.key.trim()] = t.value;
      });
      const updated = await api.transactions.updateTrafficInfo(xid, {
        trafficColor: editColor || undefined,
        businessType: editBusinessType || undefined,
        tags,
      });
      setTx(updated);
      setEditingTraffic(false);
    } catch {
    } finally {
      setSavingTraffic(false);
    }
  };

  const addTag = () => {
    setEditTags([...editTags, { key: '', value: '' }]);
  };

  const removeTag = (index: number) => {
    setEditTags(editTags.filter((_, i) => i !== index));
  };

  const updateTag = (index: number, field: 'key' | 'value', value: string) => {
    const newTags = [...editTags];
    newTags[index][field] = value;
    setEditTags(newTags);
  };

  if (loading) {
    return (
      <div className="p-8 animate-pulse space-y-6">
        <div className="h-8 bg-monitor-card rounded w-64" />
        <div className="h-48 bg-monitor-card rounded-xl" />
      </div>
    );
  }

  if (!tx) {
    return (
      <div className="p-8 text-center">
        <p className="text-monitor-text-muted font-sans">事务未找到</p>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate('/transactions')}
          className="p-2 rounded-lg bg-monitor-card border border-monitor-border text-monitor-text-muted hover:text-monitor-text hover:border-monitor-accent transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h2 className="text-2xl font-sans font-bold text-monitor-text">事务详情</h2>
          <p className="text-monitor-text-muted text-xs font-mono mt-1">{tx.xid}</p>
        </div>
        {tx.traceId && (
          <button
            onClick={() => navigate(`/trace/${encodeURIComponent(tx.traceId)}`)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-monitor-info/10 text-monitor-info border border-monitor-info/30 text-xs font-sans font-medium hover:bg-monitor-info/20 transition-colors"
          >
            <Network className="w-4 h-4" />
            查看链路
          </button>
        )}
        <button
          onClick={() => navigate(`/diagnosis/${encodeURIComponent(tx.xid)}`)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-monitor-accent/10 text-monitor-accent border border-monitor-accent/30 text-xs font-sans font-medium hover:bg-monitor-accent/20 transition-colors"
        >
          <Stethoscope className="w-4 h-4" />
          异常诊断
        </button>
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl p-6 mb-6">
        <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4">基本信息</h3>
        <div className="grid grid-cols-2 gap-x-8">
          <InfoRow icon={Hash} label="XID" value={<span className="font-mono text-monitor-accent text-xs break-all">{tx.xid}</span>} />
          <InfoRow icon={Layers} label="模式" value={<span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${modeColor(tx.mode)}`}>{tx.mode}</span>} />
          <InfoRow
            icon={AlertCircle}
            label="状态"
            value={<span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${statusColor(tx.status)}`}>{tx.status}</span>}
          />
          <InfoRow icon={Server} label="应用" value={<span className="font-mono text-xs">{tx.applicationId}</span>} />
          <InfoRow icon={Clock} label="开始时间" value={formatTime(tx.beginTime)} />
          <InfoRow icon={Clock} label="结束时间" value={formatTime(tx.endTime)} />
          <InfoRow icon={Clock} label="持续时间" value={formatDuration(tx.beginTime, tx.endTime)} />
          <InfoRow icon={Clock} label="超时阈值" value={tx.timeoutMs ? `${tx.timeoutMs}ms` : '-'} />
          <InfoRow icon={GitBranch} label="服务组" value={<span className="font-mono text-xs">{tx.transactionServiceGroup}</span>} />
          {tx.traceId && <InfoRow icon={Network} label="Trace ID" value={<span className="font-mono text-xs text-monitor-info">{tx.traceId}</span>} />}
        </div>
        {tx.rollbackReason && (
          <div className="mt-4 p-3 bg-monitor-danger/5 border border-monitor-danger/20 rounded-lg">
            <p className="text-xs font-sans text-monitor-danger font-medium mb-1">回滚原因</p>
            <p className="text-xs font-mono text-monitor-text-dim">{tx.rollbackReason}</p>
          </div>
        )}
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-sans font-semibold text-monitor-text">流量染色</h3>
          {!editingTraffic && (
            <button
              onClick={startEditTraffic}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-monitor-surface border border-monitor-border text-xs font-sans text-monitor-text-muted hover:text-monitor-accent hover:border-monitor-accent transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
              编辑
            </button>
          )}
        </div>

        {editingTraffic ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">流量颜色</label>
                <select
                  value={editColor}
                  onChange={(e) => setEditColor(e.target.value)}
                  className="w-full bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text focus:outline-none focus:border-monitor-accent"
                >
                  <option value="">未设置</option>
                  {TRAFFIC_COLORS.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">业务类型</label>
                <input
                  type="text"
                  value={editBusinessType}
                  onChange={(e) => setEditBusinessType(e.target.value)}
                  placeholder="如：订单支付、库存扣减"
                  className="w-full bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-sans text-monitor-text-muted">标签</label>
                <button
                  onClick={addTag}
                  className="text-xs font-sans text-monitor-accent hover:underline"
                >
                  + 添加标签
                </button>
              </div>
              <div className="space-y-2">
                {editTags.map((tag, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={tag.key}
                      onChange={(e) => updateTag(idx, 'key', e.target.value)}
                      placeholder="Key"
                      className="flex-1 bg-monitor-surface border border-monitor-border rounded-lg px-3 py-1.5 text-xs font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
                    />
                    <input
                      type="text"
                      value={tag.value}
                      onChange={(e) => updateTag(idx, 'value', e.target.value)}
                      placeholder="Value"
                      className="flex-1 bg-monitor-surface border border-monitor-border rounded-lg px-3 py-1.5 text-xs font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
                    />
                    <button
                      onClick={() => removeTag(idx)}
                      className="p-1.5 rounded text-monitor-text-muted hover:text-monitor-danger transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {editTags.length === 0 && (
                  <p className="text-xs text-monitor-text-muted font-sans py-2">暂无标签</p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={saveTrafficInfo}
                disabled={savingTraffic}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-monitor-accent text-white text-xs font-sans font-medium hover:bg-monitor-accent/90 disabled:opacity-50 transition-colors"
              >
                <Check className="w-4 h-4" />
                {savingTraffic ? '保存中...' : '保存'}
              </button>
              <button
                onClick={cancelEditTraffic}
                disabled={savingTraffic}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-monitor-surface border border-monitor-border text-monitor-text-muted text-xs font-sans hover:text-monitor-text hover:border-monitor-accent disabled:opacity-50 transition-colors"
              >
                <X className="w-4 h-4" />
                取消
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-x-8">
            <InfoRow
              icon={Palette}
              label="流量颜色"
              value={tx.trafficColor ? (
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${colorMap[tx.trafficColor] || 'bg-gray-500/20 text-gray-400'}`}>
                  {tx.trafficColor}
                </span>
              ) : (
                <span className="text-xs text-monitor-text-muted font-sans">未设置</span>
              )}
            />
            <InfoRow
              icon={Tag}
              label="业务类型"
              value={<span className="font-mono text-xs">{tx.businessType || '-'}</span>}
            />
          </div>
        )}

        {!editingTraffic && tx.tags && Object.keys(tx.tags).length > 0 && (
          <div className="mt-4 pt-4 border-t border-monitor-border/50">
            <p className="text-xs font-sans text-monitor-text-muted mb-2">自定义标签</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(tx.tags).map(([key, value]) => (
                <span
                  key={key}
                  className="px-2 py-1 rounded bg-monitor-surface border border-monitor-border text-[10px] font-mono"
                >
                  <span className="text-monitor-accent">{key}</span>
                  <span className="text-monitor-text-muted mx-1">=</span>
                  <span className="text-monitor-text">{value}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl overflow-hidden">
        <div className="flex border-b border-monitor-border">
          <button
            onClick={() => setActiveTab('branches')}
            className={`px-6 py-3.5 text-xs font-sans font-medium transition-colors ${
              activeTab === 'branches'
                ? 'text-monitor-accent border-b-2 border-monitor-accent bg-monitor-accent/5'
                : 'text-monitor-text-muted hover:text-monitor-text'
            }`}
          >
            分支事务 ({branches.length})
          </button>
          <button
            onClick={() => setActiveTab('events')}
            className={`px-6 py-3.5 text-xs font-sans font-medium transition-colors ${
              activeTab === 'events'
                ? 'text-monitor-accent border-b-2 border-monitor-accent bg-monitor-accent/5'
                : 'text-monitor-text-muted hover:text-monitor-text'
            }`}
          >
            事件记录 ({events.length})
          </button>
        </div>

        {activeTab === 'branches' ? (
          branches.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="border-b border-monitor-border">
                  <th className="text-left px-5 py-3 text-xs font-sans font-semibold text-monitor-text-muted">Branch ID</th>
                  <th className="text-left px-5 py-3 text-xs font-sans font-semibold text-monitor-text-muted">资源</th>
                  <th className="text-left px-5 py-3 text-xs font-sans font-semibold text-monitor-text-muted">状态</th>
                  <th className="text-left px-5 py-3 text-xs font-sans font-semibold text-monitor-text-muted">模式</th>
                  <th className="text-left px-5 py-3 text-xs font-sans font-semibold text-monitor-text-muted">开始时间</th>
                  <th className="text-left px-5 py-3 text-xs font-sans font-semibold text-monitor-text-muted">错误</th>
                </tr>
              </thead>
              <tbody>
                {branches.map((b) => (
                  <tr key={b.id} className="border-b border-monitor-border/50 hover:bg-monitor-hover/30 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-monitor-accent">{b.branchId}</td>
                    <td className="px-5 py-3 font-mono text-xs text-monitor-text-dim max-w-[200px] truncate">{b.resourceId}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${statusColor(b.status)}`}>{b.status}</span>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${modeColor(b.mode)}`}>{b.mode}</span>
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-monitor-text-dim">{formatTime(b.beginTime)}</td>
                    <td className="px-5 py-3 font-mono text-[10px] text-monitor-danger max-w-[200px] truncate">{b.errorMessage || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-12 text-center text-monitor-text-muted text-sm font-sans">暂无分支事务</div>
          )
        ) : events.length > 0 ? (
          <div className="p-5">
            <div className="relative">
              <div className="absolute left-4 top-0 bottom-0 w-px bg-monitor-border" />
              {events.map((event, idx) => (
                <div key={event.id} className="relative pl-10 pb-6 last:pb-0">
                  <div className="absolute left-3 top-1 w-3 h-3 rounded-full border-2 border-monitor-accent bg-monitor-bg" />
                  <div className="bg-monitor-surface border border-monitor-border rounded-lg p-4">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-monitor-accent/10 text-monitor-accent border border-monitor-accent/30">
                        {event.phase}
                      </span>
                      <span className="text-[10px] font-mono text-monitor-text-muted">{event.eventType}</span>
                      <span className="text-[10px] font-mono text-monitor-text-muted ml-auto">{formatTime(event.eventTime)}</span>
                    </div>
                    {event.branchId && (
                      <p className="text-xs font-mono text-monitor-text-dim mb-1">Branch: {event.branchId}</p>
                    )}
                    {event.errorMessage && (
                      <p className="text-xs font-mono text-monitor-danger bg-monitor-danger/5 rounded p-2">{event.errorMessage}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="py-12 text-center text-monitor-text-muted text-sm font-sans">暂无事件记录</div>
        )}
      </div>
    </div>
  );
}
