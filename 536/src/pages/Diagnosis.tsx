import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Stethoscope,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Wrench,
  RotateCcw,
  GitBranch,
  AlertCircle,
  ArrowDown,
  RefreshCw,
  User,
  ArrowDownCircle,
  Search,
  Sparkles,
  Play,
} from 'lucide-react';
import { api } from '@/api';
import { severityColor, severityDot, alertLevelColor } from '@/utils/format';
import type { DiagnosisReport, DiagnosisSeverity, RollbackLogAnalysis, RollbackLogEntry, CompensationRecommendation, CompensationStrategy } from '@/types';

function SeverityIcon({ severity }: { severity: DiagnosisSeverity }) {
  switch (severity) {
    case 'CRITICAL':
      return <XCircle className="w-5 h-5 text-red-500" />;
    case 'HIGH':
      return <AlertTriangle className="w-5 h-5 text-red-400" />;
    case 'MEDIUM':
      return <Info className="w-5 h-5 text-amber-400" />;
    default:
      return <CheckCircle className="w-5 h-5 text-blue-400" />;
  }
}

function severityLabel(severity: DiagnosisSeverity): string {
  const map: Record<DiagnosisSeverity, string> = {
    LOW: '低',
    MEDIUM: '中',
    HIGH: '高',
    CRITICAL: '严重',
  };
  return map[severity] || '未知';
}

function cascadeDirectionLabel(dir: string): string {
  const map: Record<string, string> = {
    SINGLE: '单点回滚',
    SINGLE_BRANCH: '单分支回滚',
    FORWARD_CASCADE: '正向级联回滚',
    REVERSE_CASCADE: '反向级联回滚',
    RETRY_SAME_BRANCH: '同分支重试回滚',
  };
  return map[dir] || dir;
}

function cascadeDirectionColor(dir: string): string {
  if (dir === 'REVERSE_CASCADE') return 'bg-monitor-danger/10 text-monitor-danger border border-monitor-danger/30';
  if (dir === 'FORWARD_CASCADE') return 'bg-monitor-warning/10 text-monitor-warning border border-monitor-warning/30';
  return 'bg-monitor-info/10 text-monitor-info border border-monitor-info/30';
}

function errorTypeLabel(type: string): string {
  const map: Record<string, string> = {
    DEADLOCK: '死锁',
    CONNECTION: '连接异常',
    TIMEOUT: '超时',
    NULL_POINTER: '空指针',
    DATA_CONSTRAINT: '数据约束',
    PERMISSION: '权限',
    RESOURCE_EXHAUSTED: '资源耗尽',
    RETRY_EXHAUSTED: '重试耗尽',
    RUNTIME_ERROR: '运行时异常',
    CONNECTION_TIMEOUT: '连接超时',
    NETWORK_ERROR: '网络错误',
    SERVICE_UNAVAILABLE: '服务不可用',
    PERMISSION_DENIED: '权限拒绝',
    UNKNOWN: '未知',
  };
  return map[type] || type;
}

function strategyIcon(type: CompensationStrategy['type']) {
  switch (type) {
    case 'RETRY':
      return <RefreshCw className="w-4 h-4" />;
    case 'MANUAL':
      return <User className="w-4 h-4" />;
    case 'DEGRADE':
      return <ArrowDownCircle className="w-4 h-4" />;
    case 'RECONCILE':
      return <Search className="w-4 h-4" />;
  }
}

function strategyColor(type: CompensationStrategy['type'], isRecommended: boolean) {
  if (!isRecommended) return 'bg-monitor-surface border-monitor-border text-monitor-text';
  switch (type) {
    case 'RETRY':
      return 'bg-green-500/10 border-green-500/30 text-green-400';
    case 'MANUAL':
      return 'bg-amber-500/10 border-amber-500/30 text-amber-400';
    case 'DEGRADE':
      return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
    case 'RECONCILE':
      return 'bg-purple-500/10 border-purple-500/30 text-purple-400';
  }
}

