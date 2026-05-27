import React, { useEffect } from 'react';
import {
  Lightbulb,
  Check,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Trash2,
  Scissors,
  Sliders,
  XCircle,
  RefreshCw as RefreshIcon,
  Edit3,
  Copy,
  CircleDot,
} from 'lucide-react';
import { useDataStore } from '../../store/useDataStore';
import { Badge } from '../common/Badge';
import { getActionLabel, getActionIcon } from '../../utils/recommendationEngine';
import type { RuleRecommendation, RecommendationActionType } from '../../types';

interface RuleRecommendationsProps {
  className?: string;
}

const actionIconMap: Record<RecommendationActionType, React.ReactNode> = {
  remove_duplicates: <Copy size={16} />,
  fill_missing: <CircleDot size={16} />,
  remove_outliers: <Trash2 size={16} />,
  cap_outliers: <Scissors size={16} />,
  normalize: <Sliders size={16} />,
  remove_column: <XCircle size={16} />,
  convert_type: <RefreshIcon size={16} />,
  rename_column: <Edit3 size={16} />,
};

export const RuleRecommendations: React.FC<RuleRecommendationsProps> = ({ className = '' }) => {
  const {
    uploadedData,
    recommendations,
    generateRecommendations,
    applyRecommendation,
    applyAllRecommendations,
    isGeneratingRecommendations,
  } = useDataStore();

  useEffect(() => {
    if (uploadedData && recommendations.length === 0) {
      generateRecommendations();
    }
  }, [uploadedData, recommendations.length, generateRecommendations]);

  if (!uploadedData) {
    return null;
  }

  const getPriorityColor = (priority: RuleRecommendation['priority']) => {
    switch (priority) {
      case 'high':
        return 'border-l-danger-400 bg-danger-500/10';
      case 'medium':
        return 'border-l-warning-400 bg-warning-500/10';
      case 'low':
        return 'border-l-primary-400 bg-primary-500/10';
    }
  };

  const getPriorityBadge = (priority: RuleRecommendation['priority']) => {
    switch (priority) {
      case 'high':
        return <Badge type="danger">高优先级</Badge>;
      case 'medium':
        return <Badge type="warning">中优先级</Badge>;
      case 'low':
        return <Badge type="success">低优先级</Badge>;
    }
  };

  const getMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      mean: '均值填充',
      median: '中位数填充',
      mode: '众数填充',
      interpolate: '插值填充',
      ffill: '前向填充',
      bfill: '后向填充',
      constant: '固定值',
      zscore: 'Z-score',
      iqr: 'IQR',
      minmax: 'Min-Max',
      robust: 'Robust',
    };
    return labels[method] || method;
  };

  const appliedCount = recommendations.filter((r) => r.applied).length;
  const unappliedCount = recommendations.filter((r) => !r.applied).length;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-semibold text-bg-100 flex items-center gap-2">
            <Lightbulb size={18} className="text-accent-400" />
            智能清洗推荐
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={generateRecommendations}
              disabled={isGeneratingRecommendations}
              className="btn btn-ghost text-sm"
            >
              <RefreshCw size={16} className={isGeneratingRecommendations ? 'animate-spin' : ''} />
              重新生成
            </button>
            {unappliedCount > 0 && (
              <button
                onClick={applyAllRecommendations}
                className="btn btn-primary text-sm flex items-center gap-2"
              >
                <Sparkles size={16} />
                一键应用全部
              </button>
            )}
          </div>
        </div>
      </div>

      {isGeneratingRecommendations && recommendations.length === 0 ? (
        <div className="card">
          <div className="card-body text-center py-12 text-bg-500">
            <Lightbulb size={48} className="mx-auto mb-4 opacity-30" />
            <p>正在分析数据并生成推荐...</p>
          </div>
        </div>
      ) : recommendations.length === 0 ? (
        <div className="card">
          <div className="card-body text-center py-12 text-bg-500">
            <Check size={48} className="mx-auto mb-4 text-success-500 opacity-50" />
            <p>数据质量良好，暂无推荐操作</p>
          </div>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="card">
              <div className="card-body text-center">
                <div className="text-3xl font-bold text-primary-400">{recommendations.length}</div>
                <div className="text-sm text-bg-400">总推荐数</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-3xl font-bold text-success-400">{appliedCount}</div>
                <div className="text-sm text-bg-400">已应用</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-3xl font-bold text-warning-400">{unappliedCount}</div>
                <div className="text-sm text-bg-400">待应用</div>
              </div>
            </div>
          </div>

          {/* Recommendations List */}
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <RecommendationCard
                key={rec.id}
                recommendation={rec}
                onApply={() => applyRecommendation(rec.id)}
                getPriorityColor={getPriorityColor}
                getPriorityBadge={getPriorityBadge}
                getMethodLabel={getMethodLabel}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

interface RecommendationCardProps {
  recommendation: RuleRecommendation;
  onApply: () => void;
  getPriorityColor: (priority: RuleRecommendation['priority']) => string;
  getPriorityBadge: (priority: RuleRecommendation['priority']) => React.ReactNode;
  getMethodLabel: (method: string) => string;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onApply,
  getPriorityColor,
  getPriorityBadge,
  getMethodLabel,
}) => {
  const { columnName, action, priority, confidence, reason, suggestedConfig, applied } =
    recommendation;

  return (
    <div
      className={`card border-l-4 ${getPriorityColor(priority)} ${
        applied ? 'opacity-60' : ''
      } transition-all duration-200 hover:bg-bg-800/50`}
    >
      <div className="card-body">
        <div className="flex items-start gap-4">
          {/* Action Icon */}
          <div
            className={`p-3 rounded-lg ${
              applied ? 'bg-success-500/20 text-success-400' : 'bg-primary-500/20 text-primary-400'
            }`}
          >
            {applied ? <Check size={20} /> : actionIconMap[action]}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <span className="font-medium text-bg-100">
                {columnName === '__dataset__' ? '全局操作' : columnName}
              </span>
              {getPriorityBadge(priority)}
              <Badge type="numeric">{(confidence * 100).toFixed(0)}% 置信度</Badge>
            </div>

            <div className="flex items-center gap-2 text-sm text-bg-300 mb-2">
              <span className="font-medium text-accent-400">{getActionLabel(action)}</span>
              {suggestedConfig?.method && (
                <>
                  <ArrowRight size={14} className="text-bg-500" />
                  <span>{getMethodLabel(suggestedConfig.method)}</span>
                </>
              )}
              {suggestedConfig?.threshold !== undefined && (
                <span className="text-bg-400">阈值: {suggestedConfig.threshold}</span>
              )}
              {suggestedConfig?.action && (
                <span className="text-bg-400">
                  处理: {suggestedConfig.action === 'remove' ? '删除' : suggestedConfig.action === 'cap' ? '盖帽' : '标记'}
                </span>
              )}
            </div>

            <p className="text-sm text-bg-400">{reason}</p>
          </div>

          {/* Action Button */}
          <div className="flex-shrink-0">
            {applied ? (
              <button className="btn btn-ghost text-sm text-success-400 cursor-default" disabled>
                <Check size={16} />
                已应用
              </button>
            ) : (
              <button
                onClick={onApply}
                className="btn btn-primary text-sm"
              >
                应用
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
