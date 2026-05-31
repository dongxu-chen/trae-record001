import { Copy, Check, FileText, Hash, Languages, ShieldCheck, AlertTriangle, Layers, ArrowRight } from 'lucide-react';
import { useState } from 'react';
import QualityEvaluationPanel from './QualityEvaluationPanel';
import TopicSegmentationPanel from './TopicSegmentationPanel';

const SummaryResult = ({ result }) => {
  const [copied, setCopied] = useState(false);
  const [showCorrected, setShowCorrected] = useState(false);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!result) return null;

  const displaySummary = showCorrected && result.corrected_summary
    ? result.corrected_summary
    : result.summary;

  const hasCorrections = result.fact_check && result.fact_check.corrections && result.fact_check.corrections.length > 0;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 card-shadow">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <FileText className="w-6 h-6 text-purple-600" />
            摘要结果
          </h3>
          <button
            onClick={() => copyToClipboard(displaySummary)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-green-600 text-sm">已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-gray-600" />
                <span className="text-gray-600 text-sm">复制</span>
              </>
            )}
          </button>
        </div>

        {result.chunks_processed > 1 && (
          <div className="mb-4 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" />
            <span className="text-sm text-blue-700">
              长文档已通过滑动窗口分块处理，共 <span className="font-bold">{result.chunks_processed}</span> 个分块，增量合并生成摘要
            </span>
          </div>
        )}

        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-5 mb-6">
          <p className="text-gray-700 leading-relaxed text-lg">{displaySummary}</p>
        </div>

        {hasCorrections && (
          <div className="mb-6 border border-amber-200 bg-amber-50 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-amber-600" />
                <h4 className="font-semibold text-amber-800">事实性校验</h4>
              </div>
              <button
                onClick={() => setShowCorrected(!showCorrected)}
                className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                  showCorrected
                    ? 'bg-amber-200 text-amber-800'
                    : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                }`}
              >
                {showCorrected ? '查看原文摘要' : '查看修正摘要'}
              </button>
            </div>

            <div className="flex items-center gap-2 mb-3">
              {result.fact_check.is_consistent ? (
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                  ✓ 事实一致
                </span>
              ) : (
                <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                  ✗ 发现事实偏差
                </span>
              )}
            </div>

            {result.fact_check.corrections.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-amber-700 font-medium">自动修正：</p>
                {result.fact_check.corrections.map((correction, index) => (
                  <div key={index} className="flex items-center gap-2 text-sm bg-white rounded-lg p-3">
                    <span className="text-red-500 line-through">{correction.original}</span>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                    <span className="text-green-600 font-medium">{correction.corrected}</span>
                  </div>
                ))}
              </div>
            )}

            {result.fact_check.number_issues.filter(i => i.severity === 'error').length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-sm text-red-700 font-medium flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" /> 数字偏差：
                </p>
                {result.fact_check.number_issues
                  .filter(i => i.severity === 'error')
                  .map((issue, index) => (
                    <div key={index} className="text-xs text-red-600 bg-red-50 p-2 rounded-lg">
                      {issue.message}
                    </div>
                  ))}
              </div>
            )}

            {result.fact_check.entity_issues.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-sm text-orange-700 font-medium flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" /> 实体偏差：
                </p>
                {result.fact_check.entity_issues.map((issue, index) => (
                  <div key={index} className="text-xs text-orange-600 bg-orange-50 p-2 rounded-lg">
                    {issue.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {result.fact_check && result.fact_check.is_consistent && !hasCorrections && (
          <div className="mb-6 px-4 py-3 bg-green-50 border border-green-200 rounded-xl flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-green-600" />
            <span className="text-sm text-green-700">事实性校验通过：摘要中的数字和实体与原文一致</span>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-purple-600">{result.original_length}</div>
            <div className="text-sm text-gray-500">原文长度</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-indigo-600">{result.summary_length}</div>
            <div className="text-sm text-gray-500">摘要长度</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold text-green-600">
              {(result.compression_ratio * 100).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500">压缩率</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <div className="flex items-center justify-center gap-1 text-lg font-bold text-blue-600">
              <Languages className="w-5 h-5" />
              {result.language.toUpperCase()}
            </div>
            <div className="text-sm text-gray-500">检测语言</div>
          </div>
        </div>

        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Hash className="w-5 h-5 text-purple-600" />
            <h4 className="font-semibold text-gray-700">提取的关键词</h4>
          </div>
          <div className="flex flex-wrap">
            {result.key_phrases.map((keyword, index) => (
              <span key={index} className="keyword-tag">
                {keyword}
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between text-sm text-gray-500 pt-4 border-t border-gray-100">
          <span>摘要类型: <span className="font-medium text-gray-700">{result.summary_type}</span></span>
          <span>使用模型: <span className="font-medium text-gray-700">{result.model}</span></span>
          {result.chunks_processed > 1 && (
            <span>分块数: <span className="font-medium text-gray-700">{result.chunks_processed}</span></span>
          )}
        </div>
      </div>

      {result.quality_evaluation && (
        <QualityEvaluationPanel evaluation={result.quality_evaluation} />
      )}

      {result.topic_summary && (
        <TopicSegmentationPanel topicSummary={result.topic_summary} />
      )}
    </div>
  );
};

export default SummaryResult;