function CompensationSection({ recommendation, onExecute }: {
  recommendation: CompensationRecommendation;
  onExecute: (type: string) => Promise<void>;
}) {
  const [executing, setExecuting] = useState<string | null>(null);

  const handleExecute = async (type: string) => {
    setExecuting(type);
    try {
      await onExecute(type);
    } finally {
      setExecuting(null);
    }
  };

  return (
    <div className="bg-monitor-card border border-monitor-border rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-monitor-border flex items-center gap-3">
        <Sparkles className="w-4 h-4 text-monitor-accent" />
        <h3 className="text-sm font-sans font-semibold text-monitor-text">补偿策略推荐</h3>
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-monitor-accent/10 text-monitor-accent border border-monitor-accent/30">
          {errorTypeLabel(recommendation.errorType)}
        </span>
      </div>

      <div className="p-5 border-b border-monitor-border">
        <p className="text-[10px] font-sans font-medium text-monitor-text-muted mb-1">失败原因</p>
        <p className="text-xs font-mono text-monitor-text-dim">{recommendation.failureReason}</p>
      </div>

      <div className="p-5 border-b border-monitor-border bg-monitor-accent/5">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-4 h-4 text-monitor-accent" />
          <span className="text-xs font-sans font-semibold text-monitor-accent">推荐策略</span>
          <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-monitor-accent text-monitor-bg">
            RECOMMENDED
          </span>
        </div>
        <div className={`flex items-center gap-3 p-3 rounded-lg border ${strategyColor(recommendation.recommendedStrategy.type, true)}`}>
          {strategyIcon(recommendation.recommendedStrategy.type)}
          <div className="flex-1">
            <p className="text-sm font-sans font-semibold">{recommendation.recommendedStrategy.name}</p>
            <p className="text-xs opacity-80">{recommendation.recommendedStrategy.description}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] opacity-60">成功率</p>
            <p className="text-sm font-mono font-bold">{Math.round(recommendation.recommendedStrategy.successRate * 100)}%</p>
          </div>
          <button
            onClick={() => handleExecute(recommendation.recommendedStrategy.type)}
            disabled={executing === recommendation.recommendedStrategy.type}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-monitor-accent text-white text-[10px] font-sans font-medium hover:bg-monitor-accent/90 disabled:opacity-50 transition-colors"
          >
            <Play className="w-3 h-3" />
            {executing === recommendation.recommendedStrategy.type ? '执行中...' : '执行'}
          </button>
        </div>
      </div>

      {recommendation.strategies && recommendation.strategies.length > 0 && (
        <div className="p-5">
          <h4 className="text-xs font-sans font-semibold text-monitor-text-muted mb-3">其他可选策略</h4>
          <div className="space-y-2">
            {recommendation.strategies
              .filter((s) => s.type !== recommendation.recommendedStrategy.type)
              .map((strategy) => (
                <div
                  key={strategy.type}
                  className={`flex items-center gap-3 p-3 rounded-lg border ${strategyColor(strategy.type, false)}`}
                >
                  {strategyIcon(strategy.type)}
                  <div className="flex-1">
                    <p className="text-sm font-sans font-semibold">{strategy.name}</p>
                    <p className="text-xs text-monitor-text-muted">{strategy.description}</p>
                  </div>
                  <div className="text-right mr-3">
                    <p className="text-[10px] text-monitor-text-muted">成功率</p>
                    <p className="text-sm font-mono font-bold">{Math.round(strategy.successRate * 100)}%</p>
                  </div>
                  <button
                    onClick={() => handleExecute(strategy.type)}
                    disabled={executing === strategy.type}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-monitor-surface border border-monitor-border text-monitor-text text-[10px] font-sans font-medium hover:border-monitor-accent hover:text-monitor-accent disabled:opacity-50 transition-colors"
                  >
                    <Play className="w-3 h-3" />
                    {executing === strategy.type ? '执行中...' : '执行'}
                  </button>
                </div>
              ))}
          </div>
        </div>
      )}

      {recommendation.analysisDetail && (
        <div className="p-5 border-t border-monitor-border">
          <h4 className="text-xs font-sans font-semibold text-monitor-text-muted mb-2">分析详情</h4>
          <pre className="text-[10px] font-mono text-monitor-text-dim whitespace-pre-wrap bg-monitor-surface rounded-lg p-3 max-h-48 overflow-y-auto">
            {recommendation.analysisDetail}
          </pre>
        </div>
      )}
    </div>
  );
}

