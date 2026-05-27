import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  X, 
  Gauge,
  FileWarning,
  Type,
  Link2
} from 'lucide-react';
import { useAppStore } from '@/store';

interface QualityPanelProps {
  onClose: () => void;
}

const severityColors = {
  error: 'text-red-600 bg-red-50',
  warning: 'text-amber-600 bg-amber-50',
  info: 'text-blue-600 bg-blue-50',
};

const severityIcons = {
  error: <XCircle className="w-4 h-4" />,
  warning: <AlertTriangle className="w-4 h-4" />,
  info: <FileWarning className="w-4 h-4" />,
};

const issueIcons = {
  missing_mapping: <Link2 className="w-4 h-4" />,
  type_mismatch: <Type className="w-4 h-4" />,
  empty_mapping: <AlertTriangle className="w-4 h-4" />,
};

export default function QualityPanel({ onClose }: QualityPanelProps) {
  const { qualityReport, evaluateQuality, setSelectedMapping } = useAppStore();

  const report = qualityReport || evaluateQuality();

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600';
    if (score >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'from-emerald-400 to-emerald-600';
    if (score >= 60) return 'from-amber-400 to-amber-600';
    return 'from-red-400 to-red-600';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 90) return '优秀';
    if (score >= 80) return '良好';
    if (score >= 70) return '一般';
    if (score >= 60) return '及格';
    return '待改进';
  };

  const handleIssueClick = (issue: typeof report.issues[0]) => {
    if (issue.mappingId) {
      setSelectedMapping(issue.mappingId);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <Gauge className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">映射质量评估</h2>
              <p className="text-sm text-slate-500">检测字段缺失和类型错误</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <div className="flex items-center gap-6 mb-6 p-4 bg-slate-50 rounded-xl">
            <div className="relative w-20 h-20">
              <svg className="w-20 h-20 transform -rotate-90">
                <circle
                  cx="40"
                  cy="40"
                  r="35"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="6"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="35"
                  fill="none"
                  className={`bg-gradient-to-r ${getScoreBg(report.score)}`}
                  stroke="url(#gradient)"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={`${report.score * 2.2} 220`}
                />
                <defs>
                  <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor={report.score >= 80 ? '#10b981' : report.score >= 60 ? '#f59e0b' : '#ef4444'} />
                    <stop offset="100%" stopColor={report.score >= 80 ? '#059669' : report.score >= 60 ? '#d97706' : '#dc2626'} />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-2xl font-bold ${getScoreColor(report.score)}`}>
                  {report.score}
                </span>
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-lg font-semibold ${getScoreColor(report.score)}`}>
                  {getScoreLabel(report.score)}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-slate-500">总字段</div>
                  <div className="font-semibold text-slate-800">{report.totalFields}</div>
                </div>
                <div>
                  <div className="text-slate-500">已映射</div>
                  <div className="font-semibold text-emerald-600">{report.mappedFields}</div>
                </div>
                <div>
                  <div className="text-slate-500">缺失</div>
                  <div className="font-semibold text-red-600">{report.missingFields}</div>
                </div>
              </div>
            </div>
          </div>

          {report.typeWarnings > 0 && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-center gap-2 text-amber-700 text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span>检测到 {report.typeWarnings} 个类型不匹配警告</span>
              </div>
            </div>
          )}

          <div className="space-y-3">
            <h3 className="font-medium text-slate-700">问题列表</h3>
            {report.issues.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <CheckCircle className="w-12 h-12 mx-auto mb-2 text-emerald-500" />
                <p>映射质量良好，未发现问题</p>
              </div>
            ) : (
              <div className="space-y-2">
                {report.issues.map(issue => (
                  <div
                    key={issue.id}
                    onClick={() => handleIssueClick(issue)}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer hover:shadow-sm transition-shadow ${severityColors[issue.severity]}`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {severityIcons[issue.severity]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        {issueIcons[issue.type]}
                        <span className="font-medium text-sm">{issue.message}</span>
                      </div>
                      <span className="text-xs opacity-70 mt-0.5 block">
                        {issue.type === 'missing_mapping' && '请为必填字段配置映射'}
                        {issue.type === 'empty_mapping' && '请关联源字段或删除此映射'}
                        {issue.type === 'type_mismatch' && '建议添加转换函数或调整输出类型'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
          <div className="flex gap-3">
            <button
              onClick={() => evaluateQuality()}
              className="flex-1 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
            >
              重新评估
            </button>
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              继续配置
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
