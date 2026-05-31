import { useState, useEffect } from 'react';
import {
  Heart,
  Shield,
  Clock,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
  Zap,
  RefreshCw,
} from 'lucide-react';
import { useRepoStore } from '@/stores/repoStore';
import { api } from '@/utils/api';
import type {
  ProjectHealthResponse,
  UsageAnalysisResponse,
  DependencyUsageResponse,
  AutoUpgradeResponse,
  AutoUpgradeExecutionResponse,
} from '@/types';

const HealthGradeBadge = ({ grade }: { grade: string }) => {
  const getColor = () => {
    if (grade.startsWith('A')) return 'bg-green-500';
    if (grade.startsWith('B')) return 'bg-blue-500';
    if (grade.startsWith('C')) return 'bg-yellow-500';
    if (grade === 'D') return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-white font-bold ${getColor()}`}>
      {grade}
    </span>
  );
};

const ScoreBar = ({
  label,
  score,
  icon: Icon,
  color,
}: {
  label: string;
  score: number;
  icon: any;
  color: string;
}) => (
  <div className="space-y-1">
    <div className="flex items-center justify-between text-sm">
      <span className="flex items-center gap-1.5 text-gray-600">
        <Icon className="w-4 h-4" />
        {label}
      </span>
      <span className="font-semibold">{Math.round(score)}</span>
    </div>
    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
      />
    </div>
  </div>
);

const DependencyHealthItem = ({
  dep,
}: {
  dep: ProjectHealthResponse['dependencies'][0];
}) => {
  const [expanded, setExpanded] = useState(false);

  const getStatusColor = () => {
    if (dep.healthScore.overallScore >= 80) return 'border-green-300 bg-green-50';
    if (dep.healthScore.overallScore >= 60) return 'border-yellow-300 bg-yellow-50';
    return 'border-red-300 bg-red-50';
  };

  return (
    <div className={`border rounded-lg overflow-hidden ${getStatusColor()}`}>
      <div
        className="p-4 cursor-pointer flex items-center justify-between"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm font-medium">
              {dep.dependency.groupId}:{dep.dependency.artifactId}
            </span>
            <span className="text-xs text-gray-500">v{dep.dependency.version}</span>
            <HealthGradeBadge grade={dep.healthScore.grade} />
          </div>
          <div className="mt-1 text-xs text-gray-500">
            综合评分: <span className="font-semibold">{Math.round(dep.healthScore.overallScore)}</span>
          </div>
        </div>
        <div className="text-gray-400">
          <svg
            className={`w-5 h-5 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-200 pt-4 bg-white">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <ScoreBar label="安全" score={dep.healthScore.vulnerabilityScore} icon={Shield} color="bg-green-500" />
            <ScoreBar label="新鲜度" score={dep.healthScore.freshnessScore} icon={Clock} color="bg-blue-500" />
            <ScoreBar label="流行度" score={dep.healthScore.popularityScore} icon={TrendingUp} color="bg-purple-500" />
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <h5 className="text-sm font-medium text-gray-700 mb-2">建议</h5>
            <ul className="text-sm space-y-1">
              {dep.healthScore.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-600">
                  <span className="text-blue-500 mt-0.5">•</span>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

const UsageAnalysisSection = ({ repoId }: { repoId: number }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UsageAnalysisResponse | null>(null);

  const analyze = async () => {
    setLoading(true);
    try {
      const data = await api.usage.analyze(repoId);
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  if (!result) {
    return (
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
        <Trash2 className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-700 mb-2">依赖使用分析</h3>
        <p className="text-sm text-gray-500 mb-4">
          检测项目中未使用的依赖，帮助清理冗余代码，减小构建体积
        </p>
        <button
          onClick={analyze}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 mx-auto"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          {loading ? '分析中...' : '开始分析'}
        </button>
      </div>
    );
  }

  const unusedDeps = result.unusedDependencies;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">使用分析结果</h3>
        <button
          onClick={analyze}
          disabled={loading}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          重新分析
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-green-50 rounded-lg p-4 text-center">
          <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
          <div className="text-2xl font-bold text-green-700">{result.usedCount}</div>
          <div className="text-sm text-green-600">已使用</div>
        </div>
        <div className="bg-red-50 rounded-lg p-4 text-center">
          <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <div className="text-2xl font-bold text-red-700">{result.unusedCount}</div>
          <div className="text-sm text-red-600">未使用</div>
        </div>
        <div className="bg-yellow-50 rounded-lg p-4 text-center">
          <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
          <div className="text-2xl font-bold text-yellow-700">{result.unclearCount}</div>
          <div className="text-sm text-yellow-600">不确定</div>
        </div>
      </div>

      {unusedDeps.length > 0 && (
        <div className="bg-red-50 rounded-lg p-4">
          <h4 className="font-medium text-red-800 mb-3 flex items-center gap-2">
            <Trash2 className="w-4 h-4" />
            建议移除的依赖 ({unusedDeps.length})
          </h4>
          <div className="space-y-2">
            {unusedDeps.map((dep, i) => (
              <div key={i} className="bg-white rounded-lg p-3 border border-red-200">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-mono text-sm">{dep.groupId}:{dep.artifactId}</span>
                    <span className="text-xs text-gray-500 ml-2">v{dep.version}</span>
                  </div>
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                    使用率 {Math.round(dep.usageConfidence)}%
                  </span>
                </div>
                {dep.usageEvidence.length > 0 && (
                  <div className="mt-2 text-xs text-gray-500">
                    {dep.usageEvidence.map((e, j) => (
                      <div key={j}>• {e}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const AutoUpgradeSection = ({ repoId }: { repoId: number }) => {
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [candidates, setCandidates] = useState<AutoUpgradeResponse | null>(null);
  const [executionResult, setExecutionResult] = useState<AutoUpgradeExecutionResponse | null>(null);

  const loadCandidates = async () => {
    setLoading(true);
    try {
      const data = await api.autoUpgrade.getCandidates(repoId);
      setCandidates(data);
    } finally {
      setLoading(false);
    }
  };

  const executeAutoUpgrade = async () => {
    setExecuting(true);
    try {
      const result = await api.autoUpgrade.execute(repoId, 'current-user');
      setExecutionResult(result);
    } finally {
      setExecuting(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!candidates) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">自动升级</h3>
          <p className="text-sm text-gray-500 mt-1">
            高兼容性、低风险的依赖将被自动升级
          </p>
        </div>
        <button
          onClick={executeAutoUpgrade}
          disabled={executing || candidates.autoUpgradeCandidates.length === 0}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
        >
          {executing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          {executing ? '升级中...' : '执行自动升级'}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <span className="font-medium text-green-800">可自动升级</span>
          </div>
          <div className="text-3xl font-bold text-green-700">
            {candidates.autoUpgradeCandidates.length}
          </div>
          <div className="text-xs text-green-600 mt-1">
            PATCH: {candidates.summary.patchUpgrades} | MINOR: {candidates.summary.minorUpgrades}
          </div>
        </div>
        <div className="bg-yellow-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <span className="font-medium text-yellow-800">需人工审核</span>
          </div>
          <div className="text-3xl font-bold text-yellow-700">
            {candidates.manualReviewRequired.length}
          </div>
          <div className="text-xs text-yellow-600 mt-1">
            MAJOR: {candidates.summary.majorUpgrades} | 高风险: {candidates.summary.highRiskCount}
          </div>
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-700 mb-3">自动升级规则</h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
            最低兼容性分数: {candidates.summary.minCompatibilityThreshold}
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
            平均兼容性: {Math.round(candidates.summary.averageCompatibilityScore)}
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
            允许类型: {candidates.summary.allowedUpgradeTypes.join(', ')}
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
            允许风险: {candidates.summary.allowedRiskLevels.join(', ')}
          </div>
        </div>
      </div>

      {executionResult && (
        <div className={`rounded-lg p-4 ${executionResult.successCount > 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <h4 className="font-medium mb-3">执行结果</h4>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div className="text-center">
              <div className="text-xl font-bold text-green-600">{executionResult.successCount}</div>
              <div className="text-xs text-gray-500">成功</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-red-600">{executionResult.failureCount}</div>
              <div className="text-xs text-gray-500">失败</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-yellow-600">{executionResult.skippedCount}</div>
              <div className="text-xs text-gray-500">跳过</div>
            </div>
          </div>
          {executionResult.prUrl && (
            <div className="bg-white rounded p-3 border">
              <span className="text-sm">PR 已创建: </span>
              <a href={executionResult.prUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 text-sm underline">
                {executionResult.prUrl}
              </a>
            </div>
          )}
        </div>
      )}

      {candidates.autoUpgradeCandidates.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-3">待自动升级列表</h4>
          <div className="space-y-2">
            {candidates.autoUpgradeCandidates.map((dep, i) => (
              <div key={i} className="bg-white rounded-lg p-3 border flex items-center justify-between">
                <div>
                  <span className="font-mono text-sm">{dep.groupId}:{dep.artifactId}</span>
                  <div className="text-xs text-gray-500 mt-1">
                    {dep.currentVersion} → {dep.targetVersion}
                    <span className="ml-2 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                      {dep.upgradeType}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    兼容: {Math.round(dep.compatibilityScore || 0)}%
                  </span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    dep.riskLevel === 'SAFE' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {dep.riskLevel}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default function Health() {
  const { currentRepoId } = useRepoStore();
  const [loading, setLoading] = useState(false);
  const [healthData, setHealthData] = useState<ProjectHealthResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'usage' | 'autoupgrade'>('overview');

  useEffect(() => {
    if (currentRepoId) {
      loadHealthData();
    }
  }, [currentRepoId]);

  const loadHealthData = async () => {
    if (!currentRepoId) return;
    setLoading(true);
    try {
      const data = await api.health.getProjectHealth(currentRepoId);
      setHealthData(data);
    } finally {
      setLoading(false);
    }
  };

  if (!currentRepoId) {
    return (
      <div className="text-center py-16 text-gray-500">
        <Heart className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <p className="text-lg">请先选择一个仓库</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!healthData) return null;

  const tabs = [
    { key: 'overview' as const, label: '健康评分', icon: Heart },
    { key: 'usage' as const, label: '使用分析', icon: Trash2 },
    { key: 'autoupgrade' as const, label: '自动升级', icon: Zap },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">依赖健康管理</h1>
          <p className="text-gray-500 mt-1">综合评估项目依赖的健康状态</p>
        </div>
        <button
          onClick={loadHealthData}
          className="text-blue-600 hover:text-blue-800 flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-blue-100 mb-1">项目健康评分</p>
            <div className="flex items-baseline gap-4">
              <span className="text-5xl font-bold">{Math.round(healthData.overallScore)}</span>
              <HealthGradeBadge grade={healthData.grade} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-3xl font-bold">{healthData.healthyCount}</div>
              <div className="text-blue-100 text-sm">健康</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{healthData.warningCount}</div>
              <div className="text-blue-100 text-sm">警告</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{healthData.criticalCount}</div>
              <div className="text-blue-100 text-sm">危险</div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm">
        <div className="grid grid-cols-3 gap-6">
          <ScoreBar label="安全评分" score={healthData.averageVulnerabilityScore} icon={Shield} color="bg-green-500" />
          <ScoreBar label="新鲜度评分" score={healthData.averageFreshnessScore} icon={Clock} color="bg-blue-500" />
          <ScoreBar label="流行度评分" score={healthData.averagePopularityScore} icon={TrendingUp} color="bg-purple-500" />
        </div>
      </div>

      <div className="border-b border-gray-200">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="pt-2">
        {activeTab === 'overview' && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">依赖健康详情</h3>
            {healthData.dependencies
              .filter((d) => d.healthScore.overallScore < 80)
              .sort((a, b) => a.healthScore.overallScore - b.healthScore.overallScore)
              .map((dep, i) => (
                <DependencyHealthItem key={i} dep={dep} />
              ))}
            {healthData.dependencies.filter((d) => d.healthScore.overallScore < 80).length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-500" />
                <p>所有依赖健康状态良好！</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'usage' && <UsageAnalysisSection repoId={currentRepoId} />}

        {activeTab === 'autoupgrade' && <AutoUpgradeSection repoId={currentRepoId} />}
      </div>
    </div>
  );
}
