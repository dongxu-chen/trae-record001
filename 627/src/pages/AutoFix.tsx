import { useState, useEffect } from 'react';
import { Wrench, Play, CheckCircle, XCircle, AlertTriangle, Eye } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import type { AutoFixResult } from '../../shared/types.js';

export default function AutoFixPage() {
  const { autoFixPreview, fetchAutoFixPreview, executeAutoFix, fetchIssues } = useAppStore();
  const [selectedFixes, setSelectedFixes] = useState<Set<string>>(new Set());
  const [showPreview, setShowPreview] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [results, setResults] = useState<AutoFixResult[] | null>(null);

  useEffect(() => {
    void fetchAutoFixPreview();
  }, [fetchAutoFixPreview]);

  const handleToggleFix = (issueId: string) => {
    setSelectedFixes(prev => {
      const next = new Set(prev);
      if (next.has(issueId)) next.delete(issueId);
      else next.add(issueId);
      return next;
    });
  };

  const handleSelectAllFixable = () => {
    if (!autoFixPreview) return;
    const fixableIds = autoFixPreview.fixes.filter(f => f.fixed).map(f => f.issueId);
    setSelectedFixes(new Set(fixableIds));
  };

  const handleExecute = async () => {
    if (selectedFixes.size === 0) return;
    setExecuting(true);
    try {
      const fixedCount = await executeAutoFix(Array.from(selectedFixes));
      await fetchIssues();
      await fetchAutoFixPreview();
      setSelectedFixes(new Set());
      setResults(autoFixPreview?.fixes.filter(f => selectedFixes.has(f.issueId)) ?? null);
    } finally {
      setExecuting(false);
    }
  };

  if (!autoFixPreview) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">扫描可修复问题中...</p>
      </div>
    );
  }

  const fixableFixes = autoFixPreview.fixes.filter(f => f.fixed);
  const unfixableFixes = autoFixPreview.fixes.filter(f => !f.fixed);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-green-100 rounded-xl">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-gray-500 text-sm">可自动修复</p>
              <p className="text-2xl font-bold text-green-600">{autoFixPreview.totalFixable}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-orange-100 rounded-xl">
              <AlertTriangle className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <p className="text-gray-500 text-sm">需人工确认</p>
              <p className="text-2xl font-bold text-orange-600">{unfixableFixes.length}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-xl">
              <Eye className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-gray-500 text-sm">已选择修复</p>
              <p className="text-2xl font-bold text-blue-600">{selectedFixes.size}</p>
            </div>
          </div>
        </div>
      </div>

      {selectedFixes.size > 0 && (
        <div className="bg-primary-50 border border-primary-200 rounded-xl p-4 flex items-center justify-between">
          <span className="text-primary-700 text-sm">
            已选择 {selectedFixes.size} 项修复
          </span>
          <button
            onClick={handleExecute}
            disabled={executing}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            <Play className="w-4 h-4" />
            {executing ? '执行中...' : '执行修复'}
          </button>
        </div>
      )}

      {fixableFixes.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">可自动修复的问题</h3>
            <button
              onClick={handleSelectAllFixable}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              全选可修复项
            </button>
          </div>
          <div className="space-y-3">
            {fixableFixes.map((fix) => (
              <div
                key={fix.issueId}
                className={`flex items-start gap-4 p-4 rounded-lg border transition-colors ${
                  selectedFixes.has(fix.issueId)
                    ? 'border-primary-300 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedFixes.has(fix.issueId)}
                  onChange={() => handleToggleFix(fix.issueId)}
                  className="mt-1 w-4 h-4 text-primary-600 rounded"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-800">{fix.tableName}.{fix.columnName}</span>
                    <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                      {fix.fixStrategy}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{fix.message}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                    <span>行: {fix.rowIdentifier}</span>
                    <span>类型: {fix.issueType}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-xs">
                    <span className="text-red-500 line-through">{fix.oldValue || '(空值)'}</span>
                    <span className="text-gray-400">→</span>
                    <span className="text-green-600 font-medium">{fix.newValue}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {unfixableFixes.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">需人工确认的问题</h3>
          <div className="space-y-3">
            {unfixableFixes.map((fix) => (
              <div
                key={fix.issueId}
                className="flex items-start gap-4 p-4 rounded-lg border border-orange-200 bg-orange-50"
              >
                <AlertTriangle className="w-5 h-5 text-orange-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-800">{fix.tableName}.{fix.columnName}</span>
                    <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 rounded-full">
                      {fix.issueType}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{fix.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {autoFixPreview.fixes.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-300" />
          <p className="text-gray-500">当前没有可修复的质量问题</p>
        </div>
      )}
    </div>
  );
}
