import { useState } from 'react';
import { Lightbulb, AlertTriangle, Copy, Check } from 'lucide-react';
import { useLifecycleStore } from '@/store';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function getSkewColor(skew: number): string {
  if (skew > 20) return 'text-red-400';
  if (skew > 10) return 'text-amber-400';
  return 'text-sky-400';
}

function getFragColor(frag: number): string {
  if (frag > 3) return 'text-red-400';
  if (frag > 2) return 'text-amber-400';
  return 'text-sky-400';
}

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-red-500/10 text-red-400 border-red-500/30',
  medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  low: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
};

function generateSql(suggestion: { database: string; table: string; partition?: string; type: string }): string {
  const { database, table, partition, type } = suggestion;
  if (type === 'fragmentation' || type === 'large_fragmented') {
    if (partition) {
      return `ALTER TABLE ${database}.${table} PARTITION '${partition}' OPTIMIZE FINAL;`;
    }
    return `ALTER TABLE ${database}.${table} OPTIMIZE FINAL;`;
  }
  if (type === 'granularity_monthly') {
    return `ALTER TABLE ${database}.${table} MODIFY PARTITION KEY toYYYYMM(date_column);`;
  }
  if (type === 'granularity_yearly') {
    return `ALTER TABLE ${database}.${table} MODIFY PARTITION KEY toYYYY(date_column);`;
  }
  if (type === 'granularity_daily') {
    return `ALTER TABLE ${database}.${table} MODIFY PARTITION KEY toYYYYMMDD(date_column);`;
  }
  if (type === 'skew') {
    return `ALTER TABLE ${database}.${table} PARTITION '${partition}' OPTIMIZE FINAL;`;
  }
  return `ALTER TABLE ${database}.${table} ...;`;
}

const GRANULARITY_LABELS: Record<string, string> = {
  daily: '按天',
  monthly: '按月',
  yearly: '按年',
};

function SqlBlock({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center justify-between rounded-lg bg-slate-900/70 border border-slate-700/40 px-4 py-2.5">
      <code className="text-sm font-mono text-slate-300">{sql}</code>
      <button
        onClick={handleCopy}
        className="ml-3 flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-slate-700/50 hover:text-slate-200"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
        {copied ? '已复制' : '复制'}
      </button>
    </div>
  );
}

