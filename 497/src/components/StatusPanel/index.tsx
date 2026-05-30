import { useState, useMemo } from 'react';
import {
  useCurrentData,
  useCurrentLevel,
  useDrillPath,
  useIsLoading,
  useCurrentRole,
  useShowPrediction,
  usePredictionData,
  useLinkRelatedCharts,
  useRelatedCharts,
  useDrillStore,
} from '@/hooks/useDrillStore';
import {
  calculateTotal,
  formatValue,
  getLevelName,
  pathToNames,
} from '@/utils/drillUtils';
import { hasNextLevel, ROLE_CONFIG, getDimensionName } from '@/data/mockData';
import {
  TrendingUp,
  Layers,
  MapPin,
  Database,
  ArrowDownCircle,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Share2,
  Link2,
  Shield,
  Users,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  Link,
  Link2Off,
  ChevronDown,
  BarChart3,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { StatusPanelSkeleton } from '@/components/Skeleton';
import { formatPredictionDisplay } from '@/utils/prediction';
import { UserRole } from '@/types/drill';

export default function StatusPanel() {
  const currentData = useCurrentData();
  const predictionData = usePredictionData();
  const showPrediction = useShowPrediction();
  const currentLevel = useCurrentLevel();
  const path = useDrillPath();
  const isLoading = useIsLoading();
  const currentRole = useCurrentRole();
  const linkRelatedCharts = useLinkRelatedCharts();
  const relatedCharts = useRelatedCharts();
  const { setCurrentRole, togglePrediction, toggleLinkRelatedCharts } =
    useDrillStore();

  const [searchParams] = useSearchParams();
  const [copied, setCopied] = useState(false);
  const [showRoleSelector, setShowRoleSelector] = useState(false);

  const totalValue = currentData ? calculateTotal(currentData.data) : 0;
  const maxValue = currentData
    ? Math.max(...currentData.data.map((d) => d.value))
    : 0;
  const avgValue = currentData
    ? Math.round(totalValue / currentData.data.length)
    : 0;
  const canDrillMore = currentData ? hasNextLevel(pathToNames(path)) : false;
  const shortCode = searchParams.get('s') || '';

  const hasSensitiveData = useMemo(() => {
    return currentData?.data.some((d) => d.isSensitive) || false;
  }, [currentData]);

  const predictionSummary = useMemo(() => {
    if (!predictionData) return null;
    const predictions = predictionData.data
      .map((d) => d.prediction)
      .filter((p): p is NonNullable<typeof p> => p !== undefined);

    if (predictions.length === 0) return null;

    const totalPrediction = predictions.reduce(
      (sum, p) => sum + p.predictedValue,
      0
    );
    const avgConfidence =
      predictions.reduce((sum, p) => sum + p.confidence, 0) /
      predictions.length;
    const upCount = predictions.filter((p) => p.trend === 'up').length;
    const downCount = predictions.filter((p) => p.trend === 'down').length;

    return {
      totalPrediction,
      avgConfidence,
      upCount,
      downCount,
      stableCount: predictions.length - upCount - downCount,
    };
  }, [predictionData]);

  const handleShare = async () => {
    const url = `${window.location.origin}${
      window.location.pathname
    }?${searchParams.toString()}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error('Failed to copy');
    }
  };

  const handleRoleChange = (role: UserRole) => {
    setCurrentRole(role);
    setShowRoleSelector(false);
  };

  const stats = [
    {
      label: '数据总计',
      value: formatValue(totalValue),
      icon: TrendingUp,
      color: 'from-cyan-500 to-blue-500',
      bgColor: 'bg-cyan-500/10',
      textColor: 'text-cyan-400',
    },
    {
      label: '数据项数',
      value: currentData?.data.length || 0,
      icon: Database,
      color: 'from-purple-500 to-pink-500',
      bgColor: 'bg-purple-500/10',
      textColor: 'text-purple-400',
    },
    {
      label: '最大值',
      value: formatValue(maxValue),
      icon: ArrowDownCircle,
      color: 'from-orange-500 to-red-500',
      bgColor: 'bg-orange-500/10',
      textColor: 'text-orange-400',
    },
    {
      label: '平均值',
      value: formatValue(avgValue),
      icon: Layers,
      color: 'from-green-500 to-emerald-500',
      bgColor: 'bg-green-500/10',
      textColor: 'text-green-400',
    },
  ];

  const roles = Object.values(ROLE_CONFIG);

  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-400" />;
      default:
        return <Minus className="w-4 h-4 text-yellow-400" />;
    }
  };

  if (isLoading) {
    return <StatusPanelSkeleton />;
  }

  return (
    <div className="space-y-5">
      <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <span className="w-1.5 h-6 bg-gradient-to-b from-purple-400 to-pink-500 rounded-full" />
          数据概览
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="bg-slate-900/40 rounded-xl p-4 hover:bg-slate-900/60 transition-all duration-200 group"
              >
                <div
                  className={`w-10 h-10 ${stat.bgColor} rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-200`}
                >
                  <Icon className={`w-5 h-5 ${stat.textColor}`} />
                </div>
                <div className="text-2xl font-bold text-white mb-1">
                  {stat.value}
                </div>
                <div className="text-xs text-slate-400">{stat.label}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <span className="w-1.5 h-6 bg-gradient-to-b from-orange-400 to-red-500 rounded-full" />
          钻取状态
        </h3>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5 text-cyan-400" />
              <span className="text-slate-300">当前区域</span>
            </div>
            <span className="text-white font-semibold">
              {currentData?.levelName || '全国'}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
            <div className="flex items-center gap-3">
              <Layers className="w-5 h-5 text-purple-400" />
              <span className="text-slate-300">数据层级</span>
            </div>
            <span className="text-white font-semibold">
              {getLevelName(currentLevel)}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
            <div className="flex items-center gap-3">
              {canDrillMore ? (
                <CheckCircle2 className="w-5 h-5 text-green-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-orange-400" />
              )}
              <span className="text-slate-300">可继续下钻</span>
            </div>
            <span
              className={`font-semibold ${
                canDrillMore ? 'text-green-400' : 'text-orange-400'
              }`}
            >
              {canDrillMore ? '是' : '否（已到最底层）'}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
            <div className="flex items-center gap-3">
              <Link2 className="w-5 h-5 text-blue-400" />
              <span className="text-slate-300">状态短码</span>
            </div>
            <span className="text-blue-400 font-mono text-sm bg-blue-500/10 px-2 py-1 rounded">
              {shortCode || '-'}
            </span>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <button
            onClick={handleShare}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl font-medium transition-all duration-200 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40"
          >
            <Share2 className="w-4 h-4" />
            {copied ? '已复制链接！' : '分享钻取链接'}
          </button>
          <p className="text-xs text-slate-500 text-center mt-2">
            短码格式:{' '}
            <code className="text-cyan-400">
              ?s={shortCode || 'xxx'}&l={currentLevel}
            </code>
          </p>
        </div>
      </div>

      <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <span className="w-1.5 h-6 bg-gradient-to-b from-amber-400 to-orange-500 rounded-full" />
          权限控制
        </h3>

        <div className="space-y-3">
          <div className="relative">
            <button
              onClick={() => setShowRoleSelector(!showRoleSelector)}
              className="w-full flex items-center justify-between p-3 bg-slate-900/40 hover:bg-slate-900/60 rounded-xl transition-colors"
            >
              <div className="flex items-center gap-3">
                <Users className="w-5 h-5 text-amber-400" />
                <div className="text-left">
                  <div className="text-slate-300 text-sm">当前角色</div>
                  <div className="text-white font-semibold flex items-center gap-2">
                    {currentRole.name}
                    {currentRole.canViewSensitive ? (
                      <Unlock className="w-3 h-3 text-green-400" />
                    ) : (
                      <Lock className="w-3 h-3 text-red-400" />
                    )}
                  </div>
                </div>
              </div>
              <ChevronDown
                className={`w-5 h-5 text-slate-400 transition-transform ${
                  showRoleSelector ? 'rotate-180' : ''
                }`}
              />
            </button>

            {showRoleSelector && (
              <div className="absolute z-20 top-full left-0 right-0 mt-2 bg-slate-800 rounded-xl border border-slate-700 shadow-xl overflow-hidden">
                {roles.map((role) => (
                  <button
                    key={role.role}
                    onClick={() => handleRoleChange(role)}
                    className={`w-full flex items-center justify-between p-3 hover:bg-slate-700/50 transition-colors ${
                      currentRole.role === role.role
                        ? 'bg-slate-700/50'
                        : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          role.role === 'admin'
                            ? 'bg-purple-500/20'
                            : role.role === 'manager'
                            ? 'bg-blue-500/20'
                            : 'bg-slate-600/50'
                        }`}
                      >
                        <Users
                          className={`w-4 h-4 ${
                            role.role === 'admin'
                              ? 'text-purple-400'
                              : role.role === 'manager'
                              ? 'text-blue-400'
                              : 'text-slate-400'
                          }`}
                        />
                      </div>
                      <div className="text-left">
                        <div className="text-white font-medium">
                          {role.name}
                        </div>
                        <div className="text-xs text-slate-400">
                          最大层级: {role.maxDrillLevel} ·{' '}
                          {role.canViewSensitive ? '可看敏感' : '不可看敏感'}
                        </div>
                      </div>
                    </div>
                    {currentRole.role === role.role && (
                      <CheckCircle2 className="w-5 h-5 text-cyan-400" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-cyan-400" />
              <span className="text-slate-300">最大钻取层级</span>
            </div>
            <span className="text-white font-semibold">
              {currentRole.maxDrillLevel} 层
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl">
            <div className="flex items-center gap-3">
              {currentRole.canViewSensitive ? (
                <Unlock className="w-5 h-5 text-green-400" />
              ) : (
                <Lock className="w-5 h-5 text-red-400" />
              )}
              <span className="text-slate-300">敏感数据访问</span>
            </div>
            <span
              className={`font-semibold ${
                currentRole.canViewSensitive
                  ? 'text-green-400'
                  : 'text-red-400'
              }`}
            >
              {currentRole.canViewSensitive ? '已授权' : '未授权'}
            </span>
          </div>

          {hasSensitiveData && !currentRole.canViewSensitive && (
            <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-red-400 font-medium text-sm">
                  包含敏感数据
                </div>
                <div className="text-red-300/70 text-xs mt-1">
                  当前角色无权查看敏感区域数据，数据已脱敏显示
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <span className="w-1.5 h-6 bg-gradient-to-b from-green-400 to-emerald-500 rounded-full" />
          功能控制
        </h3>

        <div className="space-y-3">
          <button
            onClick={togglePrediction}
            className={`w-full flex items-center justify-between p-3 rounded-xl transition-all duration-200 ${
              showPrediction
                ? 'bg-green-500/20 border border-green-500/30'
                : 'bg-slate-900/40 hover:bg-slate-900/60'
            }`}
          >
            <div className="flex items-center gap-3">
              {showPrediction ? (
                <Eye className="w-5 h-5 text-green-400" />
              ) : (
                <EyeOff className="w-5 h-5 text-slate-400" />
              )}
              <div className="text-left">
                <div
                  className={`font-medium ${
                    showPrediction ? 'text-green-400' : 'text-slate-300'
                  }`}
                >
                  预测数据
                </div>
                <div className="text-xs text-slate-400">
                  展示下一层级预测数据
                </div>
              </div>
            </div>
            <div
              className={`w-12 h-6 rounded-full transition-colors relative ${
                showPrediction ? 'bg-green-500' : 'bg-slate-600'
              }`}
            >
              <div
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  showPrediction ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </div>
          </button>

          <button
            onClick={toggleLinkRelatedCharts}
            className={`w-full flex items-center justify-between p-3 rounded-xl transition-all duration-200 ${
              linkRelatedCharts
                ? 'bg-purple-500/20 border border-purple-500/30'
                : 'bg-slate-900/40 hover:bg-slate-900/60'
            }`}
          >
            <div className="flex items-center gap-3">
              {linkRelatedCharts ? (
                <Link className="w-5 h-5 text-purple-400" />
              ) : (
                <Link2Off className="w-5 h-5 text-slate-400" />
              )}
              <div className="text-left">
                <div
                  className={`font-medium ${
                    linkRelatedCharts ? 'text-purple-400' : 'text-slate-300'
                  }`}
                >
                  关联图表同步
                </div>
                <div className="text-xs text-slate-400">
                  下钻时同步更新关联图表
                </div>
              </div>
            </div>
            <div
              className={`w-12 h-6 rounded-full transition-colors relative ${
                linkRelatedCharts ? 'bg-purple-500' : 'bg-slate-600'
              }`}
            >
              <div
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  linkRelatedCharts ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </div>
          </button>
        </div>

        {linkRelatedCharts && (
          <div className="mt-4 pt-4 border-t border-slate-700/50">
            <div className="text-sm text-slate-400 mb-3">关联图表状态</div>
            <div className="space-y-2">
              {relatedCharts
                .filter((c) => c.isActive)
                .map((chart) => (
                  <div
                    key={chart.id}
                    className="flex items-center justify-between p-2 bg-slate-900/40 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-cyan-400" />
                      <span className="text-slate-300 text-sm">
                        {chart.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          chart.isLinked
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-slate-600/50 text-slate-400'
                        }`}
                      >
                        {chart.isLinked ? '已关联' : '未关联'}
                      </span>
                      <span className="text-xs text-slate-500">
                        Lv.{chart.currentLevel}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

      {showPrediction && predictionSummary && (
        <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/50">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <span className="w-1.5 h-6 bg-gradient-to-b from-emerald-400 to-teal-500 rounded-full" />
            预测概览
          </h3>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-slate-900/40 rounded-xl p-4">
              <div className="text-2xl font-bold text-emerald-400 mb-1">
                {formatValue(predictionSummary.totalPrediction)}
              </div>
              <div className="text-xs text-slate-400">预测总计</div>
            </div>
            <div className="bg-slate-900/40 rounded-xl p-4">
              <div className="text-2xl font-bold text-cyan-400 mb-1">
                {Math.round(predictionSummary.avgConfidence * 100)}%
              </div>
              <div className="text-xs text-slate-400">平均置信度</div>
            </div>
          </div>

          <div className="flex items-center justify-around p-3 bg-slate-900/40 rounded-xl">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <span className="text-green-400 font-semibold">
                {predictionSummary.upCount}
              </span>
              <span className="text-slate-400 text-sm">上升</span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-red-400" />
              <span className="text-red-400 font-semibold">
                {predictionSummary.downCount}
              </span>
              <span className="text-slate-400 text-sm">下降</span>
            </div>
            <div className="flex items-center gap-2">
              <Minus className="w-4 h-4 text-yellow-400" />
              <span className="text-yellow-400 font-semibold">
                {predictionSummary.stableCount}
              </span>
              <span className="text-slate-400 text-sm">稳定</span>
            </div>
          </div>
        </div>
      )}

      {currentData && (
        <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/50">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <span className="w-1.5 h-6 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-full" />
            数据明细
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {currentData.data
              .sort((a, b) => b.value - a.value)
              .map((item, index) => (
                <div
                  key={item.name}
                  className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl hover:bg-slate-900/60 transition-all duration-200"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        index === 0
                          ? 'bg-gradient-to-br from-yellow-400 to-orange-500 text-white'
                          : index === 1
                          ? 'bg-gradient-to-br from-slate-300 to-slate-400 text-slate-700'
                          : index === 2
                          ? 'bg-gradient-to-br from-amber-600 to-amber-700 text-white'
                          : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {index + 1}
                    </span>
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-200 font-medium">
                          {item.name}
                        </span>
                        {item.isSensitive && (
                          <Lock className="w-3 h-3 text-red-400" />
                        )}
                        {item.hasChildren && (
                          <span className="text-xs px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded-full">
                            可下钻
                          </span>
                        )}
                      </div>
                      {showPrediction && item.prediction && (
                        <div className="flex items-center gap-1 text-xs mt-1">
                          {getTrendIcon(item.prediction.trend)}
                          <span className="text-slate-400">
                            预测:{' '}
                            <span
                              className={
                                formatPredictionDisplay(item.prediction).color
                              }
                            >
                              {
                                formatPredictionDisplay(item.prediction).value
                              }
                            </span>
                            <span className="text-slate-500 ml-1">
                              (
                              {
                                formatPredictionDisplay(item.prediction)
                                  .confidence
                              }
                              )
                            </span>
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  <span className="text-white font-semibold">
                    {formatValue(item.value)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
