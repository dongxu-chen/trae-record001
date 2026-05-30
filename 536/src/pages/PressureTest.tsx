import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play,
  Square,
  RefreshCw,
  Gauge,
  Clock,
  Users,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  BarChart3,
  Settings,
  Activity,
  Zap,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from 'recharts';
import { api } from '@/api';
import type { PressureTestConfig, PressureTestResult, PressureTestMetrics, TransactionMode } from '@/types';

const MODES: TransactionMode[] = ['TCC', 'SAGA', 'AT'];

const defaultConfig: PressureTestConfig = {
  mode: 'AT',
  concurrency: 50,
  durationSeconds: 60,
  failureRate: 0.05,
  networkDelayMs: 100,
  businessType: '压测业务',
};

function modeColor(mode: TransactionMode): string {
  switch (mode) {
    case 'TCC':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/50';
    case 'SAGA':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    case 'AT':
      return 'bg-green-500/20 text-green-400 border-green-500/50';
    default:
      return 'bg-gray-500/20 text-gray-400';
  }
}

function statusColor(status: PressureTestResult['status']): string {
  switch (status) {
    case 'RUNNING':
      return 'bg-green-500/20 text-green-400 border-green-500/50';
    case 'COMPLETED':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    case 'FAILED':
      return 'bg-red-500/20 text-red-400 border-red-500/50';
    case 'CANCELLED':
      return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
  }
}

function statusLabel(status: PressureTestResult['status']): string {
  switch (status) {
    case 'RUNNING':
      return '运行中';
    case 'COMPLETED':
      return '已完成';
    case 'FAILED':
      return '失败';
    case 'CANCELLED':
      return '已取消';
  }
}

