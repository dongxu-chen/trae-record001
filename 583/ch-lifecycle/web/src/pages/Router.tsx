import { useState, useEffect, useCallback } from 'react';
import { Route, Database, Trash2, Play, RefreshCw, Plus } from 'lucide-react';
import * as api from '@/api/client';
import type { RoutingConfig, QueryInfo, RouteResult, RoutingRule, QuerySource, CreateRoutingRuleRequest } from '@/types';
import { cn } from '@/lib/utils';

const sourceColorMap: Record<QuerySource, string> = {
  hot: 'bg-orange-400/10 text-orange-400 border-orange-400/30',
  cold: 'bg-sky-400/10 text-sky-400 border-sky-400/30',
  auto: 'bg-violet-400/10 text-violet-400 border-violet-400/30',
};

const sourceLabelMap: Record<QuerySource, string> = {
  hot: '热数据',
  cold: '冷数据',
  auto: '自动',
};

function SourceBadge({ source, size = 'md' }: { source: QuerySource; size?: 'sm' | 'md' }) {
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1';
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full border font-medium',
      sourceColorMap[source],
      sizeClasses
    )}>
      <span className={cn(
        'h-1.5 w-1.5 rounded-full',
        source === 'hot' && 'bg-orange-400',
        source === 'cold' && 'bg-sky-400',
        source === 'auto' && 'bg-violet-400',
      )} />
      {sourceLabelMap[source]}
    </span>
  );
}

const EMPTY_RULE: Omit<CreateRoutingRuleRequest, 'id'> = {
  database: '',
  table: '',
  pattern: '',
  min_age_days: 30,
  target_source: 'cold' as QuerySource,
  priority: 0,
};