function RollbackLogSection({ log }: { log: RollbackLogAnalysis }) {
  return (
    <div className="bg-monitor-card border border-monitor-border rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-monitor-border flex items-center gap-3">
        <RotateCcw className="w-4 h-4 text-monitor-danger" />
        <h3 className="text-sm font-sans font-semibold text-monitor-text">回滚日志分析</h3>
        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${cascadeDirectionColor(log.cascadeDirection)}`}>
          {cascadeDirectionLabel(log.cascadeDirection)}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 p-5 border-b border-monitor-border">
        <div className="bg-monitor-surface rounded-lg p-3 border border-monitor-border">
          <p className="text-[10px] font-sans font-medium text-monitor-text-muted mb-1">触发分支</p>
          <p className="text-sm font-mono font-bold text-monitor-text">{log.triggerBranchId || '-'}</p>
        </div>
        <div className="bg-monitor-surface rounded-lg p-3 border border-monitor-border">
          <p className="text-[10px] font-sans font-medium text-monitor-text-muted mb-1">根因分支</p>
          <div className="flex items-center gap-2">
            <p className="text-sm font-mono font-bold text-monitor-danger">{log.rootBranchId || '-'}</p>
            {log.rootErrorType && log.rootErrorType !== 'UNKNOWN' && (
              <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-semibold bg-monitor-danger/10 text-monitor-danger">
                {errorTypeLabel(log.rootErrorType)}
              </span>
            )}
          </div>
        </div>
        <div className="bg-monitor-surface rounded-lg p-3 border border-monitor-border">
          <p className="text-[10px] font-sans font-medium text-monitor-text-muted mb-1">级联方向</p>
          <p className="text-sm font-mono font-bold text-monitor-text">{cascadeDirectionLabel(log.cascadeDirection)}</p>
        </div>
      </div>

      {log.triggerReason && (
        <div className="px-5 py-3 border-b border-monitor-border bg-monitor-danger/5">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-monitor-danger flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-[10px] font-sans font-semibold text-monitor-danger mb-0.5">触发原因</p>
              <p className="text-xs font-mono text-monitor-text-dim">{log.triggerReason}</p>
            </div>
          </div>
        </div>
      )}

      {log.timelineSummary && (
        <div className="px-5 py-3 border-b border-monitor-border">
          <p className="text-[10px] font-mono text-monitor-text-muted">{log.timelineSummary}</p>
        </div>
      )}

      {log.logChain && log.logChain.length > 0 && (
        <div className="p-5">
          <h4 className="text-xs font-sans font-semibold text-monitor-text-muted mb-3">回滚链路</h4>
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-px bg-monitor-border" />
            {log.logChain.map((entry) => (
              <RollbackLogEntryRow key={entry.sequence} entry={entry} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RollbackLogEntryRow({ entry }: { entry: RollbackLogEntry }) {
  return (
    <div className="relative pl-10 pb-5 last:pb-0">
      <div
        className={`absolute left-3 top-1 w-3 h-3 rounded-full border-2 ${
          entry.isRootCause
            ? 'border-monitor-danger bg-monitor-danger/30 shadow-lg shadow-monitor-danger/20'
            : 'border-monitor-accent bg-monitor-bg'
        }`}
      />
      {entry.isRootCause && (
        <div className="absolute left-1 top-1 w-[18px] h-[18px] rounded-full border-2 border-monitor-danger/30 animate-pulse" />
      )}
      <div className={`bg-monitor-surface border rounded-lg p-3 ${entry.isRootCause ? 'border-monitor-danger/30 bg-monitor-danger/5' : 'border-monitor-border'}`}>
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[10px] font-mono text-monitor-text-muted">#{entry.sequence}</span>
          {entry.branchId && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-mono font-semibold bg-monitor-info/10 text-monitor-info">
              <GitBranch className="w-2.5 h-2.5" />
              {entry.branchId}
            </span>
          )}
          <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-semibold bg-monitor-accent/10 text-monitor-accent border border-monitor-accent/20">
            {entry.phase}
          </span>
          <span className="text-[10px] font-mono text-monitor-text-muted">{entry.action}</span>
          {entry.isRootCause && (
            <span className="ml-auto px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-monitor-danger/10 text-monitor-danger border border-monitor-danger/30">
              ROOT CAUSE
            </span>
          )}
        </div>
        {entry.errorMessage && (
          <p className="text-xs font-mono text-monitor-danger bg-monitor-danger/5 rounded p-1.5 mb-1">{entry.errorMessage}</p>
        )}
        {entry.eventTime && (
          <p className="text-[10px] font-mono text-monitor-text-muted">{entry.eventTime}</p>
        )}
      </div>
    </div>
  );
}

export default function Diagnosis() {
  const { xid: urlXid } = useParams<{ xid: string }>();
  const navigate = useNavigate();
  const [inputXid, setInputXid] = useState(urlXid || '');
  const [report, setReport] = useState<DiagnosisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [compensation, setCompensation] = useState<CompensationRecommendation | null>(null);
  const [compensationLoading, setCompensationLoading] = useState(false);
  const [executeMessage, setExecuteMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleDiagnose = async (xid?: string) => {
    const targetXid = xid || inputXid.trim();
    if (!targetXid) return;
    setLoading(true);
    setCompensationLoading(true);
    setError('');
    setReport(null);
    setCompensation(null);
    setExecuteMessage(null);
    try {
      const [diagnosisResult, compensationResult] = await Promise.all([
        api.diagnosis.diagnose(targetXid),
        api.compensation.getRecommendation(targetXid).catch(() => null),
      ]);
      setReport(diagnosisResult);
      setCompensation(compensationResult);
    } catch (e) {
      setError('诊断请求失败，请检查后端服务是否启动');
    } finally {
      setLoading(false);
      setCompensationLoading(false);
    }
  };

  const handleExecuteStrategy = async (type: string) => {
    if (!inputXid.trim()) return;
    try {
      const result = await api.compensation.executeStrategy(inputXid.trim(), type);
      setExecuteMessage({ type: 'success', text: result.message });
      setTimeout(() => setExecuteMessage(null), 5000);
    } catch (e) {
      setExecuteMessage({ type: 'error', text: '策略执行失败，请稍后重试' });
      setTimeout(() => setExecuteMessage(null), 5000);
    }
  };

  useEffect(() => {
    if (urlXid) {
      setInputXid(urlXid);
      handleDiagnose(urlXid);
    }
  }, [urlXid]);

  return (
    <div className="p-8">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg bg-monitor-card border border-monitor-border text-monitor-text-muted hover:text-monitor-text hover:border-monitor-accent transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h2 className="text-2xl font-sans font-bold text-monitor-text">异常诊断</h2>
          <p className="text-monitor-text-muted text-sm mt-1 font-sans">分析事务异常根因，提供修复建议</p>
        </div>
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl p-5 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Stethoscope className="w-4 h-4 text-monitor-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="输入事务 XID 进行诊断..."
              value={inputXid}
              onChange={(e) => setInputXid(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleDiagnose()}
              className="w-full bg-monitor-surface border border-monitor-border rounded-lg pl-9 pr-4 py-2.5 text-sm font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
            />
          </div>
          <button
            onClick={() => handleDiagnose()}
            disabled={loading || !inputXid.trim()}
            className="px-5 py-2.5 rounded-lg bg-monitor-accent text-monitor-bg text-sm font-sans font-semibold hover:bg-monitor-accent/90 disabled:opacity-50 transition-colors"
          >
            {loading ? '诊断中...' : '开始诊断'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-monitor-danger/10 border border-monitor-danger/30 rounded-xl p-4 mb-6 flex items-center gap-3">
          <XCircle className="w-5 h-5 text-monitor-danger flex-shrink-0" />
          <p className="text-sm font-sans text-monitor-danger">{error}</p>
        </div>
      )}

      {executeMessage && (
        <div className={`${executeMessage.type === 'success' ? 'bg-green-500/10 border-green-500/30' : 'bg-monitor-danger/10 border-monitor-danger/30'} border rounded-xl p-4 mb-6 flex items-center gap-3`}>
          {executeMessage.type === 'success' ? (
            <CheckCircle className={`w-5 h-5 ${executeMessage.type === 'success' ? 'text-green-400' : 'text-monitor-danger'} flex-shrink-0`} />
          ) : (
            <XCircle className="w-5 h-5 text-monitor-danger flex-shrink-0" />
          )}
          <p className={`text-sm font-sans ${executeMessage.type === 'success' ? 'text-green-400' : 'text-monitor-danger'}`}>{executeMessage.text}</p>
        </div>
      )}

      {loading && (
        <div className="animate-pulse space-y-6">
          <div className="h-32 bg-monitor-card rounded-xl" />
          <div className="h-48 bg-monitor-card rounded-xl" />
          <div className="h-64 bg-monitor-card rounded-xl" />
        </div>
      )}

      {report && !loading && (
        <div className="space-y-6">
          <div className="bg-monitor-card border border-monitor-border rounded-xl p-6">
            <div className="flex items-start gap-6">
              <div className={`w-16 h-16 rounded-xl flex items-center justify-center ${severityColor(report.severity)}`}>
                <SeverityIcon severity={report.severity} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-sans font-bold text-monitor-text">诊断报告</h3>
                  <span className={`px-2.5 py-1 rounded text-xs font-mono font-bold ${severityColor(report.severity)}`}>
                    {severityLabel(report.severity)}
                  </span>
                  <span className="font-mono text-xs text-monitor-text-muted">XID: {report.xid}</span>
                </div>
                <div className="space-y-2">
                  <div>
                    <span className="text-xs font-sans font-medium text-monitor-text-muted">根因分析</span>
                    <p className="text-sm font-sans text-monitor-text mt-0.5">{report.rootCause}</p>
                  </div>
                </div>
              </div>
            </div>

            {report.suggestion && (
              <div className="mt-5 p-4 bg-monitor-accent/5 border border-monitor-accent/20 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Wrench className="w-4 h-4 text-monitor-accent" />
                  <span className="text-xs font-sans font-semibold text-monitor-accent">修复建议</span>
                </div>
                <pre className="text-xs font-mono text-monitor-text-dim whitespace-pre-wrap">{report.suggestion}</pre>
              </div>
            )}
          </div>

          {report.items && report.items.length > 0 && (
            <div>
              <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4">诊断明细</h3>
              <div className="space-y-3">
                {report.items.map((item, idx) => (
                  <div key={idx} className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                    <div className="flex items-start gap-4">
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <div className={`w-2.5 h-2.5 rounded-full ${severityDot(item.severity)}`} />
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${severityColor(item.severity)}`}>
                          {item.severity}
                        </span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-monitor-accent bg-monitor-accent/10 px-1.5 py-0.5 rounded">{item.category}</span>
                          <span className="text-sm font-sans font-medium text-monitor-text">{item.description}</span>
                        </div>
                        <p className="text-xs font-mono text-monitor-text-dim">{item.detail}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {report.rollbackLog && <RollbackLogSection log={report.rollbackLog} />}

          {compensation && !compensationLoading && <CompensationSection recommendation={compensation} onExecute={handleExecuteStrategy} />}

          {compensationLoading && (
            <div className="bg-monitor-card border border-monitor-border rounded-xl overflow-hidden animate-pulse">
              <div className="h-12 border-b border-monitor-border" />
              <div className="h-32 m-5 rounded-lg bg-monitor-hover" />
              <div className="h-48 m-5 rounded-lg bg-monitor-hover" />
            </div>
          )}

          {report.relatedTransactions && report.relatedTransactions.length > 0 && (
            <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
              <h3 className="text-xs font-sans font-semibold text-monitor-text-muted mb-3">关联服务</h3>
              <div className="flex flex-wrap gap-2">
                {report.relatedTransactions.map((rt, idx) => (
                  <span key={idx} className="px-3 py-1 rounded-lg bg-monitor-surface border border-monitor-border text-xs font-mono text-monitor-text-dim">
                    {rt}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!report && !loading && !error && (
        <div className="bg-monitor-card border border-monitor-border rounded-xl h-64 flex items-center justify-center">
          <div className="text-center">
            <Stethoscope className="w-12 h-12 text-monitor-text-muted mx-auto mb-3 opacity-30" />
            <p className="text-monitor-text-muted text-sm font-sans">输入事务XID开始异常诊断</p>
            <p className="text-monitor-text-muted text-xs font-sans mt-1">系统将自动分析根因并提供修复建议</p>
          </div>
        </div>
      )}
    </div>
  );
}