export default function PressureTest() {
  const [config, setConfig] = useState<PressureTestConfig>(defaultConfig);
  const [tests, setTests] = useState<PressureTestResult[]>([]);
  const [selectedTest, setSelectedTest] = useState<PressureTestResult | null>(null);
  const [runningTest, setRunningTest] = useState<PressureTestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'config' | 'history'>('config');
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const loadTests = useCallback(async () => {
    try {
      const result = await api.pressureTest.list();
      setTests(result.sort((a, b) =>
        new Date(b.startTime).getTime() - new Date(a.startTime).getTime()
      ));

      const running = result.find((t) => t.status === 'RUNNING');
      if (running) {
        setRunningTest(running);
        if (selectedTest?.testId === running.testId) {
          setSelectedTest(running);
        }
      } else {
        setRunningTest(null);
      }
    } catch {
    }
  }, [selectedTest]);

  const pollRunningTest = useCallback(async () => {
    if (!runningTest) return;
    try {
      const result = await api.pressureTest.get(runningTest.testId);
      setRunningTest(result);
      if (selectedTest?.testId === result.testId) {
        setSelectedTest(result);
      }
      if (result.status !== 'RUNNING') {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        loadTests();
      }
    } catch {
    }
  }, [runningTest, selectedTest, loadTests]);

  useEffect(() => {
    loadTests();
  }, [loadTests]);

  useEffect(() => {
    if (runningTest && runningTest.status === 'RUNNING') {
      pollIntervalRef.current = setInterval(pollRunningTest, 1000);
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [runningTest, pollRunningTest]);

  useEffect(() => {
    if (selectedTest?.metrics && selectedTest.metrics.length > 0) {
      const data = selectedTest.metrics.map((m, idx) => ({
        time: idx + 1,
        tps: Math.round(m.tps),
        avgRt: Math.round(m.avgResponseTimeMs),
        p95: Math.round(m.p95ResponseTimeMs),
        p99: Math.round(m.p99ResponseTimeMs),
        success: m.successCount,
        failure: m.failureCount,
        rollback: m.rollbackCount,
      }));
      setChartData(data);
    } else {
      setChartData([]);
    }
  }, [selectedTest]);

  const handleStart = async () => {
    setLoading(true);
    try {
      const result = await api.pressureTest.start(config);
      setRunningTest(result);
      setSelectedTest(result);
      setActiveTab('history');
      loadTests();
    } catch {
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (!runningTest) return;
    try {
      await api.pressureTest.stop(runningTest.testId);
      loadTests();
    } catch {
    }
  };

  const successRate = selectedTest?.summary
    ? selectedTest.summary.totalRequests > 0
      ? ((selectedTest.summary.successCount / selectedTest.summary.totalRequests) * 100).toFixed(1)
      : '0'
    : '0';

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-sans font-bold text-monitor-text">压测中心</h2>
          <p className="text-monitor-text-muted text-sm mt-1 font-sans">模拟高并发场景，验证分布式事务性能</p>
        </div>
        {runningTest && runningTest.status === 'RUNNING' && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/30">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs font-sans text-green-400">压测运行中</span>
            </div>
            <button
              onClick={handleStop}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-monitor-danger text-white text-xs font-sans font-medium hover:bg-monitor-danger/90 transition-colors"
            >
              <Square className="w-4 h-4" />
              停止压测
            </button>
          </div>
        )}
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('config')}
          className={`px-4 py-2 rounded-lg text-xs font-sans font-medium transition-colors ${
            activeTab === 'config'
              ? 'bg-monitor-accent text-white'
              : 'bg-monitor-card border border-monitor-border text-monitor-text-muted hover:text-monitor-text'
          }`}
        >
          <Settings className="w-4 h-4 inline mr-2" />
          压测配置
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 rounded-lg text-xs font-sans font-medium transition-colors ${
            activeTab === 'history'
              ? 'bg-monitor-accent text-white'
              : 'bg-monitor-card border border-monitor-border text-monitor-text-muted hover:text-monitor-text'
          }`}
        >
          <BarChart3 className="w-4 h-4 inline mr-2" />
          压测历史
          {tests.length > 0 && (
            <span className="ml-2 px-1.5 py-0.5 rounded bg-monitor-accent/20 text-[10px]">
              {tests.length}
            </span>
          )}
        </button>
      </div>

      {activeTab === 'config' && (
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-1 bg-monitor-card border border-monitor-border rounded-xl p-6">
            <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4 flex items-center gap-2">
              <Settings className="w-4 h-4 text-monitor-accent" />
              压测参数配置
            </h3>

            <div className="space-y-5">
              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">事务模式</label>
                <div className="grid grid-cols-3 gap-2">
                  {MODES.map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setConfig({ ...config, mode })}
                      className={`px-3 py-2 rounded-lg text-xs font-mono font-semibold border transition-colors ${
                        config.mode === mode
                          ? modeColor(mode) + ' border'
                          : 'bg-monitor-surface border-monitor-border text-monitor-text-muted hover:border-monitor-accent'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">
                  并发数: {config.concurrency}
                </label>
                <input
                  type="range"
                  min="1"
                  max="500"
                  value={config.concurrency}
                  onChange={(e) => setConfig({ ...config, concurrency: parseInt(e.target.value) })}
                  className="w-full accent-monitor-accent"
                />
                <div className="flex justify-between text-[10px] text-monitor-text-muted mt-1">
                  <span>1</span>
                  <span>500</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">
                  压测时长: {config.durationSeconds}秒
                </label>
                <input
                  type="range"
                  min="10"
                  max="300"
                  value={config.durationSeconds}
                  onChange={(e) => setConfig({ ...config, durationSeconds: parseInt(e.target.value) })}
                  className="w-full accent-monitor-accent"
                />
                <div className="flex justify-between text-[10px] text-monitor-text-muted mt-1">
                  <span>10s</span>
                  <span>300s</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">
                  失败率: {(config.failureRate * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={config.failureRate * 100}
                  onChange={(e) => setConfig({ ...config, failureRate: parseInt(e.target.value) / 100 })}
                  className="w-full accent-monitor-accent"
                />
                <div className="flex justify-between text-[10px] text-monitor-text-muted mt-1">
                  <span>0%</span>
                  <span>100%</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">
                  网络延迟: {config.networkDelayMs}ms
                </label>
                <input
                  type="range"
                  min="0"
                  max="2000"
                  value={config.networkDelayMs}
                  onChange={(e) => setConfig({ ...config, networkDelayMs: parseInt(e.target.value) })}
                  className="w-full accent-monitor-accent"
                />
                <div className="flex justify-between text-[10px] text-monitor-text-muted mt-1">
                  <span>0ms</span>
                  <span>2000ms</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-sans text-monitor-text-muted mb-2">业务类型</label>
                <input
                  type="text"
                  value={config.businessType}
                  onChange={(e) => setConfig({ ...config, businessType: e.target.value })}
                  className="w-full bg-monitor-surface border border-monitor-border rounded-lg px-3 py-2 text-xs font-mono text-monitor-text focus:outline-none focus:border-monitor-accent"
                />
              </div>
            </div>

            <button
              onClick={handleStart}
              disabled={loading || runningTest?.status === 'RUNNING'}
              className="w-full mt-6 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-monitor-accent text-white text-sm font-sans font-semibold hover:bg-monitor-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Play className="w-5 h-5" />
              {loading ? '启动中...' : '开始压测'}
            </button>
          </div>

          <div className="col-span-2 space-y-6">
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-sans text-monitor-text-muted">并发数</span>
                </div>
                <p className="text-2xl font-mono font-bold text-monitor-text">{config.concurrency}</p>
              </div>
              <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-sans text-monitor-text-muted">时长</span>
                </div>
                <p className="text-2xl font-mono font-bold text-monitor-text">{config.durationSeconds}s</p>
              </div>
              <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-sans text-monitor-text-muted">失败率</span>
                </div>
                <p className="text-2xl font-mono font-bold text-monitor-text">{(config.failureRate * 100).toFixed(0)}%</p>
              </div>
              <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-4 h-4 text-green-400" />
                  <span className="text-xs font-sans text-monitor-text-muted">延迟</span>
                </div>
                <p className="text-2xl font-mono font-bold text-monitor-text">{config.networkDelayMs}ms</p>
              </div>
            </div>

            <div className="bg-monitor-card border border-monitor-border rounded-xl p-6">
              <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4 text-monitor-accent" />
                压测模式说明
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-purple-500/5 border border-purple-500/20">
                  <h4 className="text-xs font-sans font-semibold text-purple-400 mb-2">TCC 模式</h4>
                  <p className="text-[10px] font-sans text-monitor-text-muted leading-relaxed">
                    Try-Confirm-Cancel 三阶段提交，适用于需要强一致性的业务场景，资源锁定时间短，并发性能好。
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <h4 className="text-xs font-sans font-semibold text-blue-400 mb-2">SAGA 模式</h4>
                  <p className="text-[10px] font-sans text-monitor-text-muted leading-relaxed">
                    长事务解决方案，通过正向操作和反向补偿实现最终一致性，适用于长周期、多服务的业务流程。
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-green-500/5 border border-green-500/20">
                  <h4 className="text-xs font-sans font-semibold text-green-400 mb-2">AT 模式</h4>
                  <p className="text-[10px] font-sans text-monitor-text-muted leading-relaxed">
                    自动事务模式，通过代理数据源自动生成反向SQL，业务无侵入，开发效率高，适用大多数场景。
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-monitor-card border border-monitor-border rounded-xl p-6">
              <h3 className="text-sm font-sans font-semibold text-monitor-text mb-4 flex items-center gap-2">
                <Gauge className="w-4 h-4 text-monitor-accent" />
                预计指标参考
              </h3>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <p className="text-[10px] font-sans text-monitor-text-muted mb-1">预计峰值 TPS</p>
                  <p className="text-xl font-mono font-bold text-monitor-accent">
                    {Math.round(config.concurrency * (1000 / Math.max(config.networkDelayMs, 50)))}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-sans text-monitor-text-muted mb-1">预计请求总量</p>
                  <p className="text-xl font-mono font-bold text-monitor-text">
                    {config.concurrency * config.durationSeconds * 2}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-sans text-monitor-text-muted mb-1">预计成功率</p>
                  <p className="text-xl font-mono font-bold text-green-400">
                    {((1 - config.failureRate) * 100).toFixed(0)}%
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-sans text-monitor-text-muted mb-1">预计平均 RT</p>
                  <p className="text-xl font-mono font-bold text-blue-400">
                    {config.networkDelayMs + 50}ms
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="space-y-6">
          {tests.length === 0 ? (
            <div className="bg-monitor-card border border-monitor-border rounded-xl h-64 flex items-center justify-center">
              <div className="text-center">
                <Gauge className="w-12 h-12 text-monitor-text-muted mx-auto mb-3 opacity-30" />
                <p className="text-monitor-text-muted text-sm font-sans">暂无压测记录</p>
                <p className="text-monitor-text-muted text-xs font-sans mt-1">配置参数后开始第一次压测</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-6">
              <div className="col-span-1 space-y-3">
                {tests.map((test) => (
                  <div
                    key={test.testId}
                    onClick={() => setSelectedTest(test)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTest?.testId === test.testId
                        ? 'bg-monitor-accent/10 border-monitor-accent'
                        : 'bg-monitor-card border-monitor-border hover:border-monitor-accent/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${modeColor(test.config.mode)}`}>
                        {test.config.mode}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${statusColor(test.status)}`}>
                        {statusLabel(test.status)}
                      </span>
                    </div>
                    <p className="text-xs font-mono text-monitor-text mb-1">{test.testId}</p>
                    <p className="text-[10px] font-sans text-monitor-text-muted">
                      并发 {test.config.concurrency} · {test.config.durationSeconds}s
                    </p>
                    {test.summary && (
                      <p className="text-[10px] font-mono text-monitor-text-dim mt-2">
                        TPS: {Math.round(test.summary.tps)} · 成功率: {test.summary.totalRequests > 0
                          ? ((test.summary.successCount / test.summary.totalRequests) * 100).toFixed(1)
                          : 0}%
                      </p>
                    )}
                  </div>
                ))}
              </div>

              <div className="col-span-3 space-y-6">
                {selectedTest ? (
                  <>
                    <div className="grid grid-cols-6 gap-4">
                      <div className="bg-monitor-card border border-monitor-border rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <TrendingUp className="w-3.5 h-3.5 text-monitor-accent" />
                          <span className="text-[10px] font-sans text-monitor-text-muted">峰值 TPS</span>
                        </div>
                        <p className="text-xl font-mono font-bold text-monitor-accent">
                          {selectedTest.summary ? Math.round(selectedTest.summary.tps) : '-'}
                        </p>
                      </div>
                      <div className="bg-monitor-card border border-monitor-border rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <Activity className="w-3.5 h-3.5 text-blue-400" />
                          <span className="text-[10px] font-sans text-monitor-text-muted">请求总数</span>
                        </div>
                        <p className="text-xl font-mono font-bold text-monitor-text">
                          {selectedTest.summary?.totalRequests || '-'}
                        </p>
                      </div>
                      <div className="bg-monitor-card border border-monitor-border rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                          <span className="text-[10px] font-sans text-monitor-text-muted">成功</span>
                        </div>
                        <p className="text-xl font-mono font-bold text-green-400">
                          {selectedTest.summary?.successCount || '-'}
                        </p>
                      </div>
                      <div className="bg-monitor-card border border-monitor-border rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <XCircle className="w-3.5 h-3.5 text-red-400" />
                          <span className="text-[10px] font-sans text-monitor-text-muted">失败</span>
                        </div>
                        <p className="text-xl font-mono font-bold text-red-400">
                          {selectedTest.summary?.failureCount || '-'}
                        </p>
                      </div>
                      <div className="bg-monitor-card border border-monitor-border rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <RefreshCw className="w-3.5 h-3.5 text-amber-400" />
                          <span className="text-[10px] font-sans text-monitor-text-muted">回滚</span>
                        </div>
                        <p className="text-xl font-mono font-bold text-amber-400">
                          {selectedTest.summary?.rollbackCount || '-'}
                        </p>
                      </div>
                      <div className="bg-monitor-card border border-monitor-border rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <Gauge className="w-3.5 h-3.5 text-purple-400" />
                          <span className="text-[10px] font-sans text-monitor-text-muted">成功率</span>
                        </div>
                        <p className="text-xl font-mono font-bold text-purple-400">{successRate}%</p>
                      </div>
                    </div>

                    {chartData.length > 0 && (
                      <>
                        <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                          <h4 className="text-xs font-sans font-semibold text-monitor-text mb-4">TPS 趋势</h4>
                          <ResponsiveContainer width="100%" height={200}>
                            <AreaChart data={chartData}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                              <XAxis dataKey="time" stroke="#666" fontSize={10} tickLine={false} axisLine={false} />
                              <YAxis stroke="#666" fontSize={10} tickLine={false} axisLine={false} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: '8px', fontSize: '10px' }}
                              />
                              <Area type="monotone" dataKey="tps" stroke="#10b981" fill="#10b98133" strokeWidth={2} name="TPS" />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>

                        <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                          <h4 className="text-xs font-sans font-semibold text-monitor-text mb-4">响应时间趋势 (ms)</h4>
                          <ResponsiveContainer width="100%" height={200}>
                            <LineChart data={chartData}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                              <XAxis dataKey="time" stroke="#666" fontSize={10} tickLine={false} axisLine={false} />
                              <YAxis stroke="#666" fontSize={10} tickLine={false} axisLine={false} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: '8px', fontSize: '10px' }}
                              />
                              <Legend wrapperStyle={{ fontSize: '10px' }} />
                              <Line type="monotone" dataKey="avgRt" stroke="#3b82f6" strokeWidth={2} dot={false} name="平均 RT" />
                              <Line type="monotone" dataKey="p95" stroke="#f59e0b" strokeWidth={2} dot={false} name="P95" />
                              <Line type="monotone" dataKey="p99" stroke="#ef4444" strokeWidth={2} dot={false} name="P99" />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>

                        <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                          <h4 className="text-xs font-sans font-semibold text-monitor-text mb-4">成功/失败统计</h4>
                          <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={chartData}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                              <XAxis dataKey="time" stroke="#666" fontSize={10} tickLine={false} axisLine={false} />
                              <YAxis stroke="#666" fontSize={10} tickLine={false} axisLine={false} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: '8px', fontSize: '10px' }}
                              />
                              <Legend wrapperStyle={{ fontSize: '10px' }} />
                              <Bar dataKey="success" fill="#10b981" name="成功" stackId="a" />
                              <Bar dataKey="failure" fill="#ef4444" name="失败" stackId="a" />
                              <Bar dataKey="rollback" fill="#f59e0b" name="回滚" stackId="b" />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>

                        {selectedTest.summary && (
                          <div className="bg-monitor-card border border-monitor-border rounded-xl p-5">
                            <h4 className="text-xs font-sans font-semibold text-monitor-text mb-4">详细指标</h4>
                            <div className="grid grid-cols-4 gap-6">
                              <div>
                                <p className="text-[10px] font-sans text-monitor-text-muted mb-2">平均响应时间</p>
                                <p className="text-2xl font-mono font-bold text-blue-400">
                                  {Math.round(selectedTest.summary.avgResponseTimeMs)}ms
                                </p>
                              </div>
                              <div>
                                <p className="text-[10px] font-sans text-monitor-text-muted mb-2">P95 响应时间</p>
                                <p className="text-2xl font-mono font-bold text-amber-400">
                                  {Math.round(selectedTest.summary.p95ResponseTimeMs)}ms
                                </p>
                              </div>
                              <div>
                                <p className="text-[10px] font-sans text-monitor-text-muted mb-2">P99 响应时间</p>
                                <p className="text-2xl font-mono font-bold text-red-400">
                                  {Math.round(selectedTest.summary.p99ResponseTimeMs)}ms
                                </p>
                              </div>
                              <div>
                                <p className="text-[10px] font-sans text-monitor-text-muted mb-2">超时次数</p>
                                <p className="text-2xl font-mono font-bold text-monitor-text">
                                  {selectedTest.summary.timeoutCount}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </>
                ) : (
                  <div className="bg-monitor-card border border-monitor-border rounded-xl h-96 flex items-center justify-center">
                    <div className="text-center">
                      <BarChart3 className="w-12 h-12 text-monitor-text-muted mx-auto mb-3 opacity-30" />
                      <p className="text-monitor-text-muted text-sm font-sans">选择一个压测记录查看详情</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