export default function Advisor() {
  const [database, setDatabase] = useState('');
  const [table, setTable] = useState('');

  const { analysisResult, analysisLoading, analysisError, analyzeTable } = useLifecycleStore();

  const handleAnalyze = () => {
    if (!database.trim() || !table.trim()) return;
    analyzeTable(database.trim(), table.trim());
  };

  const summaryCards = analysisResult
    ? [
        { label: '分区数量', value: analysisResult.partition_count, color: 'text-sky-400' },
        { label: '倾斜比率', value: analysisResult.skew_ratio.toFixed(1), color: getSkewColor(analysisResult.skew_ratio) },
        { label: '碎片化程度', value: analysisResult.fragmentation.toFixed(1), color: getFragColor(analysisResult.fragmentation) },
        { label: '平均分区大小', value: formatBytes(analysisResult.avg_partition_size), color: 'text-sky-400' },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">优化建议</h1>
        <p className="mt-1 text-sm text-slate-400">分析表结构与分区状态，获取优化建议</p>
      </div>

      <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-5">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="mb-1.5 block text-sm font-medium text-slate-300">数据库</label>
            <input
              type="text"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              placeholder="输入数据库名称"
              className="w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-sky-400/50 focus:ring-1 focus:ring-sky-400/20"
            />
          </div>
          <div className="flex-1">
            <label className="mb-1.5 block text-sm font-medium text-slate-300">表</label>
            <input
              type="text"
              value={table}
              onChange={(e) => setTable(e.target.value)}
              placeholder="输入表名称"
              className="w-full rounded-lg border border-slate-600/50 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors focus:border-sky-400/50 focus:ring-1 focus:ring-sky-400/20"
            />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={analysisLoading || !database.trim() || !table.trim()}
            className="flex items-center gap-2 rounded-lg bg-sky-400 px-5 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-sky-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Lightbulb className="h-4 w-4" />
            {analysisLoading ? '分析中...' : '分析'}
          </button>
        </div>
      </div>

      {analysisError && (
        <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {analysisError}
        </div>
      )}

      {analysisResult && (
        <>
          <div>
            <h2 className="mb-4 text-lg font-semibold text-slate-100">分析结果</h2>
            <div className="grid grid-cols-4 gap-4">
              {summaryCards.map((card) => (
                <div
                  key={card.label}
                  className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5"
                >
                  <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
                  <p className="mt-1 text-sm text-slate-400">{card.label}</p>
                </div>
              ))}
            </div>
          </div>

          {analysisResult.pattern && (
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
              <h2 className="mb-4 text-lg font-semibold text-slate-100">分区模式</h2>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-slate-500">当前粒度</p>
                  <p className="mt-1 text-lg font-semibold text-sky-400">
                    {GRANULARITY_LABELS[analysisResult.pattern.granularity] || analysisResult.pattern.granularity}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">识别分区数</p>
                  <p className="mt-1 text-lg font-semibold text-slate-200">{analysisResult.pattern.count}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">数据跨度</p>
                  <p className="mt-1 text-lg font-semibold text-slate-200">{analysisResult.pattern.time_span_days} 天</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">平均分区大小</p>
                  <p className="mt-1 text-lg font-semibold text-slate-200">{formatBytes(analysisResult.pattern.avg_size_bytes)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">平均行数</p>
                  <p className="mt-1 text-lg font-semibold text-slate-200">{analysisResult.pattern.avg_rows.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">识别置信度</p>
                  <p className="mt-1 text-lg font-semibold text-slate-200">{(analysisResult.pattern.confidence * 100).toFixed(0)}%</p>
                </div>
              </div>
            </div>
          )}

          {analysisResult.granularity_recommendation && (
            <div className="bg-gradient-to-r from-sky-500/10 to-sky-500/5 border border-sky-500/30 rounded-xl p-5">
              <h2 className="mb-3 text-lg font-semibold text-sky-400">分区粒度建议</h2>
              <div className="flex items-center gap-6 mb-4">
                <div className="text-center">
                  <p className="text-xs text-slate-500">当前</p>
                  <p className="mt-1 text-xl font-bold text-slate-400">
                    {GRANULARITY_LABELS[analysisResult.granularity_recommendation.current] || analysisResult.granularity_recommendation.current}
                  </p>
                </div>
                <div className="text-2xl text-sky-400">→</div>
                <div className="text-center">
                  <p className="text-xs text-slate-500">建议</p>
                  <p className="mt-1 text-xl font-bold text-sky-400">
                    {GRANULARITY_LABELS[analysisResult.granularity_recommendation.recommended] || analysisResult.granularity_recommendation.recommended}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500">预计分区数</p>
                  <p className="mt-1 text-xl font-bold text-sky-400">~{analysisResult.granularity_recommendation.estimated_part_count}</p>
                </div>
              </div>
              <p className="text-sm text-slate-300">{analysisResult.granularity_recommendation.reason}</p>
              {analysisResult.granularity_recommendation.sql_template && (
                <div className="mt-3">
                  <SqlBlock sql={analysisResult.granularity_recommendation.sql_template + ';'} />
                </div>
              )}
            </div>
          )}

          <div>
            <h2 className="mb-4 text-lg font-semibold text-slate-100">优化建议</h2>
            <div className="space-y-3">
              {analysisResult.suggestions.map((suggestion, idx) => {
                const severity = suggestion.severity || 'low';
                const severityStyle = SEVERITY_STYLES[severity] || SEVERITY_STYLES.low;
                const sql = generateSql(suggestion);

                return (
                  <div
                    key={idx}
                    className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 space-y-3"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <span
                          className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${severityStyle}`}
                        >
                          {severity}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-slate-200">{suggestion.type}</p>
                          {suggestion.partition && (
                            <p className="mt-0.5 text-xs font-mono text-slate-500">
                              分区: {suggestion.partition}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    <p className="text-sm text-slate-400">{suggestion.description}</p>

                    <div className="flex gap-6 text-sm">
                      <div>
                        <span className="text-slate-500">操作: </span>
                        <span className="text-slate-300">{suggestion.action}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">影响: </span>
                        <span className="text-slate-300">{suggestion.impact}</span>
                      </div>
                    </div>

                    <div>
                      <p className="mb-1.5 text-xs font-medium text-slate-500">SQL 语句</p>
                      <SqlBlock sql={sql} />
                    </div>
                  </div>
                );
              })}

              {analysisResult.suggestions.length === 0 && (
                <div className="flex items-center justify-center rounded-xl bg-slate-800/50 border border-slate-700/50 py-10 text-sm text-slate-500">
                  暂无优化建议，表状态良好
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
