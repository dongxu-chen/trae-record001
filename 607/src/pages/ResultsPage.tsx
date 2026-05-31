import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Histogram,
} from 'recharts';
import {
  ArrowLeft,
  Download,
  Target,
  TrendingUp,
  CheckCircle,
  AlertTriangle,
  BarChart3,
  Shield,
  Users,
  RefreshCw,
  Sparkles,
  Activity,
  Zap,
  GitBranch,
  AlertCircle,
  FileText,
  Loader2,
} from 'lucide-react';
import { useDataStore } from '../store/useDataStore';
import CausalGraph from '../components/CausalGraph';
import { generateReport } from '../services/api';

function formatNumber(num: number, decimals = 4) {
  if (num === null || num === undefined || isNaN(num)) return 'N/A';
  return Number(num).toFixed(decimals);
}

function getPValueColor(pValue: number) {
  if (pValue === null || pValue === undefined) return 'text-gray-500';
  if (pValue < 0.01) return 'text-green-600';
  if (pValue < 0.05) return 'text-green-500';
  if (pValue < 0.1) return 'text-amber-500';
  return 'text-red-500';
}

function getPValueLabel(pValue: number) {
  if (pValue === null || pValue === undefined) return 'N/A';
  if (pValue < 0.01) return '*** (p<0.01)';
  if (pValue < 0.05) return '** (p<0.05)';
  if (pValue < 0.1) return '* (p<0.10)';
  return '不显著';
}

