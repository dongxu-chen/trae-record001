import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  Check,
  ChevronLeft,
  ChevronRight,
  Shield,
  Plus,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { api } from '@/api';
import { alertLevelColor } from '@/utils/format';
import { useMonitorStore } from '@/store';
import type { AlertRecord, AlertRule } from '@/types';

export default function Alerts() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'alerts' | 'rules'>('alerts');
  const { alertRules, loadAlertRules, addAlertRule, removeAlertRule, acknowledgeAlert, loadAlertCount } = useMonitorStore();
  const [newRule, setNewRule] = useState({ name: '', description: '', level: 'WARNING', condition: 'TIMEOUT', thresholdMs: 30000, enabled: true });

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.alerts.getUnacknowledged(page, 15);
      setAlerts(result.content);
      setTotalPages(result.totalPages);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    if (tab === 'alerts') fetchAlerts();
    else loadAlertRules();
  }, [tab, fetchAlerts, loadAlertRules]);

  const handleAcknowledge = async (id: number) => {
    await acknowledgeAlert(id, 'admin');
    await fetchAlerts();
  };

  const handleAddRule = async () => {
    if (!newRule.name) return;
    await addAlertRule(newRule as AlertRule);
    setNewRule({ name: '', description: '', level: 'WARNING', condition: 'TIMEOUT', thresholdMs: 30000, enabled: true });
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-sans font-bold text-monitor-text">告警管理</h2>
          <p className="text-monitor-text-muted text-sm mt-1 font-sans">管理事务告警与告警规则</p>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab('alerts')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-sans font-medium transition-colors ${
            tab === 'alerts' ? 'bg-monitor-accent/10 text-monitor-accent border border-monitor-accent/30' : 'bg-monitor-card border border-monitor-border text-monitor-text-muted hover:text-monitor-text'
          }`}
        >
          <Bell className="w-4 h-4" />
          告警列表
        </button>
        <button
          onClick={() => setTab('rules')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-sans font-medium transition-colors ${
            tab === 'rules' ? 'bg-monitor-accent/10 text-monitor-accent border border-monitor-accent/30' : 'bg-monitor-card border border-monitor-border text-monitor-text-muted hover:text-monitor-text'
          }`}
        >
          <Shield className="w-4 h-4" />
          规则管理
        </button>
      </div>

      {tab === 'alerts' ? (
        <div className="bg-monitor-card border border-monitor-border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-monitor-border">
                <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted">级别</th>
                <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted">告警名称</th>
                <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted">XID</th>
                <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted">消息</th>
                <th className="text-left px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted">触发时间</th>
                <th className="text-right px-5 py-3.5 text-xs font-sans font-semibold text-monitor-text-muted">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-monitor-border/50">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-5 py-4"><div className="h-4 bg-monitor-hover rounded animate-pulse" /></td>
                    ))}
                  </tr>
                ))
              ) : alerts.length > 0 ? (
                alerts.map((alert) => (
                  <tr key={alert.id} className="border-b border-monitor-border/50 hover:bg-monitor-hover/30 transition-colors">
                    <td className="px-5 py-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${alertLevelColor(alert.level)}`}>
                        {alert.level}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-xs font-sans font-medium text-monitor-text">{alert.alertName}</span>
                    </td>
                    <td className="px-5 py-4">
                      <button
                        onClick={() => navigate(`/transactions/${encodeURIComponent(alert.xid)}`)}
                        className="font-mono text-xs text-monitor-accent hover:underline"
                      >
                        {alert.xid.slice(0, 16)}...
                      </button>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-xs font-mono text-monitor-text-dim max-w-[300px] truncate block">{alert.message}</span>
                    </td>
                    <td className="px-5 py-4">
                      <span className="font-mono text-xs text-monitor-text-dim">
                        {new Date(alert.triggeredAt).toLocaleString('zh-CN')}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      {!alert.acknowledged && (
                        <button
                          onClick={() => handleAcknowledge(alert.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-monitor-accent/10 text-monitor-accent text-[10px] font-sans font-medium hover:bg-monitor-accent/20 transition-colors ml-auto"
                        >
                          <Check className="w-3 h-3" />
                          确认
                        </button>
                      )}
                      {alert.acknowledged && (
                        <span className="text-[10px] font-mono text-monitor-text-muted">已确认</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-monitor-text-muted text-sm font-sans">
                    <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-monitor-accent/30" />
                    暂无未确认告警
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-4 border-t border-monitor-border">
              <span className="text-xs font-mono text-monitor-text-muted">第 {page + 1} / {totalPages} 页</span>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0} className="p-2 rounded-lg bg-monitor-surface border border-monitor-border text-monitor-text-muted hover:text-monitor-text disabled:opacity-30 transition-colors">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1} className="p-2 rounded-lg bg-monitor-surface border border-monitor-border text-monitor-text-muted hover:text-monitor-text disabled:opacity-30 transition-colors">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div>
          <div className="bg-monitor-card border border-monitor-border rounded-xl p-5 mb-6">
            <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4">添加告警规则</h3>
            <div className="grid grid-cols-3 gap-4">
              <input
                type="text"
                placeholder="规则名称"
                value={newRule.name}
                onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                className="bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
              />
              <select
                value={newRule.condition}
                onChange={(e) => setNewRule({ ...newRule, condition: e.target.value })}
                className="bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text focus:outline-none focus:border-monitor-accent"
              >
                <option value="TIMEOUT">超时 (TIMEOUT)</option>
                <option value="STATUS_FAILED">状态失败 (STATUS_FAILED)</option>
                <option value="STATUS_ROLLBACK">回滚 (STATUS_ROLLBACK)</option>
                <option value="LONG_RUNNING">长时间运行 (LONG_RUNNING)</option>
              </select>
              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder="阈值(ms)"
                  value={newRule.thresholdMs}
                  onChange={(e) => setNewRule({ ...newRule, thresholdMs: Number(e.target.value) })}
                  className="flex-1 bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
                />
                <button
                  onClick={handleAddRule}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-monitor-accent text-monitor-bg text-xs font-sans font-semibold hover:bg-monitor-accent/90 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  添加
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {alertRules.map((rule) => (
              <div key={rule.name} className="bg-monitor-card border border-monitor-border rounded-xl p-5 flex items-center gap-6">
                <div className={`w-2.5 h-2.5 rounded-full ${rule.enabled ? 'bg-monitor-accent' : 'bg-monitor-text-muted'}`} />
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-sans font-semibold text-monitor-text">{rule.name}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${alertLevelColor(rule.level)}`}>{rule.level}</span>
                    <span className="text-[10px] font-mono text-monitor-text-muted">{rule.condition}</span>
                  </div>
                  <p className="text-xs font-sans text-monitor-text-dim mt-1">{rule.description}</p>
                </div>
                <span className="text-xs font-mono text-monitor-text-muted">{rule.thresholdMs}ms</span>
                <button
                  onClick={() => removeAlertRule(rule.name)}
                  className="p-2 rounded-lg hover:bg-monitor-danger/10 text-monitor-text-muted hover:text-monitor-danger transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {alertRules.length === 0 && (
              <div className="text-center py-12 text-monitor-text-muted text-sm font-sans">暂无告警规则</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
