import { BarChart3, FileText, AlertCircle, CheckCircle2, Star } from 'lucide-react';

const QualityEvaluationPanel = ({ evaluation }) => {
  if (!evaluation) return null;

  const getQualityColor = (quality) => {
    switch (quality) {
      case 'Excellent': return 'text-green-600 bg-green-50 border-green-200';
      case 'Good': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'Fair': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'Poor': return 'text-orange-600 bg-orange-50 border-orange-200';
      default: return 'text-red-600 bg-red-50 border-red-200';
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.7) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBarColor = (score) => {
    if (score >= 0.7) return 'bg-green-500';
    if (score >= 0.5) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-white rounded-2xl p-6 card-shadow">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-purple-600" />
          摘要质量评估
        </h3>
        <span className={`px-4 py-2 rounded-full text-sm font-semibold border ${getQualityColor(evaluation.overall_quality)}`}>
          <Star className="w-4 h-4 inline mr-1" />
          {evaluation.overall_quality}
        </span>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">综合评分</span>
          <span className={`text-lg font-bold ${getScoreColor(evaluation.overall_score)}`}>
            {(evaluation.overall_score * 100).toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${getScoreBarColor(evaluation.overall_score)}`}
            style={{ width: `${evaluation.overall_score * 100}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">ROUGE-1</div>
          <div className={`text-xl font-bold ${getScoreColor(evaluation.rouge_scores.rouge1)}`}>
            {(evaluation.rouge_scores.rouge1 * 100).toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">ROUGE-2</div>
          <div className={`text-xl font-bold ${getScoreColor(evaluation.rouge_scores.rouge2)}`}>
            {(evaluation.rouge_scores.rouge2 * 100).toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">ROUGE-L</div>
          <div className={`text-xl font-bold ${getScoreColor(evaluation.rouge_scores.rougel)}`}>
            {(evaluation.rouge_scores.rougel * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="space-y-3 mb-6">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-600">事实一致性</span>
            <span className={`text-sm font-medium ${getScoreColor(evaluation.factual_consistency)}`}>
              {(evaluation.factual_consistency * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getScoreBarColor(evaluation.factual_consistency)}`}
              style={{ width: `${evaluation.factual_consistency * 100}%` }}
            />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-600">语义相关性</span>
            <span className={`text-sm font-medium ${getScoreColor(evaluation.relevance_score)}`}>
              {(evaluation.relevance_score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getScoreBarColor(evaluation.relevance_score)}`}
              style={{ width: `${evaluation.relevance_score * 100}%` }}
            />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-600">信息覆盖率</span>
            <span className={`text-sm font-medium ${getScoreColor(evaluation.coverage_score)}`}>
              {(evaluation.coverage_score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getScoreBarColor(evaluation.coverage_score)}`}
              style={{ width: `${evaluation.coverage_score * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="border-t border-gray-100 pt-4">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">关键要点覆盖</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {evaluation.key_points_covered.slice(0, 8).map((item, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 text-green-700 rounded-full text-xs"
            >
              <CheckCircle2 className="w-3 h-3" />
              {item.phrase}
            </span>
          ))}
        </div>
        {evaluation.missing_key_points.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-orange-500" />
              <span className="text-xs text-orange-600">可能遗漏的要点</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {evaluation.missing_key_points.slice(0, 5).map((item, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-orange-50 text-orange-700 rounded-full text-xs"
                >
                  {item.phrase}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QualityEvaluationPanel;