export default function ResultsPage() {
  const navigate = useNavigate();
  const { result, method, treatment, outcome, covariates, error, resetData } = useDataStore();
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  const handleGenerateReport = async () => {
    if (!result) return;
    
    setGeneratingReport(true);
    setReportError(null);
    
    try {
      const response = await generateReport(
        result,
        method,
        treatment,
        outcome,
        covariates,
        result.sampleSize,
        'html'
      );
      
      const blob = new Blob([response.content], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = response.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setReportError(err instanceof Error ? err.message : '生成报告失败');
    } finally {
      setGeneratingReport(false);
    }
  };

  if (!result) {
    return (
      <div className="min-h-screen bg-grid-pattern">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto text-center">
            <div className="card">
              <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-800 mb-2">暂无分析结果</h3>
              <p className="text-gray-600 mb-4">请先配置变量并运行因果推断分析</p>
              <button onClick={() => navigate('/configure')} className="btn-primary">
                前往配置变量
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isPSM = method === 'psm';
  const hasLassoSelection = result.lassoSelection;
  const hasParallelTrendTests = result.parallelTrendTests;
  const hasEnhancedPlacebo = result.robustnessTests?.enhancedPlacebo;
  const hasCausalGraph = result.causal_graph && result.causal_graph.nodes;
  const hasSensitivityAnalysis = result.sensitivity_analysis;
  const hasEValue = result.robustnessTests?.sensitivityAnalysis?.e_value;
  const hasRosenbaum = result.robustnessTests?.sensitivityAnalysis?.rosenbaum;

  const propensityData = result.propensityScores ? [
    ...result.propensityScores.treated.slice(0, 200).map((s) => ({
      score: s,
      group: '处理组',
    })),
    ...result.propensityScores.control.slice(0, 200).map((s) => ({
      score: s,
      group: '对照组',
    })),
  ] : [];

  const balanceData = result.balanceCheck
    ? Object.entries(result.balanceCheck.before).map(([cov, val]) => ({
        covariate: cov,
        before: Math.abs(val.stdDiff),
        after: Math.abs(result.balanceCheck!.after[cov]?.stdDiff || 0),
      }))
    : [];

  const parallelTrendData = result.parallelTrend
    ? result.parallelTrend.timePoints.map((t, i) => ({
        time: t,
        处理组: result.parallelTrend!.treatedMeans[i],
        对照组: result.parallelTrend!.controlMeans[i],
      }))
    : [];

  const robustnessData = result.robustnessTests.differentMethods?.map((m) => ({
    method: m.method,
    estimate: m.estimate,
    lower: m.estimate - 1.96 * m.stdError,
    upper: m.estimate + 1.96 * m.stdError,
  })) || [];

  const lassoImportanceData = hasLassoSelection
    ? result.lassoSelection!.covariate_importance.slice(0, 10).map((item: any) => ({
        covariate: item.covariate,
        importance: item.combined_importance * 100,
      }))
    : [];

  const placeboDistributionData = hasEnhancedPlacebo && result.robustnessTests?.enhancedPlacebo?.combined
    ? result.robustnessTests.enhancedPlacebo.combined.all_effects?.slice(0, 100).map((e: number) => ({
        effect: e,
      })) || []
    : [];

  const rosenbaumData = hasRosenbaum
    ? result.robustnessTests.sensitivityAnalysis.rosenbaum.bounds.map((b: any) => ({
        gamma: `Γ=${b.gamma}`,
        pValueUpper: b.p_value_upper,
        pValueLower: b.p_value_lower,
        significant: b.significant_upper,
      }))
    : [];

  const omvScenarioData = hasSensitivityAnalysis && result.sensitivity_analysis.omitted_variable_scenarios
    ? result.sensitivity_analysis.omitted_variable_scenarios.map((s: any) => ({
        correlation: `r=${s.assumed_correlation_with_outcome}`,
        adjustedEstimate: s.adjusted_estimate,
        biasMagnitude: s.bias_magnitude,
        stillSignificant: s.still_significant,
      }))
    : [];

  const getRobustnessColor = (level: string) => {
    switch (level) {
      case 'high': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-amber-600 bg-amber-100';
      case 'low': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getRobustnessLabel = (level: string) => {
    switch (level) {
      case 'high': return '高稳健性';
      case 'medium': return '中稳健性';
      case 'low': return '低稳健性';
      default: return '待评估';
    }
  };

  return (
    <div className="min-h-screen bg-grid-pattern">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="font-display text-3xl font-semibold text-primary-800 mb-2">
              分析结果
            </h2>
            <p className="text-gray-600">
              {isPSM ? '倾向性匹配 (PSM)' : '双重差分 (DID)'} 分析 - 
              处理变量: <span className="font-medium text-primary-600">{treatment}</span> - 
              结果变量: <span className="font-medium text-primary-600">{outcome}</span>
              {hasLassoSelection && (
                <span className="ml-2 text-accent-600">
                  <Sparkles className="w-4 h-4 inline mr-1" />
                  LASSO自动筛选
                </span>
              )}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleGenerateReport}
              disabled={generatingReport}
              className="btn-primary flex items-center gap-2 bg-gradient-to-r from-primary-600 to-primary-800"
            >
              {generatingReport ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              {generatingReport ? '生成中...' : '生成报告'}
            </button>
            <button
              onClick={() => navigate('/configure')}
              className="btn-secondary flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              重新配置
            </button>
            <button
              onClick={() => {
                resetData();
                navigate('/');
              }}
              className="btn-primary flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              新分析
            </button>
          </div>
        </div>

        {reportError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-700 font-medium">报告生成失败</p>
              <p className="text-red-600 text-sm">{reportError}</p>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-700 font-medium">分析出错</p>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-5 h-5 opacity-80" />
              <span className="text-sm opacity-80">ATE (平均处理效应)</span>
            </div>
            <p className="text-3xl font-semibold font-display mb-1">
              {formatNumber(result.ate.estimate)}
            </p>
            <div className="flex items-center justify-between text-xs">
              <span>p值: <span className={getPValueColor(result.ate.pValue)}>{formatNumber(result.ate.pValue, 3)}</span></span>
              <span>[{formatNumber(result.ate.confidenceInterval[0])}, {formatNumber(result.ate.confidenceInterval[1])}]</span>
            </div>
          </div>

          <div className="stat-card-accent">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 opacity-80" />
              <span className="text-sm opacity-80">ATT (处理组平均效应)</span>
            </div>
            <p className="text-3xl font-semibold font-display mb-1">
              {formatNumber(result.att.estimate)}
            </p>
            <div className="flex items-center justify-between text-xs">
              <span>p值: <span className={getPValueColor(result.att.pValue)}>{formatNumber(result.att.pValue, 3)}</span></span>
              <span>[{formatNumber(result.att.confidenceInterval[0])}, {formatNumber(result.att.confidenceInterval[1])}]</span>
            </div>
          </div>

          <div className="bg-gradient-to-br from-data-teal to-data-blue text-white rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Users className="w-5 h-5 opacity-80" />
              <span className="text-sm opacity-80">样本量</span>
            </div>
            <p className="text-3xl font-semibold font-display mb-1">
              {result.sampleSize?.total?.toLocaleString() || '-'}
            </p>
            <div className="flex items-center justify-between text-xs">
              <span>处理组: {result.sampleSize?.treated?.toLocaleString() || '-'}</span>
              <span>对照组: {result.sampleSize?.control?.toLocaleString() || '-'}</span>
            </div>
          </div>

          <div className="bg-gradient-to-br from-data-purple to-data-orange text-white rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="w-5 h-5 opacity-80" />
              <span className="text-sm opacity-80">统计显著性</span>
            </div>
            <p className="text-3xl font-semibold font-display mb-1">
              {result.ate.pValue < 0.05 ? '显著' : '不显著'}
            </p>
            <div className="text-xs">
              {getPValueLabel(result.ate.pValue)}
            </div>
          </div>
        </div>

        {hasLassoSelection && (
          <div className="card mb-8">
            <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-accent-500" />
              LASSO自动协变量筛选结果
              <span className="text-sm font-normal text-gray-500 ml-2">
                (方法: {result.lassoSelection!.method_used === 'double_lasso' ? '双重LASSO' : 
                        result.lassoSelection!.method_used === 'treatment' ? '处理预测' :
                        result.lassoSelection!.method_used === 'outcome' ? '结果预测' : '扰动稳定'})
              </span>
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-gray-600 mb-3">最终选择的协变量 ({result.lassoSelection!.selected_covariates.length}个):</p>
                <div className="flex flex-wrap gap-2">
                  {result.lassoSelection!.selected_covariates.map((cov: string) => (
                    <span key={cov} className="px-3 py-1 bg-accent-100 text-accent-700 rounded-full text-sm">
                      {cov}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-3">协变量重要性 (Top 10):</p>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={lassoImportanceData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="covariate" width={80} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="importance" fill="#d4a855" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {hasCausalGraph && (
          <div className="card mb-8">
            <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-primary-500" />
              因果图分析
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <CausalGraph
                  nodes={result.causal_graph.nodes}
                  edges={result.causal_graph.edges}
                  width={600}
                  height={320}
                />
              </div>
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-700 mb-2">网络统计</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">节点数量</span>
                      <span className="font-mono font-medium">{result.causal_graph.nodes.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">边数量</span>
                      <span className="font-mono font-medium">{result.causal_graph.edges.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">后门路径</span>
                      <span className="font-mono font-medium">{result.causal_graph.backdoor_paths?.backdoor_path_count || 0}</span>
                    </div>
                  </div>
                </div>
                {result.causal_graph.backdoor_paths?.backdoor_paths?.length > 0 && (
                  <div className="p-4 bg-amber-50 rounded-lg">
                    <p className="text-sm font-medium text-amber-700 mb-2">识别的后门路径</p>
                    <div className="space-y-1 text-xs">
                      {result.causal_graph.backdoor_paths.backdoor_paths.slice(0, 3).map((path: string[], i: number) => (
                        <div key={i} className="text-amber-600 font-mono">
                          {path.join(' → ')}
                        </div>
                      ))}
                    </div>
                    {result.causal_graph.backdoor_paths.suggested_adjustment?.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-amber-200">
                        <p className="text-xs text-amber-600">建议控制变量:</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {result.causal_graph.backdoor_paths.suggested_adjustment.map((v: string) => (
                            <span key={v} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">
                              {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm font-medium text-blue-700 mb-2">因果解释</p>
                  <p className="text-xs text-blue-600">
                    基于PC算法学习的变量关系网络。绿色箭头表示因果路径，橙色箭头表示混淆路径，虚线表示相关关系。
                    建议结合领域知识解释图中关系。
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {isPSM && result.propensityScores && (
            <div className="card">
              <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary-500" />
                倾向得分分布
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="score" name="倾向得分" domain={[0, 1]} />
                  <YAxis type="category" dataKey="group" name="组别" />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter name="得分" data={propensityData}>
                    {propensityData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.group === '处理组' ? '#d4a855' : '#1e3a5f'}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}

          {isPSM && result.balanceCheck && (
            <div className="card">
              <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-accent-500" />
                平衡性检验 (标准化均值差异)
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={balanceData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 'auto']} />
                  <YAxis type="category" dataKey="covariate" width={80} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="before" name="匹配前" fill="#1e3a5f" />
                  <Bar dataKey="after" name="匹配后" fill="#d4a855" />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-xs text-gray-500 mt-2">
                匹配后标准化均值差异应小于0.1，表示协变量平衡良好
              </p>
            </div>
          )}

          {!isPSM && result.parallelTrend && (
            <div className="card lg:col-span-2">
              <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary-500" />
                平行趋势检验
              </h3>
              {hasParallelTrendTests && result.parallelTrendTests?.statistical && (
                <div className="mb-4 p-4 rounded-lg bg-gray-50">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">F统计量</p>
                      <p className="text-xl font-semibold text-gray-800">
                        {formatNumber(result.parallelTrendTests.statistical.f_statistic, 3)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">p值</p>
                      <p className={`text-xl font-semibold ${result.parallelTrendTests.statistical.passed ? 'text-green-600' : 'text-red-600'}`}>
                        {formatNumber(result.parallelTrendTests.statistical.p_value, 4)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">检验结论</p>
                      <p className={`text-xl font-semibold ${result.parallelTrendTests.statistical.passed ? 'text-green-600' : 'text-red-600'}`}>
                        {result.parallelTrendTests.statistical.passed ? '✓ 通过' : '✗ 未通过'}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    {result.parallelTrendTests.statistical.note}
                  </p>
                </div>
              )}
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={parallelTrendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="处理组"
                    stroke="#d4a855"
                    strokeWidth={3}
                    dot={{ r: 5 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="对照组"
                    stroke="#1e3a5f"
                    strokeWidth={3}
                    dot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
              <p className="text-xs text-gray-500 mt-2">
                处理前两组趋势应保持平行，满足DID的平行趋势假设
              </p>
            </div>
          )}
        </div>

        <div className="card mb-8">
          <h3 className="font-semibold text-gray-800 mb-6 flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent-500" />
            稳健性检验
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {hasEnhancedPlacebo && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-accent-500" />
                  增强安慰剂检验
                </h4>
                {placeboDistributionData.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-2">安慰剂效应分布:</p>
                    <ResponsiveContainer width="100%" height={120}>
                      <BarChart data={placeboDistributionData.map(d => ({
                        ...d,
                        effect: Math.round(d.effect * 100) / 100,
                        count: 1,
                      }))}>
                        <XAxis dataKey="effect" tick={{ fontSize: 9 }} />
                        <YAxis tick={{ fontSize: 9 }} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#d4a855" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">真实效应:</span>
                    <span className="font-mono font-medium">{formatNumber(result.ate.estimate)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">安慰剂均值:</span>
                    <span className="font-mono">{formatNumber(result.robustnessTests.enhancedPlacebo.combined?.mean_effect || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">置换p值:</span>
                    <span className={`font-mono font-medium ${getPValueColor(result.robustnessTests.enhancedPlacebo.combined?.p_value || 1)}`}>
                      {formatNumber(result.robustnessTests.enhancedPlacebo.combined?.p_value || 1, 4)}
                    </span>
                  </div>
                </div>
                <div className="mt-3 p-2 rounded bg-white text-xs">
                  {result.robustnessTests.enhancedPlacebo.combined?.p_value > 0.05
                    ? '✓ 安慰剂效应不显著，结果稳健'
                    : '⚠ 安慰剂效应显著，需谨慎解释结果'}
                </div>
              </div>
            )}

            {result.robustnessTests.placeboTest && !hasEnhancedPlacebo && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <h4 className="font-medium text-gray-700 mb-3">安慰剂检验</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">虚拟处理效应:</span>
                    <span className="font-mono">{formatNumber(result.robustnessTests.placeboTest.estimate)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">p值:</span>
                    <span className={`font-mono ${getPValueColor(result.robustnessTests.placeboTest.pValue)}`}>
                      {formatNumber(result.robustnessTests.placeboTest.pValue, 3)}
                    </span>
                  </div>
                  <div className="mt-2 p-2 rounded bg-white">
                    <p className="text-xs text-gray-600">
                      {result.robustnessTests.placeboTest.pValue > 0.05
                        ? '✓ 安慰剂效应不显著，结果稳健'
                        : '⚠ 安慰剂效应显著，需谨慎解释结果'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {hasEValue && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-data-teal" />
                  E-value 分析
                </h4>
                <div className="text-center mb-3">
                  <p className="text-3xl font-bold text-primary-600 font-display">
                    {formatNumber(result.robustnessTests.sensitivityAnalysis.e_value.e_value, 2)}
                  </p>
                  <p className="text-xs text-gray-500">最小关联强度阈值</p>
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">风险比</span>
                    <span className="font-mono">{formatNumber(result.robustnessTests.sensitivityAnalysis.e_value.risk_ratio, 3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">CI下界E-value</span>
                    <span className="font-mono">{formatNumber(result.robustnessTests.sensitivityAnalysis.e_value.lower_ci_e_value, 2)}</span>
                  </div>
                </div>
                <div className="mt-2 p-2 rounded bg-white text-xs text-gray-600">
                  {result.robustnessTests.sensitivityAnalysis.e_value.interpretation}
                </div>
              </div>
            )}

            {hasRosenbaum && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-data-purple" />
                  Rosenbaum 界限
                </h4>
                <div className="text-center mb-3">
                  <p className="text-3xl font-bold text-accent-600 font-display">
                    Γ = {formatNumber(result.robustnessTests.sensitivityAnalysis.rosenbaum.critical_gamma, 2)}
                  </p>
                  <p className="text-xs text-gray-500">临界混杂强度</p>
                </div>
                <ResponsiveContainer width="100%" height={80}>
                  <BarChart data={rosenbaumData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="gamma" tick={{ fontSize: 8 }} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 8 }} />
                    <Tooltip />
                    <Bar dataKey="pValueUpper">
                      {rosenbaumData.map((entry: any, index: number) => (
                        <Cell key={index} fill={entry.significant ? '#10b981' : '#ef4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-2 p-2 rounded bg-white text-xs text-gray-600">
                  {result.robustnessTests.sensitivityAnalysis.rosenbaum.interpretation}
                </div>
              </div>
            )}

            {hasSensitivityAnalysis && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-data-teal" />
                  遗漏变量偏差模拟
                </h4>
                <ResponsiveContainer width="100%" height={100}>
                  <BarChart data={omvScenarioData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tick={{ fontSize: 8 }} />
                    <YAxis dataKey="correlation" type="category" tick={{ fontSize: 8 }} width={50} />
                    <Tooltip />
                    <Bar dataKey="adjustedEstimate">
                      {omvScenarioData.map((entry: any, index: number) => (
                        <Cell key={index} fill={entry.stillSignificant ? '#10b981' : '#ef4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-xs text-gray-500 mt-2">
                  绿色=效应仍显著, 红色=效应不再显著
                </p>
              </div>
            )}

            {hasSensitivityAnalysis && result.sensitivity_analysis.robustness_summary && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <h4 className="font-medium text-gray-700 mb-3">整体稳健性评估</h4>
                <div className="text-center">
                  <span className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${getRobustnessColor(result.sensitivity_analysis.robustness_summary.overall_robustness)}`}>
                    {getRobustnessLabel(result.sensitivity_analysis.robustness_summary.overall_robustness)}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className={`p-2 rounded text-center ${result.sensitivity_analysis.robustness_summary.e_value_gt_2 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {result.sensitivity_analysis.robustness_summary.e_value_gt_2 ? '✓' : '✗'} E-value {' > '} 2
                  </div>
                  <div className={`p-2 rounded text-center ${result.sensitivity_analysis.robustness_summary.critical_gamma_gt_1_5 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {result.sensitivity_analysis.robustness_summary.critical_gamma_gt_1_5 ? '✓' : '✗'} Γ {' > '} 1.5
                  </div>
                </div>
              </div>
            )}

            {result.robustnessTests.differentMethods && (
              <div className="p-4 bg-gray-50 rounded-xl">
                <h4 className="font-medium text-gray-700 mb-3">多方法比较</h4>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={robustnessData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="method" width={70} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="estimate" fill="#d4a855" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Download className="w-5 h-5 text-primary-500" />
            结果摘要
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left font-medium text-gray-600">指标</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">估计值</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">标准误</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">p值</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">95%置信区间</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">显著性</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 font-medium text-gray-700">ATE</td>
                  <td className="px-4 py-3 font-mono">{formatNumber(result.ate.estimate)}</td>
                  <td className="px-4 py-3 font-mono">{formatNumber(result.ate.stdError)}</td>
                  <td className={`px-4 py-3 font-mono ${getPValueColor(result.ate.pValue)}`}>
                    {formatNumber(result.ate.pValue, 4)}
                  </td>
                  <td className="px-4 py-3 font-mono">
                    [{formatNumber(result.ate.confidenceInterval[0])}, {formatNumber(result.ate.confidenceInterval[1])}]
                  </td>
                  <td className="px-4 py-3">{getPValueLabel(result.ate.pValue)}</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 font-medium text-gray-700">ATT</td>
                  <td className="px-4 py-3 font-mono">{formatNumber(result.att.estimate)}</td>
                  <td className="px-4 py-3 font-mono">{formatNumber(result.att.stdError)}</td>
                  <td className={`px-4 py-3 font-mono ${getPValueColor(result.att.pValue)}`}>
                    {formatNumber(result.att.pValue, 4)}
                  </td>
                  <td className="px-4 py-3 font-mono">
                    [{formatNumber(result.att.confidenceInterval[0])}, {formatNumber(result.att.confidenceInterval[1])}]
                  </td>
                  <td className="px-4 py-3">{getPValueLabel(result.att.pValue)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
