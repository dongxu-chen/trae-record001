import { Copy, Check, FileText, Layers, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import QualityEvaluationPanel from './QualityEvaluationPanel';

const MultiDocSummaryResult = ({ result }) => {
  const [copied, setCopied] = useState(false);
  const [showIntermediate, setShowIntermediate] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(result.summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!result) return null;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 card-shadow">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <Layers className="w-6 h-6 text-purple-600" />
            多文档综合摘要
          </h3>
          <button
            onClick={copyToClipboard}
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

        <div className="mb-4 flex items-center gap-4">
          <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
            {result.num_docs} 个文档
          </span>
          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
            {result.summary_type}
          </span>
          {result.model && (
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
              {result.model.toUpperCase()}
            </span>
          )}
        </div>

        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-5 mb-6">
          <p className="text-gray-700 leading-relaxed text-lg">{result.summary}</p>
        </div>

        {result.doc_contributions && result.doc_contributions.length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-700 mb-3">文档贡献度</h4>
            <div className="space-y-2">
              {result.doc_contributions.map((contrib, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <span className="text-sm text-gray-500 w-24">文档 {contrib.doc_id + 1}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
                      style={{
                        width: `${contrib.total_sentences > 0 ? (contrib.sentences_used / contrib.total_sentences * 100) : 0}%`
                      }}
                    />
                  </div>
                  <span className="text-sm text-gray-600 w-20 text-right">
                    {contrib.sentences_used}/{contrib.total_sentences} 句
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {result.intermediate_summaries && result.intermediate_summaries.length > 0 && (
          <div className="border-t border-gray-100 pt-4">
            <button
              onClick={() => setShowIntermediate(!showIntermediate)}
              className="flex items-center gap-2 text-sm font-medium text-purple-600 hover:text-purple-700"
            >
              {showIntermediate ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              查看单文档中间摘要
            </button>
            {showIntermediate && (
              <div className="mt-4 space-y-3">
                {result.intermediate_summaries.map((summary, idx) => (
                  <div key={idx} className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs font-medium text-gray-500 mb-2">
                      文档 {idx + 1} 摘要
                    </div>
                    <p className="text-sm text-gray-600">{summary}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {result.quality_evaluation && (
        <QualityEvaluationPanel evaluation={result.quality_evaluation} />
      )}
    </div>
  );
};

export default MultiDocSummaryResult;