export default function Router() {
  const [config, setConfig] = useState<RoutingConfig | null>(null);
  const [configForm, setConfigForm] = useState<RoutingConfig | null>(null);
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [queryInfo, setQueryInfo] = useState<QueryInfo | null>(null);
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [routing, setRouting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sql, setSql] = useState('');
  const [database, setDatabase] = useState('default');

  const [newRule, setNewRule] = useState<Omit<CreateRoutingRuleRequest, 'id'>>(EMPTY_RULE);
  const [addingRule, setAddingRule] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [configData, rulesData] = await Promise.all([
        api.getRouterConfig(),
        api.getRoutingRules(),
      ]);
      setConfig(configData);
      setConfigForm(configData);
      setRules(rulesData);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSaveConfig = useCallback(async () => {
    if (!configForm) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateRouterConfig(configForm);
      setConfig(updated);
      setConfigForm(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }, [configForm]);

  const handleAnalyze = useCallback(async () => {
    if (!sql || !database) return;
    setAnalyzing(true);
    setError(null);
    setQueryInfo(null);
    setRouteResult(null);
    try {
      const result = await api.analyzeQuery(sql, database);
      setQueryInfo(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  }, [sql, database]);

  const handleRoute = useCallback(async () => {
    if (!sql || !database) return;
    setRouting(true);
    setError(null);
    setRouteResult(null);
    try {
      const result = await api.routeQuery(sql, database);
      setRouteResult(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRouting(false);
    }
  }, [sql, database]);

  const handleAddRule = useCallback(async () => {
    if (!newRule.database || !newRule.table || !newRule.pattern) return;
    setAddingRule(true);
    setError(null);
    try {
      const created = await api.addRoutingRule(newRule);
      setRules((prev) => [...prev, created]);
      setNewRule(EMPTY_RULE);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAddingRule(false);
    }
  }, [newRule]);

  const handleDeleteRule = useCallback(async (id: string) => {
    if (!confirm('确定要删除此路由规则吗？')) return;
    try {
      await api.deleteRoutingRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-400/10">
              <Route className="h-5 w-5 text-sky-400" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">查询路由</h1>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            基于数据年龄的智能查询路由，自动将查询分发到热/冷存储节点，优化查询性能
          </p>
        </div>

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {configForm && (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-100">路由配置</h2>
              <button
                onClick={handleSaveConfig}
                disabled={saving}
                className="flex items-center gap-2 rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50"
              >
                <RefreshCw className={cn('h-4 w-4', saving && 'animate-spin')} />
                保存配置
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="flex items-center justify-between rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3">
                <div>
                  <p className="text-sm text-slate-300">启用智能路由</p>
                  <p className="text-xs text-slate-500">自动根据数据年龄选择查询源</p>
                </div>
                <button
                  onClick={() => setConfigForm((c) => c ? { ...c, enable_smart_routing: !c.enable_smart_routing } : c)}
                  className={cn(
                    'relative h-6 w-11 rounded-full transition-colors',
                    configForm.enable_smart_routing ? 'bg-sky-500' : 'bg-slate-600'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
                      configForm.enable_smart_routing ? 'left-[22px]' : 'left-0.5'
                    )}
                  />
                </button>
              </div>

              <div>
                <label className="mb-1 block text-sm text-slate-400">默认查询源</label>
                <select
                  value={configForm.default_source}
                  onChange={(e) => setConfigForm((c) => c ? { ...c, default_source: e.target.value as QuerySource } : c)}
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-sky-400 transition-colors"
                >
                  <option value="hot">热数据 (Hot)</option>
                  <option value="cold">冷数据 (Cold)</option>
                  <option value="auto">自动选择 (Auto)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm text-slate-400">热数据节点</label>
                <input
                  type="text"
                  value={configForm.hot_host}
                  onChange={(e) => setConfigForm((c) => c ? { ...c, hot_host: e.target.value } : c)}
                  placeholder="clickhouse-hot:8123"
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 transition-colors"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm text-slate-400">冷数据节点</label>
                <input
                  type="text"
                  value={configForm.cold_host}
                  onChange={(e) => setConfigForm((c) => c ? { ...c, cold_host: e.target.value } : c)}
                  placeholder="clickhouse-cold:8123"
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 transition-colors"
                />
              </div>
            </div>
          </div>
        )}

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">SQL 分析</h2>

          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="col-span-3">
              <label className="mb-1 block text-sm text-slate-400">SQL 语句</label>
              <textarea
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                placeholder="SELECT * FROM events WHERE event_date >= '2024-01-01'"
                rows={3}
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 transition-colors font-mono resize-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-400">数据库</label>
              <input
                type="text"
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                placeholder="default"
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 transition-colors"
              />
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing || !sql || !database}
                  className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-slate-700 px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-600 disabled:opacity-50"
                >
                  {analyzing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
                  分析
                </button>
                <button
                  onClick={handleRoute}
                  disabled={routing || !sql || !database}
                  className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-sky-400 px-3 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50"
                >
                  {routing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  路由查询
                </button>
              </div>
            </div>
          </div>

          {queryInfo && (
            <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 p-4 mb-4">
              <h3 className="text-sm font-medium text-slate-300 mb-3">查询分析结果</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 mb-1">提取的表</p>
                  <div className="flex flex-wrap gap-2">
                    {queryInfo.table_names?.length > 0 ? (
                      queryInfo.table_names.map((table, idx) => (
                        <span key={idx} className="rounded bg-slate-700/50 px-2 py-0.5 text-xs font-mono text-slate-300">
                          {table}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">未检测到表</span>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">时间范围</p>
                  {queryInfo.start_time && queryInfo.end_time ? (
                    <div className="text-sm">
                      <span className="text-slate-300 font-mono">{queryInfo.start_time}</span>
                      <span className="text-slate-500 mx-2">→</span>
                      <span className="text-slate-300 font-mono">{queryInfo.end_time}</span>
                    </div>
                  ) : (
                    <span className="text-sm text-slate-500">未检测到时间范围</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {routeResult && (
            <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 p-4">
              <h3 className="text-sm font-medium text-slate-300 mb-3">路由结果</h3>
              <div className="grid grid-cols-4 gap-4">
                <div className="rounded-lg bg-slate-800/50 border border-slate-700/30 px-4 py-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">查询源</p>
                  <SourceBadge source={routeResult.source as QuerySource} />
                </div>
                <div className="rounded-lg bg-slate-800/50 border border-slate-700/30 px-4 py-3">
                  <p className="text-xs text-slate-500 mb-1">目标主机</p>
                  <p className="text-sm font-mono text-slate-300">{routeResult.target_host}</p>
                </div>
                <div className="rounded-lg bg-slate-800/50 border border-slate-700/30 px-4 py-3">
                  <p className="text-xs text-slate-500 mb-1">预估行数</p>
                  <p className="text-lg font-bold text-sky-400">{routeResult.estimated_rows.toLocaleString()}</p>
                </div>
                <div className="col-span-4">
                  <p className="text-xs text-slate-500 mb-1">路由原因</p>
                  <p className="text-sm text-slate-300">{routeResult.reason}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
          <h2 className="mb-4 text-lg font-semibold text-slate-100">路由规则</h2>

          <div className="rounded-lg bg-slate-900/50 border border-slate-700/30 p-4 mb-4">
            <div className="grid grid-cols-6 gap-3 mb-3">
              <div>
                <label className="mb-1 block text-xs text-slate-500">数据库</label>
                <input
                  type="text"
                  value={newRule.database}
                  onChange={(e) => setNewRule((r) => ({ ...r, database: e.target.value }))}
                  placeholder="default"
                  className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">表</label>
                <input
                  type="text"
                  value={newRule.table}
                  onChange={(e) => setNewRule((r) => ({ ...r, table: e.target.value }))}
                  placeholder="events"
                  className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">模式</label>
                <input
                  type="text"
                  value={newRule.pattern}
                  onChange={(e) => setNewRule((r) => ({ ...r, pattern: e.target.value }))}
                  placeholder="2024-01-%"
                  className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-400 font-mono"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">最小天数</label>
                <input
                  type="number"
                  min={0}
                  value={newRule.min_age_days}
                  onChange={(e) => setNewRule((r) => ({ ...r, min_age_days: Number(e.target.value) }))}
                  className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-white outline-none focus:border-sky-400"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">目标源</label>
                <select
                  value={newRule.target_source}
                  onChange={(e) => setNewRule((r) => ({ ...r, target_source: e.target.value as QuerySource }))}
                  className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-white outline-none focus:border-sky-400"
                >
                  <option value="hot">热数据</option>
                  <option value="cold">冷数据</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">优先级</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min={0}
                    value={newRule.priority}
                    onChange={(e) => setNewRule((r) => ({ ...r, priority: Number(e.target.value) }))}
                    className="flex-1 rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-white outline-none focus:border-sky-400"
                  />
                  <button
                    onClick={handleAddRule}
                    disabled={addingRule || !newRule.database || !newRule.table || !newRule.pattern}
                    className="flex items-center justify-center rounded bg-sky-400 px-3 py-1.5 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50"
                  >
                    {addingRule ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {loading && rules.length === 0 ? (
            <div className="py-12 text-center text-slate-500">Loading...</div>
          ) : rules.length === 0 ? (
            <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 py-12 text-center">
              <Route className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-500 text-sm">暂无路由规则</p>
              <p className="text-slate-600 text-xs mt-1">使用上方表单创建自定义路由规则</p>
            </div>
          ) : (
            <div className="space-y-2">
              {rules.sort((a, b) => a.priority - b.priority).map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center gap-3 rounded-lg bg-slate-900/50 border border-slate-700/30 px-4 py-3"
                >
                  <div className="flex-1 grid grid-cols-6 gap-3 items-center">
                    <div>
                      <span className="text-xs text-slate-500">数据库</span>
                      <p className="text-sm font-mono text-slate-300">{rule.database}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">表</span>
                      <p className="text-sm font-mono text-slate-300">{rule.table}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">模式</span>
                      <p className="text-sm font-mono text-sky-400">{rule.pattern}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">最小天数</span>
                      <p className="text-sm text-slate-300">{rule.min_age_days} 天</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">优先级</span>
                      <p className="text-sm text-slate-300">{rule.priority}</p>
                    </div>
                    <div className="flex items-center justify-between">
                      <SourceBadge source={rule.target_source as QuerySource} size="sm" />
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-red-500/10 hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
