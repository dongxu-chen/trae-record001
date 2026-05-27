import React, { useEffect } from 'react';
import { Activity, CheckCircle, AlertTriangle, XCircle, RefreshCw, Info } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { useDataStore } from '../../store/useDataStore';
import { getQualityScoreColor, getQualityScoreBgColor, getQualityLabel } from '../../utils/qualityEvaluator';
import { Badge, TypeBadge } from '../common/Badge';
import type { ColumnQualityReport, QualityIssue } from '../../types';

interface QualityAssessmentProps {
  className?: string;
}

export const QualityAssessment: React.FC<QualityAssessmentProps> = ({ className = '' }) => {
  const { uploadedData, qualityReport, evaluateQuality, isEvaluatingQuality } = useDataStore();

  useEffect(() => {
    if (uploadedData && !qualityReport) {
      evaluateQuality();
    }
  }, [uploadedData, qualityReport, evaluateQuality]);

  if (!uploadedData) {
    return null;
  }

  const getSeverityIcon = (severity: QualityIssue['severity']) => {
    switch (severity) {
      case 'critical':
        return <XCircle size={14} className="text-danger-400" />;
      case 'warning':
        return <AlertTriangle size={14} className="text-warning-400" />;
      case 'info':
        return <Info size={14} className="text-primary-400" />;
    }
  };

  const getSeverityBadge = (severity: QualityIssue['severity']) => {
    switch (severity) {
      case 'critical':
        return <Badge type="danger">严重</Badge>;
      case 'warning':
        return <Badge type="warning">警告</Badge>;
      case 'info':
        return <Badge type="success">提示</Badge>;
    }
  };

  const overallOption = qualityReport
    ? {
        backgroundColor: 'transparent',
        series: [
          {
            type: 'gauge',
            startAngle: 90,
            endAngle: -270,
            pointer: {
              show: false,
            },
            progress: {
              show: true,
              overlap: false,
              roundCap: true,
              clip: false,
              itemStyle: {
                color: {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 1,
                  y2: 0,
                  colorStops: [
                    { offset: 0, color: '#ef4444' },
                    { offset: 0.5, color: '#f59e0b' },
                    { offset: 1, color: '#10b981' },
                  ],
                },
              },
            },
            axisLine: {
              lineStyle: {
                width: 18,
                color: [[1, '#334155']],
              },
            },
            splitLine: {
              show: false,
            },
            axisTick: {
              show: false,
            },
            axisLabel: {
              show: false,
            },
            data: [
              {
                value: qualityReport.overallMetrics.overall,
                detail: {
                  offsetCenter: ['0%', '0%'],
                  fontSize: 32,
                  fontWeight: 'bold',
                  formatter: '{value}分',
                },
              },
            ],
            detail: {
              width: 60,
              height: 14,
              fontSize: 32,
              color: '#e2e8f0',
            },
          },
        ],
      }
    : null;

  const radarOption = qualityReport
    ? {
        backgroundColor: 'transparent',
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: '#475569',
          textStyle: { color: '#e2e8f0' },
        },
        radar: {
          indicator: [
            { name: '完整度', max: 100 },
            { name: '一致性', max: 100 },
            { name: '准确性', max: 100 },
          ],
          axisName: {
            color: '#94a3b8',
            fontSize: 12,
          },
          splitArea: {
            areaStyle: {
              color: ['#1e293b', '#334155'],
            },
          },
          axisLine: {
            lineStyle: {
              color: '#475569',
            },
          },
          splitLine: {
            lineStyle: {
              color: '#475569',
            },
          },
        },
        series: [
          {
            type: 'radar',
            data: [
              {
                value: [
                  qualityReport.overallMetrics.completeness,
                  qualityReport.overallMetrics.consistency,
                  qualityReport.overallMetrics.accuracy,
                ],
                name: '数据质量',
                areaStyle: {
                  color: 'rgba(59, 130, 246, 0.3)',
                },
                lineStyle: {
                  color: '#3b82f6',
                  width: 2,
                },
                itemStyle: {
                  color: '#3b82f6',
                },
              },
            ],
          },
        ],
      }
    : null;

  const renderScoreBar = (score: number, label: string) => (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-bg-400">{label}</span>
        <span className={`font-mono font-semibold ${getQualityScoreColor(score)}`}>
          {score.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-bg-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getQualityScoreBgColor(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );

  const allIssues = qualityReport
    ? qualityReport.columnReports.flatMap((cr) =>
        cr.issues.map((issue) => ({ ...issue, columnName: cr.columnName }))
      )
    : [];

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-semibold text-bg-100 flex items-center gap-2">
            <Activity size={18} className="text-primary-400" />
            数据质量评估
          </h3>
          <button
            onClick={evaluateQuality}
            disabled={isEvaluatingQuality}
            className="btn btn-ghost text-sm"
          >
            <RefreshCw size={16} className={isEvaluatingQuality ? 'animate-spin' : ''} />
            重新评估
          </button>
        </div>
      </div>

      {!qualityReport ? (
        <div className="card">
          <div className="card-body text-center py-12 text-bg-500">
            <Activity size={48} className="mx-auto mb-4 opacity-30" />
            <p>正在评估数据质量...</p>
          </div>
        </div>
      ) : (
        <>
          {/* Overall Score */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="card md:col-span-1">
              <div className="card-body">
                <div className="text-center">
                  <div className="h-48">
                    {overallOption && (
                      <ReactECharts option={overallOption} style={{ height: '100%' }} />
                    )}
                  </div>
                  <div
                    className={`text-2xl font-bold ${getQualityScoreColor(
                      qualityReport.overallMetrics.overall
                    )}`}
                  >
                    {getQualityLabel(qualityReport.overallMetrics.overall)}
                  </div>
                  <p className="text-sm text-bg-400 mt-1">综合质量评分</p>
                </div>
              </div>
            </div>

            <div className="card md:col-span-2">
              <div className="card-body space-y-6">
                <h4 className="font-medium text-bg-100">质量维度分析</h4>
                <div className="space-y-4">
                  {renderScoreBar(qualityReport.overallMetrics.completeness, '完整度')}
                  {renderScoreBar(qualityReport.overallMetrics.consistency, '一致性')}
                  {renderScoreBar(qualityReport.overallMetrics.accuracy, '准确性')}
                </div>

                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-bg-700">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-danger-400">
                      {qualityReport.severityBreakdown.critical}
                    </div>
                    <div className="text-xs text-bg-400">严重问题</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-warning-400">
                      {qualityReport.severityBreakdown.warning}
                    </div>
                    <div className="text-xs text-bg-400">警告</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary-400">
                      {qualityReport.severityBreakdown.info}
                    </div>
                    <div className="text-xs text-bg-400">提示</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Radar Chart */}
          <div className="card">
            <div className="card-header">
              <h4 className="font-medium text-bg-100">质量维度雷达图</h4>
            </div>
            <div className="card-body">
              <div className="h-80">
                {radarOption && (
                  <ReactECharts option={radarOption} style={{ height: '100%' }} />
                )}
              </div>
            </div>
          </div>

          {/* Column Quality Reports */}
          <div className="card">
            <div className="card-header">
              <h4 className="font-medium text-bg-100">各列质量详情</h4>
            </div>
            <div className="card-body p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-bg-800 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider">
                        列名
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider">
                        类型
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider">
                        完整度
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider">
                        一致性
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider">
                        准确性
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider">
                        综合
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider">
                        问题
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-bg-700">
                    {qualityReport.columnReports.map((colReport, idx) => (
                      <ColumnQualityRow key={idx} report={colReport} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Issues List */}
          {allIssues.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h4 className="font-medium text-bg-100">
                  问题列表
                  <Badge type="warning" className="ml-2">
                    {allIssues.length}
                  </Badge>
                </h4>
              </div>
              <div className="card-body p-0">
                <div className="max-h-96 overflow-y-auto">
                  {allIssues.map((issue, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 px-4 py-3 border-b border-bg-700 hover:bg-bg-800/50"
                    >
                      {getSeverityIcon(issue.severity)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-bg-200">{issue.columnName}</span>
                          {getSeverityBadge(issue.severity)}
                        </div>
                        <p className="text-sm text-bg-400 mt-1">{issue.message}</p>
                        {issue.value !== undefined && issue.threshold !== undefined && (
                          <p className="text-xs text-bg-500 mt-1 font-mono">
                            当前值: {issue.value.toFixed(2)} / 阈值: {issue.threshold}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

const ColumnQualityRow: React.FC<{ report: ColumnQualityReport }> = ({ report }) => {
  const renderMiniScore = (score: number) => (
    <div className="flex items-center gap-2">
      <span className={`text-sm font-mono ${getQualityScoreColor(score)}`}>
        {score.toFixed(0)}%
      </span>
      <div className="w-16 h-1.5 bg-bg-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${getQualityScoreBgColor(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );

  return (
    <tr className="border-b border-bg-700 hover:bg-bg-800/50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="font-medium text-bg-200">{report.columnName}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <TypeBadge type={report.columnType} />
      </td>
      <td className="px-4 py-3">{renderMiniScore(report.metrics.completeness)}</td>
      <td className="px-4 py-3">{renderMiniScore(report.metrics.consistency)}</td>
      <td className="px-4 py-3">{renderMiniScore(report.metrics.accuracy)}</td>
      <td className="px-4 py-3">
        <span className={`text-sm font-semibold ${getQualityScoreColor(report.metrics.overall)}`}>
          {report.metrics.overall.toFixed(0)}%
        </span>
      </td>
      <td className="px-4 py-3">
        {report.issues.length > 0 ? (
          <div className="flex items-center gap-1">
            {report.issues.some((i) => i.severity === 'critical') && (
              <Badge type="danger">
                {report.issues.filter((i) => i.severity === 'critical').length}
              </Badge>
            )}
            {report.issues.some((i) => i.severity === 'warning') && (
              <Badge type="warning">
                {report.issues.filter((i) => i.severity === 'warning').length}
              </Badge>
            )}
            {report.issues.some((i) => i.severity === 'info') && (
              <Badge type="success">
                {report.issues.filter((i) => i.severity === 'info').length}
              </Badge>
            )}
          </div>
        ) : (
          <CheckCircle size={16} className="text-success-500" />
        )}
      </td>
    </tr>
  );
};
