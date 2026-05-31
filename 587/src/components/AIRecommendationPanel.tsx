import React, { useState } from 'react';
import { Sparkles, AlertTriangle, TrendingUp, BarChart2, Plus, X, ChevronDown, ChevronUp, CheckCircle } from 'lucide-react';
import { AIRecommendation, annotationTemplates } from '../utils/aiAnalysis';
import { useStore } from '../store/useStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { AnnotationType, RelativePoint } from '../../shared/types';
import { v4 as uuidv4 } from 'uuid';

interface AIRecommendationPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const AIRecommendationPanel: React.FC<AIRecommendationPanelProps> = ({ isOpen, onClose }) => {
  const {
    aiRecommendations,
    currentUser,
    permissions,
    isAnalyzing,
    setAIRecommendations,
    setIsAnalyzing,
    chartData,
    annotations,
  } = useStore();

  const { sendAnnotationAdd } = useWebSocket();
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['异常检测', '趋势分析', '统计信息', '风险提示']));
  const [addedRecommendations, setAddedRecommendations] = useState<Set<string>>(new Set());

  const categoryIcons: Record<string, React.ReactNode> = {
    '异常检测': <AlertTriangle size={16} className="text-amber-500" />,
    '趋势分析': <TrendingUp size={16} className="text-green-500" />,
    '统计信息': <BarChart2 size={16} className="text-blue-500" />,
    '风险提示': <AlertTriangle size={16} className="text-red-500" />,
  };

  const groupedRecommendations = aiRecommendations.reduce((acc, rec) => {
    if (!acc[rec.category]) {
      acc[rec.category] = [];
    }
    acc[rec.category].push(rec);
    return acc;
  }, {} as Record<string, AIRecommendation[]>);

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const addRecommendation = (rec: AIRecommendation) => {
    if (!currentUser || permissions === 'read') return;

    const annotation = {
      type: rec.annotationType as AnnotationType,
      position: rec.position as RelativePoint,
      endPosition: rec.endPosition as RelativePoint | undefined,
      content: rec.content,
      color: rec.color,
      authorId: currentUser.id,
      authorName: currentUser.name,
    };

    sendAnnotationAdd(annotation);
    setAddedRecommendations(prev => new Set([...prev, rec.id]));

    setTimeout(() => {
      setAddedRecommendations(prev => {
        const next = new Set(prev);
        next.delete(rec.id);
        return next;
      });
    }, 2000);
  };

  const addAllRecommendations = () => {
    aiRecommendations.forEach(rec => {
      if (!addedRecommendations.has(rec.id)) {
        addRecommendation(rec);
      }
    });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-500';
    if (confidence >= 0.75) return 'text-amber-500';
    return 'text-gray-500';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.9) return '高';
    if (confidence >= 0.75) return '中';
    return '低';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div className="bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 text-white">
            <Sparkles size={24} />
            <div>
              <h2 className="text-xl font-semibold">AI 注释推荐</h2>
              <p className="text-sm text-white/80">
                基于数据分析智能发现 {aiRecommendations.length} 个值得关注的点
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            已存在 {annotations.length} 条注释
          </div>
          <div className="flex items-center gap-2">
            {permissions !== 'read' && (
              <button
                onClick={addAllRecommendations}
                className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-200 transition-colors"
              >
                一键添加全部
              </button>
            )}
          </div>
        </div>

        <div className="overflow-y-auto max-h-[50vh] p-4">
          {aiRecommendations.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Sparkles size={48} className="mx-auto mb-3 opacity-50" />
              <p>暂无推荐</p>
              <p className="text-sm mt-1">AI分析暂未发现需要关注的数据点</p>
            </div>
          ) : (
            Object.entries(groupedRecommendations).map(([category, recs]) => (
              <div key={category} className="mb-4">
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {categoryIcons[category]}
                    <span className="font-medium text-gray-700">{category}</span>
                    <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded-full text-xs">
                      {recs.length}
                    </span>
                  </div>
                  {expandedCategories.has(category) ? (
                    <ChevronUp size={18} className="text-gray-400" />
                  ) : (
                    <ChevronDown size={18} className="text-gray-400" />
                  )}
                </button>

                {expandedCategories.has(category) && (
                  <div className="mt-2 space-y-2 ml-2">
                    {recs.map((rec) => {
                      const isAdded = addedRecommendations.has(rec.id);
                      return (
                        <div
                          key={rec.id}
                          className="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg hover:border-purple-300 transition-colors"
                        >
                          <div
                            className="w-3 h-3 rounded-full mt-1.5 flex-shrink-0"
                            style={{ backgroundColor: rec.color }}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800">{rec.content}</p>
                            <div className="flex items-center gap-3 mt-1.5">
                              <span className="text-xs text-gray-500">
                                类型: {rec.annotationType === 'text' ? '文本' : rec.annotationType === 'arrow' ? '箭头' : '高亮'}
                              </span>
                              <span className={`text-xs ${getConfidenceColor(rec.confidence)}`}>
                                置信度: {getConfidenceLabel(rec.confidence)} ({Math.round(rec.confidence * 100)}%)
                              </span>
                            </div>
                          </div>
                          {permissions !== 'read' && (
                            <button
                              onClick={() => addRecommendation(rec)}
                              disabled={isAdded}
                              className={`p-2 rounded-lg transition-colors flex-shrink-0 ${
                                isAdded
                                  ? 'bg-green-100 text-green-600'
                                  : 'bg-purple-100 text-purple-600 hover:bg-purple-200'
                              }`}
                              title={isAdded ? '已添加' : '添加此注释'}
                            >
                              {isAdded ? <CheckCircle size={18} /> : <Plus size={18} />}
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          <p className="text-xs text-gray-500">
            💡 提示：推荐基于统计分析，建议结合业务背景进行判断
          </p>
          <div className="text-xs text-gray-400">
            支持检测：异常点 · 趋势变化 · 统计特征
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIRecommendationPanel;
